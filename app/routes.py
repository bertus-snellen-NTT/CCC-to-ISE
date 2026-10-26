from pathlib import Path

import requests
from flask import Blueprint, current_app, jsonify, render_template

from app.services.catalyst_center import CatalystCenterClient, load_settings
from app.services.ise import ISEClient, load_ise_settings

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/api/assurance/mac-addresses")
def assurance_mac_addresses():
    config_path = _config_path()

    try:
        settings = load_settings(config_path)
    except (OSError, ValueError) as error:
        return jsonify(error=str(error)), 503

    try:
        mac_addresses = CatalystCenterClient(settings).get_assurance_mac_addresses()
    except (requests.RequestException, ValueError) as error:
        return jsonify(error=f"Catalyst Center request failed: {error}"), 502

    return jsonify(count=len(mac_addresses), macAddresses=mac_addresses)


@main.route("/api/ise/endpoints")
def ise_endpoints_for_assurance_clients():
    config_path = _config_path()

    try:
        catalyst_settings = load_settings(config_path)
        ise_settings = load_ise_settings(config_path)
    except (OSError, ValueError) as error:
        return jsonify(error=str(error)), 503

    try:
        mac_addresses = CatalystCenterClient(
            catalyst_settings
        ).get_assurance_mac_addresses()
    except (requests.RequestException, ValueError) as error:
        return jsonify(error=f"Catalyst Center request failed: {error}"), 502

    ise_client = ISEClient(ise_settings)
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
        return jsonify(error=f"ISE request failed: {error}"), 502

    found = [result for result in results if result["found"]]
    missing = [result["macAddress"] for result in results if not result["found"]]
    return jsonify(
        checked=len(results),
        foundCount=len(found),
        missingCount=len(missing),
        results=results,
        missingMacAddresses=missing,
    )


def _config_path() -> Path:
    config_path = Path(current_app.config["CATALYST_CENTER_CONFIG"])
    if not config_path.is_absolute():
        config_path = Path(current_app.root_path).parent / config_path
    return config_path
