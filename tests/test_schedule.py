import string
from datetime import time

from hypothesis import given, strategies

from heroku_scaling_scheduler.schedule import Schedule, parse_schedule


def test_parses_schedule():
    schedules = parse_schedule("0900-1700:2;1700-1900:1;1900-0900:0")

    assert len(schedules) == 3

    assert schedules[0].start_time == time(9)
    assert schedules[0].end_time == time(17)
    assert schedules[0].scale == 2

    assert schedules[1].start_time == time(17)
    assert schedules[1].end_time == time(19)
    assert schedules[1].scale == 1

    assert schedules[2].start_time == time(19)
    assert schedules[2].end_time == time(9)
    assert schedules[2].scale == 0


def test_parses_single_schedule():
    schedules = parse_schedule("0900-1700:3")

    assert len(schedules) == 1

    assert schedules[0].start_time == time(9)
    assert schedules[0].end_time == time(17)
    assert schedules[0].scale == 3

    assert schedules[0].serialize() == "0900-1700:3"


def test_parses_all_day_schedule():
    schedules = parse_schedule("0000-2359:3")

    assert len(schedules) == 1

    assert schedules[0].start_time == time.min
    assert schedules[0].end_time == time(23, 59)
    assert schedules[0].scale == 3


def test_negative_scale():
    assert len(parse_schedule("0000-2359:-3")) == 0


def test_schedule_covers_time():
    schedule = Schedule(time(9), time(17), 1)

    assert schedule.covers(time(9, 1))
    assert schedule.covers(time(16, 59))


def test_covers_crossing_midnight():
    schedule = Schedule(time(20), time(8), 1)

    assert schedule.covers(time.max)
    assert schedule.covers(time.min)
    assert schedule.covers(time(5))
    assert schedule.covers(time(22))


@given(strategies.text(min_size=3, max_size=15))
def test_invalid_schedule(schedule_candidate):
    parse_schedule(schedule_candidate)


@given(strategies.text(alphabet=string.digits))
def test_invalid_time(strategy_time: str):
    parse_schedule(f"{strategy_time}-2359:1")
