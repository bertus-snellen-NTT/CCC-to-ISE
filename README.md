# Catalyst Center to ISE Endpoint Check

A Flask app that retrieves distinct client MAC addresses from Cisco Catalyst Center Assurance.

## Requirements

- Python 3.9 or newer
- pip
- A Cisco Catalyst Center account with permission to read client data
- A Cisco ISE account with ERS API access enabled and permission to read endpoints

## Setup

Create and activate a virtual environment, then install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Update the local `config.ini` with your Catalyst Center host and credentials. If it does not exist (for example, after a fresh clone), copy `config.example.ini` to `config.ini` first. `config.ini` is ignored by Git; do not commit credentials.

```ini
[catalyst_center]
host = https://your-catalyst-center-host
username = your_username
password = your_password
verify_tls = true
page_size = 500
request_timeout_seconds = 60

[ise]
host = https://your-ise-host:9060
username = your_ers_username
password = your_ers_password
verify_tls = true
request_timeout_seconds = 60
```

Leave both `verify_tls` values set to `true` when using trusted certificates. If Catalyst Center or ISE uses a private CA, add that CA to the machine's trust store rather than disabling certificate verification.

The Catalyst Center `request_timeout_seconds` sets the timeout for authentication and every clients page. The ISE section uses the ERS API base address (typically HTTPS port 9060); its `request_timeout_seconds` applies to each endpoint lookup. Enable ERS API access for the ISE account and fill in these values in the ignored local `config.ini`.

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

## Run

```powershell
python run.py
```

Open <http://127.0.0.1:5000> in your browser. The development server runs with debug mode enabled; do not use it as a production server.

## API

`GET /api/assurance/mac-addresses` authenticates with Catalyst Center and retrieves clients from `/dna/data/api/v1/clients`, paging through the available results with one-based offsets. The request includes the current epoch timestamp in milliseconds, as required by the data API, and reuses it across pages. The JSON response contains a sorted, deduplicated `macAddresses` array and its `count`:

```json
{
  "count": 2,
  "macAddresses": ["00:11:22:33:44:55", "aa:bb:cc:dd:ee:ff"]
}
```

The result reflects client records available from the Catalyst Center clients endpoint for your account; it is not a promise of an unlimited historical inventory. Configuration errors return HTTP 503 and Catalyst Center/API failures return HTTP 502.

`GET /api/ise/endpoints` retrieves the current Catalyst Center Assurance MAC addresses, then checks each address against the ISE ERS endpoint API. It returns per-MAC lookup results, endpoint resources found by ISE, and a list of MAC addresses with no matching endpoint. The request uses ISE's `mac.EQ` filter and requires valid ISE ERS credentials. Configuration errors return HTTP 503; CATC or ISE API errors return HTTP 502.

## Project structure

```text
.
├── app/
│   ├── __init__.py
│   ├── routes.py
│   ├── services/
│   │   ├── catalyst_center.py
│   │   └── ise.py
│   ├── static/
│   │   └── css/
│   │       └── style.css
│   └── templates/
│       └── index.html
├── config.example.ini
├── requirements.txt
└── run.py
```

## Keeping this README up to date

Update this README whenever project changes affect setup, dependencies, commands, routes, or the project structure. Keep the structure section and instructions aligned with the actual code so the README remains a reliable guide for new contributors.
