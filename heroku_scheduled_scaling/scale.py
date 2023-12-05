import logging
from datetime import datetime

from heroku3.models.app import App

from .schedule import parse_schedule

logging.basicConfig()
logger = logging.getLogger("heroku_scheduled_scaling")
logger.setLevel(logging.INFO)

BOOLEAN_TRUE_STRINGS = {"true", "on", "ok", "y", "yes", "1"}


def get_schedule_for_app(app_config: dict[str, str], process: str) -> str | None:
    if scaling_schedule := app_config.get(f"SCALING_SCHEDULE_{process.upper()}"):
        return scaling_schedule

    if scaling_schedule := app_config.get("SCALING_SCHEDULE"):
        return scaling_schedule

    return None


def get_scale_for_app(app: App, process: str = "web") -> int | None:
    """
    Get the expected scale for an app.

    `None` signifies "Don't change anything".
    """
    if process == "release":
        return None

    now = datetime.now()

    config = app.config()

    # Also grab as dict, as `ConfigVars` doesn't implement `.get`
    config_dict = config.to_dict()

    if not (scaling_schedule := get_schedule_for_app(config_dict, process)):
        # No schedule
        return None

    scaling_disabled = config_dict.get("SCALING_SCHEDULE_DISABLE", "")
    if scaling_disabled:
        if scaling_disabled.lower() in BOOLEAN_TRUE_STRINGS:
            # Scheduling temporarily disabled - don't do anything
            return None

        try:
            disabled_until_date = datetime.fromisoformat(scaling_disabled)
        except ValueError:
            logger.exception("Unable to parse $SCALING_SCHEDULE_DISABLE")
            return None  # err on the side of caution - do nothing.

        if disabled_until_date > now:
            # Still temporarily disabled
            return None

        if disabled_until_date <= now:
            # Unset the expired schedule
            config.update({"SCALING_SCHEDULE_DISABLE": None})

    now_time = now.time()
    for schedule in parse_schedule(scaling_schedule):
        if schedule.covers(now_time):
            return schedule.scale

    return None


def scale_app(app: App) -> None:
    formations = app.process_formation()

    process_scales = {
        formation.type: scale
        for formation in formations
        if (scale := get_scale_for_app(app, formation.type)) is not None
    }

    if not process_scales:
        return

    for process, scale in process_scales.items():
        if formations[process].quantity != scale:
            logger.info(
                "Scaling app %s (%s) to %d dynos (from %d)",
                app.name,
                process,
                scale,
                formations[process].quantity,
            )

    app.batch_scale_formation_processes(process_scales)

    if (web_scale := process_scales.get("web")) is not None:
        # For a better experience, enable maintenance mode for apps scaled to 0
        if web_scale == 0 and not app.maintenance:
            logger.info("Enabling maintenance mode for %s", app.name)
            app.enable_maintenance_mode()
        elif web_scale and app.maintenance:
            # NOTE: This can result in maintenance mode being disabled unexpectedly, but
            # this will only happen on scaling boundaries.
            logger.info("Disabling maintenance mode for %s", app.name)
            app.disable_maintenance_mode()
