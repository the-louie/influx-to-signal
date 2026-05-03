# TODO

## Add a non-root USER to the Dockerfile

**Severity:** Low
**Files:** Dockerfile

Now that cron has been removed, there is no technical blocker preventing the container
from running as a non-root user. Add a `RUN useradd` and `USER` directive so the
Python process does not run as root.
