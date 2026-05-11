import asyncio
import os
from traceback import print_exception

import aiohttp
import sentry_sdk

from .scale import scale_app
from .utils import get_heroku_apps


async def main() -> None:
    if sentry_dsn := os.environ.get("SENTRY_DSN"):
        sentry_sdk.init(sentry_dsn)

    client = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=5),
        base_url="https://api.heroku.com/",
        auth=aiohttp.BasicAuth("", os.environ["HEROKU_API_KEY"]),
        headers={"Accept": "application/vnd.heroku+json; version=3"},
    )

    apps = await get_heroku_apps(client)

    tasks = []
    async with asyncio.TaskGroup() as tg:
        for app in apps:
            tasks.append(tg.create_task(scale_app(client, app)))

    for task in tasks:
        if exception := task.exception():
            sentry_sdk.capture_exception(exception)
            print_exception(exception)


if __name__ == "__main__":
    asyncio.run(main())
