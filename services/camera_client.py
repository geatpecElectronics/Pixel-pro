# =============================================================
#  services/camera_client.py
#  Equivalent to MedCamApp/Commands/CameraCommandClient.cs
#
#  Sends JSON commands to Labomed camera on:
#    host: camera.local
#    port: 8888  (TCP, newline-terminated JSON)
# =============================================================

import socket
import json
import asyncio
from typing import Optional


CAMERA_HOST = "camera.local"
CAMERA_PORT = 8888
TIMEOUT_SEC = 3.0


def _send_command(payload: dict) -> Optional[str]:
    """
    Synchronous TCP send.  Returns response text or None on error.
    The camera expects:  JSON + newline
    """
    try:
        data = (json.dumps(payload) + "\n").encode("utf-8")
        with socket.create_connection((CAMERA_HOST, CAMERA_PORT), timeout=TIMEOUT_SEC) as sock:
            sock.sendall(data)
            # Try to read response (best-effort, 4 KB)
            try:
                sock.settimeout(1.0)
                return sock.recv(4096).decode("utf-8")
            except Exception:
                return None
    except Exception as e:
        print(f"[CameraClient] ERROR: {e}")
        return None


async def send_command_async(payload: dict) -> Optional[str]:
    """Async wrapper – runs _send_command in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _send_command, payload)


# ── 1. Start WiFi stream ─────────────────────────────────────
def start_wifi_stream():
    return _send_command({"command": "start_wifi_stream", "params": {}})


# ── 2. Stop stream ───────────────────────────────────────────
def stop_stream():
    return _send_command({"command": "stop_stream", "params": {}})


# ── 3. Exposure & Gain ───────────────────────────────────────
def set_exposure(auto_enable: bool, ev: float = 0.0,
                 exposure_time: int = 25000, analogue_gain: float = 1.0):
    params = {"auto_enable": auto_enable}
    if auto_enable:
        params["ev"] = ev
    else:
        params["exposure_time"] = exposure_time
        params["analogue_gain"] = analogue_gain
    return _send_command({"command": "set_exposure", "params": params})


# ── 4. White Balance (AWB) ───────────────────────────────────
def set_awb(awb_enable: bool, red_gain: float = 1.0,
            blue_gain: float = 1.0, green_gain: float = 1.0):
    return _send_command({
        "command": "set_awb",
        "params": {
            "awb_enable": awb_enable,
            "red_gain":   red_gain,
            "blue_gain":  blue_gain,
            "green_gain": green_gain,
        }
    })


# ── 5. Orientation / Flip ────────────────────────────────────
def set_orientation(hflip: bool, vflip: bool, rotation: int = 0):
    return _send_command({
        "command": "set_orientation",
        "params": {"hflip": hflip, "vflip": vflip, "rotation": rotation}
    })


# ── 6. Resolution & FPS ─────────────────────────────────────
def set_format(res_index: int, fps_index: int):
    # res_index: 0=1920x1080, 1=3840x2160
    # fps_index: 0=30fps,     1=60fps
    return _send_command({
        "command": "set_format",
        "params": {"res_index": res_index, "fps_index": fps_index}
    })


# ── 7. ISP (contrast, saturation, sharpness, brightness) ────
def set_isp(contrast: float, saturation: float,
            sharpness: float, brightness: float):
    return _send_command({
        "command": "set_isp",
        "params": {
            "contrast":   round(contrast,   2),
            "saturation": round(saturation, 2),
            "sharpness":  round(sharpness,  2),
            "brightness": round(brightness, 2),
        }
    })


# ── 8. Ping ──────────────────────────────────────────────────
def ping() -> bool:
    result = _send_command({"command": "ping", "params": {}})
    return result is not None


# ── 9. Get status ────────────────────────────────────────────
def get_status() -> Optional[str]:
    return _send_command({"command": "get_status", "params": {}})
