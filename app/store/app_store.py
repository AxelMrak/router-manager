from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.models.device import Device
from app.models.schedule import Schedule
from app.models.router_info import RouterInfo


class AppStore(QObject):
    """Centralized application state with Qt signals for reactive UI."""

    # Signals emitted when state changes
    devices_updated = Signal(list)  # list[Device]
    device_changed = Signal(str)  # mac address
    schedules_updated = Signal(list)  # list[Schedule]
    router_info_updated = Signal(object)  # RouterInfo
    connection_status_changed = Signal(bool)  # connected
    error_occurred = Signal(str, str)  # title, message
    loading_changed = Signal(bool)  # is_loading
    guest_devices_updated = Signal(list)  # list[Device]

    def __init__(self) -> None:
        super().__init__()
        self._devices: list[Device] = []
        self._schedules: list[Schedule] = []
        self._guest_devices: list[Device] = []
        self._router_info: RouterInfo = RouterInfo()
        self._connected: bool = False
        self._loading: bool = False
        self._device_aliases: dict[str, str] = {}  # mac -> custom alias

    # --- Properties ---

    @property
    def devices(self) -> list[Device]:
        return self._devices

    @property
    def online_devices(self) -> list[Device]:
        from app.models.device import DeviceStatus

        return [d for d in self._devices if d.status == DeviceStatus.ONLINE]

    @property
    def blocked_devices(self) -> list[Device]:
        from app.models.device import DeviceStatus

        return [d for d in self._devices if d.status == DeviceStatus.BLOCKED]

    @property
    def guest_devices(self) -> list[Device]:
        return self._guest_devices

    @property
    def schedules(self) -> list[Schedule]:
        return self._schedules

    @property
    def router_info(self) -> RouterInfo:
        return self._router_info

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_loading(self) -> bool:
        return self._loading

    # --- Mutators (emit signals after changes) ---

    def set_devices(self, devices: list[Device]) -> None:
        """Replace device list and emit signal."""
        self._devices = devices
        self.devices_updated.emit(devices)

    def update_device(self, mac: str, **kwargs) -> None:
        """Update a single device's fields and emit signal."""
        mac_upper = mac.upper()
        for device in self._devices:
            if device.mac.upper() == mac_upper:
                device.update_from_dict(kwargs)
                self.device_changed.emit(mac_upper)
                break

    def set_schedules(self, schedules: list[Schedule]) -> None:
        """Replace schedules list and emit signal."""
        self._schedules = schedules
        self.schedules_updated.emit(schedules)

    def add_schedule(self, schedule: Schedule) -> None:
        """Add a schedule and emit signal."""
        self._schedules.append(schedule)
        self.schedules_updated.emit(self._schedules)

    def remove_schedule(self, schedule_id: str) -> None:
        """Remove a schedule by ID and emit signal."""
        self._schedules = [s for s in self._schedules if s.id != schedule_id]
        self.schedules_updated.emit(self._schedules)

    def set_router_info(self, info: RouterInfo) -> None:
        """Set router info and emit signal."""
        self._router_info = info
        self.router_info_updated.emit(info)

    def set_connected(self, connected: bool) -> None:
        """Set connection status and emit signal."""
        self._connected = connected
        self.connection_status_changed.emit(connected)

    def set_loading(self, loading: bool) -> None:
        """Set loading state and emit signal."""
        self._loading = loading
        self.loading_changed.emit(loading)

    def emit_error(self, title: str, message: str) -> None:
        """Emit an error signal."""
        self.error_occurred.emit(title, message)

    # --- Device aliases (persisted locally) ---

    def get_alias(self, mac: str) -> str | None:
        """Get custom alias for a MAC address."""
        return self._device_aliases.get(mac.upper())

    def set_alias(self, mac: str, alias: str) -> None:
        """Set custom alias for a MAC address."""
        self._device_aliases[mac.upper()] = alias

    def load_aliases(self, aliases: dict[str, str]) -> None:
        """Load aliases from database."""
        self._device_aliases = {k.upper(): v for k, v in aliases.items()}

    # --- Guest management ---

    def add_guest(self, mac: str) -> None:
        """Mark a device as guest."""
        mac_upper = mac.upper()
        if mac_upper not in [d.mac.upper() for d in self._guest_devices]:
            # Find the device in main list
            for device in self._devices:
                if device.mac.upper() == mac_upper:
                    device.is_guest = True
                    self._guest_devices.append(device)
                    break
        self.guest_devices_updated.emit(self._guest_devices)

    def remove_guest(self, mac: str) -> None:
        """Remove guest flag from a device."""
        mac_upper = mac.upper()
        self._guest_devices = [d for d in self._guest_devices if d.mac.upper() != mac_upper]
        for device in self._devices:
            if device.mac.upper() == mac_upper:
                device.is_guest = False
                break
        self.guest_devices_updated.emit(self._guest_devices)

    def is_guest(self, mac: str) -> bool:
        """Check if a device is marked as guest."""
        return any(d.mac.upper() == mac.upper() for d in self._guest_devices)

    def load_guest_macs(self, guest_macs: list[str]) -> None:
        """Load guest MACs from database and update device list."""
        self._guest_devices = []
        guest_set = {m.upper() for m in guest_macs}
        for device in self._devices:
            if device.mac.upper() in guest_set:
                device.is_guest = True
                self._guest_devices.append(device)
        self.guest_devices_updated.emit(self._guest_devices)

    # --- Lookup helpers ---

    def get_device_by_mac(self, mac: str) -> Device | None:
        """Find a device by MAC address."""
        mac_upper = mac.upper()
        for device in self._devices:
            if device.mac.upper() == mac_upper:
                return device
        return None

    def get_device_by_ip(self, ip: str) -> Device | None:
        """Find a device by IP address."""
        for device in self._devices:
            if device.ip == ip:
                return device
        return None

    def get_schedules_for_device(self, mac: str) -> list[Schedule]:
        """Get all schedules for a specific device."""
        mac_upper = mac.upper()
        return [s for s in self._schedules if s.mac.upper() == mac_upper]
