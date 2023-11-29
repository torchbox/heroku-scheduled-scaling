import logging
from datetime import datetime

from heroku3.models.app import App

from .schedule import parse_schedule

logging.basicConfig()
logger = logging.getLogger("heroku_scheduled_scaling")
logger.setLevel(logging.INFO)

BOOLEAN_TRUE_STRINGS = {"true", "on", "ok", "y", "yes", "1"}


def get_scale_for_app(app: App, now: datetime | None = None) -> int | None:
    """
    Get the expected scale for an app.

    `None` signifies "Don't change anything".
    """
    if now is None:
        now = datetime.now()

    config = app.config()

    # Also grab as dict, as `ConfigVars` doesn't implement `.get`
    config_dict = config.to_dict()

    if not (scaling_schedule := config_dict.get("SCALING_SCHEDULE")):
        # No schedule
        return

    scaling_disabled = config_dict.get("SCALING_SCHEDULE_DISABLE", "")
    if scaling_disabled:
        if scaling_disabled.lower() in BOOLEAN_TRUE_STRINGS:
            # Scheduling temporarily disabled - don't do anything
            return

        try:
            disabled_until_date = datetime.fromisoformat(scaling_disabled)
        except ValueError:
            logger.exception("Unable to parse $SCALING_SCHEDULE_DISABLE")
            return  # err on the side of caution - do nothing.

        if disabled_until_date > now:
            # Still temporarily disabled
            return

        if disabled_until_date <= now:
            # Unset the expired schedule
            config.update({"SCALING_SCHEDULE_DISABLE": None})

    now_time = now.time()
    for schedule in parse_schedule(scaling_schedule):
        if schedule.covers(now_time):
            return schedule.scale


def scale_app(app: App, now: datetime | None = None):
    scale = get_scale_for_app(app, now)

    if scale is None:
        return

    web_formation = app.process_formation()["web"]
    if web_formation.quantity == scale:
        logger.info("App %s is already at correct scale: %d", app.name, scale)
        return

    # Basic apps don't support multiple dynos
    if scale > 1 and web_formation.size == "Basic":
        logger.warning(
            "Scaling %s from Basic to Standard-1X to meet schedule.", app.name
        )
        new_size = "Standard-1X"
    else:
        new_size = None

    logger.info(
        "Scaling app %s to %d dynos (from %d)", app.name, scale, web_formation.quantity
    )
    web_formation.update(size=new_size, quantity=scale)

    # For a better experience, enable maintenance mode for apps scaled to 0
    if scale == 0 and not app.maintenance:
        logger.info("Enabling maintenance mode for %s", app.name)
        app.enable_maintenance_mode()
    elif scale and app.maintenance:
        # NOTE: This can result in maintenance mode being disabled unexpectedly, but
        # this will only happen on scaling boundaries.
        logger.info("Disabling maintenance mode for %s", app.name)
        app.disable_maintenance_mode()
