import configparser
import time
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass(frozen=True)
class CatalystCenterSettings:
    host: str
    username: str
    password: str
    verify_tls: bool
    page_size: int
    request_timeout_seconds: int


def load_settings(path: Path) -> CatalystCenterSettings:
    if not path.is_file():
        raise FileNotFoundError(
            f"Catalyst Center config not found: {path}. "
            "Copy config.example.ini to config.ini and fill in your credentials."
        )

    config = configparser.ConfigParser()
    if not config.read(path):
        raise ValueError(f"Could not read Catalyst Center config: {path}")

    try:
        section = config["catalyst_center"]
        host = section["host"].strip().rstrip("/")
        username = section["username"].strip()
        password = section["password"]
        verify_tls = section.getboolean("verify_tls", fallback=True)
        page_size = section.getint("page_size", fallback=500)
        request_timeout_seconds = section.getint(
            "request_timeout_seconds", fallback=60
        )
    except (KeyError, ValueError) as error:
        raise ValueError(
            f"Invalid Catalyst Center config in {path}: {error}"
        ) from error

    if not host or not username or not password:
        raise ValueError(
            "Catalyst Center config requires non-empty host, username, and password."
        )
    if page_size < 1:
        raise ValueError("Catalyst Center page_size must be a positive integer.")
    if request_timeout_seconds < 1:
        raise ValueError("Catalyst Center request_timeout_seconds must be positive.")

    if not host.startswith(("https://", "http://")):
        host = f"https://{host}"
    if not host.startswith("https://"):
        raise ValueError("Catalyst Center host must use HTTPS.")

    return CatalystCenterSettings(
        host=host,
        username=username,
        password=password,
        verify_tls=verify_tls,
        page_size=page_size,
        request_timeout_seconds=request_timeout_seconds,
    )


class CatalystCenterClient:
    def __init__(self, settings: CatalystCenterSettings):
        self.settings = settings
        self.session = requests.Session()
        self.session.verify = settings.verify_tls
        self.session.headers.update({"Accept": "application/json"})

    def get_assurance_clients(self) -> list[dict]:
        self._authenticate()
        assurance_clients = []
        offset = 1
        timestamp = int(time.time() * 1000)

        while True:
            response = self.session.get(
                f"{self.settings.host}/dna/data/api/v1/clients",
                params={
                    "timestamp": timestamp,
                    "limit": self.settings.page_size,
                    "offset": offset,
                    "type": "Wired",
                },
                timeout=self.settings.request_timeout_seconds,
            )
            self._raise_for_api_error(response)
            payload = response.json()
            clients = payload.get("response") if isinstance(payload, dict) else None
            if not isinstance(clients, list):
                raise ValueError(
                    "Unexpected Catalyst Center clients response: "
                    "expected a response list."
                )

            for client in clients:
                if isinstance(client, dict):
                    assurance_clients.append(client)

            if len(clients) < self.settings.page_size:
                break
            offset += len(clients)

        return assurance_clients

    def get_assurance_mac_addresses(self) -> list[str]:
        mac_addresses = {
            client["macAddress"].strip().lower()
            for client in self.get_assurance_clients()
            if isinstance(client.get("macAddress"), str)
            and client["macAddress"].strip()
        }
        return sorted(mac_addresses)

    @staticmethod
    def _raise_for_api_error(response: requests.Response) -> None:
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            detail = response.text.strip()
            if detail:
                detail = detail[:1000]
                raise requests.HTTPError(
                    f"{error} - Catalyst Center response: {detail}",
                    response=response,
                ) from error
            raise

    def _authenticate(self) -> None:
        response = self.session.post(
            f"{self.settings.host}/dna/system/api/v1/auth/token",
            auth=(self.settings.username, self.settings.password),
            timeout=self.settings.request_timeout_seconds,
        )
        self._raise_for_api_error(response)
        payload = response.json()
        token = payload.get("Token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            raise ValueError(
                "Unexpected Catalyst Center authentication response: "
                "token was not provided."
            )
        self.session.headers["X-Auth-Token"] = token
