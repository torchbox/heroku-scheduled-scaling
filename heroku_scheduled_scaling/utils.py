import os
import zoneinfo
from datetime import datetime
from typing import Iterable

import heroku3
from heroku3.models.app import App


def get_apps_for_teams(heroku: heroku3.core.Heroku, teams: list[str]) -> Iterable[App]:
    for team in teams:
        yield from heroku._get_resources(  # type:ignore[attr-defined]
            ("teams", team, "apps"), App
        )


def get_heroku_client() -> heroku3.core.Heroku:
    return heroku3.from_key(os.environ["HEROKU_API_KEY"])


def get_heroku_apps() -> list[App]:
    heroku = get_heroku_client()

    heroku_teams = os.environ.get("HEROKU_TEAMS", "").split(",")
    return (
        heroku.apps()
        if heroku_teams is None
        else list(get_apps_for_teams(heroku, heroku_teams))
    )


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
