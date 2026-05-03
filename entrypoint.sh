#!/bin/sh
set -e

# Validate CRON_SCHEDULE against a strict pattern to prevent injection.
# Accepts standard 5-field cron expressions (digits, commas, slashes, hyphens, asterisks).
CRON_SCHEDULE="${CRON_SCHEDULE:-0 10 * * *}"
if ! echo "${CRON_SCHEDULE}" | grep -Eq '^([0-9*/,\-]+[[:space:]]+){4}[0-9*/,\-]+$'; then
    echo "ERROR: CRON_SCHEDULE contains invalid characters: ${CRON_SCHEDULE}" >&2
    exit 1
fi

# Write env vars in a shell-sourceable format.
# Restrict file permissions so only root can read the secrets.
printenv | grep -Ev '^(HOME|PATH|HOSTNAME|TERM|SHLVL|PWD|_)=' | \
    sed "s/'/'\\\\''/g; s/=\(.*\)/='\1'/" > /app/.env.cron
chmod 0600 /app/.env.cron

# Create the cron entry, sourcing the env file safely before running the script.
echo "${CRON_SCHEDULE} . /app/.env.cron && cd /app && /usr/local/bin/python main.py >> /proc/1/fd/1 2>> /proc/1/fd/2" \
    > /etc/cron.d/temperature-bot
chmod 0644 /etc/cron.d/temperature-bot
crontab /etc/cron.d/temperature-bot

echo "Cron scheduled: ${CRON_SCHEDULE}"

# Run once immediately if requested
if [ "${RUN_ON_STARTUP:-false}" = "true" ]; then
    echo "Running once on startup…"
    /usr/local/bin/python main.py
fi

echo "Starting crond…"
exec cron -f
