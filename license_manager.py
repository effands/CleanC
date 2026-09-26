"""CleanC License & HWID Management Module.

Menghasilkan Hardware ID (HWID) unik per-device yang kompatibel dengan Windows dan macOS,
serta mengelola autentikasi lisensi produk CleanC dengan AppCenter Ziqva.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


PRODUCT_NAME = "CleanC"
APPCENTER_BASE = "https://appcenter.ziqva.com"
PING_ONLINE_URL = "https://srv-ziqlabs-1.my.id/api/online-device"

# Storage lokasi cache lisensi
if sys.platform == "win32":
    LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    LICENSE_CACHE_DIR = LOCAL_APPDATA / "CleanC"
else:
    LICENSE_CACHE_DIR = Path.home() / ".cleanc"

LICENSE_CACHE_FILE = LICENSE_CACHE_DIR / "license.json"


class DeviceError(Exception):
    """Exception khusus untuk error autentikasi dan aktivasi lisensi."""

    def __init__(self, code: str, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


def _run_cmd(cmd: list[str] | str) -> str:
    """Jalankan shell command dengan aman dan kembalikan output stdout."""
    try:
        if isinstance(cmd, str):
            res = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
        else:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
        return (res.stdout or "").strip()
    except Exception:
        return ""


def get_windows_machine_guid() -> str:
    """Membaca MachineGuid unik Windows dari Registry (standar node-machine-id)."""
    if sys.platform != "win32":
        return ""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        )
        val, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        return str(val).strip()
    except Exception:
        pass

    try:
        # Fallback via PowerShell jika winreg terkendala
        ps_cmd = 'powershell -NoProfile -Command "(Get-ItemProperty -Path \'HKLM:\\SOFTWARE\\Microsoft\\Cryptography\').MachineGuid"'
        out = _run_cmd(ps_cmd)
        if out and len(out) > 8:
            return out
    except Exception:
        pass
    return ""


def get_disk_or_bios_serial() -> str:
    """Mendapatkan serial unik BIOS, Motherboard, atau HDD."""
    if sys.platform == "win32":
        # Coba ambil UUID komputer atau serial disk
        for cmd in [
            "powershell -NoProfile -Command \"(Get-CimInstance Win32_ComputerSystemProduct).UUID\"",
            "powershell -NoProfile -Command \"(Get-CimInstance Win32_BIOS).SerialNumber\"",
            "wmic bios get serialnumber",
            "wmic diskdrive get serialnumber",
            "wmic baseboard get serialnumber",
        ]:
            out = _run_cmd(cmd)
            for line in out.splitlines():
                line = line.strip()
                if line and line.lower() not in ("serialnumber", "uuid", "none", "to be filled by o.e.m.", "default string"):
                    return line
    elif sys.platform == "darwin":
        # macOS serial & Hardware UUID
        for cmd in [
            "ioreg -rd1 -c IOPlatformExpertDevice | awk -F '\"' '/IOPlatformSerialNumber/{print $4; exit}'",
            "ioreg -rd1 -c IOPlatformExpertDevice | awk -F '\"' '/IOPlatformUUID/{print $4; exit}'",
            "system_profiler SPHardwareDataType | awk -F ': ' '/Serial Number/{print $2; exit}'",
            "system_profiler SPHardwareDataType | awk -F ': ' '/Hardware UUID/{print $2; exit}'",
        ]:
            out = _run_cmd(cmd)
            if out:
                return out
    else:
        # Linux UUID / DMI
        for p in [
            "/sys/class/dmi/id/product_uuid",
            "/sys/class/dmi/id/product_serial",
            "/etc/machine-id",
            "/var/lib/dbus/machine-id",
        ]:
            try:
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as f:
                        val = f.read().strip()
                        if val:
                            return val
            except Exception:
                pass
    return ""


def generate_unique_hwid() -> str:
    """Menghasilkan Machine ID unik dan konsisten untuk CleanC."""
    guid = get_windows_machine_guid()
    hardware_serial = get_disk_or_bios_serial()
    
    # Ambil komponen tambahan penunjang kestabilan identifikasi
    host_info = [
        guid,
        hardware_serial,
        platform.node(),
        platform.machine(),
        platform.processor(),
    ]
    
    # Format identik standar CleanC
    if guid:
        # Jika Windows MachineGuid tersedia, gunakan format standar
        clean_guid = guid.strip().upper()
        return f"CLEANC_{clean_guid}"
    
    raw_str = "|".join(host_info)
    hash_hex = hashlib.sha256(raw_str.encode("utf-8")).hexdigest().upper()
    
    # Format UUID-like 8-4-4-4-12
    formatted = f"{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:32]}"
    return f"CLEANC_{formatted}"


def normalize_license_date(value: any) -> str:
    """Format tanggal lisensi dari server Ziqva."""
    if value is None or value == "":
        return "unknown"
    s = str(value).strip()
    if not s:
        return "unknown"
    if s.isdigit():
        try:
            epoch = int(s)
            if epoch > 0:
                dt = datetime.fromtimestamp(epoch)
                return dt.strftime("%d %b %Y, %H:%M")
        except Exception:
            pass
    return s


class DeviceManager:
    """Pengelola siklus hidup lisensi, HWID, dan status CleanC."""

    def __init__(self, product_name: str = PRODUCT_NAME) -> None:
        self.product_name = product_name
        self.machine_id = generate_unique_hwid()
        self.registered = False
        self.user_name = "unknown"
        self.user_email = "unknown"
        self.label = "#unknown"
        self.created = "unknown"
        self.expired = "unknown"
        self.remaining = "unknown"
        self.last_token = ""
        
        self.check_interval = 600  # 10 menit
        self.ping_interval = 90    # 90 detik
        self._stop_event = threading.Event()
        
        self.load_local_license()
        self._start_background_loops()

    def get_machine_id(self) -> str:
        """Mengembalikan HWID saat ini."""
        return self.machine_id

    def is_registered(self) -> bool:
        """Cek apakah lisensi terdaftar dan aktif."""
        return self.registered

    def load_local_license(self) -> None:
        """Muat data lisensi yang tersimpan secara lokal."""
        try:
            if LICENSE_CACHE_FILE.exists():
                with open(LICENSE_CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.registered = bool(data.get("registered", False))
                    self.user_name = data.get("user_name", "unknown")
                    self.user_email = data.get("user_email", "unknown")
                    self.label = data.get("label", "#unknown")
                    self.created = data.get("created", "unknown")
                    self.expired = data.get("expired", "unknown")
                    self.remaining = data.get("remaining", "unknown")
                    self.last_token = data.get("token", "")
        except Exception:
            pass

    def save_local_license(self) -> None:
        """Simpan cache data lisensi secara lokal."""
        try:
            LICENSE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            payload = {
                "registered": self.registered,
                "user_name": self.user_name,
                "user_email": self.user_email,
                "label": self.label,
                "created": self.created,
                "expired": self.expired,
                "remaining": self.remaining,
                "token": self.last_token,
                "machine_id": self.machine_id,
                "updated_at": datetime.now().isoformat(),
            }
            with open(LICENSE_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

    def _prepare_data(self, data: dict) -> None:
        """Ekstrak informasi respon dari Ziqva AppCenter."""
        tobel = data.get("tobelsoft", {})
        sub_data = tobel.get("data", {}) if isinstance(tobel, dict) else {}
        if not sub_data:
            return

        user = sub_data.get("user", {})
        if isinstance(user, dict):
            self.user_name = user.get("name") or self.user_name
            self.user_email = user.get("email") or self.user_email

        self.label = sub_data.get("label") or self.label
        self.created = normalize_license_date(sub_data.get("created"))
        self.expired = normalize_license_date(sub_data.get("expired"))
        
        rem = sub_data.get("remaining")
        if rem is not None:
            self.remaining = str(rem)

    def activate_license(self, token: str) -> tuple[bool, str]:
        """Kirim permintaan aktivasi token ke Ziqva AppCenter."""
        token = token.strip()
        if not token:
            return False, "Token lisensi tidak boleh kosong."

        params = urllib.parse.urlencode({
            "token": token,
            "product": self.product_name,
            "machine_id": self.machine_id,
        })
        url = f"{APPCENTER_BASE}/device/activation?{params}"

        try:
            req = urllib.request.Request(
                url,
                data=b"",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "CleanC-App/2.5",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                body = response.read().decode("utf-8")
                res_json = json.loads(body)

                tobel = res_json.get("tobelsoft", {})
                is_error = tobel.get("error", True)
                message = tobel.get("message", "Terjadi kesalahan aktivasi.")

                if is_error:
                    return False, message

                self.registered = True
                self.last_token = token
                self._prepare_data(res_json)
                self.save_local_license()
                
                # Segera kirim ping online
                threading.Thread(target=self._send_ping_once, daemon=True).start()
                return True, message or "Lisensi CleanC berhasil diaktifkan!"
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
                err_json = json.loads(err_body)
                msg = err_json.get("tobelsoft", {}).get("message", f"HTTP Error {e.code}")
                return False, msg
            except Exception:
                return False, f"Server error ({e.code}): {e.reason}"
        except Exception as e:
            return False, f"Gagal menghubungi server: {str(e)}"

    def refresh_status(self) -> bool:
        """Cek status keaktifan lisensi terkini ke server."""
        params = urllib.parse.urlencode({
            "product": self.product_name,
            "machine_id": self.machine_id,
        })
        url = f"{APPCENTER_BASE}/device/status?{params}"

        try:
            req = urllib.request.Request(
                url,
                data=b"",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "CleanC-App/2.5",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                body = response.read().decode("utf-8")
                res_json = json.loads(body)

                tobel = res_json.get("tobelsoft", {})
                data = tobel.get("data", {})
                is_reg = bool(data.get("registered", False))
                
                self._prepare_data(res_json)
                self.registered = is_reg
                self.save_local_license()
                return self.registered
        except Exception:
            # Jika offline, gunakan status lokal
            return self.registered

    def _send_ping_once(self) -> None:
        """Kirimkan 1x heartbeat device online."""
        if not self.registered or self.user_email == "unknown":
            return
        try:
            payload = json.dumps({
                "machine_id": self.machine_id,
                "email": self.user_email,
                "user_name": self.user_name,
                "product_name": self.product_name,
            }).encode("utf-8")

            req = urllib.request.Request(
                PING_ONLINE_URL,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "action": "ping",
                    "User-Agent": "CleanC-App/2.5",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8):
                pass
        except Exception:
            pass

    def _start_background_loops(self) -> None:
        """Jalankan background thread untuk periodic check dan heartbeat ping."""
        def check_worker():
            # Initial verification setelah beberapa detik
            time.sleep(3)
            self.refresh_status()
            
            while not self._stop_event.is_set():
                if self.registered:
                    self.refresh_status()
                self._stop_event.wait(self.check_interval)

        def ping_worker():
            while not self._stop_event.is_set():
                if self.registered:
                    self._send_ping_once()
                self._stop_event.wait(self.ping_interval)

        threading.Thread(target=check_worker, daemon=True).start()
        threading.Thread(target=ping_worker, daemon=True).start()

    def stop(self) -> None:
        """Hentikan background loop saat aplikasi keluar."""
        self._stop_event.set()

    def get_display_info(self) -> dict:
        """Dapatkan data terstruktur untuk tampilan UI."""
        return {
            "registered": self.registered,
            "machine_id": self.machine_id,
            "user_name": self.user_name,
            "user_email": self.user_email,
            "label": self.label,
            "created": self.created,
            "expired": self.expired,
            "remaining": self.remaining,
            "token": self.last_token,
            "product": self.product_name,
        }
