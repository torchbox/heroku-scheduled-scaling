import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, time

SCHEDULE_RE = re.compile(r"(\d{4})-(\d{4}):(\d+?);?")


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


def parse_schedule(schedule_str: str) -> list[Schedule]:
    schedules = []

    for match in SCHEDULE_RE.findall(schedule_str):
        with suppress(ValueError):
            schedules.append(
                Schedule(
                    parse_time(match[0]),
                    parse_time(match[1]),
                    int(match[2]),
                )
            )

    return schedules
