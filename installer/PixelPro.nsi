; =============================================================
;  PixelPro.nsi  -  Pixel Pro Windows Installer
;  Produces: installer\PixelPro_Setup.exe
; =============================================================

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"
!include "FileFunc.nsh"

; ── App metadata ──────────────────────────────────────────────
!define APP_NAME      "Pixel Pro"
!define APP_EXE       "PixelPro.exe"
!define APP_VERSION   "1.0.0"
!define APP_PUBLISHER "Labomed"
!define APP_URL       "https://labomed.com"
!define APP_DIR_NAME  "PixelPro"
!define REG_KEY       "Software\Microsoft\Windows\CurrentVersion\Uninstall\PixelPro"

!define MUI_ICON   "..\assets\logo.ico"
!define MUI_UNICON "..\assets\logo.ico"

Name              "${APP_NAME} ${APP_VERSION}"
OutFile           "PixelPro_Setup.exe"
InstallDir        "$PROGRAMFILES64\Labomed\${APP_DIR_NAME}"
InstallDirRegKey  HKLM "${REG_KEY}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor     /SOLID lzma
Unicode           true
BrandingText      "Labomed - Pixel Pro ${APP_VERSION}"

; ── MUI pages ─────────────────────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE   "Welcome to Pixel Pro ${APP_VERSION}"
!define MUI_WELCOMEPAGE_TEXT    "This wizard will install Pixel Pro on your computer.$\r$\n$\r$\nPixel Pro is a medical imaging and patient management application for Labomed imaging systems.$\r$\n$\r$\nThe following will be installed automatically if needed:$\r$\n  - VC++ 2022 Runtime$\r$\n  - USB RNDIS driver (for USB camera)$\r$\n$\r$\nClick Next to continue."

!define MUI_FINISHPAGE_RUN      "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Pixel Pro"
!define MUI_FINISHPAGE_LINK     "Visit Labomed"
!define MUI_FINISHPAGE_LINK_LOCATION "${APP_URL}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE   "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"


; =============================================================
;  INSTALL
; =============================================================
Section "Pixel Pro" SecMain
  SectionIn RO

  ; App files
  SetOutPath "$INSTDIR"
  File /r "..\dist\PixelPro\*.*"

  ; VC++ 2022 Runtime - skip if already installed
  ReadRegDWORD $0 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Installed"
  ${If} $0 != 1
    DetailPrint "Installing VC++ 2022 Runtime..."
    File /oname=$TEMP\vc_redist.x64.exe "vc_redist.x64.exe"
    ExecWait '"$TEMP\vc_redist.x64.exe" /install /quiet /norestart' $1
    Delete "$TEMP\vc_redist.x64.exe"
    ${If} $1 != 0
    ${AndIf} $1 != 3010
      MessageBox MB_ICONEXCLAMATION "VC++ Runtime install returned code $1.$\r$\nThe app may still work if an older runtime is present."
    ${EndIf}
    DetailPrint "VC++ Runtime done (code $1)"
  ${Else}
    DetailPrint "VC++ 2022 Runtime already installed - skipping."
  ${EndIf}

  ; RNDIS USB driver - install if bundled, otherwise write setup guide
  ${If} ${FileExists} "$INSTDIR\drivers\mod-duo-rndis.inf"
    DetailPrint "Installing RNDIS USB driver..."
    ExecWait 'pnputil /add-driver "$INSTDIR\drivers\mod-duo-rndis.inf" /install' $2
    DetailPrint "RNDIS driver install done (code $2)"
  ${Else}
    FileOpen $3 "$INSTDIR\USB_CAMERA_DRIVER_SETUP.txt" w
    FileWrite $3 "USB Camera Driver Setup$\r$\n"
    FileWrite $3 "=======================$\r$\n$\r$\n"
    FileWrite $3 "If the USB camera shows as COM port in Device Manager:$\r$\n$\r$\n"
    FileWrite $3 "Option A - Windows Update (easiest):$\r$\n"
    FileWrite $3 "  1. Press Windows key, type: View optional updates$\r$\n"
    FileWrite $3 "  2. Find USB RNDIS Gadget or Remote NDIS - install it$\r$\n$\r$\n"
    FileWrite $3 "Option B - Device Manager:$\r$\n"
    FileWrite $3 "  1. Right-click device -> Update driver$\r$\n"
    FileWrite $3 "  2. Browse -> Let me pick -> Network Adapters$\r$\n"
    FileWrite $3 "  3. Microsoft -> Remote NDIS Compatible Device$\r$\n$\r$\n"
    FileWrite $3 "Option C - Download driver:$\r$\n"
    FileWrite $3 "  https://github.com/albert-fit/windows_10_raspi_usb_otg_fix$\r$\n"
    FileClose $3
  ${EndIf}

  ; Uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Add/Remove Programs
  WriteRegStr   HKLM "${REG_KEY}" "DisplayName"          "${APP_NAME}"
  WriteRegStr   HKLM "${REG_KEY}" "DisplayVersion"       "${APP_VERSION}"
  WriteRegStr   HKLM "${REG_KEY}" "Publisher"            "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${REG_KEY}" "URLInfoAbout"         "${APP_URL}"
  WriteRegStr   HKLM "${REG_KEY}" "InstallLocation"      "$INSTDIR"
  WriteRegStr   HKLM "${REG_KEY}" "UninstallString"      '"$INSTDIR\Uninstall.exe"'
  WriteRegStr   HKLM "${REG_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegStr   HKLM "${REG_KEY}" "DisplayIcon"          "$INSTDIR\${APP_EXE},0"
  WriteRegDWORD HKLM "${REG_KEY}" "NoModify"             1
  WriteRegDWORD HKLM "${REG_KEY}" "NoRepair"             1

  ; Estimate installed size for ARP
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  WriteRegDWORD HKLM "${REG_KEY}" "EstimatedSize" "$0"

  ; Desktop shortcut
  CreateShortcut "$DESKTOP\Pixel Pro.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0 SW_SHOWNORMAL "" "Labomed Pixel Pro Medical Imaging"

  ; Start Menu
  CreateDirectory "$SMPROGRAMS\Labomed\Pixel Pro"
  CreateShortcut "$SMPROGRAMS\Labomed\Pixel Pro\Pixel Pro.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0 SW_SHOWNORMAL "" "Labomed Pixel Pro"
  CreateShortcut "$SMPROGRAMS\Labomed\Pixel Pro\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

SectionEnd


; =============================================================
;  UNINSTALL
; =============================================================
Section "Uninstall"

  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\Pixel Pro.lnk"
  RMDir /r "$SMPROGRAMS\Labomed\Pixel Pro"
  RMDir "$SMPROGRAMS\Labomed"
  DeleteRegKey HKLM "${REG_KEY}"

  MessageBox MB_ICONINFORMATION "Pixel Pro has been uninstalled.$\r$\n$\r$\nYour patient database is preserved at:$\r$\n  %APPDATA%\Labomed\PixelPro\$\r$\n$\r$\nDelete that folder manually to remove all data."

SectionEnd
