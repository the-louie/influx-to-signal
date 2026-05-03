# Temperature Bot

A Python bot that queries InfluxDB for the highest temperature since the start of yesterday (i.e. yesterday + today so far) and publishes it to a Signal group chat. Runs as a long-lived Docker stack with its own cron schedule alongside a bundled signal-cli-rest-api instance.

## Architecture

- **signal-api** — [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) container, provides the Signal messaging backend
- **publisher** — Python container with internal cron that queries InfluxDB and sends the result via signal-api
- All configuration via `.env` (copy `.env.example`)

## Dependencies

- `influxdb-client` — InfluxDB v2 Python client (Flux queries)
- `requests` — HTTP POST to signal-cli-rest-api `/v2/send` endpoint
- `python-dotenv` — loads `.env` file

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
| `SIGNAL_API_MODE` | signal-cli-rest-api mode: `normal`, `native`, `json-rpc`, or `json-rpc-native` (default: `json-rpc`) |
| `SIGNAL_API_PORT` | Host port to expose signal-cli-rest-api on (default: `8080`) |
| `SIGNAL_PROTOCOL` | `http` or `https` (default: `http`) |
| `SIGNAL_SERVICE` | signal-cli-rest-api host:port as seen by the publisher container (default: `signal-api:8080`) |
| `SIGNAL_PHONE_NUMBER` | Bot phone number in E.164 format, e.g. `+46701234567` |
| `SIGNAL_RECIPIENT` | Group ID or phone number to send to |
| `CRON_SCHEDULE` | Cron expression for the publish schedule (default: `0 10 * * *`, daily at 10:00) |
| `RUN_ON_STARTUP` | Set to `true` to send a message immediately when the container starts (default: `false`) |

### 3. Link your Signal account

The signal-cli-rest-api service must be linked to your Signal account before it can send messages. Start the stack in normal mode first:

```bash
# Override mode temporarily for linking
SIGNAL_API_MODE=normal docker compose up signal-api
```

Open the QR code link in your browser and scan it with your Signal app (Settings > Linked Devices > Link New Device):

```
http://localhost:8080/v1/qrcodelink?device_name=temperature-bot
```

Once linked, stop the service with `Ctrl+C`. The credentials are persisted in `./signal-cli-config/`.

### 4. Find the Signal group ID

With the service running, list all groups the linked account is a member of:

```bash
docker compose up -d signal-api
curl -s http://localhost:8080/v1/groups/<your-phone-number> | python3 -m json.tool
```

Each group entry looks like:

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

### 5. Build and start the stack

```bash
docker compose build
docker compose up -d
```

The publisher container runs cron in the foreground and will send the temperature message on the configured schedule (default: daily at 10:00).

### 6. Manually trigger a message

To send a message immediately without waiting for the next cron tick:

```bash
docker compose exec publisher python main.py
```

Or, if the stack is not running, use `run` instead:

```bash
docker compose run --rm publisher python main.py
```

## Logs

View live logs from both services:

```bash
docker compose logs -f
```

Publisher only:

```bash
docker compose logs -f publisher
```
