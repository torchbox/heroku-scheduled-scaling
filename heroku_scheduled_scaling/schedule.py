from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, time

import pyparsing


@dataclass(frozen=True, slots=True)
class Schedule:
    start_time: time
    end_time: time
    scale: int

    def covers(self, current_time: time) -> bool:
        if self.start_time < self.end_time:
            return current_time >= self.start_time and current_time <= self.end_time
        else:  # crosses midnight
            return current_time >= self.start_time or current_time <= self.end_time

    def serialize(self) -> str:
        return f"{self.start_time.strftime('%H%M')}-{self.end_time.strftime('%H%M')}:{self.scale}"


def parse_time(val: str) -> time:
    return datetime.strptime(val, "%H%M").time()


def get_schedule_format() -> pyparsing.ParserElement:
    """
    Get the `pyparsing` definition for a schedule set
    """

    time_range = (
        pyparsing.Word(pyparsing.nums, exact=4).setResultsName("start_time")
        + pyparsing.Suppress("-")
        + pyparsing.Word(pyparsing.nums, exact=4).setResultsName("end_time")
    )
    scale = pyparsing.Word(pyparsing.nums, exact=1).setResultsName("scale")
    schedule_entry = pyparsing.Group(time_range + pyparsing.Suppress(":") + scale)

    return pyparsing.delimitedList(schedule_entry, delim=";")


SCHEDULE_PARSER = get_schedule_format()


def parse_schedule(schedule_str: str) -> list[Schedule]:
    schedules: list[Schedule] = []

    try:
        parsed_results = SCHEDULE_PARSER.parseString(schedule_str, parseAll=True)
    except pyparsing.exceptions.ParseException:
        return schedules

    for match in parsed_results:
        with suppress(ValueError):
            schedules.append(
                Schedule(
                    parse_time(match[0]),
                    parse_time(match[1]),
                    int(match[2]),
                )
            )

    return schedules
