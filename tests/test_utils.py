from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from heroku_scheduled_scaling import utils


def test_get_zone_info() -> None:
    assert (
        utils.get_zone_info("Europe/London").key  # type:ignore[union-attr]
        == "Europe/London"
    )
    assert utils.get_zone_info("UTC").key == "UTC"  # type:ignore[union-attr]


@pytest.mark.parametrize("zone_key", ["Invalid", "Space/Earth", ""])
def test_get_invalid_zone_info(zone_key: str) -> None:
    assert utils.get_zone_info(zone_key) is None


def test_naive_datetime() -> None:
    assert utils.is_naive(datetime.now())
    assert not utils.is_naive(datetime.now().astimezone(ZoneInfo("UTC")))
    assert not utils.is_naive(datetime.now().astimezone(ZoneInfo("Europe/London")))
    assert not utils.is_naive(
        datetime.now().astimezone(ZoneInfo("America/Los_Angeles"))
    )
