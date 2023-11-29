import logging
from datetime import datetime, time

from heroku3.models.app import App

from .schedule import parse_schedule

logging.basicConfig()
logger = logging.getLogger("heroku_scheduled_scaling")
logger.setLevel(logging.INFO)


def get_scale_for_app(app: App, now_time: time | None = None) -> int | None:
    if now_time is None:
        now_time = datetime.now().time()

    config = app.config().to_dict()

    if not (scaling_schedule := config.get("SCALING_SCHEDULE")):
        # No schedule
        return

    for schedule in parse_schedule(scaling_schedule):
        if schedule.covers(now_time):
            return schedule.scale


def scale_app(app: App, now_time: time | None = None):
    scale = get_scale_for_app(app, now_time)

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
