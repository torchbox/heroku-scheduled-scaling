import string
from datetime import datetime, time

from hypothesis import given, strategies

from heroku_scheduled_scaling.schedule import Schedule, parse_schedule

NOW = datetime.now()
TODAY = NOW.date()


def test_parses_schedule() -> None:
    schedules = parse_schedule("0900-1700:2;1700-1900:1;1900-0900:0")

    assert len(schedules) == 3

    assert schedules[0] == Schedule(time(9), time(17), 2)
    assert schedules[1] == Schedule(time(17), time(19), 1)
    assert schedules[2] == Schedule(time(19), time(9), 0)


def test_parses_schedule_with_days() -> None:
    schedules = parse_schedule(
        "0-5(0900-1700:2;1700-1900:1;1900-0900:0);5-6(0000-2359:0)"
    )

    assert len(schedules) == 4

    assert schedules[0] == Schedule(time(9), time(17), 2, 0, 5)
    assert schedules[1] == Schedule(time(17), time(19), 1, 0, 5)
    assert schedules[2] == Schedule(time(19), time(9), 0, 0, 5)
    assert schedules[3] == Schedule(time(0), time(23, 59), 0, 5, 6)


def test_mix_day_format() -> None:
    schedules = parse_schedule("0-5(0900-1700:2;1700-1900:1;1900-0900:0);0000-2359:0")

    assert len(schedules) == 4

    assert schedules[0] == Schedule(time(9), time(17), 2, 0, 5)
    assert schedules[1] == Schedule(time(17), time(19), 1, 0, 5)
    assert schedules[2] == Schedule(time(19), time(9), 0, 0, 5)
    assert schedules[3] == Schedule(time(0), time(23, 59), 0, 0, 6)


def test_single_day() -> None:
    schedules = parse_schedule("0(0900-1700:2)")

    assert len(schedules) == 1

    assert schedules[0] == Schedule(time(9), time(17), 2, 0, 0)


def test_parses_single_schedule() -> None:
    schedules = parse_schedule("0900-1700:3")

    assert len(schedules) == 1

    assert schedules[0].start_time == time(9)
    assert schedules[0].end_time == time(17)
    assert schedules[0].scale == 3

    assert schedules[0].serialize() == "0-6(0900-1700:3)"


@given(
    strategies.times(),
    strategies.times(),
    strategies.integers(min_value=0),
    strategies.integers(min_value=0, max_value=6),
    strategies.integers(min_value=0, max_value=6),
)
def test_e2e_parse(
    start_time: time, end_time: time, scale: int, start_day: int, end_day: int
) -> None:
    schedule = Schedule(
        start_time.replace(second=0, microsecond=0),
        end_time.replace(second=0, microsecond=0),
        scale,
        start_day,
        end_day,
    )

    assert parse_schedule(schedule.serialize()) == [schedule]


def test_parses_all_day_schedule() -> None:
    schedules = parse_schedule("0000-2359:3")

    assert len(schedules) == 1

    assert schedules[0].start_time == time.min
    assert schedules[0].end_time == time(23, 59)
    assert schedules[0].scale == 3


def test_negative_scale() -> None:
    assert len(parse_schedule("0000-2359:-3")) == 0


def test_schedule_covers_time() -> None:
    schedule = Schedule(time(9), time(17), 1)

    assert schedule.covers(datetime.combine(TODAY, time(9, 1)))
    assert schedule.covers(datetime.combine(TODAY, time(16, 59)))


def test_schedule_covers_day() -> None:
    # Monday only
    schedule = Schedule(time(9), time(17), 1, 0, 1)

    # 1970-01-01 is a Thursday
    assert not schedule.covers(datetime(1970, 1, 1, 10))
    assert not schedule.covers(datetime(1970, 1, 2, 10))
    assert not schedule.covers(datetime(1970, 1, 3, 10))
    assert not schedule.covers(datetime(1970, 1, 4, 10))

    assert schedule.covers(datetime(1970, 1, 5, 10))
    assert schedule.covers(datetime(1970, 1, 6, 10))

    assert not schedule.covers(datetime(1970, 1, 7, 10))


def test_covers_crossing_midnight() -> None:
    schedule = Schedule(time(20), time(8), 1)

    assert schedule.covers(datetime.combine(TODAY, time.max))
    assert schedule.covers(datetime.combine(TODAY, time.min))
    assert schedule.covers(datetime.combine(TODAY, time(5)))
    assert schedule.covers(datetime.combine(TODAY, time(22)))


@given(strategies.text(min_size=3, max_size=15))
def test_invalid_schedule(schedule_candidate: str) -> None:
    assert len(parse_schedule(schedule_candidate)) == 0


@given(strategies.text(alphabet=string.digits))
def test_invalid_time(strategy_time: str) -> None:
    parse_schedule(f"{strategy_time}-2359:1")
