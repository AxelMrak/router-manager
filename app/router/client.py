"""JSON-RPC client for OpenWrt /ubus router API."""

from __future__ import annotations

import logging
import threading
from typing import Any

import requests

from app.router.exceptions import (
    RouterAPIError,
    RouterAuthError,
    RouterConnectionError,
    RouterError,
    RouterTimeoutError,
)

logger = logging.getLogger(__name__)


class RouterClient:
    """Thread-safe JSON-RPC client for /ubus router API."""

    def __init__(
        self,
        host: str,
        username: str = "root",
        password: str = "",
        timeout: int = 10,
    ) -> None:
        """Initialize the router client.

        Args:
            host: Router IP address or hostname (e.g. "192.168.1.1").
            username: Router authentication username.
            password: Router authentication password.
            timeout: Request timeout in seconds.
        """
        self.host = host
        self.base_url = f"http://{host}/ubus"
        self.username = username
        self.password = password
        self.timeout = timeout
        self._request_id = 0
        self._lock = threading.Lock()
        self.session = requests.Session()
        self.session.verify = False
        self.auth_token: str | None = None

    def _next_id(self) -> int:
        """Generate next JSON-RPC request ID (thread-safe)."""
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _rpc_call(self, method: str, params: list) -> dict:
        """Make a JSON-RPC call to /ubus.

        Args:
            method: The ubus method name.
            params: Parameters for the RPC call.

        Returns:
            Parsed JSON response dict.

        Raises:
            RouterConnectionError: Cannot reach router.
            RouterTimeoutError: Request timed out.
            RouterAuthError: Authentication failed or expired.
            RouterAPIError: Malformed or unexpected response.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }

        try:
            response = self.session.post(
                self.base_url,
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as e:
            logger.warning("Request timed out to %s: %s", self.host, e)
            raise RouterTimeoutError(f"Request timed out: {e}") from e
        except requests.ConnectionError as e:
            logger.warning("Connection failed to %s: %s", self.host, e)
            raise RouterConnectionError(f"Cannot reach router at {self.host}: {e}") from e
        except requests.RequestException as e:
            logger.error("Request failed to %s: %s", self.host, e)
            raise RouterError(f"Request failed: {e}") from e

        if response.status_code == 401:
            self.auth_token = None
            logger.warning("Authentication required or expired for %s", self.host)
            raise RouterAuthError("Authentication required or expired")

        if response.status_code != 200:
            logger.error(
                "HTTP %d from %s: %s",
                response.status_code,
                self.host,
                response.text[:200],
            )
            raise RouterAPIError(
                f"HTTP {response.status_code}: {response.text[:100]}",
                code=response.status_code,
            )

        try:
            data = response.json()
        except ValueError as e:
            response_preview = response.text[:200] if response.text else "(empty)"
            logger.error(
                "Malformed JSON from %s: %s. Response: %s",
                self.host,
                e,
                response_preview,
            )
            raise RouterAPIError(
                f"Respuesta no-JSON del router. ¿Es {self.host} un router compatible con ubus? "
                f"Respuesta: {response_preview[:100]}",
            ) from e

        if "error" in data:
            err = data["error"]
            code = err.get("code")
            message = err.get("message", "Unknown error")
            logger.error("RPC error from %s: [%d] %s", self.host, code, message)

            if code in (-32001, -32002, -32602):
                raise RouterAuthError(message)
            raise RouterAPIError(message, code=code, response=data)

        return data.get("result", data)

    def login(self) -> bool:
        """Authenticate with the router.

        Calls the session.login ubus method and stores the returned auth token.

        Returns:
            True if login succeeded.

        Raises:
            RouterConnectionError: Cannot reach router.
            RouterTimeoutError: Request timed out.
            RouterAuthError: Authentication failed.
            RouterAPIError: Unexpected response.
        """
        logger.info("Attempting login to router %s as %s", self.host, self.username)

        params = [
            "00000000000000000000000000000000",
            "session",
            "login",
            {"username": self.username, "password": self.password},
        ]

        try:
            result = self._rpc_call("call", params)
        except RouterError:
            raise

        if isinstance(result, list) and len(result) >= 2:
            data = result[1] if isinstance(result[1], dict) else {}
            self.auth_token = data.get("ubus_rpc_session")
            if self.auth_token:
                logger.info("Login successful, token acquired for %s", self.host)
                return True

        logger.error("Login response missing token: %s", result)
        raise RouterAPIError("Login response missing auth token", response=result)

    def logout(self) -> None:
        """Log out from the router and clear the auth token."""
        if not self.auth_token:
            return

        logger.info("Logging out from router %s", self.host)
        params = [self.auth_token, "session", "destroy", {}]

        try:
            self._rpc_call("call", params)
        except RouterError as e:
            logger.warning("Logout RPC failed (non-critical): %s", e)
        finally:
            self.auth_token = None

    def get_devices(self) -> list[dict]:
        """Get all connected devices from the router.

        Tries multiple ubus call patterns to retrieve device information:
        - dhcp ipv4leases
        - hostapd get_clients
        - network.interface dump

        Returns:
            List of device dicts with keys: mac, ip, hostname, etc.
        """
        logger.debug("Fetching connected devices from %s", self.host)

        methods = [
            ("dhcp", "ipv4leases", {}),
            ("hostapd.wlan0", "get_clients", {}),
            ("hostapd.wlan1", "get_clients", {}),
            ("hostapd.phy0-ap0", "get_clients", {}),
            ("hostapd.phy1-ap0", "get_clients", {}),
            ("network.interface", "dump", {}),
        ]

        for service, method, params in methods:
            try:
                rpc_params = [self.auth_token or "", service, method, params]
                result = self._rpc_call("call", rpc_params)

                devices = self._normalize_device_list(result)
                if devices:
                    logger.debug("Found %d devices via %s.%s", len(devices), service, method)
                    return devices
            except RouterError as e:
                logger.debug("Device query via %s.%s failed: %s", service, method, e)
                continue

        logger.warning("No devices found via any known method on %s", self.host)
        return []

    def _normalize_device_list(self, result: Any) -> list[dict]:
        """Normalize raw ubus device list to a consistent format."""
        devices = []

        if isinstance(result, list) and len(result) >= 2:
            data = result[1]

            if isinstance(data, dict):
                # Try DHCP leases format first.
                # Standard ubus dhcp.ipv4leases returns [0, {"leases": [...]}].
                # Some routers nest it: [0, {"dhcp": {"leases": [...]}}]
                # or [0, {"dhcp": {"ipv4": {"leases": [...]}}}].
                leases = data.get("leases", [])
                if not leases and "dhcp" in data:
                    dhcp = data["dhcp"]
                    if isinstance(dhcp, dict):
                        leases = dhcp.get("leases", [])
                        if not leases:
                            leases = dhcp.get("ipv4", {}).get("leases", [])

                if leases:
                    for lease in leases:
                        if isinstance(lease, dict):
                            devices.append({
                                "mac": lease.get("mac", ""),
                                "ip": lease.get("ip", ""),
                                "hostname": lease.get("hostname", ""),
                            })
                    return devices

                # Try hostapd clients format.
                if "clients" in data:
                    for mac, info in data["clients"].items():
                        if isinstance(info, dict):
                            devices.append({
                                "mac": mac,
                                "ip": info.get("ip", ""),
                                "hostname": info.get("hostname", ""),
                            })
                    return devices

        return devices

    def get_host_list(self) -> list[dict]:
        """Get host list via alternative network APIs.

        Returns:
            List of host dicts.
        """
        logger.debug("Fetching host list via system APIs from %s", self.host)

        try:
            params = [self.auth_token or "", "network.device", "status", {}]
            result = self._rpc_call("call", params)

            if isinstance(result, list) and len(result) >= 2:
                data = result[1]
                if isinstance(data, dict):
                    hosts = []
                    for device, info in data.items():
                        if "stats" in info:
                            hosts.append({
                                "device": device,
                                "mac": info.get("mac"),
                                "rx_bytes": info["stats"].get("rx_bytes"),
                                "tx_bytes": info["stats"].get("tx_bytes"),
                            })
                    return hosts
        except RouterError as e:
            logger.debug("Host list query failed: %s", e)

        return []

    def block_device(self, mac: str) -> bool:
        """Block internet access for a device by MAC address.

        Args:
            mac: MAC address of the device to block.

        Returns:
            True if the block was applied successfully.
        """
        logger.info("Blocking device %s on router %s", mac, self.host)

        try:
            params = [
                self.auth_token or "",
                "firewall",
                "add_redirect",
                {
                    "src": "wan",
                    "dest": "lan",
                    "mac": mac,
                    "action": "drop",
                },
            ]
            result = self._rpc_call("call", params)

            if isinstance(result, list) and len(result) >= 1:
                return result[0].get("success", False)
        except RouterError as e:
            logger.error("Failed to block device %s: %s", mac, e)
            raise RouterAPIError(f"Failed to block device: {e}") from e

        return False

    def unblock_device(self, mac: str) -> bool:
        """Remove internet block for a device by MAC address.

        Args:
            mac: MAC address of the device to unblock.

        Returns:
            True if the block was removed successfully.
        """
        logger.info("Unblocking device %s on router %s", mac, self.host)

        try:
            params = [
                self.auth_token or "",
                "firewall",
                "remove_redirect",
                {"mac": mac},
            ]
            result = self._rpc_call("call", params)

            if isinstance(result, list) and len(result) >= 1:
                return result[0].get("success", False)
        except RouterError as e:
            logger.error("Failed to unblock device %s: %s", mac, e)
            raise RouterAPIError(f"Failed to unblock device: {e}") from e

        return False

    def get_firewall_rules(self) -> list[dict]:
        """Get current firewall rules from the router.

        Returns:
            List of firewall rule dicts.
        """
        logger.debug("Fetching firewall rules from %s", self.host)

        try:
            params = [self.auth_token or "", "firewall", "dump", {}]
            result = self._rpc_call("call", params)

            if isinstance(result, list) and len(result) >= 2:
                data = result[1]
                if isinstance(data, dict):
                    rules = data.get("rules", [])
                    return [
                        {
                            "id": r.get("id"),
                            "src": r.get("src"),
                            "dest": r.get("dest"),
                            "action": r.get("action"),
                            "enabled": r.get("enabled", True),
                        }
                        for r in rules
                    ]
        except RouterError as e:
            logger.warning("Failed to fetch firewall rules: %s", e)

        return []

    def create_schedule(
        self,
        name: str,
        mac: str,
        weekdays: list[int],
        start_time: str,
        end_time: str,
        enabled: bool = True,
    ) -> dict:
        """Create an internet access schedule for a device.

        Args:
            name: Human-readable schedule name.
            mac: MAC address of the target device.
            weekdays: List of weekdays (0=Monday, 6=Sunday).
            start_time: Start time in "HH:MM" format.
            end_time: End time in "HH:MM" format.
            enabled: Whether the schedule is initially enabled.

        Returns:
            Created schedule dict with id.
        """
        logger.info(
            "Creating schedule '%s' for device %s on router %s",
            name,
            mac,
            self.host,
        )

        schedule = {
            "name": name,
            "mac": mac,
            "weekdays": weekdays,
            "start_time": start_time,
            "end_time": end_time,
            "enabled": enabled,
        }

        try:
            params = [self.auth_token or "", "schedule", "add", schedule]
            result = self._rpc_call("call", params)

            if isinstance(result, list) and len(result) >= 1:
                response = result[0]
                schedule_id = response.get("id")
                if schedule_id:
                    logger.info("Schedule created with id %s", schedule_id)
                    return {"id": schedule_id, **schedule}
        except RouterError as e:
            logger.error("Failed to create schedule: %s", e)
            raise RouterAPIError(f"Failed to create schedule: {e}") from e

        raise RouterAPIError("Schedule creation failed, no ID returned")

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete an existing schedule by ID.

        Args:
            schedule_id: The schedule identifier to delete.

        Returns:
            True if deletion succeeded.
        """
        logger.info("Deleting schedule %s on router %s", schedule_id, self.host)

        try:
            params = [self.auth_token or "", "schedule", "delete", {"id": schedule_id}]
            result = self._rpc_call("call", params)

            if isinstance(result, list) and len(result) >= 1:
                return result[0].get("success", False)
        except RouterError as e:
            logger.error("Failed to delete schedule %s: %s", schedule_id, e)
            raise RouterAPIError(f"Failed to delete schedule: {e}") from e

        return False

    def get_schedules(self) -> list[dict]:
        """Get all configured schedules from the router.

        Returns:
            List of schedule dicts.
        """
        logger.debug("Fetching schedules from %s", self.host)

        try:
            params = [self.auth_token or "", "schedule", "list", {}]
            result = self._rpc_call("call", params)

            if isinstance(result, list) and len(result) >= 2:
                schedules = result[1]
                if isinstance(schedules, list):
                    return schedules
        except RouterError as e:
            logger.warning("Failed to fetch schedules: %s", e)

        return []

    def update_schedule(self, schedule_id: str, **kwargs: Any) -> bool:
        """Update an existing schedule.

        Args:
            schedule_id: The schedule identifier to update.
            **kwargs: Fields to update (name, mac, weekdays, start_time, end_time, enabled).

        Returns:
            True if update succeeded.
        """
        logger.info("Updating schedule %s on router %s", schedule_id, self.host)

        try:
            params = [
                self.auth_token or "",
                "schedule",
                "update",
                {"id": schedule_id, **kwargs},
            ]
            result = self._rpc_call("call", params)

            if isinstance(result, list) and len(result) >= 1:
                return result[0].get("success", False)
        except RouterError as e:
            logger.error("Failed to update schedule %s: %s", schedule_id, e)
            raise RouterAPIError(f"Failed to update schedule: {e}") from e

        return False

    def get_bandwidth_usage(self, mac: str | None = None) -> dict:
        """Get bandwidth statistics from the router.

        Args:
            mac: Optional MAC address to filter stats for a specific device.

        Returns:
            Dict with bandwidth statistics.
        """
        logger.debug("Fetching bandwidth usage from %s", self.host)

        try:
            params = [self.auth_token or "", "bandwidth", "get_stats", {"mac": mac} if mac else {}]
            result = self._rpc_call("call", params)

            if isinstance(result, list) and len(result) >= 2:
                return result[1] if isinstance(result[1], dict) else {}
        except RouterError as e:
            logger.debug("Bandwidth query failed: %s", e)

        return {}

    def get_system_info(self) -> dict:
        """Get router system information.

        Uses system.board (model, firmware version, hostname) plus
        system.info (uptime). Returns keys compatible with
        RouterInfo.from_router_data().

        Returns:
            Dict with keys: model, firmware_version, hostname, uptime.
        """
        logger.debug("Fetching system info from %s", self.host)

        info: dict = {}

        # system.board provides model, firmware version, hostname
        try:
            params = [self.auth_token or "", "system", "board", {}]
            result = self._rpc_call("call", params)

            if isinstance(result, list) and len(result) >= 2:
                board = result[1]
                if isinstance(board, dict):
                    info["model"] = board.get("model", "")
                    info["hostname"] = board.get("hostname", "")
                    release = board.get("release")
                    if isinstance(release, dict):
                        info["firmware_version"] = release.get("version", "")
        except RouterError as e:
            logger.debug("system.board query failed: %s", e)

        # system.info provides uptime
        try:
            params = [self.auth_token or "", "system", "info", {}]
            result = self._rpc_call("call", params)

            if isinstance(result, list) and len(result) >= 2:
                sysinfo = result[1]
                if isinstance(sysinfo, dict):
                    info["uptime"] = sysinfo.get("uptime", 0)
        except RouterError as e:
            logger.debug("system.info query failed: %s", e)

        # Ensure all expected keys have defaults
        info.setdefault("model", "")
        info.setdefault("firmware_version", "")
        info.setdefault("hostname", "")
        info.setdefault("uptime", 0)

        return info

    def test_connection(self) -> bool:
        """Test router connectivity without full authentication.

        Returns:
            True if router is reachable and responds to ubus API.
        """
        logger.debug("Testing connection to %s", self.host)

        try:
            response = self.session.post(
                self.base_url,
                timeout=5,
                json={"jsonrpc": "2.0", "id": 1, "method": "list", "params": []},
            )
            return response.status_code in (200, 401, 403)
        except requests.RequestException as e:
            logger.debug("Connection test failed: %s", e)
            return False