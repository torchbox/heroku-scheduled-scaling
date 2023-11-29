import os

import heroku3
from heroku3.models.app import App


def get_apps_for_teams(heroku, teams):
    for team in teams:
        yield from heroku._get_resources(("teams", team, "apps"), App)


def get_heroku_client():
    return heroku3.from_key(os.environ["HEROKU_API_KEY"])


def get_heroku_apps():
    heroku = get_heroku_client()
    heroku_teams = (
        os.getenv("HEROKU_TEAMS").split(",") if "HEROKU_TEAMS" in os.environ else None
    )
    return (
        heroku.apps()
        if heroku_teams is None
        else list(get_apps_for_teams(heroku_teams))
    )
