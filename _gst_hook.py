
import os, sys

if getattr(sys, "frozen", False):
    _base        = sys._MEIPASS
    _gst_bin     = os.path.join(_base, "gstreamer", "bin")
    _gst_plugins = os.path.join(_base, "gstreamer", "plugins")

    os.environ["PATH"]                   = _gst_bin + os.pathsep + os.environ.get("PATH", "")
    os.environ["GST_PLUGIN_PATH"]        = _gst_plugins
    os.environ["GST_PLUGIN_SYSTEM_PATH"] = _gst_plugins
    os.environ["MEDCAMPY_GST_BIN"]       = _gst_bin

    _cache = os.path.join(
        os.environ.get("LOCALAPPDATA", _base),
        "Labomed", "PixelPro", "gst_registry.bin"
    )
    os.makedirs(os.path.dirname(_cache), exist_ok=True)
    os.environ["GST_REGISTRY"] = _cache
