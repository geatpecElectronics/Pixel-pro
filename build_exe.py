# =============================================================
#  build_exe.py  —  Pixel Pro one-command builder
#
#  Run on your Windows build machine:
#      cd C:\MedCamPy
#      python build_exe.py
#
#  Output:
#      installer\PixelPro_Setup.exe   (~250-350 MB)
#
#  What the installer gives the end user (no manual steps):
#    - PixelPro.exe         (no Python needed)
#    - GStreamer DLLs       (bundled — no separate install)
#    - VC++ 2022 Runtime    (silently installed if missing)
#    - RNDIS USB driver     (silently installed for USB camera)
#    - Desktop + Start Menu shortcuts
#    - Add/Remove Programs entry + full uninstaller
#
#  PREREQUISITES on your build PC (one-time setup):
#    1. Python 3.10+
#         https://python.org  (tick "Add to PATH")
#    2. pip install pyinstaller pillow reportlab pydicom
#    3. GStreamer COMPLETE (MSVC 64-bit)
#         https://gstreamer.freedesktop.org/download/
#         Install path: C:\Program Files\gstreamer\1.0\msvc_x86_64
#    4. NSIS 3.x
#         https://nsis.sourceforge.io/Download
#    5. VC++ 2022 Redistributable installer (for bundling)
#         https://aka.ms/vs/17/release/vc_redist.x64.exe
#         Save to: installer\vc_redist.x64.exe
#    6. RNDIS driver zip (for USB camera — already in your repo)
#         installer\drivers\mod-duo-rndis.zip
# =============================================================

import os, sys, shutil, subprocess, textwrap

# ── Config ────────────────────────────────────────────────────
APP_NAME    = "PixelPro"
APP_VERSION = "1.0.0"   # plain semver only — do not read from VERSION.txt
ENTRY       = "app.py"
ICON        = r"assets\logo.ico"

GST_ROOT    = r"C:\Program Files\gstreamer\1.0\msvc_x86_64"
GST_BIN     = os.path.join(GST_ROOT, "bin")
GST_LIB     = os.path.join(GST_ROOT, "lib")

# GStreamer plugins can be in different locations depending on install type.
# Check all known locations and use whichever exists.
_plugin_candidates = [
    os.path.join(GST_LIB, "gstreamer-1.0"),          # standard COMPLETE install
    os.path.join(GST_BIN, "gstreamer-1.0"),           # some installs put them in bin
    os.path.join(GST_ROOT, "lib", "gstreamer-1.0"),
    os.path.join(GST_ROOT, "bin"),                    # flat layout fallback
]
GST_PLUGINS = next(
    (p for p in _plugin_candidates
     if os.path.isdir(p) and any(f.endswith(".dll") for f in os.listdir(p))),
    os.path.join(GST_LIB, "gstreamer-1.0")           # default (will warn if missing)
)

NSIS_PATHS  = [
    r"C:\Program Files (x86)\NSIS\makensis.exe",
    r"C:\Program Files\NSIS\makensis.exe",
]

# GStreamer plugins Pixel Pro needs
REQUIRED_PLUGINS = [
    "libgstcoreelements",       # filesrc, filesink, tee, queue
    "libgstapp",
    "libgstmediafoundation",    # mfvideosrc — Windows webcam
    "libgstwinks",              # ksvideosrc — fallback
    "libgstautodetect",         # autovideosink
    "libgstd3d11",              # D3D11 GPU sink
    "libgstd3dvideo",
    "libgstvideoconvert",
    "libgstvideofilter",
    "libgstvideoscale",
    "libgstvideorate",
    "libgsttcp",                # tcpclientsrc — WiFi / USB gadget stream
    "libgstudp",
    "libgstisomp4",             # mp4mux, qtdemux
    "libgstmpegtsmux",          # mpegtsmux
    "libgstmpegtsdemux",        # tsdemux
    "libgstlibav",              # avdec_h264 (FFmpeg H.264 decoder)
    "libgstx264",               # x264enc — recording
    "libgstopenh264",
    "libgstvideoparsersbad",    # h264parse lives here
    "libgstpng",
    "libgstjpeg",
    "libgstplayback",
    "libgsttypefindfunctions",
    "libgstrawparse",
    "libgstvideotestsrc",
    "libgstdirectsound",
    "libgstwasapi",
    "libgstaudiotestsrc",
]


# ── Helpers ───────────────────────────────────────────────────
def banner(n, total, msg):
    print(f"\n{'='*62}\n  [{n}/{total}]  {msg}\n{'='*62}")

def ok(msg):   print(f"  OK   {msg}")
def warn(msg): print(f"  WARN {msg}")
def die(msg):  print(f"\n  FAIL {msg}\n"); sys.exit(1)


# ── 1. Prerequisites ──────────────────────────────────────────
banner(1, 7, "Checking prerequisites")

if not os.path.exists(ICON):
    die(f"Icon not found: {ICON}")
ok(f"Icon: {ICON}")

if not os.path.isdir(GST_BIN):
    die(
        f"GStreamer not found at:\n  {GST_ROOT}\n\n"
        "  Install COMPLETE (not Runtime) from:\n"
        "  https://gstreamer.freedesktop.org/download/\n"
        "  Architecture: MSVC 64-bit"
    )
ok(f"GStreamer: {GST_ROOT}")

try:
    import PyInstaller
    ok(f"PyInstaller {PyInstaller.__version__}")
except ImportError:
    die("PyInstaller missing.  Run:  pip install pyinstaller")

MAKENSIS = next((p for p in NSIS_PATHS if os.path.exists(p)), None)
if MAKENSIS:
    ok(f"NSIS: {MAKENSIS}")
else:
    warn("NSIS not found — installer won't be built.")

VC_REDIST = os.path.join("installer", "vc_redist.x64.exe")
if os.path.exists(VC_REDIST):
    ok(f"VC++ redist: {VC_REDIST}")
else:
    warn(
        "VC++ redist not found at installer\\vc_redist.x64.exe\n"
        "  Download: https://aka.ms/vs/17/release/vc_redist.x64.exe\n"
        "  Save to installer\\vc_redist.x64.exe\n"
        "  Without it the installer won't auto-install the VC runtime."
    )

RNDIS_DRIVER = os.path.join("installer", "drivers", "mod-duo-rndis.inf")
if os.path.exists(RNDIS_DRIVER):
    ok(f"RNDIS driver: {RNDIS_DRIVER}  (will be bundled + auto-installed)")
else:
    warn(
        "RNDIS driver not found — USB camera driver won't be auto-installed.\n"
        "  The installer will still work. End users can get the driver via:\n"
        "    Windows Update -> View optional updates -> USB RNDIS Gadget\n"
        "  OR download from:\n"
        "    https://github.com/albert-fit/windows_10_raspi_usb_otg_fix\n"
        "  To bundle it: extract mod-duo-rndis.zip into installer\\drivers\\"
    )


# ── 2. Collect GStreamer files ────────────────────────────────
banner(2, 7, "Collecting GStreamer files")

bin_dlls = [
    os.path.join(GST_BIN, f)
    for f in os.listdir(GST_BIN)
    if f.lower().endswith(".dll")
]
ok(f"GStreamer bin DLLs: {len(bin_dlls)}")
ok(f"GStreamer plugins dir: {GST_PLUGINS}")

gst_launch = os.path.join(GST_BIN, "gst-launch-1.0.exe")
if not os.path.exists(gst_launch):
    die(f"gst-launch-1.0.exe not found in {GST_BIN}")
ok("gst-launch-1.0.exe found")

# Named plugins first, then ALL remaining plugins for full compatibility
# Exclude gstpython.dll — it requires a specific Python version (causes warning)
EXCLUDE_PLUGINS = {"gstpython.dll"}

plugin_dlls = []
for name in REQUIRED_PLUGINS:
    path = os.path.join(GST_PLUGINS, name + ".dll")
    if os.path.exists(path):
        plugin_dlls.append(path)
    else:
        warn(f"Plugin not found (skipping): {name}.dll")

named_set = set(plugin_dlls)
for f in os.listdir(GST_PLUGINS):
    if f.lower().endswith(".dll") and f.lower() not in EXCLUDE_PLUGINS:
        full = os.path.join(GST_PLUGINS, f)
        if full not in named_set:
            plugin_dlls.append(full)

ok(f"Plugin DLLs total: {len(plugin_dlls)}")

gir_dir   = os.path.join(GST_LIB, "girepository-1.0")
gir_files = []
if os.path.isdir(gir_dir):
    gir_files = [os.path.join(gir_dir, f) for f in os.listdir(gir_dir)]
    ok(f"GIR typelibs: {len(gir_files)}")


# ── 3. Runtime hook ───────────────────────────────────────────
banner(3, 7, "Writing PyInstaller runtime hook")

hook_code = textwrap.dedent(r"""
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
""")

with open("_gst_hook.py", "w") as f:
    f.write(hook_code)
ok("_gst_hook.py written")


# ── 4. PyInstaller spec ───────────────────────────────────────
banner(4, 7, "Writing PyInstaller spec")

def _dl(pairs):
    return ",\n        ".join(f"({repr(s)}, {repr(d)})" for s, d in pairs)

datas = [
    ("assets",   "assets"),
    ("models",   "models"),
    ("ui",       "ui"),
    ("services", "services"),
    ("utils",    "utils"),
    (gst_launch, "gstreamer/bin"),
]
datas += [(d, "gstreamer/bin")     for d in bin_dlls]
datas += [(d, "gstreamer/plugins") for d in plugin_dlls]
datas += [(f, "gstreamer/gir")     for f in gir_files]

spec = f"""# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['{ENTRY}'],
    pathex=['.'],
    binaries=[],
    datas=[
        {_dl(datas)}
    ],
    hiddenimports=[
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.orm',
        'sqlalchemy.sql.default_comparator',
        'sqlalchemy.ext.declarative',
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        'PyQt6.QtPrintSupport', 'PyQt6.sip',
        'reportlab', 'reportlab.platypus', 'reportlab.lib',
        'reportlab.lib.pagesizes', 'reportlab.lib.styles',
        'reportlab.lib.units', 'reportlab.pdfgen',
        'PIL', 'PIL.Image',
    ],
    hookspath=[],
    runtime_hooks=['_gst_hook.py'],
    excludes=['tkinter','matplotlib','scipy','pandas','IPython',
              'notebook','pytest','sphinx'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=r'{ICON}',
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False,
    upx=False,
    name='{APP_NAME}',
)
"""

with open("PixelPro.spec", "w") as f: f.write(spec)

# Remove any stale version_info.txt from previous builds — it causes crashes
if os.path.exists("version_info.txt"):
    os.remove("version_info.txt")

ok("PixelPro.spec written")


# ── 5. Pre-flight: verify all app imports work ────────────────
banner(5, 7, "Pre-flight import check")

required_packages = [
    ("PyQt6",       "PyQt6"),
    ("sqlalchemy",  "SQLAlchemy"),
    ("PIL",         "Pillow"),
    ("reportlab",   "reportlab"),
    ("pydicom",     "pydicom"),
]

all_ok = True
for mod, pkg in required_packages:
    try:
        __import__(mod)
        ok(f"{pkg}")
    except ImportError:
        warn(f"{pkg} NOT INSTALLED  ->  run:  pip install {pkg}")
        all_ok = False

if not all_ok:
    die(
        "Missing packages above. Install them with pip then re-run.\n"
        "  pip install PyQt6 SQLAlchemy Pillow reportlab pydicom pyinstaller"
    )


# ── 6. PyInstaller ────────────────────────────────────────────
banner(6, 7, "Running PyInstaller  (5-10 min)")
print("  Full output shown below. Look for 'ERROR' or 'ModuleNotFound'.\n")

r = subprocess.run(
    [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
     "--log-level=WARN", "PixelPro.spec"],
    check=False
)
if r.returncode != 0:
    print("""
  PyInstaller failed. Common causes and fixes:

  1. Missing package
       Look above for lines like: ModuleNotFoundError / ImportError
       Fix: pip install <package-name>

  2. Bad file path in datas
       Look for: FileNotFoundError or "no such file"
       This means a GStreamer DLL path doesn't exist
       Fix: confirm GStreamer is installed at:
            C:\\Program Files\\gstreamer\\1.0\\msvc_x86_64

  3. PyInstaller too old
       Fix: pip install --upgrade pyinstaller

  4. To see full debug output, run manually:
       pyinstaller --clean --log-level=DEBUG PixelPro.spec > debug.txt 2>&1
       notepad debug.txt
""")
    die(f"PyInstaller failed (code {r.returncode})")

exe_path = os.path.join("dist", APP_NAME, APP_NAME + ".exe")
if not os.path.exists(exe_path):
    die(f"Expected exe not found: {exe_path}")
ok(f"Exe: {exe_path}  ({os.path.getsize(exe_path)/1e6:.0f} MB)")


# ── 6. Stage installer\drivers ───────────────────────────────
banner(7, 8, "Staging installer assets")

os.makedirs("installer", exist_ok=True)
os.makedirs(os.path.join("installer", "drivers"), exist_ok=True)

# Write the RNDIS .inf installer helper script (extracted at runtime by NSIS)
rndis_install_bat = textwrap.dedent(r"""
@echo off
:: Install RNDIS driver silently using pnputil (built into Windows 10/11)
:: Called by the NSIS installer with admin rights
set DRIVER_DIR=%~dp0
pnputil /add-driver "%DRIVER_DIR%mod-duo-rndis.inf" /install >nul 2>&1
exit /b 0
""")
with open(os.path.join("installer", "drivers", "install_rndis.bat"), "w") as f:
    f.write(rndis_install_bat)
ok("install_rndis.bat written")


# ── 7. NSIS installer ─────────────────────────────────────────
banner(8, 8, "Building NSIS installer")

if not MAKENSIS:
    print("""
  Skipped (NSIS not found).

  Portable zip still works — just ZIP dist\\PixelPro\\ and share it.
  To build the proper installer:
    1. Install NSIS from https://nsis.sourceforge.io/Download
    2. Re-run: python build_exe.py
""")
    sys.exit(0)

nsi_path = os.path.join("installer", "PixelPro.nsi")
r = subprocess.run([MAKENSIS, nsi_path], check=False)

if r.returncode != 0:
    die(f"NSIS failed (code {r.returncode})")

setup_path = os.path.join("installer", "PixelPro_Setup.exe")
size_mb = os.path.getsize(setup_path) / 1e6 if os.path.exists(setup_path) else 0

print(f"""
{'='*62}
  BUILD COMPLETE

  installer\\PixelPro_Setup.exe   ({size_mb:.0f} MB)

  Share this ONE file.  End user: double-click -> Next -> Finish.

  Auto-installed on the target machine:
    PixelPro.exe       (Python not needed)
    GStreamer          (bundled, no install needed)
    VC++ 2022 Runtime  (silent, if missing)
    RNDIS USB driver   (silent, for USB camera)
    Shortcuts + ARP entry + Uninstaller
{'='*62}
""")
