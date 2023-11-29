from datetime import time
from unittest.mock import MagicMock

from heroku_scaling_scheduler.scale import get_scale_for_app, scale_app


def test_gets_app_scale():
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {
        "SCALING_SCHEDULE": "0900-1700:2;1700-1900:1;1900-0900:0"
    }

    assert get_scale_for_app(app, now_time=time(12)) == 2
    assert get_scale_for_app(app, now_time=time(22)) == 0


def test_no_scale_coverage():
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "0900-1700:2"}

    assert get_scale_for_app(app, now_time=time(12)) == 2
    assert get_scale_for_app(app, now_time=time(22)) is None


def test_invalid_schedule():
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {
        "SCALING_SCHEDULE": "Not a schedule"
    }

    assert get_scale_for_app(app, now_time=time(12)) is None
    assert get_scale_for_app(app, now_time=time(22)) is None


def test_no_app_schedule():
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {}

    assert get_scale_for_app(app) is None


def test_does_nothing_when_matching_schedule():
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "0900-1700:2"}
    app.process_formation.return_value["web"].quantity = 2

    scale_app(app, time(12))

    app.process_formation.return_value["web"].update.assert_not_called()
    app.enable_maintenance_mode.assert_not_called()
    app.disable_maintenance_mode.assert_not_called()


def test_scales_app():
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "0900-1700:2"}
    app.process_formation.return_value["web"].quantity = 1
    app.maintenance = False

    scale_app(app, time(12))

    app.process_formation.return_value["web"].update.assert_called_with(
        size=None, quantity=2
    )
    app.enable_maintenance_mode.assert_not_called()
    app.disable_maintenance_mode.assert_not_called()


def test_scales_basic_app():
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "0900-1700:2"}
    app.process_formation.return_value["web"].quantity = 1
    app.process_formation.return_value["web"].size = "Basic"
    app.maintenance = False

    scale_app(app, time(12))

    app.process_formation.return_value["web"].update.assert_called_with(
        size="Standard-1X", quantity=2
    )
    app.enable_maintenance_mode.assert_not_called()
    app.disable_maintenance_mode.assert_not_called()


def test_enables_maintenance_mode():
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "0900-1700:0"}
    app.process_formation.return_value["web"].quantity = 1
    app.process_formation.return_value["web"].size = "Basic"
    app.maintenance = False

    scale_app(app, time(12))

    app.process_formation.return_value["web"].update.assert_called_with(
        size=None, quantity=0
    )
    app.enable_maintenance_mode.assert_called()
    app.disable_maintenance_mode.assert_not_called()


def test_disables_maintenance_mode():
    app = MagicMock()

    app.config.return_value.to_dict.return_value = {"SCALING_SCHEDULE": "0900-1700:1"}
    app.process_formation.return_value["web"].quantity = 0
    app.process_formation.return_value["web"].size = "Basic"
    app.maintenance = True

    scale_app(app, time(12))

    app.process_formation.return_value["web"].update.assert_called_with(
        size=None, quantity=1
    )
    app.enable_maintenance_mode.assert_not_called()
    app.disable_maintenance_mode.assert_called()
