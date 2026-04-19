; =============================================================
;  MedCamPy — NSIS Installer Script
;  Produces: MedCamPy_Setup.exe
;
;  Features:
;   - Branded install wizard (Labomed)
;   - Installs to C:\Program Files\Labomed\MedCamPy\
;   - Desktop shortcut with icon
;   - Start Menu: Labomed > MedCamPy
;   - Add/Remove Programs entry
;   - Full uninstaller
;   - Silent install: MedCamPy_Setup.exe /S
; =============================================================

!include "MUI2.nsh"
!include "LogicLib.nsh"

; ── App metadata ──────────────────────────────────────────────
!define APP_NAME      "MedCamPy"
!define APP_VERSION   "1.0.0"
!define APP_PUBLISHER "Labomed"
!define APP_URL       "https://labomed.com"
!define APP_EXE       "MedCamPy.exe"
!define REG_UNINSTALL "Software\Microsoft\Windows\CurrentVersion\Uninstall\MedCamPy"

!define MUI_ICON   "..\assets\logo.ico"
!define MUI_UNICON "..\assets\logo.ico"

; ── Output ────────────────────────────────────────────────────
Name              "${APP_NAME} ${APP_VERSION}"
OutFile           "MedCamPy_Setup.exe"
InstallDir        "$PROGRAMFILES64\Labomed\MedCamPy"
InstallDirRegKey  HKLM "${REG_UNINSTALL}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor     /SOLID lzma
Unicode           true

; ── MUI config ───────────────────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE    "Welcome to MedCamPy ${APP_VERSION} Setup"
!define MUI_WELCOMEPAGE_TEXT     "This wizard will install MedCamPy on your computer.$\r$\n$\r$\nMedCamPy is a medical camera and patient management application for Labomed imaging systems.$\r$\n$\r$\nClick Next to continue."
!define MUI_FINISHPAGE_RUN       "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT  "Launch MedCamPy"

; ── Installer pages ───────────────────────────────────────────
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE    "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; ── Uninstaller pages ─────────────────────────────────────────
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ── Install ───────────────────────────────────────────────────
Section "MedCamPy" SecMain
  SectionIn RO

  SetOutPath "$INSTDIR"
  File /r "..\dist\MedCamPy\*.*"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Add/Remove Programs
  WriteRegStr   HKLM "${REG_UNINSTALL}" "DisplayName"          "${APP_NAME}"
  WriteRegStr   HKLM "${REG_UNINSTALL}" "DisplayVersion"       "${APP_VERSION}"
  WriteRegStr   HKLM "${REG_UNINSTALL}" "Publisher"            "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${REG_UNINSTALL}" "URLInfoAbout"         "${APP_URL}"
  WriteRegStr   HKLM "${REG_UNINSTALL}" "InstallLocation"      "$INSTDIR"
  WriteRegStr   HKLM "${REG_UNINSTALL}" "UninstallString"      '"$INSTDIR\Uninstall.exe"'
  WriteRegStr   HKLM "${REG_UNINSTALL}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegStr   HKLM "${REG_UNINSTALL}" "DisplayIcon"          "$INSTDIR\${APP_EXE},0"
  WriteRegDWORD HKLM "${REG_UNINSTALL}" "NoModify"             1
  WriteRegDWORD HKLM "${REG_UNINSTALL}" "NoRepair"             1

  ; Desktop shortcut
  CreateShortcut \
    "$DESKTOP\${APP_NAME}.lnk" \
    "$INSTDIR\${APP_EXE}" "" \
    "$INSTDIR\${APP_EXE}" 0 \
    SW_SHOWNORMAL "" \
    "Labomed Medical Camera & Patient Management"

  ; Start Menu
  CreateDirectory "$SMPROGRAMS\Labomed\MedCamPy"
  CreateShortcut \
    "$SMPROGRAMS\Labomed\MedCamPy\MedCamPy.lnk" \
    "$INSTDIR\${APP_EXE}" "" \
    "$INSTDIR\${APP_EXE}" 0 \
    SW_SHOWNORMAL "" "Labomed MedCamPy"
  CreateShortcut \
    "$SMPROGRAMS\Labomed\MedCamPy\Uninstall.lnk" \
    "$INSTDIR\Uninstall.exe"

SectionEnd

; ── Uninstall ─────────────────────────────────────────────────
Section "Uninstall"
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  RMDir /r "$SMPROGRAMS\Labomed\MedCamPy"
  RMDir "$SMPROGRAMS\Labomed"
  DeleteRegKey HKLM "${REG_UNINSTALL}"
SectionEnd
