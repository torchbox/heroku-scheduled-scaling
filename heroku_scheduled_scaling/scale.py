import logging
import os
from datetime import datetime

from heroku3.models.app import App
from zoneinfo import ZoneInfo

from .schedule import parse_schedule
from .utils import get_zone_info, is_naive

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


def get_template_schedule(scaling_schedule: str) -> str:
    if templated_scaling_schedule := os.environ.get(
        "SCHEDULE_TEMPLATE_" + scaling_schedule
    ):
        return get_template_schedule(templated_scaling_schedule)

    return scaling_schedule


def get_timezone_for_app(app_config: dict) -> ZoneInfo:
    """
    Get timezone from app, then from us, falling back to UTC
    """
    if app_timezone := get_zone_info(app_config.get("SCALING_SCHEDULE_TIMEZONE", "")):
        return app_timezone

    elif default_timezone := get_zone_info(
        os.environ.get("SCALING_SCHEDULE_TIMEZONE", "")
    ):
        return default_timezone

    return ZoneInfo("UTC")


def get_scale_for_app(app: App, process: str = "web") -> int | None:
    """
    Get the expected scale for an app.

    `None` signifies "Don't change anything".
    """
    if process == "release":
        return None

    config = app.config()

    # Also grab as dict, as `ConfigVars` doesn't implement `.get`
    config_dict = config.to_dict()

    timezone = get_timezone_for_app(config_dict)
    now = datetime.now().astimezone(timezone)

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

        # If the disabled date is naive, assume it's in the timezone of the app
        if is_naive(disabled_until_date):
            disabled_until_date = disabled_until_date.replace(tzinfo=timezone)

        if disabled_until_date > now:
            # Still temporarily disabled
            return None

        if disabled_until_date <= now:
            # Unset the expired schedule
            config.update({"SCALING_SCHEDULE_DISABLE": None})

    # If the schedule is a template, resolve it
    scaling_schedule = get_template_schedule(scaling_schedule)

    for schedule in parse_schedule(scaling_schedule):
        if schedule.covers(now):
            return schedule.scale

    logger.error(
        "Unable to parse schedule for %s (%s): %s", app.name, process, scaling_schedule
    )

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
