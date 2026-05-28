from dataclasses import dataclass


@dataclass
class RouterInfo:
    hostname: str = ""
    model: str = ""
    firmware_version: str = ""
    uptime: int = 0  # seconds
    ip_address: str = ""
    connected: bool = False

    @property
    def uptime_display(self) -> str:
        """Human-readable uptime string."""
        seconds = self.uptime
        if seconds < 0:
            return "Unknown"

        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or not parts:
            parts.append(f"{minutes}m")

        return " ".join(parts)

    @classmethod
    def from_router_data(cls, data: dict) -> "RouterInfo":
        """Create RouterInfo from router API response."""
        hostname = (
            data.get("hostname")
            or data.get("name")
            or data.get("router_name")
            or ""
        )

        model = (
            data.get("model")
            or data.get("model_name")
            or data.get("device_model")
            or data.get("hardware")
            or ""
        )

        firmware_version = (
            data.get("firmware_version")
            or data.get("version")
            or data.get("fw_version")
            or data.get("software_version")
            or ""
        )

        uptime = data.get("uptime") or data.get("uptime_seconds") or 0
        if isinstance(uptime, str):
            uptime = int(uptime) if uptime.isdigit() else 0

        ip_address = (
            data.get("ip")
            or data.get("ip_address")
            or data.get("lan_ip")
            or data.get("router_ip")
            or ""
        )

        connected = data.get("connected", True)
        if isinstance(connected, str):
            connected = connected.lower() in ("true", "1", "yes", "on")

        return cls(
            hostname=str(hostname),
            model=str(model),
            firmware_version=str(firmware_version),
            uptime=int(uptime),
            ip_address=str(ip_address),
            connected=bool(connected),
        )
