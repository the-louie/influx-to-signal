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

## Deployment

### 1. Clone the repository

```bash
cd /docker
git clone <repo-url> temperature-bot
cd temperature-bot
```

For future updates, pull the latest changes and rebuild:

```bash
cd /docker/temperature-bot
git pull
docker compose build
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in all values:

| Variable | Description |
|:---------|:------------|
| `INFLUXDB_URL` | InfluxDB URL, e.g. `http://10.13.110.32:8086` |
| `INFLUXDB_TOKEN` | InfluxDB API token |
| `INFLUXDB_ORG` | InfluxDB organization name |
| `INFLUXDB_BUCKET` | Bucket to query, e.g. `home_assistant` |
| `MEASUREMENT` | Flux measurement filter, e.g. `http_listener_v2` |
| `FIELD` | Flux field filter, e.g. `temperature` |
| `DEVICE_ID` | Flux device_id tag filter, e.g. `gisebo-01` |
| `HOST_FILTER` | Flux host tag filter, e.g. `61781446e5e9` |
| `TZ_OFFSET_HOURS` | UTC offset for determining "start of yesterday" (default: `2` for CEST) |
| `SIGNAL_PROTOCOL` | `http` or `https` (default: `http`) |
| `SIGNAL_SERVICE` | signal-cli-rest-api host:port, e.g. `signal-api:8080` |
| `SIGNAL_PHONE_NUMBER` | Bot phone number, e.g. `+46701234567` |
| `SIGNAL_RECIPIENT` | Group ID or phone number to send to |

### 3. Find the Signal group ID

The bot sends messages via the [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api). To send to a group chat, you need the group's internal ID.

**Prerequisites:** The signal-cli-rest-api service must be running and linked to your phone number (see the [signal-cli-rest-api setup guide](https://github.com/bbernhard/signal-cli-rest-api#getting-started)).

List all groups the linked account is a member of:

```bash
curl -s http://<signal-api-host>:8080/v1/groups/<your-phone-number> | python3 -m json.tool
```

This returns a JSON array. Each group entry looks like:

```json
{
    "id": "group.OyZzqio1xDmYiLsQ1VsqRcUFOU4tK2TcECmYt2KeozHJwglMBHAPS7jlkrm=",
    "internal_id": "OyZzqio1xDmYiLsQ1VsqRcUFOU4tK2TcECmYt2KeozHJwglMBHAPS7jlkrm=",
    "name": "My Group Name",
    ...
}
```

Copy the `id` value (the one prefixed with `group.`) and set it as `SIGNAL_RECIPIENT` in your `.env`:

```
SIGNAL_RECIPIENT=group.OyZzqio1xDmYiLsQ1VsqRcUFOU4tK2TcECmYt2KeozHJwglMBHAPS7jlkrm=
```

To send to an individual contact instead of a group, use their phone number in E.164 format:

```
SIGNAL_RECIPIENT=+46701234567
```

### 4. Build the container

```bash
docker compose build
```

### 5. Test manually

Run the script once to verify the full pipeline works:

```bash
docker compose run --rm publisher
```

You should see log output confirming the InfluxDB query and Signal message delivery.

### 6. Schedule via host crontab

Open the host crontab:

```bash
crontab -e
```

Add an entry to trigger the bot on the desired schedule. For example, every day at 08:00:

```cron
0 8 * * * cd /docker/temperature-bot && docker compose run --rm publisher >> /var/log/temperature-bot.log 2>&1
```

Logs are appended to `/var/log/temperature-bot.log` for debugging.
