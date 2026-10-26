import configparser
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass(frozen=True)
class ISESettings:
    host: str
    username: str
    password: str
    verify_tls: bool
    request_timeout_seconds: int


def load_ise_settings(path: Path) -> ISESettings:
    if not path.is_file():
        raise FileNotFoundError(
            f"ISE config not found: {path}. "
            "Copy config.example.ini to config.ini and add your ISE settings."
        )

    config = configparser.ConfigParser()
    if not config.read(path):
        raise ValueError(f"Could not read ISE config: {path}")

    try:
        section = config["ise"]
        host = section["host"].strip().rstrip("/")
        username = section["username"].strip()
        password = section["password"]
        verify_tls = section.getboolean("verify_tls", fallback=True)
        request_timeout_seconds = section.getint(
            "request_timeout_seconds", fallback=60
        )
    except (KeyError, ValueError) as error:
        raise ValueError(f"Invalid ISE config in {path}: {error}") from error

    if not host or not username or not password:
        raise ValueError(
            "ISE config requires non-empty host, username, and password."
        )
    if not host.startswith(("https://", "http://")):
        host = f"https://{host}"
    if not host.startswith("https://"):
        raise ValueError("ISE host must use HTTPS.")
    if request_timeout_seconds < 1:
        raise ValueError("ISE request_timeout_seconds must be positive.")

    return ISESettings(
        host=host,
        username=username,
        password=password,
        verify_tls=verify_tls,
        request_timeout_seconds=request_timeout_seconds,
    )


class ISEClient:
    def __init__(self, settings: ISESettings):
        self.settings = settings
        self.session = requests.Session()
        self.session.auth = (settings.username, settings.password)
        self.session.verify = settings.verify_tls
        self.session.headers.update({"Accept": "application/json"})

    def find_endpoints_by_mac(self, mac_address: str) -> list[dict]:
        response = self.session.get(
            f"{self.settings.host}/ers/config/endpoint",
            params={"filter": f"mac.EQ.{mac_address}"},
            timeout=self.settings.request_timeout_seconds,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            detail = response.text.strip()
            if detail:
                raise requests.HTTPError(
                    f"{error} - ISE response: {detail[:1000]}",
                    response=response,
                ) from error
            raise

        payload = response.json()
        search_result = (
            payload.get("SearchResult") if isinstance(payload, dict) else None
        )
        if not isinstance(search_result, dict):
            raise ValueError(
                "Unexpected ISE endpoint response: expected a SearchResult object."
            )

        endpoints = search_result.get("resources", [])
        if not isinstance(endpoints, list):
            raise ValueError(
                "Unexpected ISE endpoint response: expected a resources list."
            )
        return [endpoint for endpoint in endpoints if isinstance(endpoint, dict)]
