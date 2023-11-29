# Heroku Scheduled Scaling

Scale Heroku `web` dynos based on a schedule.

## Deployment

The easiest deployment for this is within Heroku. Deploy the repository to Heroku (using the "container" runtime), stop the web dyno, and use Heroku Scheduler to run `heroku-scheduled-scaling` every 10 minutes (or less frequently if you prefer).

To install manually (requires [Poetry](https://python-poetry.org/)):

```
poetry install
poetry run heroku-scheduled-scaling
```

### Configuration

- `HEROKU_API_KEY`: Heroku API key - used for authentication. The corresponding user must have the ability to scale and read environment variables for apps.
- `HEROKU_TEAMS`: Comma-separated list of Heroku teams to operate on. All others are ignored, regardless of whether they have a schedule.
- `SENTRY_DSN` (optional): Sentry integration (for error reporting)

## Usage

### Schedule

The schedule is read from a `$SCALING_SCHEDULE` environment variable configured in each application.

The schedule format is a simple, human-readable format, which notes time ranges alongside dyno counts. If there are gaps in the schedule, no changes will be made. If parts of the schedule overlap, the first matching rule will be used.

Example: `0900-1700:2;1700-1900:1;1900-0900:0`.

This means:

- Between 9am and 5pm, 2 dynos will be running
- Between 5pm and 7pm, 1 dyno will be running
- Between 7pm and 9am, no dynos will be running (and maintenance mode will be enabled)

Times are based on the time of the server (Heroku's use UTC).

### Temporarily disable scaling

To disable scaling, set `$SCALING_SCHEDULE_DISABLE` to a true-looking value.

Alternatively, it can be set to an ISO-8601 timestamp (eg `2023-11-29T16:15:14+00:00`). Up until this time, no scheduling changes will be made. Afterwards, the value will be automatically removed scheduling will continue. This can be useful as part of other automations.
