# Heroku Scheduled Scaling

[![Main](https://github.com/torchbox/heroku-scheduled-scaling/actions/workflows/ci.yml/badge.svg)](https://github.com/torchbox/heroku-scheduled-scaling/actions/workflows/ci.yml)

Scale Heroku dynos based on a schedule.

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
- `SCHEDULE_TEMPLATE_*` (optional): Pre-defined scaling templates (see [below](#scaling-templates)).
- `SCALING_SCHEDULE_TIMEZONE` (optional): Timezone for scaling schedules (see [below](#schedule)).

All other configuration is handled on the app you wish to scale.

## Usage

### Schedule

The schedule is read from a `$SCALING_SCHEDULE` environment variable configured in each application.

The schedule format is a _relatively_ simple, human-readable format, which notes time ranges alongside dyno counts. If there are gaps in the schedule, no changes will be made. If parts of the schedule overlap, the first matching rule will be used.

Example: `0900-1700:2;1700-1900:1;1900-0900:0`:

- Between 9am and 5pm, 2 dynos will be running
- Between 5pm and 7pm, 1 dyno will be running
- Between 7pm and 9am, no dynos will be running (and maintenance mode will be enabled)

Example: `0830-1800:1;0000-2359:0`:

- Between 8:30am and 6pm, 1 dyno will be running
- Everywhen else, no dynos will be running

Example: `0-4(0830-1800:1;0000-2359:0);5-6(1200-2359:1;0000-2359:0)`:

- Between 8:30am and 6pm on weekdays (`0` = Monday, `4` = Friday), 1 dyno will be running
- Between 12pm and 11:59pm on weekends, 1 dyno will be running
- Everywhen else, no dynos will be running

To review which apps have a scaling config set, try [`heroku-audit`](https://github.com/torchbox/heroku-audit).

### Timezones

By default, times are in UTC. To override the timezone for all apps, set `$SCALING_SCHEDULE_TIMEZONE` on `heroku-scheduled-scaling`. To override the timezone per app, set `$SCALING_SCHEDULE_TIMEZONE` on the app itself. Valid values are any IANA timezone (eg `Europe/London`).


### Scaling processes separately

By default, `SCALING_SCHEDULE` will scale all processes together. To scale a specific process, define its own schedule (eg `$SCALING_SCHEDULE_WEB`). If a process doesn't have a specific schedule, the global `$SCALING_SCHEDULE` is used. If that is not defined, no changes are made (this allows scaling a `worker` process without affecting `web`).

### Temporarily disable scaling

To disable scaling, set `$SCALING_SCHEDULE_DISABLE` to a true-looking value.

Alternatively, it can be set to an ISO-8601 timestamp (eg `2023-11-29T16:15:14+00:00`). Up until this time, no scheduling changes will be made. Afterwards, the value will be automatically removed scheduling will continue. This can be useful as part of other automations. If the UTC offset is omitted (eg `2023-11-29T16:15:14`), the timezone of the app will be used (see [Timezones](#timezones)).

### Scaling templates

It's often necessary to define a single scaling schedule, and reuse it between apps. This is possible with templates.

For example, define on `heroku-scheduled-scaling`:

```
SCHEDULE_TEMPLATE_OFFICE_HOURS=0900-1700:2;1700-1900:1;1900-0900:0
```

And then reuse it on the given app:

```
SCALING_SCHEDULE=OFFICE_HOURS
```
