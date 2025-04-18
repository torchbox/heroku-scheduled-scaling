import concurrent.futures
import os
from traceback import print_exception

import sentry_sdk

from .scale import scale_app
from .utils import get_heroku_apps, get_heroku_client


def main() -> None:
    if sentry_dsn := os.environ.get("SENTRY_DSN"):
        sentry_sdk.init(sentry_dsn)

    apps = get_heroku_apps()

    requests_pool_size = (
        get_heroku_client()._session.adapters["https://"]._pool_connections  # type: ignore[attr-defined]
    )

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(
            int(os.environ.get("CONCURRENCY", requests_pool_size)), requests_pool_size
        )
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
