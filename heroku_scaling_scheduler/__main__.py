import concurrent.futures
import logging
import os
from datetime import datetime, time
from traceback import print_exception

import sentry_sdk
from heroku3.models.app import App

from .schedule import parse_schedule
from .utils import get_heroku_apps, get_heroku_client

logging.basicConfig()
logger = logging.getLogger("heroku_scaling_scheduler")
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


def scale_app(app: App):
    scale = get_scale_for_app(app)

    if scale is None:
        return

    web_formation = app.process_formation()["web"]
    if web_formation.quantity == scale:
        logger.info("App %s is already at correct scale: %d", app.name, scale)
        return

    # Basic apps don't support multiple dynos
    if scale > 1 and web_formation.size == "Basic":
        logger.warning("Scaling Basic app to Standard-1X to meet schedule.")
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


def main():
    if sentry_dsn := os.environ.get("SENTRY_DSN"):
        sentry_sdk.init(sentry_dsn)

    apps = get_heroku_apps()

    requests_pool_size = (
        get_heroku_client()._session.adapters["https://"]._pool_connections
    )

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=requests_pool_size
    ) as executor:
        futures = []
        for app in apps:
            futures.append(executor.submit(scale_app, app))

        for future in concurrent.futures.as_completed(futures):
            if exception := future.exception():
                sentry_sdk.capture_exception(exception)
                print_exception(exception)


if __name__ == "__main__":
    main()
