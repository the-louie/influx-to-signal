import os
import re
import sys
import logging
from datetime import datetime, timedelta, timezone

import requests
import influxdb_client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    """Read a required environment variable, raising a clear error if missing."""
    value = os.environ.get(name)
    if not value:
        log.error("Required environment variable %s is not set", name)
        sys.exit(1)
    return value


def _safe_identifier(value: str, name: str) -> str:
    """Validate that a value is safe for interpolation into a Flux query.

    Allows alphanumeric characters, hyphens, underscores, and dots.
    This prevents injection of Flux operators or string terminators.
    """
    if not re.match(r"^[A-Za-z0-9_\-\.]+$", value):
        log.error(
            "Environment variable %s contains unsafe characters: %s", name, value
        )
        sys.exit(1)
    return value


# InfluxDB config
INFLUXDB_URL = _require_env("INFLUXDB_URL")
INFLUXDB_TOKEN = _require_env("INFLUXDB_TOKEN")
INFLUXDB_ORG = _require_env("INFLUXDB_ORG")
INFLUXDB_BUCKET = _safe_identifier(_require_env("INFLUXDB_BUCKET"), "INFLUXDB_BUCKET")
MEASUREMENT = _safe_identifier(_require_env("MEASUREMENT"), "MEASUREMENT")
FIELD = _safe_identifier(_require_env("FIELD"), "FIELD")
DEVICE_ID = _safe_identifier(_require_env("DEVICE_ID"), "DEVICE_ID")
HOST_FILTER = _safe_identifier(_require_env("HOST_FILTER"), "HOST_FILTER")
TZ = timezone(timedelta(hours=float(os.environ.get("TZ_OFFSET_HOURS", "2"))))

# Signal config
SIGNAL_SERVICE = _require_env("SIGNAL_SERVICE")
SIGNAL_PHONE_NUMBER = _require_env("SIGNAL_PHONE_NUMBER")
SIGNAL_RECIPIENT = _require_env("SIGNAL_RECIPIENT")


def query_max_temperature() -> tuple[float, str]:
    """Query InfluxDB for the max temperature since the start of yesterday.

    Returns (temperature_value, timestamp_iso).
    """
    yesterday_start = datetime.now(TZ).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=1)
    range_start = yesterday_start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    query = f"""
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: {range_start})
  |> filter(fn: (r) => r["_measurement"] == "{MEASUREMENT}")
  |> filter(fn: (r) => r["_field"] == "{FIELD}")
  |> filter(fn: (r) => r["device_id"] == "{DEVICE_ID}")
  |> filter(fn: (r) => r["host"] == "{HOST_FILTER}")
  |> max()
  |> yield(name: "max_temperature")
"""
    client = influxdb_client.InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG,
    )
    try:
        result = client.query_api().query(org=INFLUXDB_ORG, query=query)
    finally:
        client.close()

    for table in result:
        for record in table.records:
            return record.get_value(), record.get_time().isoformat()

    raise RuntimeError("No temperature data returned from InfluxDB")


def send_signal_message(text: str) -> None:
    """Send a message via signal-cli-rest-api."""
    protocol = os.environ.get("SIGNAL_PROTOCOL", "http")
    url = f"{protocol}://{SIGNAL_SERVICE}/v2/send"
    payload = {
        "message": text,
        "number": SIGNAL_PHONE_NUMBER,
        "recipients": [SIGNAL_RECIPIENT],
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    log.info("Signal message sent (timestamp: %s)", resp.json().get("timestamp"))


def _is_within_active_period() -> bool:
    """Check if today falls within the configured ACTIVE_FROM / ACTIVE_TO window.

    Both dates are inclusive. If neither is set the bot is always active.
    """
    active_from = os.environ.get("ACTIVE_FROM", "")
    active_to = os.environ.get("ACTIVE_TO", "")

    if not active_from and not active_to:
        return True

    today = datetime.now(TZ).date()

    if active_from:
        start = datetime.strptime(active_from, "%Y-%m-%d").date()
        if today < start:
            return False

    if active_to:
        end = datetime.strptime(active_to, "%Y-%m-%d").date()
        if today > end:
            return False

    return True


def main() -> None:
    if not _is_within_active_period():
        log.info(
            "Outside active period (%s – %s), skipping.",
            os.environ.get("ACTIVE_FROM", "unset"),
            os.environ.get("ACTIVE_TO", "unset"),
        )
        return

    yesterday = (datetime.now(TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    log.info("Querying InfluxDB for max temperature (%s – %s)…", yesterday, today)

    try:
        temp, ts = query_max_temperature()
    except Exception:
        log.exception("Failed to query InfluxDB")
        sys.exit(1)

    min_temp = os.environ.get("MIN_TEMPERATURE", "")
    if min_temp and temp < float(min_temp):
        log.info(
            "Temperature %.1f°C is below minimum threshold %s°C, skipping.",
            temp, min_temp,
        )
        return

    local_time = datetime.fromisoformat(ts).astimezone(TZ).strftime("%H:%M")
    message = f"🌡️ Högsta temperatur ({yesterday} – {today}): {temp}°C (kl {local_time})"
    log.info("Sending: %s", message)

    try:
        send_signal_message(message)
    except Exception:
        log.exception("Failed to send Signal message")
        sys.exit(1)

    log.info("Done.")


if __name__ == "__main__":
    main()
