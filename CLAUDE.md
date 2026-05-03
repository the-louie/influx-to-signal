# Temperature Bot

A Python script that queries InfluxDB for the highest temperature since the start of yesterday (i.e. yesterday + today so far) and publishes it to a Signal group chat.

## Architecture

- **main.py** — single-file script: queries InfluxDB, sends result via signal-cli-rest-api
- Runs as a one-shot container, triggered by a host crontab entry
- All configuration via `.env` (copy `.env.example`)

## Dependencies

- `influxdb-client` — InfluxDB v2 Python client (Flux queries)
- `requests` — HTTP POST to signal-cli-rest-api `/v2/send` endpoint
- `python-dotenv` — loads `.env` file

Signal integration uses the [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) REST endpoint directly (not the signalbot framework, which is designed for long-running interactive bots).

## Build & Run

```bash
cp .env.example .env   # fill in real values
docker compose build
```

Manual test run:

```bash
docker compose run --rm publisher
```

## Scheduling

Add a host crontab entry to trigger the container on a schedule:

```cron
0 8 * * * cd /docker/temperature-bot && docker compose run --rm publisher >> /var/log/temperature-bot.log 2>&1
```

## Env Vars

See `.env.example` for all required settings. Key groups:

- `INFLUXDB_URL`, `INFLUXDB_TOKEN`, `INFLUXDB_ORG`, `INFLUXDB_BUCKET` — InfluxDB connection
- `MEASUREMENT`, `FIELD`, `DEVICE_ID`, `HOST_FILTER` — Flux query filters
- `TZ_OFFSET_HOURS` — UTC offset for determining "start of yesterday" (default: `2` for CEST)
- `SIGNAL_PROTOCOL`, `SIGNAL_SERVICE`, `SIGNAL_PHONE_NUMBER`, `SIGNAL_RECIPIENT` — Signal delivery
