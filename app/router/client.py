"""JSON-RPC client for OpenWrt /ubus router API."""

from __future__ import annotations

import base64
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

        cookies = {}
        if self.auth_token:
            cookies["ubus_rpc_session"] = self.auth_token

        try:
            response = self.session.post(
                self.base_url,
                json=payload,
                cookies=cookies,
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
                self._cgi_password = base64.b64encode(self.password.encode()).decode()
                self._login_cgi()
                return True

        logger.error("Login response missing token: %s", result)
        raise RouterAPIError("Login response missing auth token", response=result)

    def _login_cgi(self) -> bool:
        """Login via Netis CGI endpoint (POST /cgi-bin/login.cgi).

        Netis/W7 routers use a proprietary CGI stack with cookie-based
        authentication. The password is base64-encoded and the router
        responds with a Set-Cookie: password=<base64> header. This cookie
        authenticates all subsequent requests.

        Returns:
            True if CGI login succeeded and cookie was captured.
        """
        logger.debug("Attempting CGI login to %s", self.host)

        encoded_password = base64.b64encode(self.password.encode()).decode()
        cgi_url = f"http://{self.host}/cgi-bin/login.cgi"

        try:
            response = self.session.post(
                cgi_url,
                data={"password": encoded_password},
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            logger.debug("CGI login failed: %s", e)
            return False

        if response.status_code == 200:
            cookie = response.headers.get("Set-Cookie", "")
            if "password=" in cookie:
                logger.info("CGI login successful for %s", self.host)
                return True

        logger.debug("CGI login: unexpected response %d", response.status_code)
        return False

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

        Tries standard OpenWrt ubus first. If no ubus services are
        available (common on W7/Netis consumer routers), falls back
        to proprietary CGI endpoints.

        Returns:
            List of device dicts with keys: mac, ip, hostname, etc.
        """
        logger.debug("Fetching connected devices from %s", self.host)

        available = self.get_available_services()

        if not available:
            logger.debug("No ubus services on %s — trying CGI first", self.host)
            cgi_devices = self._get_devices_cgi()
            if cgi_devices:
                return cgi_devices

        device_methods: list[tuple[str, str, dict]] = []

        if "dhcp" in available or not available:
            device_methods.append(("dhcp", "ipv4leases", {}))

        for svc in sorted(available):
            if svc.startswith("hostapd."):
                device_methods.append((svc, "get_clients", {}))

        if not any("hostapd" in s for s in available):
            for iface in ("wlan0", "wlan1", "phy0-ap0", "phy1-ap0", "radio0", "radio1"):
                device_methods.append((f"hostapd.{iface}", "get_clients", {}))

        if "network.interface" in available or not available:
            device_methods.append(("network.interface", "dump", {}))

        for service, method, params in device_methods:
            result = self._try_rpc_with_retry(service, method, params)
            if result is None:
                continue

            devices = self._normalize_device_list(result)
            if devices:
                logger.info(
                    "Found %d devices via %s.%s on %s", len(devices), service, method, self.host
                )
                return devices

        cgi_devices = self._get_devices_cgi()
        if cgi_devices:
            return cgi_devices

        if not available:
            logger.warning(
                "No ubus services discovered on %s — router may not expose any data via ubus",
                self.host,
            )
        else:
            logger.warning(
                "No devices found via any method on %s. Available services: %s",
                self.host,
                sorted(available),
            )
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

    def _fetch_cgi(self, endpoint: str, body: dict) -> dict | None:
        """POST to a CGI endpoint with cookie auth.

        W7/Netis routers authenticate CGI requests via Cookie: password=<base64>.
        This is entirely separate from the ubus_rpc_session token.
        """
        url = f"http://{self.host}{endpoint}"
        cookies = {}
        if hasattr(self, "_cgi_password"):
            cookies["password"] = self._cgi_password

        try:
            response = self.session.post(
                url, data=body, cookies=cookies, timeout=self.timeout
            )
        except requests.RequestException as e:
            logger.debug("CGI %s failed: %s", endpoint, e)
            return None

        if response.status_code != 200:
            logger.debug("CGI %s returned HTTP %d", endpoint, response.status_code)
            return None

        try:
            return response.json()
        except ValueError:
            logger.debug("CGI %s response is not JSON", endpoint)
            return None

    def _get_devices_cgi(self) -> list[dict]:
        """Get devices via Netis CGI endpoint (skk_get.cgi).

        W7/Netis routers use a proprietary CGI stack. POST /cgi-bin/skk_get.cgi
        returns system info + device lists (arpList, dhcpList, statsList).
        Falls back to /cgi-bin-igd/netcore_get.cgi for older firmware.

        Auth: Cookie: password=<base64>
        """
        devices: list[dict] = []

        data = self._fetch_cgi(
            "/cgi-bin/skk_get.cgi",
            {"mode_name": "skk_get", "wl_link": "0"},
        )

        if data:
            for source in ("arpList", "dhcpList", "statsList"):
                entries = data.get(source, data.get(source.lower(), []))
                if isinstance(entries, dict):
                    entries = list(entries.values())
                for entry in (entries if isinstance(entries, list) else []):
                    if isinstance(entry, dict):
                        devices.append({
                            "mac": entry.get("mac", entry.get("hwaddr", entry.get("hwAddr", ""))),
                            "ip": entry.get("ip", entry.get("ipaddr", entry.get("ipAddr", ""))),
                            "hostname": entry.get(
                                "hostname",
                                entry.get("name", entry.get("hostName", ""))
                            ),
                        })

        if not devices:
            data = self._fetch_cgi(
                "/cgi-bin-igd/netcore_get.cgi",
                {"mode_name": "netcore_get", "no": "no"},
            )
            if data:
                # Legacy response format varies — extract anything that looks like a device
                for key in ("dev_list", "dhcp_list", "arp_list", "client_list"):
                    entries = data.get(key, [])
                    if isinstance(entries, dict):
                        entries = list(entries.values())
                    for entry in (entries if isinstance(entries, list) else []):
                        if isinstance(entry, dict):
                            devices.append({
                                "mac": entry.get("mac", entry.get("hwaddr", "")),
                                "ip": entry.get("ip", ""),
                                "hostname": entry.get("hostname", entry.get("name", "")),
                            })

        if devices:
            logger.info("Found %d devices via CGI on %s", len(devices), self.host)
        else:
            logger.debug("No devices found via CGI on %s", self.host)

        return devices

    def _get_system_info_cgi(self) -> dict:
        """Get router system info via skk_get.cgi.

        W7/Netis routers return system info in the skk_get.cgi response,
        including version, model, uptime, CPU, memory, etc.
        """
        data = self._fetch_cgi(
            "/cgi-bin/skk_get.cgi",
            {"mode_name": "skk_get", "wl_link": "0"},
        )
        if not data:
            return {}

        info: dict = {}
        if "model" in data:
            info["model"] = data["model"]
        if "hostname" in data:
            info["hostname"] = data["hostname"]
        if "version" in data:
            info["firmware_version"] = data["version"]
        if "uptime" in data:
            info["uptime"] = data["uptime"]
        return info

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

        Tries standard OpenWrt system.board + system.info first,
        then falls back to W7/Netis proprietary system.info format
        which wraps data in a .values sub-object.

        Returns:
            Dict with keys: model, firmware_version, hostname, uptime.
        """
        logger.debug("Fetching system info from %s", self.host)

        info: dict = {}

        # Standard OpenWrt: system.board provides model, firmware, hostname
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

        # Standard OpenWrt: system.info provides uptime
        try:
            params = [self.auth_token or "", "system", "info", {}]
            result = self._rpc_call("call", params)

            if isinstance(result, list) and len(result) >= 2:
                sysinfo = result[1]
                if isinstance(sysinfo, dict):
                    # W7/Netis routers wrap data in .values (proprietary format)
                    values = sysinfo.get("values", sysinfo)
                    if isinstance(values, dict):
                        info["uptime"] = values.get("uptime", 0)
                        # W7 system.info also contains model/hostname
                        if not info.get("model") and values.get("model"):
                            info["model"] = values["model"]
                        if not info.get("hostname") and values.get("hostname"):
                            info["hostname"] = values["hostname"]
        except RouterError as e:
            logger.debug("system.info query failed: %s", e)

        info.setdefault("model", "")
        info.setdefault("firmware_version", "")
        info.setdefault("hostname", "")
        info.setdefault("uptime", 0)

        if not info["model"] and not info["uptime"]:
            cgi_info = self._get_system_info_cgi()
            if cgi_info:
                logger.info("Got system info via CGI from %s", self.host)
                for key in ("model", "firmware_version", "hostname", "uptime"):
                    if key in cgi_info and cgi_info[key]:
                        info[key] = cgi_info[key]

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
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "list",
                    "params": [],
                },
                timeout=5,
            )
            return response.status_code in (200, 401, 403)
        except requests.RequestException as e:
            logger.debug("Connection test failed: %s", e)
            return False

    def get_available_services(self) -> set[str]:
        """Discover ubus services accessible to the current session.

        Calls 'ubus list' with and without auth token to find what
        services and methods are available on this router.

        Returns:
            Set of service names (e.g. {'dhcp', 'system', 'network.interface'}).
        """
        logger.debug("Discovering available ubus services on %s", self.host)

        services: set[str] = set()

        for token in (self.auth_token, None):
            params = [token or "", "list", ""] if token else ["list", ""]
            try:
                result = self._rpc_call("list", params) if token else self._rpc_call(
                    "list", params
                )
                if isinstance(result, list) and len(result) >= 2:
                    data = result[1] if isinstance(result[1], dict) else {}
                    services.update(data.keys())
            except RouterError as e:
                logger.debug("ubus list query failed (token=%s): %s", bool(token), e)

        logger.info("Found %d accessible ubus services on %s", len(services), self.host)
        if services:
            logger.debug("Available services: %s", sorted(services))
        return services

    def _try_rpc_with_retry(self, service: str, method: str, params: dict) -> list | None:
        """Try an ubus call with auth token, retry without if denied.

        Returns None on failure, the result list on success.
        """
        if self.auth_token:
            try:
                result = self._rpc_call(
                    "call", [self.auth_token, service, method, params]
                )
                if isinstance(result, list) and len(result) >= 1:
                    return result
            except RouterAuthError:
                logger.debug(
                    "Permission denied for %s.%s with auth, retrying without",
                    service,
                    method,
                )
            except RouterError as e:
                logger.debug(
                    "Service %s.%s not found: %s", service, method, e
                )
                return None

        try:
            result = self._rpc_call(
                "call", ["00000000000000000000000000000000", service, method, params]
            )
            if isinstance(result, list) and len(result) >= 1:
                return result
        except RouterError as e:
            logger.debug("Service %s.%s unavailable (no auth): %s", service, method, e)

        return None