"""CleanC - Modern Deep Storage & System Cleaner GUI.

Pembersih Cache & Service Worker Google Chrome, CapCut Hub (Cache, Projects, Versi Lama),
dan Windows Panther Monitor Logs dengan antarmuka modern dan animasi interaktif.
"""

from __future__ import annotations

import math
import os
import sys

# ----------------------------------------------------------------------
# WINDOWS HIGH-DPI AWARENESS (Must be called before Tkinter initialization)
# ----------------------------------------------------------------------
if sys.platform == "win32":
    try:
        import ctypes
        # Set distinct AppUserModelID so Windows taskbar binds CleanC icon instead of default Python/Tkinter feather
        app_id = "ziqva.cleanc.storageoptimizer.2.5"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

    try:
        # Per-Monitor V2 DPI Awareness (Windows 10 1703+ / Windows 11)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Per-Monitor V1 DPI Awareness (Windows 8.1+)
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                # System DPI Awareness (Windows Vista+)
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageFilter, ImageTk

from clean_chrome_service_workers import (
    DEFAULT_BRAVE_USER_DATA,
    DEFAULT_CAPCUT_APPS,
    DEFAULT_CAPCUT_CACHE,
    DEFAULT_CAPCUT_PROJECTS,
    DEFAULT_CHROME_USER_DATA,
    DEFAULT_EDGE_USER_DATA,
    DEFAULT_FIREFOX_USER_DATA,
    DEFAULT_USER_DATA,
    BROWSER_PATHS,
    PANTHER_DIR,
    PANTHER_MONITOR_DIR,
    TYPE_CACHE,
    TYPE_SERVICE_WORKER,
    categorize_target,
    clean_capcut_cache,
    clean_capcut_old_versions,
    clean_capcut_projects,
    clean_panther_logs,
    extract_profile_name,
    find_targets,
    format_size,
    get_capcut_cache_info,
    get_capcut_projects_info,
    get_capcut_versions_info,
    get_dir_size,
    get_panther_info,
    is_admin,
    is_browser_running,
    is_capcut_running,
    kill_browser_process,
    kill_capcut_process,
    clean_dev_cache_targets,
    get_dev_cache_info,
    get_drive_c_usage,
    load_clean_stats,
    record_freed_bytes,
    remove_target,
)

# ----------------------------------------------------------------------
# THEME PALETTE CONSTANTS (Deep Dark Obsidian & Neon Accents)
# ----------------------------------------------------------------------
COLOR_BG_ROOT = "#090d16"         # Dark background root
COLOR_BG_SURFACE = "#111827"      # Surface / Cards
COLOR_BG_CARD = "#172033"         # Elevated Card
COLOR_BG_INPUT = "#0f172a"        # Inputs & Search
COLOR_BORDER = "#30415c"          # Soft borders
COLOR_BORDER_LIGHT = "#4b6388"    # Focused borders

COLOR_TEXT_WHITE = "#f8fafc"      # Primary text
COLOR_TEXT_MUTED = "#94a3b8"      # Secondary text
COLOR_TEXT_DIM = "#64748b"        # Subtle captions

COLOR_BLUE = "#3b82f6"            # Chrome / Electric Blue
COLOR_BLUE_HOVER = "#60a5fa"
COLOR_CYAN = "#06b6d4"            # Cyber Cyan
COLOR_CYAN_LIGHT = "#38bdf8"
COLOR_PURPLE = "#8b5cf6"          # CapCut Neon Violet
COLOR_PURPLE_HOVER = "#a78bfa"
COLOR_GREEN = "#10b981"           # Emerald Success
COLOR_GREEN_HOVER = "#34d399"
COLOR_RED = "#ef4444"             # Rose / Crimson Danger
COLOR_RED_HOVER = "#f87171"
COLOR_AMBER = "#f59e0b"           # Warning / Caution

FILTER_ALL = "Semua (Service Worker & Cache)"
FILTER_SW = "Hanya Service Worker"
FILTER_CACHE = "Hanya Cache"

SCOPE_CAPCUT_ALL = "Semua (Cache & Projects)"
SCOPE_CAPCUT_CACHE = "Hanya Cache (User Data\\Cache)"
SCOPE_CAPCUT_PROJECTS = "Hanya Projects (User Data\\Projects)"

# UI-wide language replacements.  The application is intentionally kept in
# one file, so a recursive refresh keeps every existing screen in sync.
UI_EN_REPLACEMENTS = [
    ("Cache dari Playwright (binary browser lama), Node.js, NPM, PIP Python, dan PNPM dapat mengakumulasi puluhan Gigabyte di %LOCALAPPDATA%. CleanC secara cerdas menandai versi browser Playwright lama dan cache aman untuk dibersihkan, sembari tetap menjaga versi aktif tersimpan.", "Playwright (old browser binaries), Node.js, NPM, Python PIP, and PNPM caches can accumulate dozens of gigabytes in %LOCALAPPDATA%. CleanC identifies old Playwright browser versions and safe caches while protecting active versions."),
    ("Cache dari Playwright (binary browser lama), Node.js, NPM, PIP Python, dan PNPM dapat", "Playwright (old browser binaries), Node.js, NPM, Python PIP, and PNPM caches can"),
    ("mengakumulasi puluhan Gigabyte di %LOCALAPPDATA%. CleanC secara cerdas menandai versi browser", "accumulate dozens of gigabytes in %LOCALAPPDATA%. CleanC identifies old browser"),
    ("Playwright lama dan cache aman untuk dibersihkan, sembari tetap menjaga versi aktif tersimpan.", "Playwright versions and safe caches while protecting active versions."),
    ("Folder C:\\Windows\\Panther\\monitor secara berkala mengakumulasi files log diagnostic sistem dan telemetry yang dapat menyita ruang hard disk. CleanC dapat menghentikan service monitor secara aman, membersihkan seluruh log usang, dan menyalakan kembali driver sistem.", "C:\\Windows\\Panther\\monitor periodically accumulates diagnostic and telemetry logs that consume disk space. CleanC safely stops the monitor service, removes stale logs, and restarts the system driver."),
    ("Folder C:\\Windows\\Panther\\monitor secara berkala mengakumulasi file log diagnostic sistem", "C:\\Windows\\Panther\\monitor periodically accumulates system diagnostic logs"),
    ("dan telemetry yang dapat menyita ruang hard disk. CleanC dapat menghentikan service monitor secara", "and telemetry that consume disk space. CleanC safely stops the monitor service,"),
    ("aman, membersihkan seluruh log usang, dan menyalakan kembali driver sistem.", "removes stale logs, and restarts the system driver."),
    ("Folder C:\\Windows\\Panther\\monitor secara berkala mengakumulasi files log diagnostic sistem dan telemetry yang dapat menyita ruang hard disk. CleanC dapat menghentikan service monitor secara aman, membersihkan seluruh log usang, dan menyalakan kembali driver sistem.", "C:\\Windows\\Panther\\monitor periodically accumulates diagnostic and telemetry logs that consume disk space. CleanC safely stops the monitor service, removes stale logs, and restarts the system driver."),
    ("File sementara CapCut", "Temporary CapCut files"), ("Draft video editing", "Video editing drafts"),
    ("Bersihkan Item Selected", "Clean Selected Items"),
    ("[OPTIONAL] Versi Terbaru", "[OPTIONAL] Latest Version"),
    ("[REKOMENDASI] Sangat Aman Dihapus", "[RECOMMENDED] Safe to Delete"),
    ("Folder Bersih (0 B)", "Empty Folder (0 B)"),
    ("Sedang memindai Cache & Projects CapCut... Mohon tunggu.", "Scanning CapCut Cache & Projects... Please wait."),
    ("Versi Aktif Terlindungi", "Protected Active Version"), ("Dilindungi & Terkunci", "Protected & Locked"),
    ("Ruang Dapat Dihemat", "Space You Can Save"), ("versi lama dapat dihapus", "old versions can be deleted"),
    ("TERBARU (DILINDUNGI)", "LATEST (PROTECTED)"),
    ("Hanya terpasang 1 versi terbaru. Tidak ada versi lama untuk dihapus.", "Only the latest version is installed. There are no old versions to delete."),
    ("Klik 'Clean Panther Logs' untuk membersihkan folders log monitor.", "Click 'Clean Panther Logs' to clean monitor log folders."),
    ("Also clean extra .log filess in the Panther root folders", "Also clean extra .log files in the Panther root folder"),
    ("Cache dari Playwright", "Playwright cache"), ("binary browser lama", "old browser binaries"),
    ("dapat mengakumulasi", "can accumulate"), ("puluhan Gigabyte", "dozens of gigabytes"),
    ("secara cerdas menandai", "intelligently identifies"), ("versi browser", "browser versions"),
    ("lama dan cache aman untuk dibersihkan", "old and safe caches to clean"),
    ("sembari tetap menjaga versi aktif tersimpan", "while protecting active versions"),
    ("Folder C:\\Windows\\Panther\\monitor", "The C:\\Windows\\Panther\\monitor folder"),
    ("secara berkala mengakumulasi", "periodically accumulates"), ("file log diagnostic sistem", "system diagnostic log files"),
    ("dan telemetry yang dapat menyita ruang hard disk", "and telemetry that can consume disk space"),
    ("dapat menghentikan service monitor secara aman", "can safely stop the monitor service"),
    ("membersihkan seluruh log usang", "clean all stale logs"), ("menyalakan kembali driver sistem", "restart the system driver"),
    ("Sedang memindai", "Scanning"), ("Mohon tunggu", "Please wait"),
    ("Bersihkan Item Tercentang", "Clean Selected Items"),
    ("Sangat Aman Dihapus", "Safe to Delete"), ("Versi Terbaru", "Latest Version"),
    ("Folder Bersih", "Empty Folder"), ("Terkunci & Tidak dapat dihapus", "Locked & Cannot be deleted"),
    ("Folder Versi Lama di Apps", "Old Version Folders in Apps"),
    ("Kapasitas Drive C:", "C: Drive Capacity"), ("Sisa Free:", "Free Space:"),
    ("dari Total", "of Total"), ("Tersedia", "Available"), ("Terpakai", "Used"),
    ("Total Telah Dibersihkan:", "Total Cleaned:"), ("Sesi ini:", "This session:"),
    ("Profil", "Profile"), ("Profil Terdeteksi", "Profiles Detected"),
    ("Profile Terdeteksi", "Profiles Detected"),
    ("Google Chrome User Data", "Google Chrome User Data"), ("folder target", "target folders"),
    ("Semua (Service Worker & Cache)", "All (Service Worker & Cache)"),
    ("Hanya Service Worker", "Service Worker Only"), ("Hanya Cache", "Cache Only"),
    ("Pilih target dan klik Scan untuk mencari folder yang dapat dibersihkan.", "Select a target and click Scan to find cleanable folders."),
    ("Menampilkan", "Showing"), ("dari total", "of total"), ("ditemukan", "found"),
    ("Tercentang", "Selected"), ("Siap dibersihkan", "Ready to clean"),
    ("Target Cakupan:", "Scope:"), ("Versi Lama", "Old Versions"),
    ("Nomor Versi", "Version"), ("Status Proteksi", "Protection Status"),
    ("Ukuran Disk", "Disk Size"), ("Tanggal Modifikasi", "Modified Date"),
    ("Centang Semua Versi Lama", "Check All Old Versions"), ("Hapus Centang", "Uncheck All"),
    ("Versi terbaru terkunci & terlindungi otomatis.", "Latest version is locked and protected automatically."),
    ("Scan Ulang Versi", "Rescan Versions"), ("Hapus Versi Lama Tercentang", "Delete Checked Old Versions"),
    ("Bersihkan Semua Versi Lama (1-Klik)", "Clean All Old Versions (One Click)"),
    ("Windows Panther Monitor Logs", "Windows Panther Monitor Logs"),
    ("Status Izin:", "Permission Status:"), ("Memeriksa...", "Checking..."),
    ("Menghitung...", "Calculating..."), ("Total file:", "Total files:"),
    ("Bersihkan juga file .log tambahan di root folder Panther", "Also clean extra .log files in the Panther root folder"),
    ("Bersihkan Log Panther Sekarang", "Clean Panther Logs Now"), ("Refresh", "Refresh"),
    ("Administrator (Aman)", "Administrator (Safe)"), ("Pengguna Biasa (Memerlukan UAC)", "Standard User (UAC Required)"),
    ("Status Browser:", "Browser Status:"), ("Status CapCut:", "CapCut Status:"),
    ("Versi Terbaru:", "Latest Version:"), ("Dapat Dihemat:", "Can Save:"),
    ("Memindai", "Scanning"), ("Pembersihan selesai", "Cleaning complete"),
    ("dibebaskan", "freed"), ("folder terdeteksi", "folders detected"),
    ("dari", "of"), ("dipilih", "selected"), ("Mohon tunggu", "Please wait"),
    ("sedang berjalan", "is running"), ("Disarankan ditutup sebelum menghapus", "Recommended to close before cleaning"),
    ("Pilih Rekomendasi", "Select Recommended"), ("Pilih Semua", "Select All"),
    ("Batal Pilih", "Deselect All"), ("Centang Semua", "Check All"),
    ("Uncheck All", "Uncheck All"), ("Scan Ulang", "Rescan"),
    ("Bersihkan Item Tercentang", "Clean Checked Items"),
    ("Bersihkan Sekarang", "Clean Now"), ("Scan Sekarang", "Scan Now"),
    ("Hapus Terpilih", "Delete Selected"), ("Hapus Semua Sesuai Filter", "Delete All Filtered"),
    ("Hapus Semua Sesuai Target", "Delete All in Scope"), ("Pilih Browser:", "Browser:"),
    ("Target Cakupan:", "Scope:"), ("Cari Profil:", "Search Profile:"),
    ("Cari Nama:", "Search Name:"), ("Filter:", "Filter:"), ("Tipe:", "Type:"),
    ("Path:", "Path:"), ("Browse...", "Browse..."), ("Tutup Browser", "Close Browser"),
    ("Profil Terdeteksi", "Profiles Detected"), ("Kategori", "Category"),
    ("Ukuran", "Size"), ("Lokasi Direktori", "Directory Location"),
    ("Nama Folder / File", "Folder / File Name"), ("Jumlah File", "File Count"),
    ("Path Direktori", "Directory Path"), ("Lokasi Folder", "Folder Location"),
    ("Service Worker & Cache", "Service Worker & Cache"), ("Semua Item", "All Items"),
    ("Hanya Folder / Draft", "Folders / Drafts Only"), ("Hanya File", "Files Only"),
    ("Cache & Projects (User Data)", "Cache & Projects (User Data)"),
    ("Versi Lama CapCut (Apps)", "Old CapCut Versions (Apps)"),
    ("Cache CapCut", "CapCut Cache"), ("Draft Projects", "Draft Projects"),
    ("Total Dev Cache", "Total Dev Cache"), ("Tercentang Siap Bersih", "Selected to Clean"),
    ("Rekomendasi & Status", "Recommendation & Status"), ("Pilih", "Select"),
    ("Kategori / Tool", "Category / Tool"), ("Nama Folder / Versi", "Folder / Version"),
    ("Lokasi Folder", "Folder Location"), ("Bersihkan Log Panther", "Clean Panther Logs"),
    ("Web Browsers", "Web Browsers"), ("Windows Panther", "Windows Panther"),
    ("Dev & Package Cache", "Dev & Package Cache"), ("CapCut Studio", "CapCut Studio"),
    ("Terbuka", "Running"), ("tidak berjalan", "not running"), ("sedang berjalan", "is running"),
    ("Aman untuk dibersihkan", "Safe to clean"), ("Disarankan ditutup sebelum menghapus", "Recommended to close before cleaning"),
    ("Menampilkan", "Showing"), ("dari total", "of total"), ("folder", "folders"),
    ("file", "files"), ("ditemukan", "found"), ("Terpilih", "Selected"),
]


# ----------------------------------------------------------------------
# DATA MODELS
# ----------------------------------------------------------------------
class TargetItem:
    """Representasi data target Chrome."""

    def __init__(self, path: Path, user_data: Path) -> None:
        self.path = path
        self.category = categorize_target(path)
        self.profile = extract_profile_name(path, user_data)
        self.size = get_dir_size(path)
        self.size_str = format_size(self.size)


class CapCutItem:
    """Representasi item cache atau projects CapCut."""

    def __init__(self, raw: dict) -> None:
        self.name: str = raw["name"]
        self.path: Path = raw["path"]
        self.is_dir: bool = raw["is_dir"]
        self.item_type: str = raw["type"]
        self.category: str = raw.get("category", "Cache")
        self.size: int = raw["size"]
        self.size_str: str = format_size(self.size)
        self.files: int = raw["files"]


class CapCutVersionItem:
    """Representasi folder versi CapCut di folder Apps."""

    def __init__(self, raw: dict) -> None:
        self.name: str = raw["name"]
        self.version_tuple: tuple = raw["version_tuple"]
        self.path: Path = raw["path"]
        self.is_latest: bool = raw["is_latest"]
        self.size: int = raw["size"]
        self.size_str: str = format_size(self.size)
        self.files: int = raw["files"]
        self.modified: str = raw["modified"]
        self.checked: bool = False


class DevCacheItem:
    """Representasi item cache developer dan package manager."""

    def __init__(self, raw: dict) -> None:
        self.category: str = raw["category"]
        self.name: str = raw["name"]
        self.path: Path = raw["path"]
        self.size: int = raw["size"]
        self.size_str: str = format_size(self.size)
        self.files: int = raw["files"]
        self.is_recommended: bool = raw["is_recommended"]
        self.recommendation: str = raw["recommendation"]
        self.checked: bool = self.is_recommended


# ----------------------------------------------------------------------
# ANIMATED CUSTOM CANVAS WIDGETS
# ----------------------------------------------------------------------
class ModernRadarSpinner(tk.Canvas):
    """Canvas animasi radar & orbital rings bergaya sci-fi modern."""

    def __init__(self, parent, size: int = 34, bg: str = COLOR_BG_SURFACE, **kwargs) -> None:
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0, **kwargs)
        self.size = size
        self.bg_color = bg
        self.angle_outer = 0
        self.angle_inner = 180
        self.pulse_phase = 0.0
        self.running = False
        self.after_id = None
        self.draw_idle()

    def draw_idle(self) -> None:
        self.delete("all")
        cx, cy = self.size / 2, self.size / 2
        r = self.size / 2 - 4
        self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=COLOR_BORDER, width=1.5)
        self.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=COLOR_TEXT_DIM, outline="")

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._step()

    def stop(self) -> None:
        self.running = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.draw_idle()

    def _step(self) -> None:
        if not self.running:
            return
        self.delete("all")
        cx, cy = self.size / 2, self.size / 2
        r_out = self.size / 2 - 3
        r_in = r_out - 5

        # Cincin orbit luar (Cyan / Electric Blue)
        self.create_arc(
            cx - r_out, cy - r_out, cx + r_out, cy + r_out,
            start=self.angle_outer, extent=110,
            style="arc", outline=COLOR_CYAN_LIGHT, width=2.4
        )
        self.create_arc(
            cx - r_out, cy - r_out, cx + r_out, cy + r_out,
            start=(self.angle_outer + 180) % 360, extent=50,
            style="arc", outline=COLOR_BLUE, width=1.8
        )

        # Cincin orbit dalam berputar berlawanan arah (Violet Neon)
        self.create_arc(
            cx - r_in, cy - r_in, cx + r_in, cy + r_in,
            start=self.angle_inner, extent=100,
            style="arc", outline=COLOR_PURPLE, width=1.8
        )

        # Inti orb berdenyut (Pulse)
        pulse_r = 3.0 + 1.4 * math.sin(self.pulse_phase)
        self.create_oval(
            cx - pulse_r, cy - pulse_r, cx + pulse_r, cy + pulse_r,
            fill="#ffffff", outline=COLOR_CYAN
        )

        self.angle_outer = (self.angle_outer + 8) % 360
        self.angle_inner = (self.angle_inner - 12) % 360
        self.pulse_phase += 0.25

        self.after_id = self.after(30, self._step)


class ShimmerProgressBar(tk.Canvas):
    """Progress bar modern dengan berkas laser cahaya meluncur (shimmer beam)."""

    def __init__(
        self,
        parent,
        height: int = 10,
        bg: str = COLOR_BG_SURFACE,
        track_color: str = "#182234",
        bar_color: str = COLOR_CYAN,
        **kwargs
    ) -> None:
        super().__init__(parent, height=height, bg=bg, highlightthickness=0, **kwargs)
        self.bar_height = height
        self.bg_color = bg
        self.track_color = track_color
        self.bar_color = bar_color
        self.mode = "determinate"
        self.current_pct = 0.0
        self.target_pct = 0.0
        self.beam_x = 0
        self.beam_speed = 9
        self.beam_dir = 1
        self.running = False
        self.after_id = None
        self.bind("<Configure>", lambda e: self.draw())

    def set_bar_color(self, color: str) -> None:
        self.bar_color = color
        self.draw()

    def start_indeterminate(self) -> None:
        self.mode = "indeterminate"
        self.running = True
        self.beam_x = 0
        self.beam_dir = 1
        self._animate_indeterminate()

    def stop(self) -> None:
        self.running = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.mode = "determinate"
        self.current_pct = 0.0
        self.target_pct = 0.0
        self.draw()

    def set_progress(self, current: float, total: float) -> None:
        self.mode = "determinate"
        if total <= 0:
            self.target_pct = 0.0
        else:
            self.target_pct = max(0.0, min(1.0, current / total))
        if not self.running:
            self.running = True
            self._animate_determinate()

    def _animate_determinate(self) -> None:
        diff = self.target_pct - self.current_pct
        if abs(diff) < 0.005:
            self.current_pct = self.target_pct
            self.draw()
            self.running = False
            return
        self.current_pct += diff * 0.35
        self.draw()
        self.after_id = self.after(25, self._animate_determinate)

    def _animate_indeterminate(self) -> None:
        if not self.running or self.mode != "indeterminate":
            return
        w = self.winfo_width()
        if w <= 1:
            w = 400
        beam_len = max(60, int(w * 0.28))

        self.beam_x += self.beam_speed * self.beam_dir
        if self.beam_x + beam_len >= w:
            self.beam_dir = -1
        elif self.beam_x <= 0:
            self.beam_dir = 1

        self.draw()
        self.after_id = self.after(25, self._animate_indeterminate)

    def draw(self) -> None:
        self.delete("all")
        w = self.winfo_width()
        h = self.bar_height
        if w <= 1:
            return

        r = h / 2
        # Track latar belakang bulat
        self.create_rectangle(r, 0, w - r, h, fill=self.track_color, outline="")
        self.create_oval(0, 0, h, h, fill=self.track_color, outline="")
        self.create_oval(w - h, 0, w, h, fill=self.track_color, outline="")

        if self.mode == "indeterminate":
            beam_len = max(60, int(w * 0.28))
            bx = max(0, min(w - beam_len, self.beam_x))
            # Laser glow shimmer beam
            self.create_oval(bx, 0, bx + h, h, fill=COLOR_BLUE, outline="")
            self.create_rectangle(bx + r, 0, bx + beam_len - r, h, fill=self.bar_color, outline="")
            self.create_oval(bx + beam_len - h, 0, bx + beam_len, h, fill=COLOR_CYAN_LIGHT, outline="")
        else:
            fill_w = int(w * self.current_pct)
            if fill_w > h:
                self.create_oval(0, 0, h, h, fill=self.bar_color, outline="")
                self.create_rectangle(r, 0, fill_w - r, h, fill=self.bar_color, outline="")
                self.create_oval(fill_w - h, 0, fill_w, h, fill=self.bar_color, outline="")
            elif fill_w > 0:
                self.create_oval(0, 0, fill_w, h, fill=self.bar_color, outline="")


class PulsingStatusDot(tk.Canvas):
    """Indikator titik status animasi gelombang riak bernapas."""

    def __init__(self, parent, size: int = 16, bg: str = COLOR_BG_SURFACE, **kwargs) -> None:
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0, **kwargs)
        self.size = size
        self.state_mode = "idle"
        self.pulse_phase = 0.0
        self.running = False
        self.after_id = None
        self.draw_static()

    def set_state(self, mode: str) -> None:
        self.state_mode = mode
        if mode in ("scanning", "working"):
            if not self.running:
                self.running = True
                self._step()
        else:
            self.running = False
            if self.after_id:
                self.after_cancel(self.after_id)
                self.after_id = None
            self.draw_static()

    def draw_static(self) -> None:
        self.delete("all")
        cx, cy = self.size / 2, self.size / 2
        color = COLOR_GREEN if self.state_mode == "idle" else COLOR_TEXT_DIM
        self.create_oval(cx - 3.5, cy - 3.5, cx + 3.5, cy + 3.5, fill=color, outline="")

    def _step(self) -> None:
        if not self.running:
            return
        self.delete("all")
        cx, cy = self.size / 2, self.size / 2

        color = COLOR_CYAN if self.state_mode == "scanning" else COLOR_RED
        ring_color = COLOR_BLUE if self.state_mode == "scanning" else "#991b1b"

        # Gelombang riak membesar
        r_wave = 3.5 + 3.5 * (0.5 + 0.5 * math.sin(self.pulse_phase))
        self.create_oval(cx - r_wave, cy - r_wave, cx + r_wave, cy + r_wave, outline=ring_color, width=1.5)
        self.create_oval(cx - 3.5, cy - 3.5, cx + 3.5, cy + 3.5, fill=color, outline="")

        self.pulse_phase += 0.22
        self.after_id = self.after(35, self._step)


class ModernMetricCard(tk.Frame):
    """Card metrik modern dengan ikon, angka besar, dan subjudul."""

    def __init__(
        self,
        parent,
        icon: str,
        title: str,
        value: str,
        subtitle: str = "",
        accent_color: str = COLOR_BLUE,
        **kwargs
    ) -> None:
        super().__init__(
            parent,
            bg=COLOR_BG_CARD,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            padx=12,
            pady=8,
            **kwargs
        )
        self.accent_color = accent_color

        top_row = tk.Frame(self, bg=COLOR_BG_CARD)
        top_row.pack(fill="x")

        tk.Label(
            top_row,
            text=f"{icon} {title}",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_CARD,
        ).pack(side="left")

        self.lbl_value = tk.Label(
            self,
            text=value,
            font=("Segoe UI", 14, "bold"),
            fg=accent_color,
            bg=COLOR_BG_CARD,
        )
        self.lbl_value.pack(anchor="w", pady=(2, 0))

        self.lbl_sub = tk.Label(
            self,
            text=subtitle,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_CARD,
        )
        self.lbl_sub.pack(anchor="w")

    def update_data(self, value: str, subtitle: str | None = None) -> None:
        self.lbl_value.configure(text=value)
        if subtitle is not None:
            self.lbl_sub.configure(text=subtitle)


# ----------------------------------------------------------------------
# MAIN APPLICATION
# ----------------------------------------------------------------------
class CleanCApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CleanC - Deep Storage & System Cleaner")
        # Generous modern dimensions so bottom buttons/progress are never cut off
        win_w, win_h = 1140, 860
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            win_w = min(1140, max(980, screen_w - 60))
            win_h = min(880, max(760, screen_h - 90))
            pos_x = max(0, (screen_w - win_w) // 2)
            pos_y = max(0, (screen_h - win_h) // 2 - 25)
            self.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        except Exception:
            self.geometry("1140x860")
        self.minsize(980, 720)
        self.configure(bg=COLOR_BG_ROOT)

        # Calibrate DPI font and layout scaling
        try:
            dpi = self.winfo_fpixels('1i')
            if dpi > 0:
                self.tk.call('tk', 'scaling', dpi / 72.0)
        except Exception:
            pass

        # Multi-layer app icon setup (Taskbar, Titlebar, Alt-Tab)
        base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        icon_path = base_dir / "CleanC.ico"
        if not icon_path.exists():
            icon_path = Path(__file__).resolve().parent / "CleanC.ico"
        if not icon_path.exists():
            icon_path = base_dir / "service_worker_cleaner.ico"

        if icon_path.exists():
            try:
                self.iconbitmap(default=str(icon_path))
            except Exception:
                try:
                    self.iconbitmap(str(icon_path))
                except Exception:
                    pass

        png_path = base_dir / "CleanC.png"
        if not png_path.exists():
            png_path = Path(__file__).resolve().parent / "CleanC.png"

        # Provide multi-resolution pre-sharpened mipmaps to Tkinter iconphoto
        # Prevents Tkinter/Windows from doing crude, blurry nearest-neighbor downscaling
        self._app_icon_photos = []
        if png_path.exists():
            try:
                base_img = Image.open(png_path).convert("RGBA")
                for s in (16, 20, 24, 32, 40, 48, 64, 128, 256):
                    sub = base_img.resize((s, s), Image.Resampling.LANCZOS)
                    if s <= 24:
                        sub = sub.filter(ImageFilter.UnsharpMask(radius=1.0, percent=140, threshold=2))
                    elif s <= 48:
                        sub = sub.filter(ImageFilter.UnsharpMask(radius=1.0, percent=110, threshold=2))
                    self._app_icon_photos.append(ImageTk.PhotoImage(sub))
                if self._app_icon_photos:
                    self.iconphoto(True, *self._app_icon_photos)
            except Exception:
                try:
                    self._app_icon_fallback = tk.PhotoImage(file=str(png_path))
                    self.iconphoto(True, self._app_icon_fallback)
                except Exception:
                    pass

        # Windows Win32 API icon binding: query exact system metrics for razor-sharp Taskbar & Titlebar rendering
        if sys.platform == "win32" and icon_path.exists():
            try:
                self.update_idletasks()
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                if hwnd:
                    # 11: SM_CXICON, 12: SM_CYICON (Taskbar / Alt+Tab)
                    # 49: SM_CXSMICON, 50: SM_CYSMICON (Titlebar)
                    cx_big = ctypes.windll.user32.GetSystemMetrics(11) or 32
                    cy_big = ctypes.windll.user32.GetSystemMetrics(12) or 32
                    cx_small = ctypes.windll.user32.GetSystemMetrics(49) or 16
                    cy_small = ctypes.windll.user32.GetSystemMetrics(50) or 16

                    # LR_LOADFROMFILE = 0x0010, IMAGE_ICON = 1
                    h_big = ctypes.windll.user32.LoadImageW(None, str(icon_path), 1, cx_big, cy_big, 0x0010)
                    h_small = ctypes.windll.user32.LoadImageW(None, str(icon_path), 1, cx_small, cy_small, 0x0010)
                    if h_big:
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, h_big)  # WM_SETICON, ICON_BIG
                    if h_small:
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, h_small)  # WM_SETICON, ICON_SMALL
            except Exception:
                pass

        # State Variables: Global Storage & Cleaning Stats
        self.stats_data = load_clean_stats()
        self.session_freed_bytes = 0
        self.lifetime_freed_bytes = self.stats_data.get("total_freed_bytes", 0)

        self.drive_c_free_var = tk.StringVar(value="Sisa Free: Memeriksa...")
        self.drive_c_detail_var = tk.StringVar(value="Total: Memeriksa...")
        self.total_cleaned_var = tk.StringVar(value=format_size(self.lifetime_freed_bytes))
        self.session_cleaned_var = tk.StringVar(value="Sesi ini: 0 B dibebaskan")
        self.language = "id"

        # State Variables: Web Browsers (Chrome, Brave, Edge, Firefox)
        self.all_items: list[TargetItem] = []
        self.displayed_items: list[TargetItem] = []
        self.browser_sort_column = "no"
        self.browser_sort_reverse = False
        self.is_scanning = False
        self.is_deleting = False

        # Chrome is the predictable default; users can switch to other browsers.
        init_browser_name = "🌐 Google Chrome"
        init_browser_path = DEFAULT_CHROME_USER_DATA

        self.browser_select_var = tk.StringVar(value=init_browser_name)
        self.browser_running_text_var = tk.StringVar(value="Status Browser: Memeriksa...")
        self.path_var = tk.StringVar(value=str(init_browser_path))
        self.filter_var = tk.StringVar(value=FILTER_ALL)
        self.search_var = tk.StringVar(value="")
        self.chrome_status_var = tk.StringVar(
            value="Pilih target dan klik 'Scan' untuk mencari folder yang dapat dibersihkan."
        )

        # State Variables: Panther
        self.panther_include_all = tk.BooleanVar(value=True)
        self.panther_status_var = tk.StringVar(
            value="Klik 'Bersihkan Log Panther' untuk membersihkan folder log monitor."
        )
        self.is_panther_cleaning = False

        # State Variables: CapCut Cache/Projects
        self.capcut_scope_var = tk.StringVar(value=SCOPE_CAPCUT_ALL)
        self.capcut_path_var = tk.StringVar(value=str(DEFAULT_CAPCUT_CACHE))
        self.capcut_projects_path_var = tk.StringVar(value=str(DEFAULT_CAPCUT_PROJECTS))
        self.capcut_search_var = tk.StringVar(value="")
        self.capcut_filter_type_var = tk.StringVar(value="Semua Item")
        self.capcut_all_items: list[CapCutItem] = []
        self.capcut_displayed_items: list[CapCutItem] = []
        self.capcut_sort_column = "no"
        self.capcut_sort_reverse = False
        self.generic_sort_reverse: dict[tuple[str, str], bool] = {}
        self.is_capcut_scanning = False
        self.is_capcut_deleting = False
        self.capcut_status_var = tk.StringVar(
            value="Pilih target dan klik 'Scan' untuk mencari folder cache/projects CapCut."
        )
        self.capcut_running_text_var = tk.StringVar(value="Status CapCut: Memeriksa...")

        # State Variables: CapCut Old Versions
        self.capcut_apps_path_var = tk.StringVar(value=str(DEFAULT_CAPCUT_APPS))
        self.capcut_versions: list[CapCutVersionItem] = []
        self.capcut_version_status_var = tk.StringVar(
            value="Memindai folder instalasi versi CapCut..."
        )
        self.capcut_latest_ver_var = tk.StringVar(value="Versi Terbaru: Memeriksa...")
        self.capcut_savable_var = tk.StringVar(value="Dapat Dihemat: Menghitung...")
        self.is_version_scanning = False
        self.is_version_deleting = False

        # State Variables: Dev & Package Cache
        self.dev_cache_items: list[DevCacheItem] = []
        self.dev_cache_status_var = tk.StringVar(
            value="Memindai cache developer (Playwright, NPM, PIP, PNPM)..."
        )
        self.is_dev_cache_scanning = False
        self.is_dev_cache_cleaning = False

        self._configure_styles()
        self._build_ui()
        self._install_language_traces()

        # Initial Background Scans
        self.refresh_disk_usage()
        self.refresh_panther_info()
        self.check_capcut_process()
        self.check_browser_process()
        self.start_scan()
        self.start_capcut_scan()
        self.start_capcut_version_scan()
        self.start_dev_cache_scan()

    # ------------------------------------------------------------------
    # STYLING CONFIGURATION (Sleek Dark Theme)
    # ------------------------------------------------------------------
    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # --------------------------------------------------------------
        # 1. MODERN SLIM SCROLLBARS (Strips Windows 95 arrow buttons)
        # --------------------------------------------------------------
        try:
            style.layout(
                "Vertical.TScrollbar",
                [("Vertical.Scrollbar.trough", {
                    "sticky": "ns",
                    "children": [("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]
                })]
            )
            style.layout(
                "Horizontal.TScrollbar",
                [("Horizontal.Scrollbar.trough", {
                    "sticky": "we",
                    "children": [("Horizontal.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]
                })]
            )
        except Exception:
            pass

        style.configure(
            "Vertical.TScrollbar",
            background="#2d3748",
            troughcolor="#090d16",
            bordercolor="#090d16",
            darkcolor="#2d3748",
            lightcolor="#2d3748",
            arrowsize=0,
            gripcount=0,
            relief="flat",
            borderwidth=0,
            width=8,
        )
        style.map(
            "Vertical.TScrollbar",
            background=[("pressed", COLOR_BLUE), ("active", "#4b5e82"), ("disabled", "#111827")],
            troughcolor=[("active", "#090d16")],
        )

        style.configure(
            "Horizontal.TScrollbar",
            background="#2d3748",
            troughcolor="#090d16",
            bordercolor="#090d16",
            darkcolor="#2d3748",
            lightcolor="#2d3748",
            arrowsize=0,
            gripcount=0,
            relief="flat",
            borderwidth=0,
            width=8,
        )
        style.map(
            "Horizontal.TScrollbar",
            background=[("pressed", COLOR_BLUE), ("active", "#4b5e82"), ("disabled", "#111827")],
            troughcolor=[("active", "#090d16")],
        )

        # --------------------------------------------------------------
        # 2. MODERN DARK DROPDOWN / COMBOBOX
        # --------------------------------------------------------------
        style.configure(
            "TCombobox",
            fieldbackground="#0f172a",
            background="#1e293b",
            foreground="#f8fafc",
            darkcolor="#26354d",
            lightcolor="#26354d",
            bordercolor="#26354d",
            arrowcolor=COLOR_CYAN_LIGHT,
            arrowsize=13,
            relief="flat",
            borderwidth=1,
            padding=[8, 5],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#0f172a"), ("focus", "#172033")],
            background=[("readonly", "#1e293b"), ("active", "#334155")],
            foreground=[("readonly", "#f8fafc")],
            bordercolor=[("focus", COLOR_BLUE), ("active", COLOR_CYAN_LIGHT)],
            arrowcolor=[("active", "#ffffff")],
        )

        # Tkinter popup menu options for Combobox dropdown
        self.option_add("*TCombobox*Listbox.background", "#0f172a")
        self.option_add("*TCombobox*Listbox.foreground", "#f8fafc")
        self.option_add("*TCombobox*Listbox.selectBackground", "#2563eb")
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))
        self.option_add("*TCombobox*Listbox.relief", "flat")
        self.option_add("*TCombobox*Listbox.borderWidth", "1")
        self.option_add("*TCombobox*Listbox.highlightThickness", "1")
        self.option_add("*TCombobox*Listbox.highlightColor", "#3b82f6")
        # Remove Tk's dotted keyboard-focus rectangle from native checkboxes.
        self.option_add("*Checkbutton*highlightThickness", 0)
        self.option_add("*Checkbutton*borderWidth", 0)
        self.option_add("*Checkbutton*relief", "flat")

        # --------------------------------------------------------------
        # 3. MODERN MENU TABS (Cyber Dashboard Tabs)
        # --------------------------------------------------------------
        style.configure(
            "TNotebook",
            background=COLOR_BG_ROOT,
            borderwidth=0,
            tabmargins=[0, 0, 0, 0],
            relief="flat",
        )
        style.configure(
            "TNotebook.Tab",
            background="#0d1424",
            foreground=COLOR_TEXT_MUTED,
            font=("Segoe UI", 9, "bold"),
            padding=[12, 4],
            borderwidth=1,
            bordercolor="#1e293b",
            lightcolor="#1e293b",
            darkcolor="#1e293b",
            relief="flat",
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", COLOR_BG_SURFACE), ("active", "#192438")],
            foreground=[("selected", COLOR_CYAN_LIGHT), ("active", "#ffffff")],
            bordercolor=[("selected", COLOR_CYAN), ("active", "#334155")],
            lightcolor=[("selected", COLOR_CYAN), ("active", "#334155")],
            darkcolor=[("selected", COLOR_CYAN), ("active", "#334155")],
        )

        # Sub-notebook styling
        style.configure(
            "Sub.TNotebook",
            background=COLOR_BG_SURFACE,
            borderwidth=0,
            tabmargins=[0, 0, 0, 0],
            relief="flat",
        )
        style.configure(
            "Sub.TNotebook.Tab",
            background="#0f172a",
            foreground=COLOR_TEXT_MUTED,
            font=("Segoe UI", 8, "bold"),
            padding=[10, 3],
            borderwidth=1,
            bordercolor="#1e293b",
            lightcolor="#1e293b",
            darkcolor="#1e293b",
            relief="flat",
        )
        style.map(
            "Sub.TNotebook.Tab",
            background=[("selected", COLOR_BG_CARD), ("active", "#172033")],
            foreground=[("selected", COLOR_CYAN_LIGHT), ("active", "#ffffff")],
            bordercolor=[("selected", COLOR_BLUE), ("active", "#334155")],
            lightcolor=[("selected", COLOR_BLUE), ("active", "#334155")],
            darkcolor=[("selected", COLOR_BLUE), ("active", "#334155")],
        )

        # --------------------------------------------------------------
        # 4. TREEVIEW TABLES (Clean Dark Data Grid)
        # --------------------------------------------------------------
        style.configure(
            "Treeview",
            background=COLOR_BG_INPUT,
            fieldbackground=COLOR_BG_INPUT,
            foreground=COLOR_TEXT_WHITE,
            font=("Segoe UI", 9),
            rowheight=26,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#151e2e",
            foreground=COLOR_TEXT_MUTED,
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#1e2a40")],
            foreground=[("active", COLOR_TEXT_WHITE)],
        )
        style.map(
            "Treeview",
            background=[("selected", "#1d4ed8")],
            foreground=[("selected", "#ffffff")],
        )

        # --------------------------------------------------------------
        # 5. BUTTON STYLES (Ultra Sleek, Flat, Dark Slate Theme)
        # --------------------------------------------------------------
        # Base fallback button
        style.configure(
            "TButton",
            font=("Segoe UI", 9),
            background="#1e293b",
            foreground="#f8fafc",
            borderwidth=1,
            bordercolor="#26354d",
            lightcolor="#26354d",
            darkcolor="#26354d",
            relief="flat",
            focuscolor="none",
            padding=[10, 5],
        )
        style.map(
            "TButton",
            background=[
                ("disabled", "#111827"),
                ("pressed", "#0f172a"),
                ("active", "#334155"),
            ],
            foreground=[
                ("disabled", "#475569"),
                ("active", "#ffffff"),
            ],
            relief=[("pressed", "flat"), ("!pressed", "flat")],
        )

        # Secondary Button (Clean dark slate button)
        style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 9),
            background="#1e293b",
            foreground="#f8fafc",
            borderwidth=1,
            bordercolor="#26354d",
            lightcolor="#26354d",
            darkcolor="#26354d",
            relief="flat",
            focuscolor="none",
            padding=[10, 5],
        )
        style.map(
            "Secondary.TButton",
            background=[
                ("disabled", "#111827"),
                ("pressed", "#0f172a"),
                ("active", "#334155"),
            ],
            foreground=[
                ("disabled", "#475569"),
                ("active", "#ffffff"),
            ],
            bordercolor=[("active", COLOR_BLUE)],
            relief=[("pressed", "flat"), ("!pressed", "flat")],
        )

        # Outline / Cyan Accent Button
        style.configure(
            "Outline.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#0f172a",
            foreground=COLOR_CYAN_LIGHT,
            borderwidth=1,
            bordercolor=COLOR_CYAN,
            lightcolor=COLOR_CYAN,
            darkcolor=COLOR_CYAN,
            relief="flat",
            focuscolor="none",
            padding=[10, 5],
        )
        style.map(
            "Outline.TButton",
            background=[
                ("disabled", "#111827"),
                ("pressed", "#0f172a"),
                ("active", "#1e293b"),
            ],
            foreground=[
                ("disabled", "#475569"),
                ("active", "#ffffff"),
            ],
            relief=[("pressed", "flat"), ("!pressed", "flat")],
        )

        # Primary Action Button (Electric Blue)
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 9, "bold"),
            background=COLOR_BLUE,
            foreground="#ffffff",
            borderwidth=0,
            relief="flat",
            focuscolor="none",
            padding=[12, 5],
        )
        style.map(
            "Primary.TButton",
            background=[
                ("disabled", "#1e293b"),
                ("pressed", "#1d4ed8"),
                ("active", COLOR_BLUE_HOVER),
            ],
            foreground=[("disabled", "#475569"), ("active", "#ffffff")],
        )

        # Danger Button (Rose / Crimson Red)
        style.configure(
            "Danger.TButton",
            font=("Segoe UI", 9, "bold"),
            background=COLOR_RED,
            foreground="#ffffff",
            borderwidth=0,
            relief="flat",
            focuscolor="none",
            padding=[12, 5],
        )
        style.map(
            "Danger.TButton",
            background=[
                ("disabled", "#1e293b"),
                ("pressed", "#b91c1c"),
                ("active", COLOR_RED_HOVER),
            ],
            foreground=[("disabled", "#475569"), ("active", "#ffffff")],
        )

        # Success Button (Emerald Green)
        style.configure(
            "Success.TButton",
            font=("Segoe UI", 9, "bold"),
            background=COLOR_GREEN,
            foreground="#ffffff",
            borderwidth=0,
            relief="flat",
            focuscolor="none",
            padding=[12, 5],
        )
        style.map(
            "Success.TButton",
            background=[
                ("disabled", "#1e293b"),
                ("pressed", "#047857"),
                ("active", COLOR_GREEN_HOVER),
            ],
            foreground=[("disabled", "#475569"), ("active", "#ffffff")],
        )

        # CapCut Brand Button (Neon Violet)
        style.configure(
            "CapCut.TButton",
            font=("Segoe UI", 9, "bold"),
            background=COLOR_PURPLE,
            foreground="#ffffff",
            borderwidth=0,
            relief="flat",
            focuscolor="none",
            padding=[12, 5],
        )
        style.map(
            "CapCut.TButton",
            background=[
                ("disabled", "#1e293b"),
                ("pressed", "#6d28d9"),
                ("active", COLOR_PURPLE_HOVER),
            ],
            foreground=[("disabled", "#475569"), ("active", "#ffffff")],
        )

    # ------------------------------------------------------------------
    # TOP HEADER & MAIN UI SHELL
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # Very subtle nebula wash: adds depth without competing with the data UI.
        self._nebula = tk.Canvas(self, bg=COLOR_BG_ROOT, highlightthickness=0, bd=0)
        self._nebula.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._nebula.create_oval(-180, -120, 420, 300, fill="#101d3b", outline="")
        self._nebula.create_oval(760, 40, 1320, 520, fill="#171432", outline="")
        self._nebula.create_oval(300, 620, 900, 1100, fill="#0b2430", outline="")
        # The canvas is created first, so later widgets naturally stack above it.

        # Header Container
        header_frame = tk.Frame(self, bg=COLOR_BG_ROOT, padx=16, pady=10)
        header_frame.pack(fill="x")

        # Left branding
        brand_left = tk.Frame(header_frame, bg=COLOR_BG_ROOT)
        brand_left.pack(side="left")

        title_row = tk.Frame(brand_left, bg=COLOR_BG_ROOT)
        title_row.pack(anchor="w")

        logo_title = tk.Label(
            title_row,
            text="⚡ CleanC",
            font=("Segoe UI", 18, "bold"),
            fg=COLOR_CYAN_LIGHT,
            bg=COLOR_BG_ROOT,
        )
        logo_title.pack(side="left")

        badge_ver = tk.Label(
            title_row,
            text=" v2.5 PRO ",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_WHITE,
            bg="#1e3a8a",
            padx=5,
            pady=1,
        )
        badge_ver.pack(side="left", padx=(8, 0), pady=(4, 0))

        sub_desc = tk.Label(
            brand_left,
            text="Advanced System, Browser & App Storage Optimizer",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_ROOT,
        )
        sub_desc.pack(anchor="w", pady=(2, 0))

        # Right quick controls
        brand_right = tk.Frame(header_frame, bg=COLOR_BG_ROOT)
        brand_right.pack(side="right", pady=4)

        # About Button
        self.btn_language = tk.Button(
            brand_right,
            text="EN",
            font=("Segoe UI", 8, "bold"),
            bg="#24324a", fg=COLOR_CYAN_LIGHT, relief="flat",
            activebackground="#334155", activeforeground="#ffffff",
            command=self.toggle_language, padx=9, pady=3, cursor="hand2",
        )
        self.btn_language.pack(side="right", padx=(0, 6))

        self.btn_about = tk.Button(
            brand_right,
            text="ℹ️ About",
            font=("Segoe UI", 8, "bold"),
            bg="#1e293b",
            fg=COLOR_CYAN_LIGHT,
            relief="flat",
            activebackground="#334155",
            activeforeground="#ffffff",
            command=self.show_about_popup,
            padx=9,
            pady=3,
            cursor="hand2",
        )
        self.btn_about.pack(side="right")

        # QRIS Donate Button
        self.btn_donate = tk.Button(
            brand_right,
            text="💖 Donasi QRIS",
            font=("Segoe UI", 8, "bold"),
            bg="#1e293b",
            fg="#f43f5e",
            relief="flat",
            activebackground="#334155",
            activeforeground="#ffffff",
            command=self.show_donate_popup,
            padx=9,
            pady=3,
            cursor="hand2",
        )
        self.btn_donate.pack(side="right", padx=(0, 6))

        # CapCut live process quick badge
        self.btn_header_capcut = tk.Button(
            brand_right,
            text="🎬 CapCut: Memeriksa...",
            font=("Segoe UI", 8, "bold"),
            bg="#1e293b",
            fg=COLOR_TEXT_MUTED,
            relief="flat",
            activebackground="#334155",
            activeforeground="#ffffff",
            command=self.close_capcut_process,
            padx=8,
            pady=3,
            cursor="hand2",
        )
        self.btn_header_capcut.pack(side="right", padx=(0, 6))

        # SYSTEM STORAGE & CLEANING STATS DASHBOARD STRIP
        banner = tk.Frame(self, bg=COLOR_BG_CARD, padx=14, pady=8, highlightbackground=COLOR_BORDER, highlightthickness=1)
        banner.pack(fill="x", padx=12, pady=(0, 8))

        # Left Column: Drive C: Info & Storage Bar
        c_left = tk.Frame(banner, bg=COLOR_BG_CARD)
        c_left.pack(side="left", fill="both", expand=True)

        top_c = tk.Frame(c_left, bg=COLOR_BG_CARD)
        top_c.pack(fill="x")

        tk.Label(
            top_c,
            text="💾 Kapasitas Drive C:",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_BG_CARD,
        ).pack(side="left")

        self.lbl_drive_c_free = tk.Label(
            top_c,
            textvariable=self.drive_c_free_var,
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_GREEN_HOVER,
            bg=COLOR_BG_CARD,
        )
        self.lbl_drive_c_free.pack(side="left", padx=(8, 0))

        btn_ref_c = tk.Button(
            top_c,
            text="🔄",
            font=("Segoe UI", 7),
            bg="#1e293b",
            fg=COLOR_TEXT_MUTED,
            relief="flat",
            activebackground="#334155",
            activeforeground="#ffffff",
            cursor="hand2",
            padx=4,
            pady=0,
            command=self.refresh_disk_usage,
        )
        btn_ref_c.pack(side="left", padx=(8, 0))

        self.lbl_drive_c_detail = tk.Label(
            c_left,
            textvariable=self.drive_c_detail_var,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_CARD,
        )
        self.lbl_drive_c_detail.pack(anchor="w", pady=(2, 2))

        # Visual Disk Gauge Bar
        self.canvas_disk_gauge = tk.Canvas(c_left, height=6, bg="#0f172a", highlightthickness=0)
        self.canvas_disk_gauge.pack(fill="x", pady=(2, 0))
        self.canvas_disk_gauge.bind("<Configure>", lambda e: self._draw_disk_gauge())

        # Divider
        tk.Frame(banner, bg=COLOR_BORDER, width=1).pack(side="left", fill="y", padx=16, pady=2)

        # Right Column: Total Cleaned Counter
        c_right = tk.Frame(banner, bg=COLOR_BG_CARD)
        c_right.pack(side="right", padx=(4, 0))

        top_clean = tk.Frame(c_right, bg=COLOR_BG_CARD)
        top_clean.pack(fill="x")

        tk.Label(
            top_clean,
            text="🧹 Total Telah Dibersihkan:",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_BG_CARD,
        ).pack(side="left")

        self.lbl_total_cleaned = tk.Label(
            top_clean,
            textvariable=self.total_cleaned_var,
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_CYAN_LIGHT,
            bg=COLOR_BG_CARD,
        )
        self.lbl_total_cleaned.pack(side="left", padx=(8, 0))

        self.lbl_session_cleaned = tk.Label(
            c_right,
            textvariable=self.session_cleaned_var,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_CARD,
        )
        self.lbl_session_cleaned.pack(anchor="w", pady=(2, 0))

        # Main Notebook Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # TAB 1: Web Browsers Cleaner
        chrome_frame = tk.Frame(self.notebook, bg=COLOR_BG_SURFACE, padx=12, pady=10)
        self.notebook.add(chrome_frame, text="  🌐 Web Browsers  ")
        self._build_chrome_tab(chrome_frame)

        # TAB 2: CapCut Studio Hub
        capcut_frame = tk.Frame(self.notebook, bg=COLOR_BG_SURFACE, padx=12, pady=10)
        self.notebook.add(capcut_frame, text="  🎬 CapCut Studio  ")
        self._build_capcut_tab(capcut_frame)

        # TAB 3: Windows Panther
        panther_frame = tk.Frame(self.notebook, bg=COLOR_BG_SURFACE, padx=14, pady=12)
        self.notebook.add(panther_frame, text="  🪟 Windows Panther  ")
        self._build_panther_tab(panther_frame)

        # TAB 4: Dev & Package Cache
        dev_frame = tk.Frame(self.notebook, bg=COLOR_BG_SURFACE, padx=14, pady=12)
        self.notebook.add(dev_frame, text="  🛠️ Dev & Package Cache  ")
        self._build_dev_cache_tab(dev_frame)



    # ------------------------------------------------------------------
    # SYSTEM STORAGE & DISK HEALTH METHODS
    # ------------------------------------------------------------------
    def refresh_disk_usage(self) -> None:
        """Perbarui status penyimpanan Drive C: dan gambar indikator gauge."""
        info = get_drive_c_usage()
        self._disk_info = info
        free_str = info["free_str"]
        total_str = info["total_str"]
        free_pct = info["free_pct"]
        used_pct = info["used_pct"]

        self.drive_c_free_var.set(f"Sisa Free: {free_str}")
        self.drive_c_detail_var.set(
            f"dari Total {total_str} ({free_pct:.1f}% Tersedia / {used_pct:.1f}% Terpakai)"
        )

        if hasattr(self, "lbl_drive_c_free"):
            if free_pct < 10:
                self.lbl_drive_c_free.configure(fg=COLOR_RED_HOVER)
            elif free_pct < 20:
                self.lbl_drive_c_free.configure(fg=COLOR_AMBER)
            else:
                self.lbl_drive_c_free.configure(fg=COLOR_GREEN_HOVER)

        self._draw_disk_gauge()

    def _draw_disk_gauge(self) -> None:
        """Gambar mini progress gauge untuk kapasitas Drive C:."""
        if not hasattr(self, "canvas_disk_gauge"):
            return
        info = getattr(self, "_disk_info", None)
        if not info:
            info = get_drive_c_usage()
            self._disk_info = info

        used_pct = info.get("used_pct", 0)
        free_pct = info.get("free_pct", 0)
        bar_color = COLOR_RED_HOVER if free_pct < 10 else (COLOR_AMBER if free_pct < 20 else COLOR_GREEN_HOVER)

        self.canvas_disk_gauge.delete("all")
        w = self.canvas_disk_gauge.winfo_width()
        if w <= 1:
            w = 400
        h = self.canvas_disk_gauge.winfo_height() or 6

        used_w = int(w * (used_pct / 100.0))
        # Background
        self.canvas_disk_gauge.create_rectangle(0, 0, w, h, fill="#0f172a", outline="")
        # Used
        self.canvas_disk_gauge.create_rectangle(0, 0, used_w, h, fill="#2563eb", outline="")
        # Free
        self.canvas_disk_gauge.create_rectangle(used_w, 0, w, h, fill=bar_color, outline="")

    def record_cleaned_space(self, freed_bytes: int) -> None:
        """Catat pembersihan ruang disk dan perbarui tampilan counter serta Drive C:."""
        if freed_bytes <= 0:
            return
        self.session_freed_bytes += freed_bytes
        self.lifetime_freed_bytes += freed_bytes
        record_freed_bytes(freed_bytes)

        self.total_cleaned_var.set(format_size(self.lifetime_freed_bytes))
        self.session_cleaned_var.set(f"Sesi ini: {format_size(self.session_freed_bytes)} dibebaskan")

        def _flash_done():
            if hasattr(self, "lbl_total_cleaned"):
                self.lbl_total_cleaned.configure(fg=COLOR_CYAN_LIGHT)

        if hasattr(self, "lbl_total_cleaned"):
            self.lbl_total_cleaned.configure(fg=COLOR_GREEN_HOVER)
            self.after(1500, _flash_done)

        self.refresh_disk_usage()

    # ------------------------------------------------------------------
    # TAB 1: WEB BROWSERS CLEANER (CHROME, BRAVE & EDGE)
    # ------------------------------------------------------------------
    def _get_current_browser_key(self) -> str:
        name = self.browser_select_var.get()
        if "Brave" in name:
            return "brave"
        elif "Edge" in name:
            return "edge"
        elif "Firefox" in name:
            return "firefox"
        return "chrome"

    def _browser_label(self, key: str) -> str:
        return {"brave": "Brave Browser", "edge": "Microsoft Edge", "firefox": "Mozilla Firefox"}.get(key, "Google Chrome")

    def check_browser_process(self) -> None:
        key = self._get_current_browser_key()
        running = is_browser_running(key)
        b_label = self._browser_label(key)
        if running:
            self.browser_running_text_var.set(f"⚠️ {b_label} sedang berjalan (Disarankan ditutup sebelum menghapus)")
            if hasattr(self, "lbl_browser_proc"):
                self.lbl_browser_proc.configure(fg=COLOR_RED_HOVER)
            if hasattr(self, "btn_close_browser"):
                self.btn_close_browser.configure(state="normal")
        else:
            self.browser_running_text_var.set(f"✅ {b_label} tidak berjalan (Aman untuk dibersihkan)")
            if hasattr(self, "lbl_browser_proc"):
                self.lbl_browser_proc.configure(fg=COLOR_GREEN_HOVER)
            if hasattr(self, "btn_close_browser"):
                self.btn_close_browser.configure(state="disabled")

    def close_browser_process(self) -> None:
        key = self._get_current_browser_key()
        b_label = self._browser_label(key)
        if not is_browser_running(key):
            messagebox.showinfo("Info", f"{b_label} tidak sedang berjalan.")
            self.check_browser_process()
            return

        confirm = messagebox.askyesno(
            f"Tutup {b_label}",
            f"Apakah Anda yakin ingin menutup proses {b_label} sekarang?\n\n"
            "Pastikan Anda telah menyimpan tab atau pekerjaan penting di browser.",
        )
        if not confirm:
            return

        ok, msg = kill_browser_process(key)
        if ok:
            messagebox.showinfo("Berhasil", f"{b_label} berhasil ditutup.")
        else:
            messagebox.showwarning("Perhatian", msg)
        self.check_browser_process()

    def on_browser_combo_selected(self) -> None:
        key = self._get_current_browser_key()
        if key == "brave":
            self.path_var.set(str(DEFAULT_BRAVE_USER_DATA))
            b_label = "Brave Browser"
        elif key == "edge":
            self.path_var.set(str(DEFAULT_EDGE_USER_DATA))
            b_label = "Microsoft Edge"
        elif key == "firefox":
            self.path_var.set(str(DEFAULT_FIREFOX_USER_DATA))
            b_label = "Mozilla Firefox"
        else:
            self.path_var.set(str(DEFAULT_CHROME_USER_DATA))
            b_label = "Google Chrome"

        if hasattr(self, "card_chrome_profiles"):
            self.card_chrome_profiles.lbl_sub.configure(text=f"{b_label} User Data")
        self.check_browser_process()
        self.start_scan()

    def _build_chrome_tab(self, parent: tk.Frame) -> None:
        # Metrics Row
        metric_bar = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        metric_bar.pack(fill="x", pady=(0, 8))

        self.card_chrome_total = ModernMetricCard(
            metric_bar, "🌐", "Service Worker & Cache", "0 B", "Klik Scan untuk memindai", COLOR_BLUE
        )
        self.card_chrome_total.pack(side="left", fill="x", expand=True, padx=(0, 6))

        key = self._get_current_browser_key()
        b_label = self._browser_label(key)
        self.card_chrome_profiles = ModernMetricCard(
            metric_bar, "👤", "Profil Terdeteksi", "0 Profil", f"{b_label} User Data", COLOR_CYAN
        )
        self.card_chrome_profiles.pack(side="left", fill="x", expand=True)

        # Controls Card
        ctrl_card = tk.Frame(parent, bg=COLOR_BG_CARD, padx=10, pady=8, highlightbackground=COLOR_BORDER, highlightthickness=1)
        ctrl_card.pack(fill="x", pady=(0, 8))

        # Browser Selector & Process Status Row
        b_row = tk.Frame(ctrl_card, bg=COLOR_BG_CARD)
        b_row.pack(fill="x", pady=(0, 6))

        tk.Label(b_row, text="Pilih Browser:", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_BG_CARD).pack(side="left", padx=(0, 6))
        self.browser_combo = ttk.Combobox(
            b_row,
            textvariable=self.browser_select_var,
            values=["🌐 Google Chrome", "🦁 Brave Browser", "🌊 Microsoft Edge", "🦊 Mozilla Firefox"],
            state="readonly",
            width=20,
        )
        self.browser_combo.pack(side="left", padx=(0, 10))
        self.browser_combo.bind("<<ComboboxSelected>>", lambda e: self.on_browser_combo_selected())

        self.lbl_browser_proc = tk.Label(
            b_row,
            textvariable=self.browser_running_text_var,
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_GREEN_HOVER,
            bg=COLOR_BG_CARD,
        )
        self.lbl_browser_proc.pack(side="left", padx=(0, 8))

        self.btn_close_browser = ttk.Button(
            b_row,
            text="🛑 Tutup Browser",
            style="Danger.TButton",
            command=self.close_browser_process,
            state="disabled",
        )
        self.btn_close_browser.pack(side="left")

        # Path Row
        path_row = tk.Frame(ctrl_card, bg=COLOR_BG_CARD)
        path_row.pack(fill="x", pady=(0, 6))

        tk.Label(path_row, text="Path:", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_BG_CARD).pack(side="left", padx=(0, 6))
        tk.Entry(
            path_row,
            textvariable=self.path_var,
            font=("Segoe UI", 9),
            bg=COLOR_BG_INPUT,
            fg=COLOR_TEXT_WHITE,
            insertbackground=COLOR_TEXT_WHITE,
            relief="flat",
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
        ).pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=3)

        ttk.Button(path_row, text="📂 Browse...", style="Secondary.TButton", command=self.choose_folder).pack(side="left", padx=(0, 6))
        self.scan_button = ttk.Button(path_row, text="🔍 Scan Sekarang", style="Primary.TButton", command=self.start_scan)
        self.scan_button.pack(side="left")

        # Filter & Search Row
        flt_row = tk.Frame(ctrl_card, bg=COLOR_BG_CARD)
        flt_row.pack(fill="x")

        tk.Label(flt_row, text="Filter:", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_BG_CARD).pack(side="left", padx=(0, 6))
        self.filter_combobox = ttk.Combobox(
            flt_row,
            textvariable=self.filter_var,
            values=[FILTER_ALL, FILTER_SW, FILTER_CACHE],
            state="readonly",
            width=28,
        )
        self.filter_combobox.pack(side="left", padx=(0, 10))
        self.filter_combobox.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

        tk.Label(flt_row, text="Cari Profil:", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_BG_CARD).pack(side="left", padx=(0, 6))
        tk.Entry(
            flt_row,
            textvariable=self.search_var,
            font=("Segoe UI", 9),
            bg=COLOR_BG_INPUT,
            fg=COLOR_TEXT_WHITE,
            insertbackground=COLOR_TEXT_WHITE,
            relief="flat",
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            width=16,
        ).pack(side="left", padx=(0, 10), ipady=2)
        self.search_var.trace_add("write", lambda *args: self.apply_filter())

        ttk.Button(flt_row, text="☑️ Pilih Semua", style="Secondary.TButton", command=self.select_all_rows).pack(side="right", padx=(4, 0))
        ttk.Button(flt_row, text="☐ Batal Pilih", style="Secondary.TButton", command=self.deselect_all_rows).pack(side="right")

        # Bottom Action Bar (Pinned to bottom FIRST so it is NEVER cut off)
        bottom = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        bottom.pack(side="bottom", fill="x", pady=(6, 2))

        # Left status with radar spinner and pulsating dot
        left_status = tk.Frame(bottom, bg=COLOR_BG_SURFACE)
        left_status.pack(side="left", fill="x", expand=True)

        self.chrome_radar = ModernRadarSpinner(left_status, size=28, bg=COLOR_BG_SURFACE)
        self.chrome_radar.pack(side="left", padx=(0, 6))

        self.chrome_dot = PulsingStatusDot(left_status, size=16, bg=COLOR_BG_SURFACE)
        self.chrome_dot.pack(side="left", padx=(0, 6))

        tk.Label(
            left_status,
            textvariable=self.chrome_status_var,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_BG_SURFACE,
        ).pack(side="left")

        # Right Action Buttons
        self.btn_delete_selected = ttk.Button(
            bottom,
            text="🗑️ Hapus Terpilih",
            style="Secondary.TButton",
            command=self.delete_selected,
            state="disabled",
        )
        self.btn_delete_selected.pack(side="right", padx=(6, 0))

        self.btn_delete_all = ttk.Button(
            bottom,
            text="🗑️ Hapus Semua Sesuai Filter",
            command=self.delete_all_filtered,
            state="disabled",
            style="Danger.TButton",
        )
        self.btn_delete_all.pack(side="right")

        # Animated Progress Bar (Shimmer - above bottom bar)
        self.chrome_progress = ShimmerProgressBar(parent, height=8, bg=COLOR_BG_SURFACE, bar_color=COLOR_BLUE)
        self.chrome_progress.pack(side="bottom", fill="x", pady=(0, 6))

        # Table Treeview (Fills remaining space)
        tbl_frame = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        tbl_frame.pack(fill="both", expand=True, pady=(0, 6))

        cols = ("no", "profile", "category", "size", "path")
        self.tree = ttk.Treeview(tbl_frame, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("no", text="#", command=lambda: self.sort_browser("no"))
        self.tree.heading("profile", text="Profil", command=lambda: self.sort_browser("profile"))
        self.tree.heading("category", text="Kategori", command=lambda: self.sort_browser("category"))
        self.tree.heading("size", text="Ukuran", command=lambda: self.sort_browser("size"))
        self.tree.heading("path", text="Lokasi Direktori", command=lambda: self.sort_browser("path"))

        self.tree.column("no", width=42, minwidth=35, anchor="center")
        self.tree.column("profile", width=140, minwidth=100, anchor="w")
        self.tree.column("category", width=130, minwidth=100, anchor="center")
        self.tree.column("size", width=110, minwidth=80, anchor="e")
        self.tree.column("path", width=480, minwidth=220, anchor="w")

        v_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(tbl_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        tbl_frame.rowconfigure(0, weight=1)
        tbl_frame.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", lambda e: self._on_tree_select())

    def choose_folder(self) -> None:
        initial = self.path_var.get()
        if not Path(initial).is_dir():
            initial = str(DEFAULT_USER_DATA.parent)
        b_key = self._get_current_browser_key()
        b_label = self._browser_label(b_key)
        selected = filedialog.askdirectory(initialdir=initial, title=f"Pilih folder {b_label} User Data")
        if selected:
            self.path_var.set(selected)

    def start_scan(self) -> None:
        if self.is_scanning or self.is_deleting:
            return

        user_data = Path(self.path_var.get())
        b_key = self._get_current_browser_key()
        b_label = self._browser_label(b_key)

        if not user_data.is_dir():
            messagebox.showerror(
                "Folder Tidak Ditemukan",
                f"Direktori {b_label} User Data tidak valid atau browser belum pernah dibuka:\n{user_data}"
            )
            return

        self.is_scanning = True
        self.scan_button.configure(state="disabled")
        self.btn_delete_selected.configure(state="disabled")
        self.btn_delete_all.configure(state="disabled")

        # Start animations
        self.chrome_radar.start()
        self.chrome_dot.set_state("scanning")
        self.chrome_progress.start_indeterminate()
        self.chrome_status_var.set(f"Sedang memindai profil {b_label}... Mohon tunggu.")

        self.tree.delete(*self.tree.get_children())
        self.all_items.clear()
        self.displayed_items.clear()

        threading.Thread(target=self._scan_worker, args=(user_data,), daemon=True).start()

    def _scan_worker(self, user_data: Path) -> None:
        try:
            raw_targets = find_targets(user_data)
            items = [TargetItem(p, user_data) for p in raw_targets]
            self.after(0, self._scan_done, items, None)
        except Exception as exc:
            self.after(0, self._scan_done, [], str(exc))

    def _scan_done(self, items: list[TargetItem], error: str | None) -> None:
        self.chrome_radar.stop()
        self.chrome_dot.set_state("idle")
        self.chrome_progress.stop()
        self.is_scanning = False
        self.scan_button.configure(state="normal")
        self.check_browser_process()

        if error:
            messagebox.showerror("Gagal Memindai", f"Terjadi kesalahan saat scan:\n{error}")
            self.chrome_status_var.set("Pemindaian gagal.")
            return

        self.all_items = items
        self.apply_filter()

    def apply_filter(self) -> None:
        selected_filter = self.filter_var.get()
        query = self.search_var.get().strip().lower()

        filtered: list[TargetItem] = []
        profiles_found = set()
        for item in self.all_items:
            profiles_found.add(item.profile)
            if selected_filter in (FILTER_SW, "Service Worker only", "Service Worker Only") and item.category != "Service Worker":
                continue
            if selected_filter in (FILTER_CACHE, "Cache only", "Cache Only") and item.category != "Cache":
                continue
            if query and query not in item.profile.lower() and query not in str(item.path).lower():
                continue
            filtered.append(item)

        if self.browser_sort_column != "no":
            key = self.browser_sort_column
            filtered.sort(key=lambda item: {
                "profile": item.profile.casefold(),
                "category": item.category.casefold(),
                "size": item.size,
                "path": str(item.path).casefold(),
            }[key], reverse=self.browser_sort_reverse)

        self.displayed_items = filtered
        self.tree.delete(*self.tree.get_children())
        total_size = 0
        for idx, item in enumerate(self.displayed_items, start=1):
            total_size += item.size
            self.tree.insert(
                "",
                "end",
                iid=str(idx - 1),
                values=(idx, item.profile, item.category, item.size_str, str(item.path)),
            )

        # Update Metric Cards
        b_key = self._get_current_browser_key()
        b_label = self._browser_label(b_key)
        self.card_chrome_total.update_data(format_size(total_size), f"{len(self.displayed_items)} folder target")
        self.card_chrome_profiles.update_data(f"{len(profiles_found)} Profil", f"{b_label} User Data")

        has_items = len(self.displayed_items) > 0
        self.btn_delete_all.configure(state="normal" if has_items else "disabled")
        self.btn_delete_selected.configure(state="disabled")

        if not self.all_items:
            self.chrome_status_var.set("Tidak ditemukan folder target yang cocok.")
        else:
            self.chrome_status_var.set(
                f"Menampilkan {len(self.displayed_items)} folder ({format_size(total_size)}) "
                f"dari total {len(self.all_items)} ditemukan."
            )

    def sort_browser(self, column: str) -> None:
        if self.browser_sort_column == column:
            self.browser_sort_reverse = not self.browser_sort_reverse
        else:
            self.browser_sort_column = column
            self.browser_sort_reverse = False
        self.apply_filter()

    def sort_tree_rows(self, tree: ttk.Treeview, column: str) -> None:
        """Sort any Treeview in-place while preserving item IDs and selection."""
        key = str(tree)
        state_key = (key, column)
        reverse = not self.generic_sort_reverse.get(state_key, False)
        self.generic_sort_reverse[state_key] = reverse
        columns = list(tree["columns"])
        try:
            index = columns.index(column)
        except ValueError:
            return
        rows = [(tree.set(iid, column), iid) for iid in tree.get_children("")]

        def sort_key(row):
            value = row[0].replace(",", "").strip()
            try:
                return float(value.split()[0])
            except (ValueError, IndexError):
                return value.casefold()

        for position, (_value, iid) in enumerate(sorted(rows, key=sort_key, reverse=reverse)):
            tree.move(iid, "", position)

    def _on_tree_select(self) -> None:
        selected_iids = self.tree.selection()
        count = len(selected_iids)
        if count == 0:
            self.btn_delete_selected.configure(state="disabled")
            self.apply_filter_status_only()
            return

        self.btn_delete_selected.configure(state="normal")
        selected_size = 0
        for iid in selected_iids:
            idx = int(iid)
            if 0 <= idx < len(self.displayed_items):
                selected_size += self.displayed_items[idx].size

        total_size = sum(item.size for item in self.displayed_items)
        self.chrome_status_var.set(
            f"Terpilih: {count} folder ({format_size(selected_size)}) | "
            f"Tampil: {len(self.displayed_items)} ({format_size(total_size)})"
        )

    def apply_filter_status_only(self) -> None:
        total_size = sum(item.size for item in self.displayed_items)
        self.chrome_status_var.set(
            f"Menampilkan {len(self.displayed_items)} folder ({format_size(total_size)}) "
            f"dari total {len(self.all_items)} ditemukan."
        )

    def select_all_rows(self) -> None:
        children = self.tree.get_children()
        self.tree.selection_set(children)
        self._on_tree_select()

    def deselect_all_rows(self) -> None:
        self.tree.selection_set([])
        self._on_tree_select()

    def delete_selected(self) -> None:
        selected_iids = self.tree.selection()
        if not selected_iids:
            return

        targets: list[TargetItem] = []
        for iid in selected_iids:
            idx = int(iid)
            if 0 <= idx < len(self.displayed_items):
                targets.append(self.displayed_items[idx])

        total_size = sum(t.size for t in targets)
        b_key = self._get_current_browser_key()
        b_label = self._browser_label(b_key)

        if is_browser_running(b_key):
            close_it = messagebox.askyesno(
                f"{b_label} Sedang Berjalan",
                f"Aplikasi {b_label} saat ini sedang berjalan!\n\n"
                f"Apakah Anda ingin menutup {b_label} secara otomatis sebelum menghapus?",
            )
            if close_it:
                kill_browser_process(b_key)
                self.check_browser_process()

        confirm = messagebox.askyesno(
            "Konfirmasi Hapus",
            f"Hapus {len(targets)} folder terpilih ({format_size(total_size)})?\n\n"
            f"✓ Target: {b_label}\n"
            "Tindakan ini tidak dapat dibatalkan. Lanjutkan?",
        )
        if confirm:
            self._start_deletion(targets)

    def delete_all_filtered(self) -> None:
        if not self.displayed_items:
            return

        total_size = sum(t.size for t in self.displayed_items)
        b_key = self._get_current_browser_key()
        b_label = self._browser_label(b_key)

        if is_browser_running(b_key):
            close_it = messagebox.askyesno(
                f"{b_label} Sedang Berjalan",
                f"Aplikasi {b_label} saat ini sedang berjalan!\n\n"
                f"Apakah Anda ingin menutup {b_label} secara otomatis sebelum menghapus?",
            )
            if close_it:
                kill_browser_process(b_key)
                self.check_browser_process()

        confirm = messagebox.askyesno(
            "Konfirmasi Hapus Semua",
            f"PERINGATAN: Anda akan menghapus SEMUA {len(self.displayed_items)} folder yang tampil "
            f"({format_size(total_size)})!\n\n"
            f"✓ Browser: {b_label}\n"
            f"✓ Filter aktif: {self.filter_var.get()}\n\n"
            "Apakah Anda benar-benar yakin?",
        )
        if confirm:
            self._start_deletion(list(self.displayed_items))

    def _start_deletion(self, targets: list[TargetItem]) -> None:
        self.is_deleting = True
        self.scan_button.configure(state="disabled")
        self.btn_delete_selected.configure(state="disabled")
        self.btn_delete_all.configure(state="disabled")

        self.chrome_radar.start()
        self.chrome_dot.set_state("working")
        self.chrome_progress.set_bar_color(COLOR_RED)
        self.chrome_progress.set_progress(0, len(targets))

        threading.Thread(target=self._delete_worker, args=(targets,), daemon=True).start()

    def _delete_worker(self, targets: list[TargetItem]) -> None:
        removed = 0
        freed = 0
        failed: list[str] = []
        total = len(targets)

        for index, item in enumerate(targets, start=1):
            path = item.path
            sz = item.size
            try:
                remove_target(path)
                if not path.exists():
                    removed += 1
                    freed += sz
                else:
                    failed.append(str(path))
            except (OSError, PermissionError):
                failed.append(str(path))

            self.after(0, self._delete_progress, index, total, item)

        self.after(0, self._delete_finished, removed, failed, freed)

    def _delete_progress(self, index: int, total: int, item: TargetItem) -> None:
        self.chrome_progress.set_progress(index, total)
        self.chrome_status_var.set(f"Menghapus ({index}/{total}): {item.profile} - {item.category}")

    def _delete_finished(self, removed: int, failed: list[str], freed: int = 0) -> None:
        self.is_deleting = False
        self.chrome_radar.stop()
        self.chrome_dot.set_state("idle")
        self.chrome_progress.stop()
        self.chrome_progress.set_bar_color(COLOR_BLUE)
        self.scan_button.configure(state="normal")

        if freed > 0:
            self.record_cleaned_space(freed)

        if failed:
            messagebox.showwarning(
                "Selesai Sebagian",
                f"{removed} folder berhasil dihapus.\n{len(failed)} folder gagal dihapus "
                "(kemungkinan sedang digunakan oleh Chrome).\n\n"
                "Silakan tutup Chrome sepenuhnya lalu coba lagi.",
            )
        else:
            messagebox.showinfo(
                "Pembersihan Selesai",
                f"Berhasil! {removed} folder telah dihapus dan ruang disk telah dibebaskan.",
            )

        self.start_scan()

    # ------------------------------------------------------------------
    # TAB 2: CAPCUT STUDIO HUB (CACHE, PROJECTS & VERSI LAMA)
    # ------------------------------------------------------------------
    def _build_capcut_tab(self, parent: tk.Frame) -> None:
        # CapCut Sub-Notebook
        capcut_sub_nb = ttk.Notebook(parent, style="Sub.TNotebook")
        capcut_sub_nb.pack(fill="both", expand=True)

        # Sub-tab 1: Cache & Projects
        sub_tab_cp = tk.Frame(capcut_sub_nb, bg=COLOR_BG_SURFACE, padx=8, pady=8)
        capcut_sub_nb.add(sub_tab_cp, text="  🧹 Cache & Projects (User Data)  ")
        self._build_capcut_cache_projects_ui(sub_tab_cp)

        # Sub-tab 2: Old Versions
        sub_tab_ver = tk.Frame(capcut_sub_nb, bg=COLOR_BG_SURFACE, padx=8, pady=8)
        capcut_sub_nb.add(sub_tab_ver, text="  📦 Versi Lama CapCut (Apps)  ")
        self._build_capcut_versions_ui(sub_tab_ver)

    # ------------------------------------------------------------------
    # SUB-TAB 1: CAPCUT CACHE & PROJECTS
    # ------------------------------------------------------------------
    def _build_capcut_cache_projects_ui(self, parent: tk.Frame) -> None:
        # Metrics Row
        cp_metrics = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        cp_metrics.pack(fill="x", pady=(0, 8))

        self.card_capcut_cache = ModernMetricCard(
            cp_metrics, "🧹", "Cache CapCut", "0 B", "User Data\\Cache", COLOR_PURPLE
        )
        self.card_capcut_cache.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_capcut_projects = ModernMetricCard(
            cp_metrics, "🎬", "Draft Projects", "0 B", "com.lveditor.draft", COLOR_AMBER
        )
        self.card_capcut_projects.pack(side="left", fill="x", expand=True)

        # Control Box
        ctrl_box = tk.Frame(parent, bg=COLOR_BG_CARD, padx=10, pady=8, highlightbackground=COLOR_BORDER, highlightthickness=1)
        ctrl_box.pack(fill="x", pady=(0, 8))

        r1 = tk.Frame(ctrl_box, bg=COLOR_BG_CARD)
        r1.pack(fill="x", pady=(0, 6))

        tk.Label(r1, text="Target Cakupan:", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_BG_CARD).pack(side="left", padx=(0, 6))
        self.capcut_scope_combo = ttk.Combobox(
            r1,
            textvariable=self.capcut_scope_var,
            values=[SCOPE_CAPCUT_ALL, SCOPE_CAPCUT_CACHE, SCOPE_CAPCUT_PROJECTS],
            state="readonly",
            width=32,
        )
        self.capcut_scope_combo.pack(side="left", padx=(0, 10))
        self.capcut_scope_combo.bind("<<ComboboxSelected>>", lambda e: self.start_capcut_scan())

        self.btn_capcut_scan = ttk.Button(
            r1, text="🔍 Scan Sekarang", style="CapCut.TButton", command=self.start_capcut_scan
        )
        self.btn_capcut_scan.pack(side="left")

        r2 = tk.Frame(ctrl_box, bg=COLOR_BG_CARD)
        r2.pack(fill="x")

        tk.Label(r2, text="Tipe:", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_BG_CARD).pack(side="left", padx=(0, 4))
        self.capcut_type_combo = ttk.Combobox(
            r2,
            textvariable=self.capcut_filter_type_var,
            values=["Semua Item", "Hanya Folder / Draft", "Hanya File"],
            state="readonly",
            width=18,
        )
        self.capcut_type_combo.pack(side="left", padx=(0, 10))
        self.capcut_type_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_capcut_filter())

        tk.Label(r2, text="Cari Nama:", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_BG_CARD).pack(side="left", padx=(0, 4))
        tk.Entry(
            r2,
            textvariable=self.capcut_search_var,
            font=("Segoe UI", 9),
            bg=COLOR_BG_INPUT,
            fg=COLOR_TEXT_WHITE,
            insertbackground=COLOR_TEXT_WHITE,
            relief="flat",
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            width=16,
        ).pack(side="left", padx=(0, 10), ipady=2)
        self.capcut_search_var.trace_add("write", lambda *args: self.apply_capcut_filter())

        ttk.Button(r2, text="☑️ Pilih Semua", style="Secondary.TButton", command=self.select_all_capcut).pack(side="right", padx=(4, 0))
        ttk.Button(r2, text="☐ Batal Pilih", style="Secondary.TButton", command=self.deselect_all_capcut).pack(side="right")

        # Bottom Bar (Pinned to bottom FIRST so it is NEVER cut off)
        bottom = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        bottom.pack(side="bottom", fill="x", pady=(6, 2))

        left_stat = tk.Frame(bottom, bg=COLOR_BG_SURFACE)
        left_stat.pack(side="left", fill="x", expand=True)

        self.capcut_radar = ModernRadarSpinner(left_stat, size=28, bg=COLOR_BG_SURFACE)
        self.capcut_radar.pack(side="left", padx=(0, 6))

        self.capcut_dot = PulsingStatusDot(left_stat, size=16, bg=COLOR_BG_SURFACE)
        self.capcut_dot.pack(side="left", padx=(0, 6))

        tk.Label(
            left_stat,
            textvariable=self.capcut_status_var,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_BG_SURFACE,
        ).pack(side="left")

        self.btn_capcut_delete_selected = ttk.Button(
            bottom,
            text="🗑️ Hapus Terpilih",
            style="Secondary.TButton",
            command=self.delete_selected_capcut,
            state="disabled",
        )
        self.btn_capcut_delete_selected.pack(side="right", padx=(6, 0))

        self.btn_capcut_delete_all = ttk.Button(
            bottom,
            text="🗑️ Hapus Semua Sesuai Target",
            command=self.delete_all_capcut,
            state="disabled",
            style="Danger.TButton",
        )
        self.btn_capcut_delete_all.pack(side="right")

        # Progress bar (above bottom bar)
        self.capcut_progress = ShimmerProgressBar(parent, height=8, bg=COLOR_BG_SURFACE, bar_color=COLOR_PURPLE)
        self.capcut_progress.pack(side="bottom", fill="x", pady=(0, 6))

        # Table Treeview (Fills remaining space)
        tbl_frame = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        tbl_frame.pack(fill="both", expand=True, pady=(0, 6))

        columns = ("no", "category", "name", "type", "size", "files", "path")
        self.capcut_tree = ttk.Treeview(tbl_frame, columns=columns, show="headings", selectmode="extended")
        self.capcut_tree.heading("no", text="#", command=lambda: self.sort_capcut("no"))
        self.capcut_tree.heading("category", text="Kategori", command=lambda: self.sort_capcut("category"))
        self.capcut_tree.heading("name", text="Nama Folder / File", command=lambda: self.sort_capcut("name"))
        self.capcut_tree.heading("type", text="Tipe", command=lambda: self.sort_capcut("type"))
        self.capcut_tree.heading("size", text="Ukuran", command=lambda: self.sort_capcut("size"))
        self.capcut_tree.heading("files", text="Jumlah File", command=lambda: self.sort_capcut("files"))
        self.capcut_tree.heading("path", text="Path Direktori", command=lambda: self.sort_capcut("path"))

        self.capcut_tree.column("no", width=38, minwidth=35, anchor="center")
        self.capcut_tree.column("category", width=80, minwidth=65, anchor="center")
        self.capcut_tree.column("name", width=220, minwidth=140, anchor="w")
        self.capcut_tree.column("type", width=95, minwidth=70, anchor="center")
        self.capcut_tree.column("size", width=100, minwidth=70, anchor="e")
        self.capcut_tree.column("files", width=90, minwidth=60, anchor="e")
        self.capcut_tree.column("path", width=340, minwidth=180, anchor="w")

        v_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.capcut_tree.yview)
        h_scroll = ttk.Scrollbar(tbl_frame, orient="horizontal", command=self.capcut_tree.xview)
        self.capcut_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.capcut_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        tbl_frame.rowconfigure(0, weight=1)
        tbl_frame.columnconfigure(0, weight=1)

        self.capcut_tree.bind("<<TreeviewSelect>>", lambda e: self._on_capcut_tree_select())

    # ------------------------------------------------------------------
    # SUB-TAB 2: CAPCUT OLD VERSIONS (APPS)
    # ------------------------------------------------------------------
    def _build_capcut_versions_ui(self, parent: tk.Frame) -> None:
        # Metrics Row
        v_metrics = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        v_metrics.pack(fill="x", pady=(0, 8))

        self.card_ver_latest = ModernMetricCard(
            v_metrics, "🔒", "Versi Aktif Terlindungi", "Memeriksa...", "Terkunci & Tidak dapat dihapus", COLOR_GREEN
        )
        self.card_ver_latest.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_ver_savable = ModernMetricCard(
            v_metrics, "⚡", "Ruang Dapat Dihemat", "0 B", "Folder Versi Lama di Apps", COLOR_RED
        )
        self.card_ver_savable.pack(side="left", fill="x", expand=True)

        # Toolbar Frame
        toolbar = tk.Frame(parent, bg=COLOR_BG_CARD, padx=10, pady=8, highlightbackground=COLOR_BORDER, highlightthickness=1)
        toolbar.pack(fill="x", pady=(0, 8))

        ttk.Button(
            toolbar,
            text="☑️ Centang Semua Versi Lama",
            style="Secondary.TButton",
            command=self.select_all_old_versions,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            toolbar,
            text="☐ Hapus Centang",
            style="Secondary.TButton",
            command=self.deselect_all_old_versions,
        ).pack(side="left", padx=(0, 10))

        tk.Label(
            toolbar,
            text="💡 Versi terbaru terkunci & terlindungi otomatis.",
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_CARD,
            font=("Segoe UI", 8),
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            toolbar,
            text="🔄 Scan Ulang Versi",
            style="Secondary.TButton",
            command=self.start_capcut_version_scan,
        ).pack(side="right")

        # Bottom Bar (Pinned to bottom FIRST so it is NEVER cut off)
        ver_bottom = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        ver_bottom.pack(side="bottom", fill="x", pady=(6, 2))

        v_left = tk.Frame(ver_bottom, bg=COLOR_BG_SURFACE)
        v_left.pack(side="left", fill="x", expand=True)

        self.ver_radar = ModernRadarSpinner(v_left, size=28, bg=COLOR_BG_SURFACE)
        self.ver_radar.pack(side="left", padx=(0, 6))

        self.ver_dot = PulsingStatusDot(v_left, size=16, bg=COLOR_BG_SURFACE)
        self.ver_dot.pack(side="left", padx=(0, 6))

        tk.Label(
            v_left,
            textvariable=self.capcut_version_status_var,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_BG_SURFACE,
        ).pack(side="left")

        self.btn_delete_checked_versions = ttk.Button(
            ver_bottom,
            text="🗑️ Hapus Versi Lama Tercentang",
            style="Secondary.TButton",
            command=self.delete_checked_versions,
            state="disabled",
        )
        self.btn_delete_checked_versions.pack(side="right", padx=(6, 0))

        self.btn_clean_all_versions = ttk.Button(
            ver_bottom,
            text="⚡ Bersihkan Semua Versi Lama (1-Klik)",
            command=self.clean_all_old_versions_one_click,
            style="Danger.TButton",
        )
        self.btn_clean_all_versions.pack(side="right")

        # Progress bar (above bottom bar)
        self.capcut_version_progress = ShimmerProgressBar(parent, height=8, bg=COLOR_BG_SURFACE, bar_color=COLOR_RED)
        self.capcut_version_progress.pack(side="bottom", fill="x", pady=(0, 6))

        # Table Treeview (Fills remaining space)
        tbl_frame = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        tbl_frame.pack(fill="both", expand=True, pady=(0, 6))

        ver_cols = ("check", "version", "status", "size", "files", "modified", "path")
        self.version_tree = ttk.Treeview(
            tbl_frame, columns=ver_cols, show="headings", selectmode="browse"
        )
        for col, label in (("check", "[ ✓ ]"), ("version", "Nomor Versi"), ("status", "Status Proteksi"), ("size", "Ukuran Disk"), ("files", "Jumlah File"), ("modified", "Tanggal Modifikasi"), ("path", "Lokasi Folder")):
            self.version_tree.heading(col, text=label, command=lambda c=col: self.sort_tree_rows(self.version_tree, c))

        self.version_tree.column("check", width=45, minwidth=40, anchor="center")
        self.version_tree.column("version", width=120, minwidth=90, anchor="w")
        self.version_tree.column("status", width=220, minwidth=150, anchor="center")
        self.version_tree.column("size", width=100, minwidth=80, anchor="e")
        self.version_tree.column("files", width=90, minwidth=70, anchor="e")
        self.version_tree.column("modified", width=130, minwidth=110, anchor="center")
        self.version_tree.column("path", width=340, minwidth=180, anchor="w")

        v_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.version_tree.yview)
        h_scroll = ttk.Scrollbar(tbl_frame, orient="horizontal", command=self.version_tree.xview)
        self.version_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.version_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        tbl_frame.rowconfigure(0, weight=1)
        tbl_frame.columnconfigure(0, weight=1)

        self.version_tree.bind("<Button-1>", self._on_version_tree_click)
        self.version_tree.bind("<space>", self._on_version_tree_space)

    # ------------------------------------------------------------------
    # TAB 3: WINDOWS PANTHER CLEANER
    # ------------------------------------------------------------------
    def _build_panther_tab(self, parent: tk.Frame) -> None:
        # Header Info Card
        p_card = tk.Frame(parent, bg=COLOR_BG_CARD, padx=14, pady=12, highlightbackground=COLOR_BORDER, highlightthickness=1)
        p_card.pack(fill="x", pady=(0, 10))

        top_p = tk.Frame(p_card, bg=COLOR_BG_CARD)
        top_p.pack(fill="x")

        tk.Label(
            top_p,
            text="🪟 Windows Panther Monitor Logs",
            font=("Segoe UI", 12, "bold"),
            fg=COLOR_GREEN_HOVER,
            bg=COLOR_BG_CARD,
        ).pack(side="left")

        self.lbl_panther_admin = tk.Label(
            top_p,
            text="Status Izin: Memeriksa...",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_CARD,
        )
        self.lbl_panther_admin.pack(side="right")

        desc_text = (
            "Folder C:\\Windows\\Panther\\monitor secara berkala mengakumulasi file log diagnostic sistem "
            "dan telemetry yang dapat menyita ruang hard disk. CleanC dapat menghentikan service monitor secara "
            "aman, membersihkan seluruh log usang, dan menyalakan kembali driver sistem."
        )
        tk.Label(
            p_card,
            text=desc_text,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_CARD,
            wraplength=800,
            justify="left",
        ).pack(anchor="w", pady=(4, 8))

        # Metrics Box
        m_row = tk.Frame(p_card, bg=COLOR_BG_CARD)
        m_row.pack(fill="x")

        self.lbl_monitor_size = tk.Label(
            m_row,
            text="Ukuran C:\\Windows\\Panther\\monitor: Menghitung...",
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_GREEN_HOVER,
            bg=COLOR_BG_CARD,
        )
        self.lbl_monitor_size.pack(side="left", padx=(0, 16))

        self.lbl_panther_total = tk.Label(
            m_row,
            text="Total file: 0 file",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_CARD,
        )
        self.lbl_panther_total.pack(side="left")

        # Action Button & Checkbox
        act_row = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        act_row.pack(fill="x", pady=(0, 8))

        tk.Checkbutton(
            act_row,
            text="Bersihkan juga file .log tambahan di root folder Panther",
            variable=self.panther_include_all,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_BG_SURFACE,
            selectcolor=COLOR_BG_CARD,
            activebackground=COLOR_BG_SURFACE,
            activeforeground=COLOR_TEXT_WHITE,
            relief="flat",
            bd=0,
            highlightthickness=0,
            takefocus=0,
        ).pack(side="left")

        self.btn_panther_clean = ttk.Button(
            act_row,
            text="⚡ Bersihkan Log Panther Sekarang",
            style="Success.TButton",
            command=self.start_panther_clean,
        )
        self.btn_panther_clean.pack(side="right")

        ttk.Button(
            act_row,
            text="🔄 Refresh",
            style="Secondary.TButton",
            command=self.refresh_panther_info,
        ).pack(side="right", padx=(0, 8))

        # Status Bar (Pinned to bottom FIRST so it is NEVER cut off)
        p_bottom = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        p_bottom.pack(side="bottom", fill="x", pady=(6, 2))

        self.panther_radar = ModernRadarSpinner(p_bottom, size=24, bg=COLOR_BG_SURFACE)
        self.panther_radar.pack(side="left", padx=(0, 6))

        self.panther_dot = PulsingStatusDot(p_bottom, size=16, bg=COLOR_BG_SURFACE)
        self.panther_dot.pack(side="left", padx=(0, 6))

        tk.Label(
            p_bottom,
            textvariable=self.panther_status_var,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_BG_SURFACE,
        ).pack(side="left")

        # Treeview Table for Panther Files (Fills remaining space)
        tbl_frame = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        tbl_frame.pack(fill="both", expand=True, pady=(0, 6))

        cols = ("tag", "filename", "size")
        self.panther_tree = ttk.Treeview(tbl_frame, columns=cols, show="headings", selectmode="browse")
        for col, label in (("tag", "Tipe"), ("filename", "Nama File Log"), ("size", "Ukuran")):
            self.panther_tree.heading(col, text=label, command=lambda c=col: self.sort_tree_rows(self.panther_tree, c))

        self.panther_tree.column("tag", width=120, anchor="center")
        self.panther_tree.column("filename", width=550, anchor="w")
        self.panther_tree.column("size", width=110, anchor="e")

        v_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.panther_tree.yview)
        self.panther_tree.configure(yscrollcommand=v_scroll.set)

        self.panther_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        tbl_frame.rowconfigure(0, weight=1)
        tbl_frame.columnconfigure(0, weight=1)

    def refresh_panther_info(self) -> None:
        admin = is_admin()
        if admin:
            self.lbl_panther_admin.configure(
                text="Status Izin: Administrator (Aman)",
                fg=COLOR_GREEN_HOVER,
            )
        else:
            self.lbl_panther_admin.configure(
                text="Status Izin: Pengguna Biasa (Memerlukan UAC)",
                fg=COLOR_AMBER,
            )

        info = get_panther_info()
        self._panther_total_bytes = info.get("total_size", 0)
        mon_str = format_size(info["monitor_size"])
        tot_str = format_size(info["total_size"])
        self.lbl_monitor_size.configure(
            text=f"Ukuran C:\\Windows\\Panther\\monitor: {mon_str}"
        )
        self.lbl_panther_total.configure(
            text=f"Total file terdeteksi: {len(info['files'])} file (Total: {tot_str})"
        )

        self.panther_tree.delete(*self.panther_tree.get_children())
        for fn, sz, is_mon in info["files"]:
            tag = "★ Monitor Log" if is_mon else "Setup/Diag Log"
            self.panther_tree.insert("", "end", values=(tag, fn, format_size(sz)))

    def start_panther_clean(self) -> None:
        if self.is_panther_cleaning:
            return

        self._panther_prev_size = getattr(self, "_panther_total_bytes", 0)
        include_all = self.panther_include_all.get()
        confirm = messagebox.askyesno(
            "Konfirmasi Pembersihan Panther",
            "Apakah Anda yakin ingin membersihkan log di C:\\Windows\\Panther\\monitor?\n\n"
            "Sistem akan menghentikan driver monitor, menghapus file log lama, dan mengaktifkannya kembali.\n"
            "Jika muncul dialog izin Windows (UAC), silakan pilih 'Yes'.",
        )
        if not confirm:
            return

        self.is_panther_cleaning = True
        self.btn_panther_clean.configure(state="disabled")
        self.panther_radar.start()
        self.panther_dot.set_state("working")
        self.panther_status_var.set("Sedang membersihkan log Panther... Mohon tunggu.")

        threading.Thread(
            target=self._panther_clean_worker, args=(include_all,), daemon=True
        ).start()

    def _panther_clean_worker(self, include_all: bool) -> None:
        ok, msg = clean_panther_logs(include_all_panther=include_all)
        self.after(0, self._panther_clean_done, ok, msg)

    def _panther_clean_done(self, ok: bool, msg: str) -> None:
        self.is_panther_cleaning = False
        self.panther_radar.stop()
        self.panther_dot.set_state("idle")
        self.btn_panther_clean.configure(state="normal")
        self.refresh_panther_info()

        if ok:
            freed = getattr(self, "_panther_prev_size", 0)
            if freed > 0:
                self.record_cleaned_space(freed)
            self.panther_status_var.set("Pembersihan selesai! Folder log Panther kini bersih.")
            messagebox.showinfo("Berhasil", f"{msg}\n\nFolder log Panther telah dibersihkan.")
        else:
            self.panther_status_var.set(f"Gagal: {msg}")
            messagebox.showerror("Gagal", f"Tidak dapat membersihkan log Panther:\n{msg}")

    # ------------------------------------------------------------------
    # CAPCUT PROCESS HELPERS
    # ------------------------------------------------------------------
    def check_capcut_process(self) -> None:
        running = is_capcut_running()
        if running:
            self.capcut_running_text_var.set("⚠️ CapCut sedang berjalan (Disarankan ditutup sebelum menghapus)")
            self.btn_header_capcut.configure(
                text="🛑 CapCut Aktif (Klik Tutup)",
                bg="#7f1d1d",
                fg="#fca5a5",
            )
        else:
            self.capcut_running_text_var.set("✅ CapCut tidak berjalan (Aman untuk dibersihkan)")
            self.btn_header_capcut.configure(
                text="✅ CapCut Siap",
                bg="#064e3b",
                fg="#6ee7b7",
            )

    # ------------------------------------------------------------------
    # ABOUT & DONATE QRIS POPUPS
    # ------------------------------------------------------------------
    def toggle_language(self) -> None:
        """Switch the UI language; Indonesian is the default."""
        self.language = "en" if self.language == "id" else "id"
        self.btn_language.configure(text="ID" if self.language == "en" else "EN")
        self.btn_about.configure(text="ℹ️ About" if self.language == "en" else "ℹ️ Tentang")
        self.btn_donate.configure(text="💖 Donate QRIS" if self.language == "en" else "💖 Donasi QRIS")
        self._refresh_language_labels()

    def _translate_text(self, value: str) -> str:
        pairs = UI_EN_REPLACEMENTS if self.language == "en" else [(en, id_text) for id_text, en in UI_EN_REPLACEMENTS]
        result = value
        for source, target in pairs:
            result = result.replace(source, target)
        return result

    def _install_language_traces(self) -> None:
        self._language_trace_guard = False
        variable_names = (
            "drive_c_free_var", "drive_c_detail_var", "total_cleaned_var", "session_cleaned_var",
            "browser_running_text_var", "chrome_status_var", "filter_var", "capcut_scope_var",
            "capcut_filter_type_var", "capcut_status_var", "capcut_running_text_var",
            "panther_status_var", "dev_cache_status_var", "capcut_version_status_var",
            "capcut_latest_ver_var", "capcut_savable_var",
        )
        for name in variable_names:
            var = getattr(self, name, None)
            if var is not None:
                var.trace_add("write", lambda *_args, v=var: self._translate_var_write(v))

    def _translate_var_write(self, var) -> None:
        if self.language != "en" or getattr(self, "_language_trace_guard", False):
            return
        value = var.get()
        translated = self._translate_text(value)
        if translated != value:
            self._language_trace_guard = True
            var.set(translated)
            self._language_trace_guard = False

    def _refresh_language_labels(self) -> None:
        """Refresh the visible shell and browser controls after a language switch."""
        english = self.language == "en"
        if hasattr(self, "notebook"):
            self.notebook.tab(0, text="  🌐 Web Browsers  ")
            self.notebook.tab(1, text="  🎬 CapCut Studio  " if english else "  🎬 CapCut Studio  ")
            self.notebook.tab(2, text="  🪟 Windows Panther  " if english else "  🪟 Windows Panther  ")
            self.notebook.tab(3, text="  🛠 Dev & Package Cache  " if english else "  🛠 Cache Dev & Package  ")
        if hasattr(self, "chrome_status_var") and not self.is_scanning and not self.is_deleting:
            self.chrome_status_var.set(
                "Select a target and click Scan to find cleanable folders."
                if english else "Pilih target dan klik Scan untuk mencari folder yang dapat dibersihkan."
            )
        if hasattr(self, "filter_combobox"):
            self.filter_combobox.configure(values=(
                ["All (Service Worker & Cache)", "Service Worker only", "Cache only"]
                if english else [FILTER_ALL, FILTER_SW, FILTER_CACHE]
            ))
        if hasattr(self, "scan_button"):
            self.scan_button.configure(text="🔍 Scan Now" if english else "🔍 Scan Sekarang")
        if hasattr(self, "btn_close_browser"):
            self.btn_close_browser.configure(text="🛑 Close Browser" if english else "🛑 Tutup Browser")
        if hasattr(self, "btn_delete_selected"):
            self.btn_delete_selected.configure(text="🗑️ Delete Selected" if english else "🗑️ Hapus Terpilih")
        if hasattr(self, "btn_delete_all"):
            self.btn_delete_all.configure(text="🗑️ Delete All Filtered" if english else "🗑️ Hapus Semua Sesuai Filter")
        self._translate_visible_ui(english)

    def _translate_visible_ui(self, english: bool) -> None:
        """Translate all currently rendered widget labels and table headings."""
        pairs = UI_EN_REPLACEMENTS if english else [(en, id_text) for id_text, en in UI_EN_REPLACEMENTS]

        def translate(value: str) -> str:
            if english:
                return self._translate_text(value)
            result = value
            for source, target in pairs:
                result = result.replace(source, target)
            return result

        def visit(widget) -> None:
            try:
                if isinstance(widget, ttk.Notebook):
                    for tab_id in widget.tabs():
                        label = widget.tab(tab_id, "text")
                        widget.tab(tab_id, text=translate(label))
                elif isinstance(widget, ttk.Treeview):
                    for column in widget["columns"]:
                        heading = widget.heading(column, "text")
                        widget.heading(column, text=translate(heading))
                elif isinstance(widget, ttk.Combobox):
                    values = list(widget.cget("values"))
                    widget.configure(values=tuple(translate(str(value)) for value in values))
                if "text" in widget.keys():
                    current = widget.cget("text")
                    if current:
                        widget.configure(text=translate(current))
            except (tk.TclError, TypeError):
                pass
            for child in widget.winfo_children():
                visit(child)

        visit(self)
        for var_name in (
            "drive_c_free_var", "drive_c_detail_var", "total_cleaned_var",
            "session_cleaned_var", "browser_running_text_var", "chrome_status_var",
            "capcut_status_var", "capcut_running_text_var", "panther_status_var",
            "dev_cache_status_var", "filter_var", "capcut_scope_var", "capcut_filter_type_var",
        ):
            var = getattr(self, var_name, None)
            if var is not None:
                var.set(translate(var.get()))

    def show_about_popup(self) -> None:
        top = tk.Toplevel(self)
        english = self.language == "en"
        top.title("About CleanC" if english else "Tentang CleanC")
        top.configure(bg=COLOR_BG_ROOT)
        top.resizable(False, False)
        top.transient(self)

        base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        icon_path = base_dir / "CleanC.ico"
        if icon_path.exists():
            try:
                top.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Top decorative cyan accent strip
        tk.Frame(top, bg=COLOR_CYAN, height=4).pack(fill="x")

        card = tk.Frame(top, bg=COLOR_BG_CARD, padx=28, pady=22, highlightbackground="#385173", highlightthickness=1)
        card.pack(fill="both", expand=True, padx=16, pady=14)

        # Header Title
        tk.Label(
            card,
            text="⚡ CleanC",
            font=("Segoe UI", 20, "bold"),
            fg=COLOR_CYAN_LIGHT,
            bg=COLOR_BG_CARD,
        ).pack(anchor="center", pady=(0, 2))

        tk.Label(
            card,
            text="Advanced System, Browser & App Storage Optimizer" if english else "Pembersih Sistem, Browser & Penyimpanan Aplikasi",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_CARD,
        ).pack(anchor="center", pady=(0, 8))

        # Version Pill
        ver_frame = tk.Frame(card, bg="#1e3a8a", padx=10, pady=3)
        ver_frame.pack(anchor="center", pady=(0, 10))
        tk.Label(
            ver_frame,
            text="Version 2.5 PRO • 64-bit Edition" if english else "Versi 2.5 PRO • Edisi 64-bit",
            font=("Segoe UI", 8, "bold"),
            fg="#ffffff",
            bg="#1e3a8a",
        ).pack()

        # Description Box
        desc_frame = tk.Frame(card, bg="#0b0f19", padx=14, pady=10, highlightbackground=COLOR_BORDER, highlightthickness=1)
        desc_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            desc_frame,
            text=("CleanC is designed to recover disk space by safely cleaning hidden junk, Chromium browser caches, developer build artifacts, and CapCut cache and legacy versions."
                  if english else "CleanC dirancang untuk membebaskan ruang disk dengan membersihkan file sampah tersembunyi, cache browser Chromium, artefak developer, serta cache dan versi lama CapCut secara aman."),
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg="#0b0f19",
            justify="center",
            wraplength=420,
        ).pack()

        # Developer Info
        dev_frame = tk.Frame(card, bg=COLOR_BG_CARD)
        dev_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            dev_frame,
            text="Developed by: Ziqva" if english else "Dikembangkan oleh: Ziqva",
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_BG_CARD,
        ).pack(anchor="center")

        # More Tools Website Button
        btn_web = tk.Button(
            card,
            text="🌐 More tools at appcenter.ziqva.com" if english else "🌐 Tools lainnya di appcenter.ziqva.com",
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            relief="flat",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            cursor="hand2",
            padx=14,
            pady=8,
            command=lambda: webbrowser.open_new_tab("https://appcenter.ziqva.com"),
        )
        btn_web.pack(fill="x", pady=(0, 8))

        # Donate QRIS Button
        btn_don = tk.Button(
            card,
            text="💖 Support the developer (QRIS)" if english else "💖 Dukung Pengembang (Donasi QRIS)",
            font=("Segoe UI", 9, "bold"),
            bg="#e11d48",
            fg="#ffffff",
            relief="flat",
            activebackground="#be123c",
            activeforeground="#ffffff",
            cursor="hand2",
            padx=14,
            pady=7,
            command=lambda: [top.destroy(), self.show_donate_popup()],
        )
        btn_don.pack(fill="x", pady=(0, 10))

        # Close Button
        tk.Button(
            card,
            text="Close" if english else "Tutup",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg=COLOR_TEXT_MUTED,
            relief="flat",
            activebackground="#334155",
            activeforeground="#ffffff",
            cursor="hand2",
            padx=16,
            pady=4,
            command=top.destroy,
        ).pack(anchor="center")

        # Dynamic Auto-Centering & Precise Height (prevents any clipping on high-DPI screens)
        top.bind("<Escape>", lambda e: top.destroy())
        top.update_idletasks()
        req_w = max(520, top.winfo_reqwidth())
        req_h = top.winfo_reqheight() + 16
        try:
            x = self.winfo_x() + (self.winfo_width() - req_w) // 2
            y = self.winfo_y() + (self.winfo_height() - req_h) // 2
            top.geometry(f"{req_w}x{req_h}+{max(0, x)}+{max(0, y)}")
        except Exception:
            top.geometry("520x620")

        top.grab_set()

    def show_donate_popup(self) -> None:
        top = tk.Toplevel(self)
        english = self.language == "en"
        top.title("QRIS Donation - ZIQVA" if english else "Donasi QRIS - ZIQVA")
        top.configure(bg=COLOR_BG_ROOT)
        top.resizable(False, False)
        top.transient(self)

        base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        icon_path = base_dir / "CleanC.ico"
        if icon_path.exists():
            try:
                top.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Top decorative pink/rose strip
        tk.Frame(top, bg="#f43f5e", height=5).pack(fill="x")

        header = tk.Frame(top, bg=COLOR_BG_ROOT, pady=12)
        header.pack(fill="x")

        tk.Label(
            header,
            text="💖 Support the CleanC developer" if english else "💖 Dukung Pengembang CleanC",
            font=("Segoe UI", 14, "bold"),
            fg="#f43f5e",
            bg=COLOR_BG_ROOT,
        ).pack(anchor="center")

        tk.Label(
            header,
            text=("Scan QRIS with BCA, Mandiri, BRI, GoPay, OVO, DANA, or ShopeePay"
                  if english else "Scan QRIS melalui BCA, Mandiri, BRI, GoPay, OVO, DANA, atau ShopeePay"),
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_ROOT,
        ).pack(anchor="center", pady=(3, 0))

        # White Card Container for QR Code (optimal scanning contrast)
        qr_card = tk.Frame(top, bg="#ffffff", padx=18, pady=16, relief="flat", highlightbackground="#f43f5e", highlightthickness=2)
        qr_card.pack(padx=24, pady=(4, 18))

        # Load QRIS Image
        qris_file = base_dir / "qris_donate.png"
        if not qris_file.exists():
            qris_file = Path(__file__).resolve().parent / "qris_donate.png"

        if qris_file.exists():
            try:
                pil_img = Image.open(qris_file)
                # target width around 300px
                target_w = 300
                target_h = int(pil_img.height * (target_w / pil_img.width))
                resized = pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                top._qris_photo = ImageTk.PhotoImage(resized)
                lbl_img = tk.Label(qr_card, image=top._qris_photo, bg="#ffffff")
                lbl_img.pack()
            except Exception as e:
                tk.Label(
                    qr_card,
                    text=f"Gagal memuat gambar QRIS:\n{e}",
                    font=("Segoe UI", 9),
                    fg="#dc2626",
                    bg="#ffffff",
                    pady=40,
                ).pack()
        else:
            tk.Label(
                qr_card,
                text="File qris_donate.png tidak ditemukan.",
                font=("Segoe UI", 9),
                fg="#dc2626",
                bg="#ffffff",
                pady=40,
            ).pack()

        # Dynamic Auto-Centering & Compact Height without redundant footer
        top.bind("<Escape>", lambda e: top.destroy())
        top.update_idletasks()
        req_w = max(420, top.winfo_reqwidth())
        req_h = top.winfo_reqheight() + 10
        try:
            x = self.winfo_x() + (self.winfo_width() - req_w) // 2
            y = self.winfo_y() + (self.winfo_height() - req_h) // 2
            top.geometry(f"{req_w}x{req_h}+{max(0, x)}+{max(0, y)}")
        except Exception:
            top.geometry("420x520")

        top.grab_set()

    def close_capcut_process(self) -> None:
        if not is_capcut_running():
            messagebox.showinfo("Info", "CapCut tidak sedang berjalan.")
            self.check_capcut_process()
            return

        confirm = messagebox.askyesno(
            "Tutup CapCut",
            "Apakah Anda yakin ingin menutup proses CapCut sekarang?\n\n"
            "Pastikan Anda telah menyimpan perubahan yang sedang dikerjakan di CapCut.",
        )
        if not confirm:
            return

        ok, msg = kill_capcut_process()
        if ok:
            messagebox.showinfo("Berhasil", "CapCut berhasil ditutup.")
        else:
            messagebox.showwarning("Perhatian", msg)
        self.check_capcut_process()

    # ------------------------------------------------------------------
    # CAPCUT CACHE & PROJECTS METHODS
    # ------------------------------------------------------------------
    def start_capcut_scan(self) -> None:
        if self.is_capcut_scanning or self.is_capcut_deleting:
            return

        scope = self.capcut_scope_var.get()
        cache_dir = Path(self.capcut_path_var.get())
        projects_dir = Path(self.capcut_projects_path_var.get())

        self.is_capcut_scanning = True
        self.btn_capcut_scan.configure(state="disabled")
        self.btn_capcut_delete_selected.configure(state="disabled")
        self.btn_capcut_delete_all.configure(state="disabled")

        self.capcut_radar.start()
        self.capcut_dot.set_state("scanning")
        self.capcut_progress.start_indeterminate()
        self.capcut_status_var.set("Sedang memindai Cache & Projects CapCut... Mohon tunggu.")

        self.capcut_tree.delete(*self.capcut_tree.get_children())
        self.capcut_all_items.clear()
        self.capcut_displayed_items.clear()

        threading.Thread(
            target=self._capcut_scan_worker,
            args=(scope, cache_dir, projects_dir),
            daemon=True,
        ).start()

    def _capcut_scan_worker(self, scope: str, cache_dir: Path, projects_dir: Path) -> None:
        try:
            combined_items: list[CapCutItem] = []
            if scope in (SCOPE_CAPCUT_ALL, SCOPE_CAPCUT_CACHE):
                c_info = get_capcut_cache_info(cache_dir)
                for it in c_info.get("items", []):
                    combined_items.append(CapCutItem(it))

            if scope in (SCOPE_CAPCUT_ALL, SCOPE_CAPCUT_PROJECTS):
                p_info = get_capcut_projects_info(projects_dir)
                for it in p_info.get("items", []):
                    combined_items.append(CapCutItem(it))

            self.after(0, self._capcut_scan_done, combined_items, None)
        except Exception as exc:
            self.after(0, self._capcut_scan_done, [], str(exc))

    def _capcut_scan_done(self, items: list[CapCutItem], error: str | None) -> None:
        self.capcut_radar.stop()
        self.capcut_dot.set_state("idle")
        self.capcut_progress.stop()
        self.is_capcut_scanning = False
        self.btn_capcut_scan.configure(state="normal")
        self.check_capcut_process()

        if error:
            messagebox.showerror("Gagal Memindai CapCut", f"Terjadi kesalahan saat scan CapCut:\n{error}")
            self.capcut_status_var.set("Pemindaian CapCut gagal.")
            return

        self.capcut_all_items = items
        self.apply_capcut_filter()

    def apply_capcut_filter(self) -> None:
        type_filter = self.capcut_filter_type_var.get()
        query = self.capcut_search_var.get().strip().lower()

        filtered: list[CapCutItem] = []
        cache_bytes = 0
        projects_bytes = 0

        for item in self.capcut_all_items:
            if item.category == "Cache":
                cache_bytes += item.size
            else:
                projects_bytes += item.size

            if type_filter == "Hanya Folder / Draft" and not item.is_dir:
                continue
            if type_filter == "Hanya File" and item.is_dir:
                continue
            if query and query not in item.name.lower() and query not in str(item.path).lower():
                continue
            filtered.append(item)

        if self.capcut_sort_column != "no":
            key = self.capcut_sort_column
            filtered.sort(key=lambda item: {
                "category": item.category.casefold(),
                "name": item.name.casefold(),
                "type": item.item_type.casefold(),
                "size": item.size,
                "files": item.files,
                "path": str(item.path).casefold(),
            }[key], reverse=self.capcut_sort_reverse)

        self.capcut_displayed_items = filtered
        self.capcut_tree.delete(*self.capcut_tree.get_children())
        total_size = 0
        for idx, it in enumerate(self.capcut_displayed_items, start=1):
            total_size += it.size
            self.capcut_tree.insert(
                "",
                "end",
                iid=str(idx - 1),
                values=(
                    idx,
                    it.category,
                    it.name,
                    it.item_type,
                    it.size_str,
                    f"{it.files:,} file" if it.is_dir else "1 file",
                    str(it.path),
                ),
            )

        # Update metric cards
        self.card_capcut_cache.update_data(format_size(cache_bytes), "File sementara CapCut")
        self.card_capcut_projects.update_data(format_size(projects_bytes), "Draft video editing")

    def sort_capcut(self, column: str) -> None:
        if self.capcut_sort_column == column:
            self.capcut_sort_reverse = not self.capcut_sort_reverse
        else:
            self.capcut_sort_column = column
            self.capcut_sort_reverse = False
        self.apply_capcut_filter()

        has_items = len(self.capcut_displayed_items) > 0
        self.btn_capcut_delete_all.configure(state="normal" if has_items else "disabled")
        self.btn_capcut_delete_selected.configure(state="disabled")

        if not self.capcut_all_items:
            self.capcut_status_var.set("Folder CapCut bersih (tidak ditemukan item).")
        else:
            self.capcut_status_var.set(
                f"Menampilkan {len(self.capcut_displayed_items)} item ({format_size(total_size)}) "
                f"dari total {len(self.capcut_all_items)} ditemukan."
            )

    def _on_capcut_tree_select(self) -> None:
        selected_iids = self.capcut_tree.selection()
        count = len(selected_iids)
        if count == 0:
            self.btn_capcut_delete_selected.configure(state="disabled")
            self._update_capcut_status_only()
            return

        self.btn_capcut_delete_selected.configure(state="normal")
        selected_size = 0
        for iid in selected_iids:
            idx = int(iid)
            if 0 <= idx < len(self.capcut_displayed_items):
                selected_size += self.capcut_displayed_items[idx].size

        total_size = sum(item.size for item in self.capcut_displayed_items)
        self.capcut_status_var.set(
            f"Terpilih: {count} item ({format_size(selected_size)}) | "
            f"Tampil: {len(self.capcut_displayed_items)} ({format_size(total_size)})"
        )

    def _update_capcut_status_only(self) -> None:
        total_size = sum(item.size for item in self.capcut_displayed_items)
        self.capcut_status_var.set(
            f"Menampilkan {len(self.capcut_displayed_items)} item ({format_size(total_size)}) "
            f"dari total {len(self.capcut_all_items)} ditemukan."
        )

    def select_all_capcut(self) -> None:
        children = self.capcut_tree.get_children()
        self.capcut_tree.selection_set(children)
        self._on_capcut_tree_select()

    def deselect_all_capcut(self) -> None:
        self.capcut_tree.selection_set([])
        self._on_capcut_tree_select()

    def delete_selected_capcut(self) -> None:
        selected_iids = self.capcut_tree.selection()
        if not selected_iids:
            return

        targets: list[CapCutItem] = []
        for iid in selected_iids:
            idx = int(iid)
            if 0 <= idx < len(self.capcut_displayed_items):
                targets.append(self.capcut_displayed_items[idx])

        total_size = sum(t.size for t in targets)
        has_projects = any(t.category == "Projects" for t in targets)

        if is_capcut_running():
            close_it = messagebox.askyesno(
                "CapCut Sedang Berjalan",
                "Aplikasi CapCut saat ini sedang berjalan!\n\n"
                "Apakah Anda ingin menutup CapCut terlebih dahulu agar file tidak terkunci?",
            )
            if close_it:
                kill_capcut_process()
                self.check_capcut_process()

        warn_msg = ""
        if has_projects:
            warn_msg = (
                "⚠️ PERHATIAN KHUSUS:\n"
                "Pilihan Anda menyertakan file/folder DRAFT PROYEK CapCut.\n"
                "Menghapus draft proyek akan menghapus proyek editing Anda secara permanen!\n\n"
            )

        confirm = messagebox.askyesno(
            "Konfirmasi Hapus Item CapCut",
            f"{warn_msg}Hapus {len(targets)} item CapCut terpilih ({format_size(total_size)})?\n\n"
            "Tindakan ini tidak dapat dibatalkan. Lanjutkan?",
        )
        if confirm:
            self._start_capcut_deletion(targets)

    def delete_all_capcut(self) -> None:
        if not self.capcut_displayed_items:
            return

        total_size = sum(t.size for t in self.capcut_displayed_items)
        has_projects = any(t.category == "Projects" for t in self.capcut_displayed_items)

        if is_capcut_running():
            close_it = messagebox.askyesno(
                "CapCut Sedang Berjalan",
                "Aplikasi CapCut saat ini sedang berjalan!\n\n"
                "Untuk mencegah error file terkunci, disarankan menutup CapCut terlebih dahulu.\n\n"
                "Apakah Anda ingin menutup CapCut secara otomatis sekarang?",
            )
            if close_it:
                kill_capcut_process()
                self.check_capcut_process()

        warn_msg = ""
        if has_projects:
            warn_msg = (
                "⚠️ PERINGATAN KERAS (DRAFT PROYEK):\n"
                "Tindakan ini akan MENGHAPUS SEMUA DRAFT PROYEK EDITING CAPCUT Anda yang tampil!\n"
                "Pastikan Anda telah mengekspor video penting sebelum melanjutkan.\n\n"
            )

        confirm = messagebox.askyesno(
            "Konfirmasi Hapus Semua Item CapCut",
            f"{warn_msg}PERINGATAN: Hapus SEMUA {len(self.capcut_displayed_items)} item yang tampil "
            f"({format_size(total_size)})?\n\n"
            f"Target cakupan aktif: {self.capcut_scope_var.get()}\n\n"
            "Apakah Anda benar-benar yakin ingin melanjutkan?",
        )
        if confirm:
            self._start_capcut_deletion(list(self.capcut_displayed_items))

    def _start_capcut_deletion(self, targets: list[CapCutItem]) -> None:
        self.is_capcut_deleting = True
        self.btn_capcut_scan.configure(state="disabled")
        self.btn_capcut_delete_selected.configure(state="disabled")
        self.btn_capcut_delete_all.configure(state="disabled")

        self.capcut_radar.start()
        self.capcut_dot.set_state("working")
        self.capcut_progress.set_bar_color(COLOR_RED)
        self.capcut_progress.set_progress(0, len(targets))

        threading.Thread(target=self._capcut_delete_worker, args=(targets,), daemon=True).start()

    def _capcut_delete_worker(self, targets: list[CapCutItem]) -> None:
        removed = 0
        freed = 0
        failed: list[str] = []
        total = len(targets)

        for index, item in enumerate(targets, start=1):
            path = item.path
            sz = item.size
            try:
                remove_target(path)
                if not path.exists():
                    removed += 1
                    freed += sz
                else:
                    failed.append(str(path))
            except (OSError, PermissionError):
                failed.append(str(path))

            self.after(0, self._capcut_delete_progress, index, total, item)

        self.after(0, self._capcut_delete_finished, removed, failed, freed)

    def _capcut_delete_progress(self, index: int, total: int, item: CapCutItem) -> None:
        self.capcut_progress.set_progress(index, total)
        self.capcut_status_var.set(f"Menghapus ({index}/{total}): [{item.category}] {item.name}")

    def _capcut_delete_finished(self, removed: int, failed: list[str], freed: int = 0) -> None:
        self.is_capcut_deleting = False
        self.capcut_radar.stop()
        self.capcut_dot.set_state("idle")
        self.capcut_progress.stop()
        self.capcut_progress.set_bar_color(COLOR_PURPLE)
        self.btn_capcut_scan.configure(state="normal")
        self.check_capcut_process()

        if freed > 0:
            self.record_cleaned_space(freed)

        if failed:
            messagebox.showwarning(
                "Selesai Sebagian",
                f"{removed} item CapCut berhasil dihapus.\n{len(failed)} item gagal dihapus "
                "(kemungkinan sedang digunakan oleh proses CapCut).\n\n"
                "Silakan tutup CapCut sepenuhnya lalu coba lagi.",
            )
        else:
            messagebox.showinfo(
                "Pembersihan CapCut Selesai",
                f"Berhasil! {removed} item CapCut telah dihapus dan ruang disk telah dibebaskan.",
            )

        self.start_capcut_scan()

    # ------------------------------------------------------------------
    # CAPCUT OLD VERSIONS (APPS) METHODS
    # ------------------------------------------------------------------
    def start_capcut_version_scan(self) -> None:
        if self.is_version_scanning or self.is_version_deleting:
            return

        apps_dir = Path(self.capcut_apps_path_var.get())
        self.is_version_scanning = True
        self.btn_delete_checked_versions.configure(state="disabled")
        self.btn_clean_all_versions.configure(state="disabled")

        self.ver_radar.start()
        self.ver_dot.set_state("scanning")
        self.capcut_version_progress.start_indeterminate()
        self.capcut_version_status_var.set("Sedang memindai folder versi CapCut... Mohon tunggu.")

        self.version_tree.delete(*self.version_tree.get_children())
        self.capcut_versions.clear()

        threading.Thread(target=self._capcut_version_scan_worker, args=(apps_dir,), daemon=True).start()

    def _capcut_version_scan_worker(self, apps_dir: Path) -> None:
        try:
            info = get_capcut_versions_info(apps_dir)
            self.after(0, self._capcut_version_scan_done, info, None)
        except Exception as exc:
            self.after(0, self._capcut_version_scan_done, {}, str(exc))

    def _capcut_version_scan_done(self, v_info: dict, error: str | None) -> None:
        self.ver_radar.stop()
        self.ver_dot.set_state("idle")
        self.capcut_version_progress.stop()
        self.is_version_scanning = False

        if error:
            messagebox.showerror("Gagal Memindai Versi", f"Terjadi kesalahan saat scan versi CapCut:\n{error}")
            self.capcut_version_status_var.set("Gagal memindai versi CapCut.")
            return

        raw_versions = v_info.get("versions", [])
        self.capcut_versions = [CapCutVersionItem(v) for v in raw_versions]

        latest_name = v_info.get("latest_version") or "Tidak ditemukan"
        old_size_str = format_size(v_info.get("old_versions_size", 0))
        old_count = sum(1 for v in self.capcut_versions if not v.is_latest)

        self.card_ver_latest.update_data(latest_name, "🔒 Dilindungi & Terkunci")
        self.card_ver_savable.update_data(old_size_str, f"{old_count} versi lama dapat dihapus")

        self._render_version_tree()
        self._update_version_status_only()

        has_old = old_count > 0
        self.btn_clean_all_versions.configure(state="normal" if has_old else "disabled")

    def _render_version_tree(self) -> None:
        self.version_tree.delete(*self.version_tree.get_children())
        for idx, it in enumerate(self.capcut_versions):
            if it.is_latest:
                chk_sym = "🔒"
                stat_sym = "🔒 TERBARU (DILINDUNGI)"
                tag = "latest"
            elif it.checked:
                chk_sym = "[ ✓ ]"
                stat_sym = "🗑️ Akan Dihapus"
                tag = "checked"
            else:
                chk_sym = "[   ]"
                stat_sym = "Versi Lama (Bisa Dihapus)"
                tag = "unchecked"

            self.version_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    chk_sym,
                    it.name,
                    stat_sym,
                    it.size_str,
                    f"{it.files:,} file",
                    it.modified,
                    str(it.path),
                ),
                tags=(tag,),
            )

        self.version_tree.tag_configure("latest", foreground=COLOR_GREEN_HOVER, font=("Segoe UI", 9, "bold"))
        self.version_tree.tag_configure("checked", foreground=COLOR_RED_HOVER, font=("Segoe UI", 9, "bold"))
        self.version_tree.tag_configure("unchecked", foreground=COLOR_TEXT_WHITE)

    def _update_version_status_only(self) -> None:
        checked_items = [it for it in self.capcut_versions if it.checked and not it.is_latest]
        checked_size = sum(it.size for it in checked_items)
        old_count = sum(1 for it in self.capcut_versions if not it.is_latest)

        if checked_items:
            self.btn_delete_checked_versions.configure(state="normal")
            self.capcut_version_status_var.set(
                f"Tercentang: {len(checked_items)} versi lama ({format_size(checked_size)}). Siap dihapus."
            )
        else:
            self.btn_delete_checked_versions.configure(state="disabled")
            if old_count == 0:
                self.capcut_version_status_var.set(
                    "Hanya terpasang 1 versi terbaru. Tidak ada versi lama untuk dihapus."
                )
            else:
                self.capcut_version_status_var.set(
                    f"Ditemukan {old_count} versi lama. Centang versi yang ingin dihapus."
                )

    def _on_version_tree_click(self, event) -> None:
        iid = self.version_tree.identify_row(event.y)
        if not iid:
            return
        idx = int(iid)
        if 0 <= idx < len(self.capcut_versions):
            item = self.capcut_versions[idx]
            if item.is_latest:
                self.capcut_version_status_var.set(
                    f"Versi {item.name} adalah versi TERBARU. Versi ini DILINDUNGI dan tidak dapat dihapus."
                )
                return
            item.checked = not item.checked
            self._render_version_tree()
            self._update_version_status_only()

    def _on_version_tree_space(self, event) -> None:
        selected_iids = self.version_tree.selection()
        if not selected_iids:
            return
        for iid in selected_iids:
            idx = int(iid)
            if 0 <= idx < len(self.capcut_versions):
                item = self.capcut_versions[idx]
                if not item.is_latest:
                    item.checked = not item.checked
        self._render_version_tree()
        self._update_version_status_only()

    def select_all_old_versions(self) -> None:
        for it in self.capcut_versions:
            if not it.is_latest:
                it.checked = True
        self._render_version_tree()
        self._update_version_status_only()

    def deselect_all_old_versions(self) -> None:
        for it in self.capcut_versions:
            it.checked = False
        self._render_version_tree()
        self._update_version_status_only()

    def delete_checked_versions(self) -> None:
        targets_to_delete = [it for it in self.capcut_versions if it.checked and not it.is_latest]
        if not targets_to_delete:
            return

        total_bytes = sum(t.size for t in targets_to_delete)

        if is_capcut_running():
            close_it = messagebox.askyesno(
                "CapCut Sedang Berjalan",
                "Aplikasi CapCut saat ini sedang berjalan!\n\n"
                "Apakah Anda ingin menutup CapCut secara otomatis sebelum menghapus versi lama?",
            )
            if close_it:
                kill_capcut_process()
                self.check_capcut_process()

        latest_name = next((v.name for v in self.capcut_versions if v.is_latest), "terbaru")
        confirm_text = (
            f"Hapus {len(targets_to_delete)} folder versi lama CapCut tercentang ({format_size(total_bytes)})?\n\n"
            f"✓ Versi terbaru ({latest_name}) tetap tersimpan dan terlindungi.\n\n"
            "Tindakan ini tidak dapat dibatalkan. Lanjutkan?"
        )

        confirm = messagebox.askyesno("Konfirmasi Hapus Versi Tercentang", confirm_text)
        if confirm:
            self._start_version_deletion(targets_to_delete)

    def clean_all_old_versions_one_click(self) -> None:
        old_versions = [it for it in self.capcut_versions if not it.is_latest]
        if not old_versions:
            messagebox.showinfo(
                "Bersih",
                "Tidak ada versi lama yang ditemukan. Versi aktif saat ini adalah satu-satunya versi.",
            )
            return

        total_bytes = sum(t.size for t in old_versions)

        if is_capcut_running():
            close_it = messagebox.askyesno(
                "CapCut Sedang Berjalan",
                "Aplikasi CapCut saat ini sedang berjalan!\n\n"
                "Untuk mencegah file terkunci, disarankan menutup CapCut terlebih dahulu.\n\n"
                "Apakah Anda ingin menutup CapCut secara otomatis sekarang?",
            )
            if close_it:
                kill_capcut_process()
                self.check_capcut_process()

        latest_name = next((v.name for v in self.capcut_versions if v.is_latest), "terbaru")
        confirm_text = (
            f"⚡ 1-KLIK BERSIHKAN SEMUA VERSI LAMA\n\n"
            f"Hapus SEMUA {len(old_versions)} folder versi lama CapCut ({format_size(total_bytes)})?\n\n"
            f"✓ Versi paling baru ({latest_name}) akan TETAP DISIMPAN dan terlindungi.\n"
            f"✓ Ruang disk sebesar {format_size(total_bytes)} akan dibebaskan.\n\n"
            "Apakah Anda yakin ingin melanjutkan?"
        )

        confirm = messagebox.askyesno("Konfirmasi Bersihkan Semua Versi Lama", confirm_text)
        if confirm:
            self._start_version_deletion(old_versions)

    def _start_version_deletion(self, targets: list[CapCutVersionItem]) -> None:
        self.is_version_deleting = True
        self.btn_delete_checked_versions.configure(state="disabled")
        self.btn_clean_all_versions.configure(state="disabled")

        self.ver_radar.start()
        self.ver_dot.set_state("working")
        self.capcut_version_progress.set_bar_color(COLOR_RED)
        self.capcut_version_progress.set_progress(0, len(targets))

        threading.Thread(target=self._version_delete_worker, args=(targets,), daemon=True).start()

    def _version_delete_worker(self, targets: list[CapCutVersionItem]) -> None:
        removed = 0
        freed = 0
        failed: list[str] = []
        total = len(targets)

        for index, item in enumerate(targets, start=1):
            path = item.path
            sz = item.size
            if item.is_latest:
                continue

            try:
                remove_target(path)
                if not path.exists():
                    removed += 1
                    freed += sz
                else:
                    failed.append(str(path))
            except (OSError, PermissionError):
                failed.append(str(path))

            self.after(0, self._version_delete_progress, index, total, item)

        self.after(0, self._version_delete_finished, removed, failed, freed)

    def _version_delete_progress(self, index: int, total: int, item: CapCutVersionItem) -> None:
        self.capcut_version_progress.set_progress(index, total)
        self.capcut_version_status_var.set(f"Menghapus ({index}/{total}): Versi {item.name}")

    def _version_delete_finished(self, removed: int, failed: list[str], freed: int = 0) -> None:
        self.is_version_deleting = False
        self.ver_radar.stop()
        self.ver_dot.set_state("idle")
        self.capcut_version_progress.stop()
        self.check_capcut_process()

        if freed > 0:
            self.record_cleaned_space(freed)

        if failed:
            messagebox.showwarning(
                "Selesai Sebagian",
                f"{removed} versi lama CapCut berhasil dihapus.\n{len(failed)} folder gagal dihapus "
                "(kemungkinan sedang digunakan oleh proses CapCut).\n\n"
                "Silakan tutup CapCut sepenuhnya lalu coba lagi.",
            )
        else:
            messagebox.showinfo(
                "Pembersihan Versi Lama Selesai",
                f"Berhasil! {removed} versi lama CapCut telah dihapus dan ruang disk telah dibebaskan.",
            )

        self.start_capcut_version_scan()

    # ------------------------------------------------------------------
    # TAB 4: DEVELOPER & PACKAGE CACHE MANAGER
    # ------------------------------------------------------------------
    def _build_dev_cache_tab(self, parent: tk.Frame) -> None:
        # 1. Header Card
        dev_card = tk.Frame(parent, bg=COLOR_BG_CARD, padx=14, pady=12, highlightbackground=COLOR_BORDER, highlightthickness=1)
        dev_card.pack(fill="x", pady=(0, 10))

        top_dev = tk.Frame(dev_card, bg=COLOR_BG_CARD)
        top_dev.pack(fill="x")

        tk.Label(
            top_dev,
            text="🛠️ Developer & Package Cache Manager",
            font=("Segoe UI", 12, "bold"),
            fg=COLOR_CYAN_LIGHT,
            bg=COLOR_BG_CARD,
        ).pack(side="left")

        desc_dev = (
            "Cache dari Playwright (binary browser lama), Node.js, NPM, PIP Python, dan PNPM dapat "
            "mengakumulasi puluhan Gigabyte di %LOCALAPPDATA%. CleanC secara cerdas menandai versi browser "
            "Playwright lama dan cache aman untuk dibersihkan, sembari tetap menjaga versi aktif tersimpan."
        )
        tk.Label(
            dev_card,
            text=desc_dev,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_CARD,
            wraplength=800,
            justify="left",
        ).pack(anchor="w", pady=(4, 10))

        # Metrics Row
        m_row = tk.Frame(dev_card, bg=COLOR_BG_CARD)
        m_row.pack(fill="x")

        self.card_dev_total = ModernMetricCard(
            m_row,
            icon="💾",
            title="TOTAL DEV CACHE",
            value="0 B",
            subtitle="Memindai folder...",
            accent_color=COLOR_AMBER,
        )
        self.card_dev_total.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.card_dev_selected = ModernMetricCard(
            m_row,
            icon="🧹",
            title="TERCENTANG SIAP BERSIH",
            value="0 B",
            subtitle="0 folder dipilih",
            accent_color=COLOR_GREEN_HOVER,
        )
        self.card_dev_selected.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # 2. Action Toolbar & Selection Controls
        act_row = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        act_row.pack(fill="x", pady=(0, 8))

        # Quick selection buttons
        ttk.Button(
            act_row,
            text="⭐ Pilih Rekomendasi",
            style="Outline.TButton",
            command=self.select_recommended_dev_cache,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            act_row,
            text="☑️ Centang Semua",
            style="Secondary.TButton",
            command=self.select_all_dev_cache,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            act_row,
            text="☐ Uncheck All",
            style="Secondary.TButton",
            command=self.deselect_all_dev_cache,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            act_row,
            text="🔄 Scan Ulang",
            style="Secondary.TButton",
            command=self.start_dev_cache_scan,
        ).pack(side="left", padx=(0, 6))

        # Clean Action Button
        self.btn_clean_dev_cache = ttk.Button(
            act_row,
            text="🗑️ Bersihkan Item Tercentang",
            style="Danger.TButton",
            command=self.start_dev_cache_clean,
            state="disabled",
        )
        self.btn_clean_dev_cache.pack(side="right")

        # 4. Bottom Status Bar (Pinned to bottom FIRST so it is NEVER cut off)
        dev_bottom = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        dev_bottom.pack(side="bottom", fill="x", pady=(6, 2))

        self.dev_cache_radar = ModernRadarSpinner(dev_bottom, size=24, bg=COLOR_BG_SURFACE)
        self.dev_cache_radar.pack(side="left", padx=(0, 6))

        self.dev_cache_dot = PulsingStatusDot(dev_bottom, size=16, bg=COLOR_BG_SURFACE)
        self.dev_cache_dot.pack(side="left", padx=(0, 6))

        tk.Label(
            dev_bottom,
            textvariable=self.dev_cache_status_var,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_BG_SURFACE,
        ).pack(side="left")

        # 5. Progress bar (above bottom status bar)
        self.dev_cache_progress = ShimmerProgressBar(parent, height=6, bg=COLOR_BG_SURFACE)
        self.dev_cache_progress.pack(side="bottom", fill="x", pady=(0, 6))

        # 3. Treeview Table (Fills remaining space)
        tbl_frame = tk.Frame(parent, bg=COLOR_BG_SURFACE)
        tbl_frame.pack(fill="both", expand=True, pady=(0, 6))

        cols = ("check", "category", "name", "recommendation", "size", "files", "path")
        self.dev_cache_tree = ttk.Treeview(
            tbl_frame,
            columns=cols,
            show="headings",
            selectmode="extended",
        )
        for col, label in (("check", "Pilih"), ("category", "Kategori / Tool"), ("name", "Nama Folder / Versi"), ("recommendation", "Rekomendasi & Status"), ("size", "Ukuran"), ("files", "File"), ("path", "Lokasi Folder")):
            self.dev_cache_tree.heading(col, text=label, command=lambda c=col: self.sort_tree_rows(self.dev_cache_tree, c))

        self.dev_cache_tree.column("check", width=55, anchor="center")
        self.dev_cache_tree.column("category", width=140, anchor="w")
        self.dev_cache_tree.column("name", width=220, anchor="w")
        self.dev_cache_tree.column("recommendation", width=260, anchor="w")
        self.dev_cache_tree.column("size", width=100, anchor="e")
        self.dev_cache_tree.column("files", width=90, anchor="e")
        self.dev_cache_tree.column("path", width=360, anchor="w")

        v_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.dev_cache_tree.yview)
        h_scroll = ttk.Scrollbar(tbl_frame, orient="horizontal", command=self.dev_cache_tree.xview)
        self.dev_cache_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.dev_cache_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        tbl_frame.rowconfigure(0, weight=1)
        tbl_frame.columnconfigure(0, weight=1)

        # Bindings for toggle
        self.dev_cache_tree.bind("<Button-1>", self._on_dev_cache_click)
        self.dev_cache_tree.bind("<space>", self._on_dev_cache_space)

    def _render_dev_cache_tree(self) -> None:
        self.dev_cache_tree.delete(*self.dev_cache_tree.get_children())
        for idx, it in enumerate(self.dev_cache_items):
            if it.checked:
                chk_sym = "[ ✓ ]"
                tag = "checked"
            else:
                chk_sym = "[   ]"
                tag = "latest" if not it.is_recommended else "unchecked"

            self.dev_cache_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    chk_sym,
                    it.category,
                    it.name,
                    it.recommendation,
                    it.size_str,
                    f"{it.files:,} file",
                    str(it.path),
                ),
                tags=(tag,),
            )

        self.dev_cache_tree.tag_configure("checked", foreground=COLOR_RED_HOVER, font=("Segoe UI", 9, "bold"))
        self.dev_cache_tree.tag_configure("latest", foreground=COLOR_CYAN_LIGHT, font=("Segoe UI", 9))
        self.dev_cache_tree.tag_configure("unchecked", foreground=COLOR_TEXT_WHITE)

    def _update_dev_cache_selection_status(self) -> None:
        checked_items = [it for it in self.dev_cache_items if it.checked]
        checked_size = sum(it.size for it in checked_items)
        total_size = sum(it.size for it in self.dev_cache_items)

        self.card_dev_total.update_data(
            format_size(total_size),
            f"{len(self.dev_cache_items)} folder terdeteksi"
        )
        self.card_dev_selected.update_data(
            format_size(checked_size),
            f"{len(checked_items)} dari {len(self.dev_cache_items)} folder dipilih"
        )

        if checked_items:
            self.btn_clean_dev_cache.configure(state="normal")
            self.dev_cache_status_var.set(
                f"Tercentang: {len(checked_items)} folder ({format_size(checked_size)}). Siap dibersihkan."
            )
        else:
            self.btn_clean_dev_cache.configure(state="disabled")
            self.dev_cache_status_var.set(
                "Tidak ada folder tercentang. Centang folder yang ingin Anda bersihkan."
            )

    def _on_dev_cache_click(self, event) -> None:
        iid = self.dev_cache_tree.identify_row(event.y)
        if not iid:
            return
        idx = int(iid)
        if 0 <= idx < len(self.dev_cache_items):
            item = self.dev_cache_items[idx]
            item.checked = not item.checked
            self._render_dev_cache_tree()
            self._update_dev_cache_selection_status()

    def _on_dev_cache_space(self, event) -> None:
        selected_iids = self.dev_cache_tree.selection()
        if not selected_iids:
            return
        for iid in selected_iids:
            idx = int(iid)
            if 0 <= idx < len(self.dev_cache_items):
                item = self.dev_cache_items[idx]
                item.checked = not item.checked
        self._render_dev_cache_tree()
        self._update_dev_cache_selection_status()

    def select_recommended_dev_cache(self) -> None:
        for it in self.dev_cache_items:
            it.checked = it.is_recommended
        self._render_dev_cache_tree()
        self._update_dev_cache_selection_status()

    def select_all_dev_cache(self) -> None:
        for it in self.dev_cache_items:
            it.checked = True
        self._render_dev_cache_tree()
        self._update_dev_cache_selection_status()

    def deselect_all_dev_cache(self) -> None:
        for it in self.dev_cache_items:
            it.checked = False
        self._render_dev_cache_tree()
        self._update_dev_cache_selection_status()

    def start_dev_cache_scan(self) -> None:
        if self.is_dev_cache_scanning or self.is_dev_cache_cleaning:
            return

        self.is_dev_cache_scanning = True
        if hasattr(self, "dev_cache_radar"):
            self.dev_cache_radar.start()
        if hasattr(self, "dev_cache_dot"):
            self.dev_cache_dot.set_state("working")
        self.dev_cache_status_var.set("Memindai folder dev & package cache (%LOCALAPPDATA%)...")

        threading.Thread(target=self._dev_cache_scan_worker, daemon=True).start()

    def _dev_cache_scan_worker(self) -> None:
        info = get_dev_cache_info()
        self.after(0, self._dev_cache_scan_done, info)

    def _dev_cache_scan_done(self, info: dict) -> None:
        self.is_dev_cache_scanning = False
        if hasattr(self, "dev_cache_radar"):
            self.dev_cache_radar.stop()
        if hasattr(self, "dev_cache_dot"):
            self.dev_cache_dot.set_state("idle")

        raw_items = info.get("items", [])
        self.dev_cache_items = [DevCacheItem(r) for r in raw_items]

        if hasattr(self, "dev_cache_tree"):
            self._render_dev_cache_tree()
            self._update_dev_cache_selection_status()

    def start_dev_cache_clean(self) -> None:
        if self.is_dev_cache_cleaning or self.is_dev_cache_scanning:
            return

        selected_items = [it for it in self.dev_cache_items if it.checked]
        if not selected_items:
            messagebox.showinfo("Tidak Ada Pilihan", "Silakan centang folder yang ingin dibersihkan terlebih dahulu.")
            return

        total_bytes = sum(it.size for it in selected_items)
        confirm = messagebox.askyesno(
            "Konfirmasi Pembersihan Dev Cache",
            f"Apakah Anda yakin ingin membersihkan {len(selected_items)} folder terpilih ({format_size(total_bytes)})?\n\n"
            "Folder yang tidak dicentang akan tetap aman tersimpan.",
        )
        if not confirm:
            return

        self.is_dev_cache_cleaning = True
        self.btn_clean_dev_cache.configure(state="disabled")
        self.dev_cache_radar.start()
        self.dev_cache_dot.set_state("working")
        self.dev_cache_progress.set_bar_color(COLOR_RED)
        self.dev_cache_progress.set_progress(0, len(selected_items))

        targets = [it.path for it in selected_items]
        threading.Thread(target=self._dev_cache_clean_worker, args=(selected_items,), daemon=True).start()

    def _dev_cache_clean_worker(self, targets: list[DevCacheItem]) -> None:
        freed = 0
        success_count = 0
        errors: list[str] = []
        total = len(targets)

        for idx, item in enumerate(targets, start=1):
            path = item.path
            self.after(0, self._dev_cache_clean_progress, idx, total, item.name)
            try:
                sz = get_dir_size(path) if path.is_dir() else (path.stat().st_size if path.exists() else 0)
                if path.name == "lost_and_found" and path.is_dir():
                    for sub in list(path.iterdir()):
                        remove_target(sub)
                    freed += sz
                    success_count += 1
                else:
                    remove_target(path)
                    if not path.exists():
                        freed += sz
                        success_count += 1
                    else:
                        errors.append(f"{path.name}: Masih ada file terkunci")
            except Exception as e:
                errors.append(f"{path.name}: {e}")

        self.after(0, self._dev_cache_clean_finished, freed, success_count, errors)

    def _dev_cache_clean_progress(self, index: int, total: int, item_name: str) -> None:
        self.dev_cache_progress.set_progress(index, total)
        self.dev_cache_status_var.set(f"Membersihkan ({index}/{total}): {item_name}")

    def _dev_cache_clean_finished(self, freed: int, count: int, errors: list[str]) -> None:
        self.is_dev_cache_cleaning = False
        self.dev_cache_radar.stop()
        self.dev_cache_dot.set_state("idle")
        self.dev_cache_progress.stop()

        if freed > 0:
            self.record_cleaned_space(freed)

        if errors:
            messagebox.showwarning(
                "Pembersihan Selesai Sebagian",
                f"{count} folder berhasil dibersihkan ({format_size(freed)} dibebaskan).\n\n"
                f"{len(errors)} folder gagal/terkunci:\n" + "\n".join(errors[:5]),
            )
        else:
            messagebox.showinfo(
                "Pembersihan Selesai",
                f"Sukses! {count} folder dev cache berhasil dibersihkan.\n"
                f"Total ruang disk dibebaskan: {format_size(freed)}.",
            )

        self.start_dev_cache_scan()


# Alias for backward compatibility if imported elsewhere
App = CleanCApp


if __name__ == "__main__":
    CleanCApp().mainloop()
