from pathlib import Path

import requests
from flask import Blueprint, current_app, jsonify, render_template

from app.services.catalyst_center import CatalystCenterClient, load_settings
from app.services.ise import ISEClient, load_ise_settings
from app.services.storage import get_catalyst_center_data, save_catalyst_center_run

main = Blueprint("main", __name__)


@main.route("/")
def index():
    data = get_catalyst_center_data(_database_path())
    return render_template("index.html", **data)


@main.route("/api/assurance/clients", methods=["POST"])
def refresh_assurance_clients():
    activity_calls = []
    try:
        run = _fetch_and_store_clients(_config_path(), activity_calls)
    except (OSError, ValueError) as error:
        return jsonify(error=str(error), activityCalls=activity_calls), 503
    except requests.RequestException as error:
        return (
            jsonify(
                error=f"Catalyst Center request failed: {error}",
                activityCalls=activity_calls,
            ),
            502,
        )

    return jsonify(run=run, activityCalls=activity_calls), 201


@main.route("/api/assurance/mac-addresses")
def assurance_mac_addresses():
    config_path = _config_path()
    activity_calls = []

    try:
        settings = load_settings(config_path)
    except (OSError, ValueError) as error:
        return jsonify(error=str(error)), 503

    try:
        clients = CatalystCenterClient(
            settings, activity_calls
        ).get_assurance_clients()
    except (requests.RequestException, ValueError) as error:
        return (
            jsonify(
                error=f"Catalyst Center request failed: {error}",
                activityCalls=activity_calls,
            ),
            502,
        )

    save_catalyst_center_run(_database_path(), clients)
    mac_addresses = _mac_addresses(clients)
    return jsonify(
        count=len(mac_addresses),
        macAddresses=mac_addresses,
        activityCalls=activity_calls,
    )


@main.route("/api/ise/endpoints")
def ise_endpoints_for_assurance_clients():
    config_path = _config_path()
    activity_calls = []

    try:
        catalyst_settings = load_settings(config_path)
        ise_settings = load_ise_settings(config_path)
    except (OSError, ValueError) as error:
        return jsonify(error=str(error)), 503

    try:
        clients = CatalystCenterClient(
            catalyst_settings, activity_calls
        ).get_assurance_clients()
    except (requests.RequestException, ValueError) as error:
        return (
            jsonify(
                error=f"Catalyst Center request failed: {error}",
                activityCalls=activity_calls,
            ),
            502,
        )

    save_catalyst_center_run(_database_path(), clients)
    mac_addresses = _mac_addresses(clients)
    ise_client = ISEClient(ise_settings, activity_calls)
    results = []
    try:
        for mac_address in mac_addresses:
            endpoints = ise_client.find_endpoints_by_mac(mac_address)
            results.append(
                {
                    "macAddress": mac_address,
                    "found": bool(endpoints),
                    "endpoints": endpoints,
                }
            )
    except (requests.RequestException, ValueError) as error:
        return (
            jsonify(
                error=f"ISE request failed: {error}",
                activityCalls=activity_calls,
            ),
            502,
        )

    found = [result for result in results if result["found"]]
    missing = [result["macAddress"] for result in results if not result["found"]]
    return jsonify(
        checked=len(results),
        foundCount=len(found),
        missingCount=len(missing),
        results=results,
        missingMacAddresses=missing,
        activityCalls=activity_calls,
    )


def _config_path() -> Path:
    config_path = Path(current_app.config["CATALYST_CENTER_CONFIG"])
    if not config_path.is_absolute():
        config_path = Path(current_app.root_path).parent / config_path
    return config_path


def _database_path() -> Path:
    return Path(current_app.config["DATABASE_PATH"])


def _fetch_and_store_clients(config_path: Path, activity_calls: list[dict]) -> dict:
    settings = load_settings(config_path)
    clients = CatalystCenterClient(settings, activity_calls).get_assurance_clients()
    return save_catalyst_center_run(_database_path(), clients)


def _mac_addresses(clients: list[dict]) -> list[str]:
    return sorted(
        {
            mac_address.strip().lower()
            for client in clients
            if isinstance((mac_address := client.get("macAddress")), str)
            and mac_address.strip()
        }
    )
