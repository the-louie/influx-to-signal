# Temperature Bot

See README.md for full project documentation.

Docker stack with two services: signal-cli-rest-api (Signal backend) and publisher (Python + cron). Queries InfluxDB for max temperature, sends to Signal group. Cron runs inside the publisher container (default 10:00 daily). Manual trigger via `docker compose exec publisher python main.py`.
