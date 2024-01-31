from datetime import datetime, time
from typing import Any
from unittest.mock import MagicMock

import pytest
import time_machine
from heroku3.structures import KeyedListResource
from zoneinfo import ZoneInfo

from heroku_scheduled_scaling.scale import (
    BOOLEAN_TRUE_STRINGS,
    get_scale_for_app,
    scale_app,
)

UTC = ZoneInfo("UTC")


def now_time(time_component: time, timezone: ZoneInfo | None = UTC) -> datetime:
    return datetime.combine(datetime.now().date(), time_component).replace(
        tzinfo=timezone
    )


def test_gets_app_scale() -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {
        "SCALING_SCHEDULE": "0900-1700:2;1700-1900:1;1900-0900:0"
    }

    with time_machine.travel(now_time(time(12))):
        assert get_scale_for_app(app) == 2

    with time_machine.travel(now_time(time(22))):
        assert get_scale_for_app(app) == 0


def test_gets_app_scale_for_process() -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {
        "SCALING_SCHEDULE_WEB": "0900-1700:2;1700-1900:1;1900-0900:0",
        "SCALING_SCHEDULE_WORKER": "0000-2359:3",
    }

    with time_machine.travel(now_time(time(12))):
        assert get_scale_for_app(app) == 2
        assert get_scale_for_app(app, "web") == 2
        assert get_scale_for_app(app, "worker") == 3


def test_gets_app_scale_for_specific_process() -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {
        "SCALING_SCHEDULE": "0900-1700:2;1700-1900:1;1900-0900:0",
        "SCALING_SCHEDULE_WORKER": "0000-2359:3",
    }

    with time_machine.travel(now_time(time(12))):
        assert get_scale_for_app(app) == 2
        assert get_scale_for_app(app, "web") == 2
        assert get_scale_for_app(app, "worker") == 3


def test_no_scale_coverage() -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "0900-1700:2"}

    with time_machine.travel(now_time(time(12))):
        assert get_scale_for_app(app) == 2

    with time_machine.travel(now_time(time(22))):
        assert get_scale_for_app(app) is None


@pytest.mark.parametrize("truthy_value", BOOLEAN_TRUE_STRINGS)
def test_schedule_disabled(truthy_value: str) -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {
        "SCALING_SCHEDULE": "0900-1700:2",
        "SCALING_SCHEDULE_DISABLE": truthy_value,
    }

    with time_machine.travel(now_time(time(12))):
        assert get_scale_for_app(app) is None

    with time_machine.travel(now_time(time(22))):
        assert get_scale_for_app(app) is None


def test_schedule_temporarily_disabled() -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {
        "SCALING_SCHEDULE": "0900-1700:2",
        "SCALING_SCHEDULE_DISABLE": now_time(time(12)).isoformat(),
    }

    with time_machine.travel(now_time(time(10))):
        assert get_scale_for_app(app) is None

    app.config.return_value.update.assert_not_called()

    # The block has now expired
    with time_machine.travel(now_time(time(13))):
        assert get_scale_for_app(app) == 2

    app.config.return_value.update.assert_called_with(
        {"SCALING_SCHEDULE_DISABLE": None}
    )


def test_schedule_temporarily_disabled_naive() -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {
        "SCALING_SCHEDULE": "0900-1700:2",
        "SCALING_SCHEDULE_DISABLE": now_time(time(12), None).isoformat(),
    }

    with time_machine.travel(now_time(time(10))):
        assert get_scale_for_app(app) is None

    app.config.return_value.update.assert_not_called()

    # The block has now expired
    with time_machine.travel(now_time(time(13))):
        assert get_scale_for_app(app) == 2

    app.config.return_value.update.assert_called_with(
        {"SCALING_SCHEDULE_DISABLE": None}
    )


def test_schedule_temporarily_disabled_in_behind_timezone() -> None:
    app = MagicMock()

    timezone = ZoneInfo("America/Los_Angeles")

    app.config.return_value.to_dict.return_value = {
        "SCALING_SCHEDULE": "0000-2359:2",
        "SCALING_SCHEDULE_DISABLE": now_time(time(9), timezone).isoformat(),
        "SCALING_SCHEDULE_TIMEZONE": timezone.key,
    }

    with time_machine.travel(now_time(time(13))):
        assert get_scale_for_app(app) is None

    app.config.return_value.update.assert_not_called()

    with time_machine.travel(now_time(time(8), timezone)):
        assert get_scale_for_app(app) is None

    app.config.return_value.update.assert_not_called()

    # The block has now expired
    with time_machine.travel(now_time(time(19))):
        assert get_scale_for_app(app) == 2

    app.config.return_value.update.assert_called_with(
        {"SCALING_SCHEDULE_DISABLE": None}
    )

    with time_machine.travel(now_time(time(10), timezone)):
        assert get_scale_for_app(app) == 2


def test_schedule_temporarily_disabled_in_ahead_timezone() -> None:
    app = MagicMock()

    timezone = ZoneInfo("Australia/Perth")

    app.config.return_value.to_dict.return_value = {
        "SCALING_SCHEDULE": "0000-2359:2",
        "SCALING_SCHEDULE_DISABLE": now_time(time(20), timezone).isoformat(),
        "SCALING_SCHEDULE_TIMEZONE": timezone.key,
    }

    with time_machine.travel(now_time(time(10))):
        assert get_scale_for_app(app) is None

    app.config.return_value.update.assert_not_called()

    with time_machine.travel(now_time(time(19), timezone)):
        assert get_scale_for_app(app) is None

    app.config.return_value.update.assert_not_called()

    # The block has now expired
    with time_machine.travel(now_time(time(14))):
        assert get_scale_for_app(app) == 2

    app.config.return_value.update.assert_called_with(
        {"SCALING_SCHEDULE_DISABLE": None}
    )

    with time_machine.travel(now_time(time(21), timezone)):
        assert get_scale_for_app(app) == 2


def test_invalid_schedule() -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {
        "SCALING_SCHEDULE": "Not a schedule"
    }

    with time_machine.travel(now_time(time(12))):
        assert get_scale_for_app(app) is None

    with time_machine.travel(now_time(time(12))):
        assert get_scale_for_app(app) is None


def test_no_app_schedule() -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {}

    assert get_scale_for_app(app) is None


def test_gets_app_scale_template(monkeypatch: Any) -> None:
    monkeypatch.setenv(
        "SCHEDULE_TEMPLATE_WORKING_HOURS", "0900-1700:2;1700-1900:1;1900-0900:0"
    )

    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "WORKING_HOURS"}

    with time_machine.travel(now_time(time(12))):
        assert get_scale_for_app(app) == 2

    with time_machine.travel(now_time(time(22))):
        assert get_scale_for_app(app) == 0


def test_gets_app_scale_template_recursive(monkeypatch: Any) -> None:
    monkeypatch.setenv(
        "SCHEDULE_TEMPLATE_OFFICE_HOURS", "0900-1700:2;1700-1900:1;1900-0900:0"
    )
    monkeypatch.setenv("SCHEDULE_TEMPLATE_WORKING_HOURS", "OFFICE_HOURS")

    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "WORKING_HOURS"}

    with time_machine.travel(now_time(time(12))):
        assert get_scale_for_app(app) == 2

    with time_machine.travel(now_time(time(22))):
        assert get_scale_for_app(app) == 0


def test_does_nothing_when_matching_schedule() -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "0900-1700:2"}
    app.process_formation.return_value["web"].quantity = 2

    with time_machine.travel(now_time(time(12))):
        scale_app(app)

    app.process_formation.return_value["web"].update.assert_not_called()
    app.enable_maintenance_mode.assert_not_called()
    app.disable_maintenance_mode.assert_not_called()


def test_scales_app() -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "0900-1700:2"}
    app.maintenance = False

    formation = MagicMock()
    formation.type = "web"
    formation._ids = ["web"]
    formation.quantity = 1

    app.process_formation.return_value = KeyedListResource([formation])

    with time_machine.travel(now_time(time(12))):
        scale_app(app)

    app.batch_scale_formation_processes.assert_called_with({"web": 2})
    app.enable_maintenance_mode.assert_not_called()
    app.disable_maintenance_mode.assert_not_called()


def test_enables_maintenance_mode() -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "0900-1700:0"}
    app.maintenance = False

    formation = MagicMock()
    formation.type = "web"
    formation._ids = ["web"]
    formation.quantity = 1

    app.process_formation.return_value = KeyedListResource([formation])

    with time_machine.travel(now_time(time(12))):
        scale_app(app)

    app.batch_scale_formation_processes.assert_called_with({"web": 0})
    app.enable_maintenance_mode.assert_called()
    app.disable_maintenance_mode.assert_not_called()


def test_disables_maintenance_mode() -> None:
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "0900-1700:1"}
    app.maintenance = True

    formation = MagicMock()
    formation.type = "web"
    formation._ids = ["web"]
    formation.quantity = 0

    app.process_formation.return_value = KeyedListResource([formation])

    with time_machine.travel(now_time(time(12))):
        scale_app(app)

    app.batch_scale_formation_processes.assert_called_with({"web": 1})

    app.enable_maintenance_mode.assert_not_called()
    app.disable_maintenance_mode.assert_called()
