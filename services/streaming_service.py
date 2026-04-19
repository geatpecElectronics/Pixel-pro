# =============================================================
#  services/streaming_service.py
#
#  Internal   : mfvideosrc (local webcam on the PC)
#
#  WiFi flow  : camera.local:8888  → start command → stream on :5000
#  USB flow   : raspberrypi.local:8888 → start command → stream on :5000
#               (Pi runs in USB gadget / RNDIS mode — Windows sees it
#                as a USB Ethernet adapter; TCP works identically to WiFi)
#
#  Both WiFi and USB:
#    1. TCP connect host:8888
#    2. Send {"command": "start_wifi_stream"}
#    3. Camera binds port 5000, starts H.264/TS
#    4. GStreamer: tcpclientsrc host=<host> port=5000
#       ! tsdemux ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
#    5. If :8888 unreachable, retry every 5 s for 5 min, then call on_fail()
# =============================================================
import os, json, socket, subprocess, threading, ctypes, ctypes.wintypes, time

user32 = ctypes.windll.user32

# WiFi camera  — on local network
WIFI_HOST          = "camera.local"

# USB camera   — Pi in RNDIS/USB-gadget mode; Windows assigns a hostname
USB_HOST           = "raspberrypi.local"

STREAM_CMD_PORT    = 8888          # control port on both WiFi and USB camera
STREAM_VIDEO_PORT  = 5000          # GStreamer connects here after ACK
RETRY_INTERVAL     = 5             # seconds between retries
RETRY_TIMEOUT      = 300           # 5-minute total window
CONNECT_TIMEOUT    = 3             # per-attempt socket timeout


def _find_gst_bin():
    env = os.environ.get("MEDCAMPY_GST_BIN")
    if env and os.path.isdir(env): return env
    default = r"C:\Program Files\gstreamer\1.0\msvc_x86_64\bin"
    if os.path.isdir(default): return default
    return None


def _send_start_command(host: str) -> bool:
    """
    TCP-connect to host:8888, send start command.
    Returns True on success, False on any connection failure.
    Works identically for WiFi (camera.local) and USB (raspberrypi.local).
    """
    try:
        with socket.create_connection((host, STREAM_CMD_PORT),
                                      timeout=CONNECT_TIMEOUT) as s:
            payload = json.dumps({"command": "start_wifi_stream"}).encode()
            s.sendall(payload)
        return True
    except (OSError, ConnectionRefusedError, socket.timeout):
        return False


class _Service:
    def __init__(self):
        self._proc      = None
        self._win_hwnd  = None
        self._parent    = None
        self._fit       = None
        self._rec_proc  = None
        self._mode      = "internal"
        self._wifi_thread = None
        self._wifi_stop   = False   # set to True to cancel the retry loop

    # ── Public API ────────────────────────────────────────────

    def set_mode(self, mode: str):
        """Call this whenever the user switches the camera source radio button."""
        self._mode = mode

    def start(self, parent_hwnd: int, w: int, h: int,
              on_wifi_fail=None, on_wifi_status=None):
        """
        Start streaming.
        on_wifi_fail()          — called (via QTimer) when connection times out
        on_wifi_status(msg:str) — progress strings during retry loop
        """
        self.stop()
        self._parent = parent_hwnd

        if self._mode == "wifi":
            host = WIFI_HOST
            label = "WiFi"
        elif self._mode == "usb":
            host = USB_HOST
            label = "USB"
        else:
            # Internal webcam — synchronous, no handshake needed
            self._launch_gst_internal(parent_hwnd)
            return

        # WiFi and USB both use the same TCP-handshake + GStreamer flow
        self._wifi_stop = False
        self._wifi_thread = threading.Thread(
            target=self._connect_loop,
            args=(host, label, parent_hwnd, on_wifi_fail, on_wifi_status),
            daemon=True
        )
        self._wifi_thread.start()

    def stop(self):
        # Cancel any pending WiFi retry loop
        self._wifi_stop = True
        if self._proc:
            try: self._proc.terminate()
            except: pass
            self._proc = None
        self._win_hwnd = None

    def start_recording(self, path: str, win_id: int):
        self.stop_recording()
        gst = _find_gst_bin()
        if not gst: raise RuntimeError("GStreamer not found.")
        exe = os.path.join(gst, "gst-launch-1.0.exe")
        pipeline = (
            f"mfvideosrc ! videoconvert ! tee name=t "
            f"t. ! autovideosink sync=false "
            f"t. ! x264enc ! mp4mux ! filesink location=\"{path}\""
        )
        self._rec_proc = subprocess.Popen(
            [exe] + pipeline.split(),
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def stop_recording(self):
        if self._rec_proc:
            try: self._rec_proc.terminate()
            except: pass
            self._rec_proc = None

    # ── TCP handshake with retry (WiFi and USB) ───────────────

    def _connect_loop(self, host, label, parent_hwnd, on_fail, on_status):
        """
        Daemon thread: tries host:8888 every RETRY_INTERVAL seconds
        for RETRY_TIMEOUT seconds total.
        On success  → launches GStreamer pipeline against host:5000.
        On timeout  → fires on_fail().
        Works for both WiFi (camera.local) and USB (raspberrypi.local).
        """
        deadline = time.time() + RETRY_TIMEOUT
        attempt  = 0

        while not self._wifi_stop and time.time() < deadline:
            attempt  += 1
            remaining = int(deadline - time.time())

            if on_status:
                on_status(
                    f"Connecting to {label} camera... "
                    f"(attempt {attempt}, {remaining}s remaining)"
                )

            if _send_start_command(host):
                # Give camera 1 s to bind port 5000
                time.sleep(1.0)
                if self._wifi_stop:
                    return
                if on_status:
                    on_status(f"{label} camera connected. Starting stream...")
                self._launch_gst_tcp(host, parent_hwnd)
                return

            # Wait RETRY_INTERVAL seconds, honouring cancellation
            for _ in range(RETRY_INTERVAL * 10):
                if self._wifi_stop:
                    return
                time.sleep(0.1)

        # Timed out
        if not self._wifi_stop and on_fail:
            on_fail()

    # ── GStreamer launchers ───────────────────────────────────

    def _launch_gst_internal(self, parent_hwnd):
        """Internal / USB: mfvideosrc pipeline."""
        gst = _find_gst_bin()
        if not gst:
            raise RuntimeError(
                "GStreamer not found.\nInstall from gstreamer.freedesktop.org"
            )
        exe      = os.path.join(gst, "gst-launch-1.0.exe")
        pipeline = "mfvideosrc ! videoconvert ! autovideosink sync=false"
        self._proc = subprocess.Popen(
            [exe] + pipeline.split(),
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        proc = self._proc
        threading.Thread(target=self._reparent, args=(proc,), daemon=True).start()

    def _launch_gst_tcp(self, host: str, parent_hwnd: int):
        """
        TCP stream pipeline — used for both WiFi and USB gadget mode.
        Connects to host:5000, expects H.264 inside MPEG-TS.
        Pipeline:
          tcpclientsrc host=<host> port=5000
          ! tsdemux ! h264parse ! avdec_h264 ! videoconvert
          ! autovideosink sync=false ts-offset=-1
        """
        gst = _find_gst_bin()
        if not gst:
            return
        exe = os.path.join(gst, "gst-launch-1.0.exe")
        args = [
            exe,
            "tcpclientsrc", f"host={host}", f"port={STREAM_VIDEO_PORT}",
            "!", "tsdemux",
            "!", "h264parse",
            "!", "avdec_h264",
            "!", "videoconvert",
            "!", "autovideosink", "sync=false", "ts-offset=-1",
        ]
        self._proc = subprocess.Popen(
            args,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        proc = self._proc
        threading.Thread(target=self._reparent, args=(proc,), daemon=True).start()

    # ── Window reparenting helpers ────────────────────────────

    def _reparent(self, proc):
        """Receives proc as argument — immune to self._proc being cleared by stop()."""
        for _ in range(40):
            time.sleep(0.25)
            if proc.poll() is not None:
                return
            hwnd = self._find_window(proc.pid)
            if hwnd:
                self._win_hwnd = hwnd
                GWL_STYLE = -16
                WS_CHILD  = 0x40000000
                user32.SetWindowLongW(hwnd, GWL_STYLE, WS_CHILD)
                user32.SetParent(hwnd, self._parent)
                self._fit = threading.Thread(
                    target=self._fit_loop, daemon=True
                )
                self._fit.start()
                return

    def _find_window(self, pid):
        result = []
        def cb(hwnd, _):
            wpid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
            if wpid.value == pid and user32.IsWindowVisible(hwnd):
                result.append(hwnd)
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
        )
        user32.EnumWindows(WNDENUMPROC(cb), 0)
        return result[0] if result else None

    def _fit_loop(self):
        while self._proc and self._proc.poll() is None and self._win_hwnd:
            try:
                r = ctypes.wintypes.RECT()
                user32.GetClientRect(self._parent, ctypes.byref(r))
                user32.SetWindowPos(
                    self._win_hwnd, None, 0, 0, r.right, r.bottom, 0x0040
                )
            except: pass
            time.sleep(0.5)


StreamingService = _Service()
