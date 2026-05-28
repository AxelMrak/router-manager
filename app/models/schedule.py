from dataclasses import dataclass, field
from datetime import time

WEEKDAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


@dataclass
class Schedule:
    id: str
    name: str
    mac: str  # Target device MAC
    weekdays: list[int] = field(default_factory=lambda: list(range(7)))  # 0=Mon..6=Sun
    start_time: str = "00:00"  # HH:MM
    end_time: str = "23:59"  # HH:MM
    enabled: bool = True
    device_name: str = ""

    @property
    def weekdays_display(self) -> str:
        """Human-readable weekday string."""
        if len(self.weekdays) == 7:
            return "Todos los días"
        if self.weekdays == [0, 1, 2, 3, 4]:
            return "Días hábiles"
        if self.weekdays == [5, 6]:
            return "Fin de semana"
        return ", ".join(WEEKDAY_NAMES[d] for d in sorted(self.weekdays))

    @property
    def time_range_display(self) -> str:
        return f"{self.start_time} - {self.end_time}"

    @classmethod
    def from_router_data(cls, data: dict) -> "Schedule":
        """Create Schedule from router API response."""
        schedule_id = (
            data.get("id")
            or data.get("_id")
            or data.get("schedule_id")
            or data.get("sid")
            or str(hash(str(data)))
        )

        name = data.get("name") or data.get("schedule_name") or "Horario sin nombre"

        mac = (
            data.get("mac")
            or data.get("macaddr")
            or data.get("MAC")
            or data.get("device_mac")
            or ""
        )

        weekdays = list(range(7))
        weekdays_data = data.get("weekdays") or data.get("days") or data.get("weekday")
        if weekdays_data is not None:
            if isinstance(weekdays_data, list):
                weekdays = [int(d) % 7 for d in weekdays_data]
            elif isinstance(weekdays_data, int):
                weekdays = [weekdays_data % 7]
            elif isinstance(weekdays_data, str):
                # Parse comma-separated or range like "1,2,3" or "1-5"
                weekdays = cls._parse_weekdays_string(weekdays_data)

        start_time = data.get("start_time") or data.get("start") or data.get("from") or "00:00"
        end_time = data.get("end_time") or data.get("end") or data.get("to") or "23:59"

        enabled = data.get("enabled", data.get("active", True))
        if isinstance(enabled, str):
            enabled = enabled.lower() in ("true", "1", "yes", "on")

        device_name = data.get("device_name") or data.get("hostname") or ""

        return cls(
            id=str(schedule_id),
            name=str(name),
            mac=str(mac).upper(),
            weekdays=weekdays,
            start_time=str(start_time),
            end_time=str(end_time),
            enabled=bool(enabled),
            device_name=str(device_name),
        )

    @staticmethod
    def _parse_weekdays_string(s: str) -> list[int]:
        """Parse weekday string like '1,2,3' or '1-5' into list of ints."""
        result: list[int] = []
        parts = s.replace(" ", "").split(",")
        for part in parts:
            if "-" in part:
                try:
                    start, end = part.split("-")
                    result.extend(range(int(start), int(end) + 1))
                except ValueError:
                    pass
            else:
                try:
                    result.append(int(part))
                except ValueError:
                    pass
        return list(set(result))

    def to_router_params(self) -> dict:
        """Convert to params dict for router API calls."""
        return {
            "name": self.name,
            "mac": self.mac,
            "weekdays": self.weekdays,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "enabled": self.enabled,
        }
