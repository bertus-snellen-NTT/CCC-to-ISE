import time
from datetime import datetime, timezone
from typing import Any

import requests


def tracked_request(
    session: requests.Session,
    method: str,
    url: str,
    activity_calls: list[dict],
    path: str,
    **kwargs: Any,
) -> requests.Response:
    started_at = time.perf_counter()
    result = "Request failed"

    try:
        response = getattr(session, method)(url, **kwargs)
        result = (
            f"HTTP {response.status_code} failed"
            if response.status_code >= 400
            else f"HTTP {response.status_code}"
        )
        return response
    except requests.RequestException as error:
        result = f"Failed: {type(error).__name__}"
        raise
    finally:
        activity_calls.append(
            {
                "method": method.upper(),
                "path": path,
                "result": result,
                "duration": (time.perf_counter() - started_at) * 1000,
                "completedAt": datetime.now(timezone.utc).isoformat(
                    timespec="milliseconds"
                ),
            }
        )
