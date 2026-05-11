import os
import zoneinfo
from datetime import datetime

from aiohttp import ClientSession


async def get_apps_for_teams(client: ClientSession, teams: list[str]) -> list[dict]:
    apps = []
    for team in teams:
        response = await client.get(f"teams/{team}/apps")
        response.raise_for_status()
        apps.extend(await response.json())
    return apps


async def get_heroku_apps(client: ClientSession) -> list[dict]:
    if heroku_teams := os.environ.get("HEROKU_TEAMS", "").split(","):
        return await get_apps_for_teams(client, heroku_teams)
    else:
        # NB: Pagination isn't currently handled, but the default page size is 200.
        response = await client.get("apps")

        response.raise_for_status()

        return await response.json()  # type: ignore[no-any-return]


async def get_app_formation(client: ClientSession, app_name: str) -> dict[str, dict]:
    response = await client.get(f"apps/{app_name}/formation")

    response.raise_for_status()

    return {f["type"]: f for f in await response.json()}


def get_zone_info(key: str) -> zoneinfo.ZoneInfo | None:
    """
    Attempt to retrive the `ZoneInfo` for a given timezone, or `None`
    if the input is invalid / zone doesn't exisxt
    """
    try:
        return zoneinfo.ZoneInfo(key)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return None


def is_naive(dt: datetime) -> bool:
    """
    Determine whether the provided datetime is naive (doesn't contain a timezone).
    """
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None


async def get_app_config(client: ClientSession, app_name: str) -> dict:
    response = await client.get(f"apps/{app_name}/config-vars")

    response.raise_for_status()

    return await response.json()  # type: ignore[no-any-return]


async def update_app_config(
    client: ClientSession, app_name: str, new_config: dict
) -> None:
    response = await client.patch(
        f"apps/{app_name}/config-vars",
        json=new_config,
    )

    response.raise_for_status()


async def batch_scale_formation(
    client: ClientSession, app_name: str, formation: dict[str, int]
) -> None:
    updates = [{"type": k, "quantity": v} for k, v in formation.items()]
    response = await client.patch(
        f"apps/{app_name}/formation", json={"updates": updates}
    )

    response.raise_for_status()


async def set_app_maintenance(
    client: ClientSession, app_name: str, maintenance: bool
) -> None:
    response = await client.patch(f"apps/{app_name}", json={"maintenance": maintenance})

    response.raise_for_status()
