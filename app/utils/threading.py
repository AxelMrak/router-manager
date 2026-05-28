from PySide6.QtCore import QThread, Signal, QObject
import traceback
import logging

logger = logging.getLogger(__name__)

class WorkerThread(QThread):
    """Generic worker thread that runs a callable and emits result/error."""
    
    result = Signal(object)
    error = Signal(str, str)  # title, message
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.result.emit(result)
        except Exception as e:
            logger.error(f"Worker thread error: {e}\n{traceback.format_exc()}")
            self.error.emit("Operation Failed", str(e))

class PollingWorker(QThread):
    """Background polling worker for router data."""
    
    devices_fetched = Signal(list)     # list of raw device dicts
    schedules_fetched = Signal(list)   # list of raw schedule dicts
    system_info_fetched = Signal(dict) # raw system info dict
    connection_lost = Signal(str)      # error message
    connection_restored = Signal()
    
    def __init__(self, router_client, interval: int = 10):
        super().__init__()
        self.router_client = router_client
        self.interval = interval
        self._running = True
        self._was_connected = False
    
    def run(self):
        import time
        while self._running:
            try:
                if not self.router_client.auth_token:
                    self.router_client.login()
                    if not self._was_connected:
                        self.connection_restored.emit()
                        self._was_connected = True
                
                devices = self.router_client.get_devices()
                self.devices_fetched.emit(devices)
                
                schedules = self.router_client.get_schedules()
                self.schedules_fetched.emit(schedules)
                
                try:
                    sys_info = self.router_client.get_system_info()
                    self.system_info_fetched.emit(sys_info)
                except Exception:
                    pass  # System info is optional
                
            except Exception as e:
                if self._was_connected:
                    self.connection_lost.emit(str(e))
                    self._was_connected = False
                logger.error(f"Polling error: {e}")
            
            # Sleep in small increments for responsive shutdown
            for _ in range(self.interval * 10):
                if not self._running:
                    break
                time.sleep(0.1)
    
    def stop(self):
        self._running = False
        self.wait(3000)