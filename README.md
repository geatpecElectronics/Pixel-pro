PIXEL PRO
Medical Imaging & Patient Management Platform
Built for Labomed Imaging Systems

Overview
Pixel Pro is a Windows desktop application for medical imaging and patient management, developed for Labomed imaging systems. It enables clinicians to register patients, conduct visits, capture and annotate camera images, generate clinical PDF reports, and connect to imaging cameras via internal webcam, WiFi, or USB.

Product	Pixel Pro
Publisher	Labomed
Version	1.0.0
Platform	Windows 10 / 11  (64-bit)
Architecture	Python 3.11  +  PyQt6  +  GStreamer
Database	SQLite  (local, portable)
Build output	PixelPro_Setup.exe  (~300 MB, self-contained)

Key Features

👥  Patient Management
Register, search, edit, and soft-delete patients with full demographic records.	📅  Visit Tracking
Create and manage clinical visits per patient. Attach notes, doctor, and department.
📷  Camera Capture
Capture frames from internal webcam, WiFi camera, or Raspberry Pi USB gadget mode.	✏️  Annotation Editor
Non-destructive annotation tools: arrows, text, rectangles, freehand, circles.
📄  PDF Report Builder
Generate branded A4 clinical reports with images, observations, and diagnosis.	🏥  Hospital Profile
Global hospital identity (name, logo, address) auto-filled on every report.
📡  WiFi Camera
TCP handshake on port 8888, H.264/TS stream on port 5000 via GStreamer.	🔌  USB Camera
Raspberry Pi RNDIS/USB gadget mode - same TCP protocol over USB-Ethernet.
🖥  PACS / DICOM
PACS server configuration and DICOM export (placeholder, ready for pynetdicom).	🔐  User Auth
Login and registration with per-user sessions and role isolation.

Screen Flow
All screens are managed within a single window (QStackedWidget) — no separate windows open.

•	Login  /  Register
•	Dashboard  —  stats, quick actions, recent visits
•	Patient Manager  —  list, search, add, edit, delete
•	Visit Manager  —  visit list per patient, new visit form
•	Camera Capture  —  live feed, capture, thumbnail strip
◦	Annotation Editor  (opens as separate tool window)
•	Report Builder  —  image selection, report fields, PDF export
•	PACS Manager  —  DICOM server config

Technology Stack

Component	Technology	Purpose
UI Framework	PyQt6 6.4+	All windows, widgets, signals/slots
Database	SQLAlchemy 2.0	ORM, SQLite backend, RLS patterns
Camera / Video	GStreamer 1.x	Webcam, WiFi stream, H.264 decode, recording
PDF Reports	ReportLab 4.0	A4 clinical report generation
Medical Imaging	pydicom	DICOM read/write and PACS export
Image Processing	Pillow	Image manipulation, thumbnails
Packaging	PyInstaller 6.x	Frozen Windows executable, all deps bundled
Installer	NSIS 3.x	One-click setup with VC++ and driver install

Project Structure

Path	Contents
app.py	Entry point. Sets up Qt app, palette, data dir, launches shell.
build_exe.py	One-command build script. Produces PixelPro_Setup.exe.
models/database.py	SQLAlchemy models: User, Patient, Visit, CapturedImage, SavedReport, HospitalProfile, PACSConfig.
services/streaming_service.py	GStreamer process manager. Handles internal, WiFi, and USB camera modes with TCP handshake and retry loop.
ui/main_shell.py	Single QMainWindow shell with QStackedWidget. All navigation goes through shell.navigate().
ui/dashboard_window.py	Dashboard stats, quick actions, recent visits. Contains DashboardPage.
ui/patient_manager.py	Patient list, search, add/edit form. Contains PatientManagerPage.
ui/visit_manager.py	Visit list and new visit form. Contains VisitManagerPage.
ui/camera_capture.py	Camera feed, source selection, capture, image strip. Contains CameraPage.
ui/annotation_editor.py	Non-destructive annotation tool. Opens as separate window.
ui/report_builder.py	Image selection, report fields, PDF export. Contains ReportPage.
ui/pacs_manager.py	PACS server config and DICOM upload. Contains PACSPage.
ui/pixel_pro_report_generator.py	ReportLab PDF builder. Sections: patient, medical, images, observations, diagnosis, doctor.
installer/PixelPro.nsi	NSIS installer script. Installs VC++ runtime, RNDIS driver, shortcuts, ARP entry.
assets/	logo.png, logo.ico

Database Schema
Database location: %APPDATA%\Labomed\PixelPro\pixelpro.db  (created automatically on first launch)

•	User  —  id, username, password, email, specialization, is_active, is_deleted
•	Patient  —  id, patient_id (PT-0001), first_name, last_name, dob, gender, phone, address, ref_doc, notes, blood_group, current_medication, existing_medical, past_medical_history, allergies, email_id, created_at, is_active, is_deleted
•	Visit  —  id, visit_id (VS-0001), patient_id (FK), visit_date, doctor, department, clinical_notes, is_deleted
•	CapturedImage  —  id, visit_id (FK), file_path, annotated_path, annotation_data (JSON), selected_for_report, sort_order, captured_at, camera_source, is_deleted
•	SavedReport  —  id, visit_id (FK), hospital, department, doctor, address, observations, diagnosis, notes, signature, report_html, saved_at, is_deleted
•	HospitalProfile  —  id, name, address, email, phone, logo_path, updated_at  (single global row)
•	PACSConfig  —  id, name, pacs_ip, pacs_port, ae_title, local_ae_title, institution, modality, is_active

Camera Modes
Internal / USB Webcam
Uses Windows Media Foundation (mfvideosrc) via GStreamer. Plug-and-play, no configuration needed.

WiFi Camera
•	TCP connect to camera.local:8888
•	Send JSON command: {"command": "start_wifi_stream"}
•	Camera starts H.264/MPEG-TS stream on port 5000
•	GStreamer pipeline: tcpclientsrc host=camera.local port=5000 ! tsdemux ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
•	Auto-retry every 5 seconds for up to 5 minutes. Shows 'WiFi camera not available' on timeout.

USB Camera (Raspberry Pi Gadget Mode)
•	Same TCP protocol as WiFi but connects to raspberrypi.local:8888
•	Requires Pi configured with dtoverlay=dwc2 and modules-load=dwc2,g_ether
•	Requires RNDIS USB driver on Windows (available via Windows Update)
•	Once driver is installed, behaves identically to WiFi mode

Building the Installer
Prerequisites (build machine only)
•	Python 3.10+  —  python.org  (tick 'Add to PATH')
•	GStreamer COMPLETE (MSVC 64-bit)  —  gstreamer.freedesktop.org/download
◦	Install path: C:\Program Files\gstreamer\1.0\msvc_x86_64
◦	Choose COMPLETE, not Runtime
•	NSIS 3.x  —  nsis.sourceforge.io/Download
•	VC++ 2022 Redistributable  —  aka.ms/vs/17/release/vc_redist.x64.exe
◦	Save to: installer\vc_redist.x64.exe
•	Python packages:
◦	pip install pyinstaller pillow reportlab pydicom

Build Command
cd C:\MedCamPy
python build_exe.py

Output: installer\PixelPro_Setup.exe  (~300 MB)  — share this single file worldwide.

What the installer does on end-user machines
•	Installs PixelPro.exe and all files to C:\Program Files\Labomed\PixelPro\
•	Silently installs VC++ 2022 Runtime if not already present
•	Installs RNDIS USB driver if bundled (otherwise writes setup guide)
•	Creates Desktop shortcut and Start Menu entry
•	Adds entry to Add/Remove Programs with uninstaller

Installation (End User)
No Python, no GStreamer, no manual dependencies. Everything is bundled.

1.	Download PixelPro_Setup.exe
2.	Double-click and follow the wizard (Next > Next > Install > Finish)
3.	Launch from Desktop shortcut or Start Menu > Labomed > Pixel Pro

Data location: %APPDATA%\Labomed\PixelPro\  (preserved through uninstall/reinstall)

Development Setup
To run from source without building an installer:

cd C:\MedCamPy
pip install -r requirements.txt
python app.py

Requirements:
•	Python 3.10+
•	GStreamer COMPLETE installed at default path
•	All packages in requirements.txt

Key Design Decisions
•	Single-window architecture  —  QMainWindow + QStackedWidget. No popup windows except the annotation editor.
◦	All navigation via shell.navigate('page', **kwargs)
◦	Volatile pages (camera, report, visits) are rebuilt on each navigation
•	Portable data directory  —  database and saved images in %APPDATA%, not Program Files.
◦	Works without admin rights after install
◦	Survives uninstall/reinstall
•	is_deleted != True pattern  —  all queries use filter(Model.is_deleted != True).
◦	SQLite ALTER TABLE sets NULL (not False) for new boolean columns on existing rows
◦	filter_by(is_deleted=False) would miss NULL rows
•	expire_on_commit=False  —  prevents DetachedInstanceError when ORM objects are used after session.close().
•	GStreamer process isolation  —  gst-launch-1.0.exe runs as a subprocess and its window is reparented into the Qt video frame via Win32 API.
•	WiFi/USB camera retry loop  —  runs in a daemon thread. Retries port 8888 every 5 s for 5 min. Uses QTimer.singleShot to bounce callbacks to Qt main thread.

Known Limitations & Pending Features
•	PACS / DICOM export  —  UI and config are complete; pynetdicom C-STORE/C-FIND wiring is pending.
•	WiFi/USB camera  —  requires a compatible streaming server on the Raspberry Pi side (port 8888 command + port 5000 H.264/TS stream).
•	Annotation drag-reorder  —  image reordering in the report builder is not yet implemented.
•	Session crash recovery  —  no auto-restore of in-progress visits after unexpected close.
•	Windows only  —  GStreamer pipeline uses mfvideosrc and Win32 window reparenting. Linux/macOS not supported.

Support & Contact

Developer	GEATPEC Electronics Pvt. Ltd. (GEPL)
Client	Labomed
Website	labomed.com
Platform	Windows 10 / 11 (64-bit only)
License	Proprietary — Labomed. See installer\LICENSE.txt

Changelog
v1.0.0  (2026)
•	Initial production release
•	Single-window shell architecture with QStackedWidget
•	Patient, Visit, Camera, Annotation, Report, PACS modules
•	WiFi and USB camera with TCP handshake and 5-minute retry loop
•	ReportLab PDF generator with branded A4 report layout
•	PyInstaller + NSIS installer with bundled GStreamer and VC++ runtime
•	Portable AppData database path
•	Fusion light palette to override Windows dark mode
