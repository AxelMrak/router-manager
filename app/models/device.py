from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ConnectionType(Enum):
    WIFI = "wifi"
    ETHERNET = "ethernet"
    UNKNOWN = "unknown"


class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass
class Device:
    mac: str
    ip: str
    name: str = "Dispositivo desconocido"
    status: DeviceStatus = DeviceStatus.UNKNOWN
    connection_type: ConnectionType = ConnectionType.UNKNOWN
    internet_access: bool = True
    schedule_id: str | None = None
    last_seen: datetime | None = None
    hostname: str = ""
    vendor: str = ""
    is_guest: bool = False
    bandwidth_up: float = 0.0
    bandwidth_down: float = 0.0
    raw_data: dict = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return self.name if self.name != "Dispositivo desconocido" else (self.hostname or self.mac)

    @property
    def is_online(self) -> bool:
        return self.status == DeviceStatus.ONLINE

    def update_from_dict(self, data: dict) -> None:
        """Update fields from a raw dict (router API response)."""
        # Map common field names
        self.name = data.get("name") or data.get("hostname") or data.get("nm") or self.name

        # MAC address
        mac_value = data.get("mac") or data.get("macaddr") or data.get("MAC") or self.mac
        if mac_value:
            self.mac = mac_value.upper() if isinstance(mac_value, str) else str(mac_value)

        # IP address
        ip_value = data.get("ip") or data.get("IP") or data.get("ipaddr") or self.ip
        if ip_value:
            self.ip = str(ip_value)

        # Status
        status_str = data.get("status") or data.get("Status") or ""
        if isinstance(status_str, str):
            status_lower = status_str.lower()
            if status_lower == "online" or status_lower == "up":
                self.status = DeviceStatus.ONLINE
            elif status_lower == "offline" or status_lower == "down":
                self.status = DeviceStatus.OFFLINE
            elif status_lower == "blocked":
                self.status = DeviceStatus.BLOCKED

        # Connection type
        conn_str = data.get("connection_type") or data.get("conn_type") or data.get("type") or ""
        if isinstance(conn_str, str):
            conn_lower = conn_str.lower()
            if conn_lower in ("wifi", "wireless", "wlan"):
                self.connection_type = ConnectionType.WIFI
            elif conn_lower in ("ethernet", "lan", "wired"):
                self.connection_type = ConnectionType.ETHERNET

        # Internet access
        if "internet_access" in data:
            self.internet_access = bool(data["internet_access"])
        if "internet" in data:
            self.internet_access = bool(data["internet"])

        # Schedule ID
        schedule_val = data.get("schedule_id") or data.get("schedule") or data.get("scheduleId")
        if schedule_val is not None:
            self.schedule_id = str(schedule_val) if schedule_val else None

        # Last seen
        last_seen_val = data.get("last_seen") or data.get("lastSeen") or data.get("seen")
        if last_seen_val:
            if isinstance(last_seen_val, datetime):
                self.last_seen = last_seen_val
            elif isinstance(last_seen_val, (int, float)):
                # Unix timestamp
                self.last_seen = datetime.fromtimestamp(last_seen_val)
            elif isinstance(last_seen_val, str):
                # ISO format string
                try:
                    self.last_seen = datetime.fromisoformat(last_seen_val.replace("Z", "+00:00"))
                except ValueError:
                    pass

        # Hostname
        self.hostname = data.get("hostname") or self.hostname

        # Vendor
        self.vendor = data.get("vendor") or data.get("manufacturer") or self.vendor

        # Guest flag
        if "is_guest" in data:
            self.is_guest = bool(data["is_guest"])
        elif "guest" in data:
            self.is_guest = bool(data["guest"])

        # Bandwidth
        bw_up = data.get("bandwidth_up") or data.get("up") or data.get("upload")
        if bw_up is not None:
            self.bandwidth_up = float(bw_up)
        bw_down = data.get("bandwidth_down") or data.get("down") or data.get("download")
        if bw_down is not None:
            self.bandwidth_down = float(bw_down)

        # Store raw data for debugging
        self.raw_data = data

    @classmethod
    def from_router_data(cls, data: dict) -> "Device":
        """Create Device from router API response dict."""
        # Handle various field name conventions from ubus
        mac = (
            data.get("mac")
            or data.get("macaddr")
            or data.get("MAC")
            or data.get("mac_address")
            or data.get("hwaddr")
            or ""
        )
        ip = (
            data.get("ip")
            or data.get("IP")
            or data.get("ipaddr")
            or data.get("ip_address")
            or data.get("ipv4")
            or ""
        )

        device = cls(mac=str(mac).upper(), ip=str(ip))
        device.update_from_dict(data)
        return device
