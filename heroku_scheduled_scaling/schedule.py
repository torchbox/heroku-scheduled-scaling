from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, time

import pyparsing

WEEKDAYS = "0123456"
DELIMITER = ";"


@dataclass(frozen=True, slots=True, eq=True)
class Schedule:
    start_time: time
    end_time: time
    scale: int

    start_day: int = 0
    end_day: int = 6

    def covers(self, current: datetime) -> bool:
        if self.start_day < current.weekday() > self.end_day:
            return False

        current_time = current.time()
        if self.start_time < self.end_time:
            return current_time >= self.start_time and current_time <= self.end_time
        else:  # crosses midnight
            return current_time >= self.start_time or current_time <= self.end_time

    def serialize(self) -> str:
        return f"{self.start_day}-{self.end_day}({self.start_time.strftime('%H%M')}-{self.end_time.strftime('%H%M')}:{self.scale})"


def parse_time(val: str) -> time:
    return datetime.strptime(val, "%H%M").time()


def get_schedule_format() -> pyparsing.ParserElement:
    """
    Get the `pyparsing` definition for a schedule set
    """

    day_range = pyparsing.Char(WEEKDAYS).setResultsName(
        "start_day"
    ) + pyparsing.Optional(
        pyparsing.Suppress("-") + pyparsing.Char(WEEKDAYS).setResultsName("end_day")
    )

    time_range = (
        pyparsing.Word(pyparsing.nums, exact=4).setResultsName("start_time")
        + pyparsing.Suppress("-")
        + pyparsing.Word(pyparsing.nums, exact=4).setResultsName("end_time")
    )
    scale = pyparsing.Word(pyparsing.nums, exact=1).setResultsName("scale")
    schedule_entry = pyparsing.Group(time_range + pyparsing.Suppress(":") + scale)

    schedule_entries = pyparsing.delimitedList(
        schedule_entry, delim=DELIMITER
    ).setResultsName("schedule_entries")

    return pyparsing.delimitedList(
        pyparsing.Or(
            [
                schedule_entry,
                pyparsing.Group(
                    day_range
                    + pyparsing.Suppress("(")
                    + schedule_entries
                    + pyparsing.Suppress(")")
                ),
            ]
        ),
        delim=DELIMITER,
    )

    # return pyparsing.Or(
    #     [
    #         schedules,
    #         pyparsing.delimitedList(
    #             pyparsing.Group(
    #                 day_range
    #                 + pyparsing.Suppress("(")
    #                 + schedules.setResultsName("schedule_entries")
    #                 + pyparsing.Suppress(")")
    #             ),
    #             delim=";",
    #         ),
    #     ]
    # )


SCHEDULE_PARSER = get_schedule_format()


def parse_schedule(schedule_str: str) -> list[Schedule]:
    schedules: list[Schedule] = []

    try:
        parsed_results = SCHEDULE_PARSER.parseString(schedule_str, parseAll=True)
    except pyparsing.exceptions.ParseException:
        return schedules

    for match in parsed_results:
        match = match.as_dict()

        # If we have multiple
        if schedule_entries := match.get("schedule_entries"):
            for entry in schedule_entries:
                with suppress(ValueError):
                    schedules.append(
                        Schedule(
                            start_time=parse_time(entry["start_time"]),
                            end_time=parse_time(entry["end_time"]),
                            scale=int(entry["scale"]),
                            start_day=int(match["start_day"]),
                            end_day=int(match.get("end_day", match["start_day"])),
                        )
                    )
        else:
            with suppress(ValueError):
                schedules.append(
                    Schedule(
                        start_time=parse_time(match["start_time"]),
                        end_time=parse_time(match["end_time"]),
                        scale=int(match["scale"]),
                    )
                )

    return schedules
