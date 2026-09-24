#!/usr/bin/env python3
"""Remove Chrome's "Service Worker" or "Cache" folders from Chrome profiles.

The script defaults to a dry run. Use --delete to request deletion and
--yes to skip the final confirmation prompt.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
ROAMING_APPDATA = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))

# Browser Default Paths (Universal untuk semua laptop / user Windows)
DEFAULT_CHROME_USER_DATA = LOCAL_APPDATA / "Google" / "Chrome" / "User Data"
DEFAULT_BRAVE_USER_DATA = LOCAL_APPDATA / "BraveSoftware" / "Brave-Browser" / "User Data"
DEFAULT_EDGE_USER_DATA = LOCAL_APPDATA / "Microsoft" / "Edge" / "User Data"
DEFAULT_FIREFOX_USER_DATA = ROAMING_APPDATA / "Mozilla" / "Firefox" / "Profiles"
DEFAULT_USER_DATA = DEFAULT_CHROME_USER_DATA  # Alias untuk kompatibilitas

BROWSER_PATHS = {
    "chrome": DEFAULT_CHROME_USER_DATA,
    "brave": DEFAULT_BRAVE_USER_DATA,
    "edge": DEFAULT_EDGE_USER_DATA,
    "firefox": DEFAULT_FIREFOX_USER_DATA,
}

BROWSER_PROCESSES = {
    "chrome": "chrome.exe",
    "brave": "brave.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
}

TYPE_SERVICE_WORKER = "service worker"
TYPE_CACHE = "cache"
# Chrome stores its browser cache in several sibling directories.  They are
# all safe cache targets, while profile databases (History, Preferences, etc.)
# are intentionally left untouched.
CHROME_CACHE_NAMES = {
    TYPE_CACHE,
    "code cache",
    "gpucache",
    "dawncache",
    "grshadercache",
    "shadercache",
}
TARGET_NAMES = {TYPE_SERVICE_WORKER, *CHROME_CACHE_NAMES}

PANTHER_DIR = Path(r"C:\Windows\Panther")
PANTHER_MONITOR_DIR = Path(r"C:\Windows\Panther\monitor")

DEFAULT_CAPCUT_USER_DATA = LOCAL_APPDATA / "CapCut" / "User Data"
DEFAULT_CAPCUT_CACHE = DEFAULT_CAPCUT_USER_DATA / "Cache"
DEFAULT_CAPCUT_PROJECTS = DEFAULT_CAPCUT_USER_DATA / "Projects"
DEFAULT_CAPCUT_APPS = LOCAL_APPDATA / "CapCut" / "Apps"

WINDOWS_CLEANUP_TARGETS = {
    "thumbnail-cache": "Thumbnail Cache",
    "temporary-files": "Temporary Files",
    "windows-log-files": "Windows Log Files",
    "windows-web-cache": "Windows Web Cache",
}


def is_admin() -> bool:
    """Check if the current process has Administrator privileges."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_panther_info() -> dict:
    """Return file count, total size bytes, and list of files in Panther directory."""
    info = {"files": [], "total_size": 0, "monitor_size": 0, "exists": False}
    if not PANTHER_DIR.exists():
        return info
    info["exists"] = True

    total = 0
    monitor_sz = 0
    files_list = []
    try:
        for root, _dirs, files in os.walk(PANTHER_DIR):
            for f in files:
                p = Path(root) / f
                try:
                    sz = p.stat().st_size
                    total += sz
                    is_mon = PANTHER_MONITOR_DIR in p.parents or p.parent == PANTHER_MONITOR_DIR
                    if is_mon:
                        monitor_sz += sz
                    files_list.append((str(p.relative_to(PANTHER_DIR)), sz, is_mon))
                except OSError:
                    continue
    except OSError:
        pass

    info["files"] = files_list
    info["total_size"] = total
    info["monitor_size"] = monitor_sz
    return info


def clean_panther_logs(include_all_panther: bool = False) -> tuple[bool, str]:
    """Clean Panther monitor logs by stopping WinSetupMon driver, deleting files, and restarting it."""
    import subprocess
    import tempfile

    ps_code = [
        "$ErrorActionPreference = 'SilentlyContinue'",
        "Stop-Service -Name 'WinSetupMon' -Force -ErrorAction SilentlyContinue",
        "Start-Sleep -Milliseconds 400",
        "Remove-Item -Path 'C:\\Windows\\Panther\\monitor\\*' -Recurse -Force -ErrorAction SilentlyContinue",
    ]
    if include_all_panther:
        ps_code.append(
            "Remove-Item -Path 'C:\\Windows\\Panther\\UnattendGC\\*' -Recurse -Force -ErrorAction SilentlyContinue"
        )
    ps_code.extend([
        "Start-Service -Name 'WinSetupMon' -ErrorAction SilentlyContinue",
        "exit 0",
    ])

    script = "\n".join(ps_code)

    if is_admin():
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return True, "Log Panther berhasil dibersihkan."
        return False, f"Gagal membersihkan: {res.stderr}"
    else:
        tmp_script = Path(tempfile.gettempdir()) / "clean_panther_exec.ps1"
        tmp_script.write_text(script, encoding="utf-8")
        cmd = f'Start-Process powershell -Verb RunAs -Wait -ArgumentList \'-NoProfile -ExecutionPolicy Bypass -File "{tmp_script}"\''
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True,
            text=True,
        )
        try:
            tmp_script.unlink(missing_ok=True)
        except OSError:
            pass
        if res.returncode == 0:
            return True, "Log Panther berhasil dibersihkan dengan izin Administrator."
        return False, f"Gagal mengeksekusi dengan izin Administrator: {res.stderr}"


def get_windows_cleanup_info() -> dict[str, dict]:
    """Scan safe, well-known Windows cleanup locations without deleting them."""
    local_app = LOCAL_APPDATA
    temp_dir = Path(os.environ.get("TEMP") or (local_app / "Temp"))
    targets = {
        "thumbnail-cache": [local_app / "Microsoft" / "Windows" / "Explorer"],
        "temporary-files": [temp_dir],
        "windows-log-files": [Path(r"C:\Windows\Logs")],
        "windows-web-cache": [local_app / "Microsoft" / "Windows" / "INetCache"],
    }
    result = {}
    for key, roots in targets.items():
        files = []
        total = 0
        for root in roots:
            if not root.is_dir():
                continue
            try:
                for p in root.rglob("*"):
                    if not p.is_file():
                        continue
                    if key == "thumbnail-cache" and not p.name.casefold().startswith("thumbcache_"):
                        continue
                    try:
                        size = p.stat().st_size
                    except OSError:
                        continue
                    files.append(p)
                    total += size
            except OSError:
                continue
        result[key] = {"name": WINDOWS_CLEANUP_TARGETS[key], "files": files, "total_size": total}
    return result


def clean_windows_cleanup_target(target: str) -> tuple[int, int, list[str]]:
    """Delete files for one Windows cleanup category; locked files are reported."""
    info = get_windows_cleanup_info()
    if target not in info:
        raise ValueError(f"Target Windows tidak dikenal: {target}")
    removed = 0
    freed = 0
    failed = []
    for path in info[target]["files"]:
        try:
            size = path.stat().st_size if path.exists() else 0
            remove_target(path)
            if not path.exists():
                removed += 1
                freed += size
            else:
                failed.append(str(path))
        except (OSError, PermissionError):
            failed.append(str(path))
    return removed, freed, failed


def get_dir_size(path: Path) -> int:
    """Calculate directory size in bytes recursively."""
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += get_dir_size(Path(entry.path))
            except OSError:
                continue
    except OSError:
        pass
    return total


def format_size(size_bytes: int) -> str:
    """Format bytes into readable human format (B, KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def categorize_target(path: Path) -> str:
    """Return friendly category name of target path: 'Service Worker' or 'Cache'."""
    name = path.name.casefold()
    if name == TYPE_SERVICE_WORKER:
        return "Service Worker"
    elif name in CHROME_CACHE_NAMES:
        return "Cache"
    return path.name


def extract_profile_name(path: Path, user_data: Path) -> str:
    """Extract Chrome profile name (e.g. 'Default', 'Profile 1') from target path."""
    try:
        rel = path.relative_to(user_data)
        parts = rel.parts
        if parts:
            return parts[0]
    except ValueError:
        pass
    return "Unknown"


def find_targets(user_data: Path, target_types: set[str] | list[str] | None = None) -> list[Path]:
    """Find Chrome cache and Service Worker directories below Chrome User Data.
    
    If target_types is provided, only include directories whose casefold name is in target_types.
    Defaults to all supported targets in TARGET_NAMES.
    """
    valid_targets = {t.casefold() for t in target_types} if target_types else TARGET_NAMES
    targets: list[Path] = []

    if not user_data.is_dir():
        raise FileNotFoundError(f"Folder tidak ditemukan: {user_data}")

    # Each immediate child is treated as a profile (Default, Profile 1, etc.).
    for profile in sorted(user_data.iterdir(), key=lambda p: p.name.lower()):
        if not profile.is_dir():
            continue
        for root, dirs, _files in os.walk(profile, topdown=True):
            # Target directories we care about
            matched_targets = [name for name in dirs if name.casefold() in TARGET_NAMES]
            for name in matched_targets:
                if name.casefold() in valid_targets:
                    targets.append(Path(root) / name)
            # Prune descent into any target directory as it will be removed as a whole
            dirs[:] = [name for name in dirs if name.casefold() not in TARGET_NAMES]

    return targets


def _force_remove_readonly(func, path, _exc_info):
    """Callback to clear readonly flag and retry deletion on Windows."""
    import stat
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def remove_target(path: Path) -> None:
    """Remove one directory or file, including its contents."""
    import stat
    try:
        if path.is_dir():
            shutil.rmtree(path, onerror=_force_remove_readonly)
        elif path.exists():
            try:
                path.unlink()
            except PermissionError:
                os.chmod(path, stat.S_IWRITE)
                path.unlink()
    except PermissionError as exc:
        raise PermissionError(
            f"Tidak bisa menghapus {path}. Tutup aplikasi terkait lalu coba lagi."
        ) from exc


def is_capcut_running() -> bool:
    """Check if CapCut process is currently running."""
    import subprocess
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/NH"],
            capture_output=True,
            text=True,
            creationflags=flags,
        )
        return "CapCut.exe" in out.stdout
    except Exception:
        return False


def kill_capcut_process() -> tuple[bool, str]:
    """Terminate running CapCut processes."""
    import subprocess
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        res = subprocess.run(
            ["taskkill", "/F", "/IM", "CapCut.exe", "/T"],
            capture_output=True,
            text=True,
            creationflags=flags,
        )
        if res.returncode == 0:
            return True, "Semua proses CapCut berhasil ditutup."
        return False, f"Gagal menutup CapCut: {res.stderr or res.stdout}"
    except Exception as exc:
        return False, str(exc)


def is_browser_running(browser: str = "chrome") -> bool:
    """Check if the given browser process (chrome, brave, edge) is running."""
    import subprocess
    exe = BROWSER_PROCESSES.get(browser.lower(), browser.lower())
    if not exe.endswith(".exe"):
        exe += ".exe"
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe}", "/NH"],
            capture_output=True,
            text=True,
            creationflags=flags,
        )
        return exe.lower() in out.stdout.lower()
    except Exception:
        return False


def kill_browser_process(browser: str = "chrome") -> tuple[bool, str]:
    """Terminate the given browser process (chrome, brave, edge)."""
    import subprocess
    exe = BROWSER_PROCESSES.get(browser.lower(), browser.lower())
    if not exe.endswith(".exe"):
        exe += ".exe"
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        res = subprocess.run(
            ["taskkill", "/F", "/IM", exe, "/T"],
            capture_output=True,
            text=True,
            creationflags=flags,
        )
        if res.returncode == 0:
            return True, f"Semua proses {exe} berhasil ditutup."
        return False, f"Gagal menutup {exe}: {res.stderr or res.stdout}"
    except Exception as exc:
        return False, str(exc)


def get_capcut_cache_info(cache_dir: Path | None = None) -> dict:
    """Scan CapCut cache directory and return summary and list of items."""
    target_dir = cache_dir or DEFAULT_CAPCUT_CACHE
    info = {
        "exists": target_dir.exists() and target_dir.is_dir(),
        "path": target_dir,
        "items": [],
        "total_size": 0,
        "total_files": 0,
    }
    if not info["exists"]:
        return info

    total_sz = 0
    total_files = 0
    items = []

    try:
        entries = list(target_dir.iterdir())
    except OSError:
        return info

    for entry in sorted(entries, key=lambda e: (not e.is_dir(), e.name.lower())):
        try:
            if entry.is_dir():
                file_count = 0
                sz = 0
                for root, _dirs, files in os.walk(entry):
                    file_count += len(files)
                    for f in files:
                        try:
                            sz += (Path(root) / f).stat().st_size
                        except OSError:
                            pass
                total_sz += sz
                total_files += file_count
                items.append({
                    "name": entry.name,
                    "path": entry,
                    "is_dir": True,
                    "type": "Folder",
                    "category": "Cache",
                    "size": sz,
                    "files": file_count,
                })
            else:
                sz = entry.stat().st_size
                total_sz += sz
                total_files += 1
                items.append({
                    "name": entry.name,
                    "path": entry,
                    "is_dir": False,
                    "type": "File",
                    "category": "Cache",
                    "size": sz,
                    "files": 1,
                })
        except OSError:
            continue

    info["items"] = items
    info["total_size"] = total_sz
    info["total_files"] = total_files
    return info


def clean_capcut_cache(
    cache_dir: Path | None = None,
    targets: list[Path] | None = None,
) -> tuple[int, int, list[str]]:
    """Delete all (or specific) folders and files inside CapCut cache.

    Returns (removed_count, failed_count, failed_paths).
    """
    target_dir = cache_dir or DEFAULT_CAPCUT_CACHE
    if not target_dir.exists():
        return 0, 0, []

    if targets is not None:
        items_to_clean = targets
    else:
        try:
            items_to_clean = list(target_dir.iterdir())
        except OSError:
            return 0, 0, []

    removed = 0
    failed: list[str] = []

    for item in items_to_clean:
        try:
            remove_target(item)
            if not item.exists():
                removed += 1
            else:
                failed.append(str(item))
        except (OSError, PermissionError):
            failed.append(str(item))

    return removed, len(failed), failed


def get_capcut_projects_info(projects_dir: Path | None = None) -> dict:
    """Scan CapCut Projects directory and return summary and list of items."""
    target_dir = projects_dir or DEFAULT_CAPCUT_PROJECTS
    info = {
        "exists": target_dir.exists() and target_dir.is_dir(),
        "path": target_dir,
        "items": [],
        "total_size": 0,
        "total_files": 0,
    }
    if not info["exists"]:
        return info

    total_sz = 0
    total_files = 0
    items = []

    try:
        entries = list(target_dir.iterdir())
    except OSError:
        return info

    for entry in sorted(entries, key=lambda e: (not e.is_dir(), e.name.lower())):
        # If entry is com.lveditor.draft, expand individual project drafts
        if entry.is_dir() and entry.name.lower() == "com.lveditor.draft":
            try:
                draft_entries = list(entry.iterdir())
            except OSError:
                draft_entries = []
            for draft in sorted(draft_entries, key=lambda d: (not d.is_dir(), d.name.lower())):
                try:
                    if draft.is_dir():
                        f_count = 0
                        sz = 0
                        for root, _dirs, files in os.walk(draft):
                            f_count += len(files)
                            for f in files:
                                try:
                                    sz += (Path(root) / f).stat().st_size
                                except OSError:
                                    pass
                        total_sz += sz
                        total_files += f_count
                        items.append({
                            "name": f"draft/{draft.name}",
                            "path": draft,
                            "is_dir": True,
                            "type": "Project Draft",
                            "category": "Projects",
                            "size": sz,
                            "files": f_count,
                        })
                    else:
                        sz = draft.stat().st_size
                        total_sz += sz
                        total_files += 1
                        items.append({
                            "name": f"draft/{draft.name}",
                            "path": draft,
                            "is_dir": False,
                            "type": "File",
                            "category": "Projects",
                            "size": sz,
                            "files": 1,
                        })
                except OSError:
                    continue
        else:
            try:
                if entry.is_dir():
                    f_count = 0
                    sz = 0
                    for root, _dirs, files in os.walk(entry):
                        f_count += len(files)
                        for f in files:
                            try:
                                sz += (Path(root) / f).stat().st_size
                            except OSError:
                                pass
                    total_sz += sz
                    total_files += f_count
                    items.append({
                        "name": entry.name,
                        "path": entry,
                        "is_dir": True,
                        "type": "Folder",
                        "category": "Projects",
                        "size": sz,
                        "files": f_count,
                    })
                else:
                    sz = entry.stat().st_size
                    total_sz += sz
                    total_files += 1
                    items.append({
                        "name": entry.name,
                        "path": entry,
                        "is_dir": False,
                        "type": "File",
                        "category": "Projects",
                        "size": sz,
                        "files": 1,
                    })
            except OSError:
                continue

    info["items"] = items
    info["total_size"] = total_sz
    info["total_files"] = total_files
    return info


def clean_capcut_projects(
    projects_dir: Path | None = None,
    targets: list[Path] | None = None,
) -> tuple[int, int, list[str]]:
    """Delete all (or specific) folders and files inside CapCut Projects directory.

    Returns (removed_count, failed_count, failed_paths).
    """
    target_dir = projects_dir or DEFAULT_CAPCUT_PROJECTS
    if not target_dir.exists():
        return 0, 0, []

    if targets is not None:
        items_to_clean = targets
    else:
        try:
            items_to_clean = list(target_dir.iterdir())
        except OSError:
            return 0, 0, []

    removed = 0
    failed: list[str] = []

    for item in items_to_clean:
        try:
            remove_target(item)
            if not item.exists():
                removed += 1
            else:
                failed.append(str(item))
        except (OSError, PermissionError):
            failed.append(str(item))

    return removed, len(failed), failed


def get_capcut_versions_info(apps_dir: Path | None = None) -> dict:
    """Scan CapCut Apps folder for installed versions, auto-sort newest to oldest."""
    import re
    import datetime

    target_dir = apps_dir or DEFAULT_CAPCUT_APPS
    info = {
        "exists": target_dir.exists() and target_dir.is_dir(),
        "path": target_dir,
        "versions": [],
        "latest_version": None,
        "total_size": 0,
        "old_versions_size": 0,
    }
    if not info["exists"]:
        return info

    current_ver_str = None
    prod_info = target_dir / "ProductInfo.xml"
    if prod_info.exists():
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(prod_info)
            root = tree.getroot()
            full_appver = root.find("full_appver")
            if full_appver is not None and "value" in full_appver.attrib:
                current_ver_str = full_appver.attrib["value"].strip()
        except Exception:
            pass

    version_candidates = []
    try:
        entries = list(target_dir.iterdir())
    except OSError:
        return info

    for entry in entries:
        if entry.is_dir():
            nums = re.findall(r"\d+", entry.name)
            if len(nums) >= 2:
                v_tuple = tuple(map(int, nums))
                version_candidates.append((v_tuple, entry))

    # Auto-sort newest to oldest
    version_candidates.sort(key=lambda x: x[0], reverse=True)

    if not version_candidates:
        return info

    latest_candidate = version_candidates[0][1].name
    if current_ver_str and any(c[1].name == current_ver_str for c in version_candidates):
        latest_candidate = current_ver_str
    info["latest_version"] = latest_candidate

    total_sz = 0
    old_sz = 0
    version_list = []

    for v_tuple, entry in version_candidates:
        is_latest = (entry.name == latest_candidate)
        sz = 0
        f_count = 0
        try:
            for root, _dirs, files in os.walk(entry):
                f_count += len(files)
                for f in files:
                    try:
                        sz += (Path(root) / f).stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass

        try:
            mtime = entry.stat().st_mtime
            mod_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        except OSError:
            mod_str = "-"

        total_sz += sz
        if not is_latest:
            old_sz += sz

        version_list.append({
            "name": entry.name,
            "version_tuple": v_tuple,
            "path": entry,
            "is_latest": is_latest,
            "size": sz,
            "files": f_count,
            "modified": mod_str,
        })

    info["versions"] = version_list
    info["total_size"] = total_sz
    info["old_versions_size"] = old_sz
    return info


def clean_capcut_old_versions(
    apps_dir: Path | None = None,
    targets: list[Path] | None = None,
) -> tuple[int, int, list[str]]:
    """Delete old version folders in CapCut Apps directory, strictly protecting the latest version.

    Returns (removed_count, failed_count, failed_paths).
    """
    target_dir = apps_dir or DEFAULT_CAPCUT_APPS
    info = get_capcut_versions_info(target_dir)
    latest_name = info["latest_version"]

    if targets is not None:
        # Strictly ignore the latest version if passed
        items_to_clean = [p for p in targets if p.name != latest_name]
    else:
        # All old versions except latest
        items_to_clean = [v["path"] for v in info["versions"] if not v["is_latest"]]

    removed = 0
    failed: list[str] = []

    for item in items_to_clean:
        try:
            remove_target(item)
            if not item.exists():
                removed += 1
            else:
                failed.append(str(item))
        except (OSError, PermissionError):
            failed.append(str(item))

    return removed, len(failed), failed


def get_dir_file_count(path: Path) -> int:
    """Return count of files inside path recursively."""
    if not path.exists():
        return 0
    if path.is_file():
        return 1
    cnt = 0
    try:
        for _root, _dirs, files in os.walk(path):
            cnt += len(files)
    except Exception:
        pass
    return cnt


def get_dev_cache_info() -> dict:
    """Scan developer and package manager cache folders in Local AppData.
    Returns summary dict with total size, recommended size, and list of items.
    """
    items: list[dict] = []
    total_size = 0
    recommended_size = 0

    local_app = LOCAL_APPDATA

    # 1. ms-playwright (Browser Binaries)
    pw_dir = local_app / "ms-playwright"
    if pw_dir.exists() and pw_dir.is_dir():
        sub_dirs = [d for d in pw_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

        def _get_rev(name: str) -> int:
            parts = name.split("-")
            if len(parts) >= 2 and parts[-1].isdigit():
                return int(parts[-1])
            return 0

        chromium_max = max([_get_rev(d.name) for d in sub_dirs if d.name.startswith("chromium-")] or [0])
        shell_max = max([_get_rev(d.name) for d in sub_dirs if d.name.startswith("chromium_headless_shell-")] or [0])
        ffmpeg_max = max([_get_rev(d.name) for d in sub_dirs if d.name.startswith("ffmpeg-")] or [0])

        for d in sorted(sub_dirs, key=lambda x: x.name):
            sz = get_dir_size(d)
            fc = get_dir_file_count(d)
            total_size += sz

            rev = _get_rev(d.name)
            is_latest = False
            if d.name.startswith("chromium-") and rev == chromium_max and chromium_max > 0:
                is_latest = True
            elif d.name.startswith("chromium_headless_shell-") and rev == shell_max and shell_max > 0:
                is_latest = True
            elif d.name.startswith("ffmpeg-") and rev == ffmpeg_max and ffmpeg_max > 0:
                is_latest = True

            is_rec = not is_latest
            if is_rec:
                recommended_size += sz

            rec_label = "[REKOMENDASI] Versi Lama (Aman Dihapus)" if is_rec else "[OPSIONAL] Versi Terbaru"
            items.append({
                "category": "Playwright",
                "name": d.name,
                "label": f"Playwright {d.name}",
                "path": d,
                "size": sz,
                "size_str": format_size(sz),
                "files": fc,
                "is_recommended": is_rec,
                "recommendation": rec_label,
            })

    # 2. ms-playwright-go (Go Drivers)
    pw_go_dir = local_app / "ms-playwright-go"
    if pw_go_dir.exists() and pw_go_dir.is_dir():
        go_sub_dirs = [d for d in pw_go_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

        def _parse_semver(name: str):
            try:
                return tuple(int(x) for x in name.split("."))
            except Exception:
                return (0, 0, 0)

        max_go_ver = max([_parse_semver(d.name) for d in go_sub_dirs] or [(0, 0, 0)])

        for d in sorted(go_sub_dirs, key=lambda x: _parse_semver(x.name)):
            sz = get_dir_size(d)
            fc = get_dir_file_count(d)
            total_size += sz
            is_latest = (_parse_semver(d.name) == max_go_ver and max_go_ver != (0, 0, 0))
            is_rec = not is_latest
            if is_rec:
                recommended_size += sz

            items.append({
                "category": "Playwright Go",
                "name": d.name,
                "label": f"Playwright Go v{d.name}",
                "path": d,
                "size": sz,
                "size_str": format_size(sz),
                "files": fc,
                "is_recommended": is_rec,
                "recommendation": "[REKOMENDASI] Versi Lama (Aman Dihapus)" if is_rec else "[OPSIONAL] Versi Terbaru",
            })

    # 3. npm-cache
    npm_dir = local_app / "npm-cache"
    if npm_dir.exists():
        sz = get_dir_size(npm_dir)
        fc = get_dir_file_count(npm_dir)
        total_size += sz
        recommended_size += sz
        items.append({
            "category": "NPM Cache",
            "name": "npm-cache",
            "label": "Node.js NPM Package Cache (_cacache)",
            "path": npm_dir,
            "size": sz,
            "size_str": format_size(sz),
            "files": fc,
            "is_recommended": True,
            "recommendation": "[REKOMENDASI] Sangat Aman Dihapus (100% Cache)",
        })

    # 4. pip/cache
    pip_dir = local_app / "pip" / "cache"
    if pip_dir.exists():
        sz = get_dir_size(pip_dir)
        fc = get_dir_file_count(pip_dir)
        total_size += sz
        recommended_size += sz
        items.append({
            "category": "PIP Cache",
            "name": "pip/cache",
            "label": "Python PIP Wheel & Download Cache",
            "path": pip_dir,
            "size": sz,
            "size_str": format_size(sz),
            "files": fc,
            "is_recommended": True,
            "recommendation": "[REKOMENDASI] Sangat Aman Dihapus (100% Cache)",
        })

    # 5. pnpm-cache
    pnpm_dir = local_app / "pnpm-cache"
    if pnpm_dir.exists():
        sz = get_dir_size(pnpm_dir)
        fc = get_dir_file_count(pnpm_dir)
        total_size += sz
        recommended_size += sz
        items.append({
            "category": "PNPM Cache",
            "name": "pnpm-cache",
            "label": "PNPM Package Manager Cache",
            "path": pnpm_dir,
            "size": sz,
            "size_str": format_size(sz),
            "files": fc,
            "is_recommended": True,
            "recommendation": "[REKOMENDASI] Sangat Aman Dihapus (100% Cache)",
        })

    # 6. node-gyp/Cache
    ng_dir = local_app / "node-gyp" / "Cache"
    if ng_dir.exists() and ng_dir.is_dir():
        for d in sorted(ng_dir.iterdir()):
            if d.is_dir():
                sz = get_dir_size(d)
                fc = get_dir_file_count(d)
                total_size += sz
                recommended_size += sz
                items.append({
                    "category": "Node-Gyp",
                    "name": f"node-gyp/{d.name}",
                    "label": f"Node.js Native C++ Header v{d.name}",
                    "path": d,
                    "size": sz,
                    "size_str": format_size(sz),
                    "files": fc,
                    "is_recommended": True,
                    "recommendation": "[REKOMENDASI] Aman Dihapus (Header Cache)",
                })

    # 7. Google DriveFS (Lost & Found, CEF Cache, Crashpad)
    drivefs_dir = local_app / "Google" / "DriveFS"
    if drivefs_dir.exists() and drivefs_dir.is_dir():
        for acc_dir in drivefs_dir.iterdir():
            if acc_dir.is_dir() and acc_dir.name.isdigit():
                laf = acc_dir / "lost_and_found"
                if laf.exists():
                    sz = get_dir_size(laf)
                    fc = get_dir_file_count(laf)
                    total_size += sz
                    if sz > 0 or fc > 0:
                        recommended_size += sz
                    items.append({
                        "category": "Google Drive",
                        "name": f"lost_and_found ({acc_dir.name[:6]}...)",
                        "label": "Google Drive Lost & Found",
                        "path": laf,
                        "size": sz,
                        "size_str": format_size(sz),
                        "files": fc,
                        "is_recommended": (sz > 0 or fc > 0),
                        "recommendation": "[REKOMENDASI] Sampah Konflik Google Drive" if (sz > 0 or fc > 0) else "Folder Bersih (0 B)",
                    })

        for g_name, g_desc in [
            ("cef_cache", "Cache Browser CEF Google Drive"),
            ("Crashpad", "Crash Dump Google Drive"),
        ]:
            g_dir = drivefs_dir / g_name
            if g_dir.exists():
                sz = get_dir_size(g_dir)
                fc = get_dir_file_count(g_dir)
                if sz > 0:
                    total_size += sz
                    recommended_size += sz
                    items.append({
                        "category": "Google Drive",
                        "name": f"DriveFS/{g_name}",
                        "label": f"Google Drive {g_name}",
                        "path": g_dir,
                        "size": sz,
                        "size_str": format_size(sz),
                        "files": fc,
                        "is_recommended": True,
                        "recommendation": f"[REKOMENDASI] {g_desc}",
                    })

    return {
        "items": items,
        "total_size": total_size,
        "recommended_size": recommended_size,
        "item_count": len(items),
    }


def clean_dev_cache_targets(targets: list[Path]) -> tuple[int, int, list[str]]:
    """Clean the specified dev cache paths."""
    removed = 0
    failed: list[str] = []
    for p in targets:
        try:
            if not p.exists():
                continue
            if p.name == "lost_and_found":
                for sub in list(p.iterdir()):
                    remove_target(sub)
                removed += 1
            else:
                remove_target(p)
                if not p.exists():
                    removed += 1
                else:
                    failed.append(str(p))
        except (OSError, PermissionError):
            failed.append(str(p))
    return removed, len(failed), failed


STATS_FILE = LOCAL_APPDATA / "CleanC" / "stats.json"


def get_drive_c_usage() -> dict:
    """Mengembalikan informasi penggunaan drive C: secara akurat."""
    try:
        total, used, free = shutil.disk_usage("C:\\")
        free_pct = (free / total) * 100 if total > 0 else 0
        used_pct = (used / total) * 100 if total > 0 else 0
        return {
            "total": total,
            "used": used,
            "free": free,
            "free_pct": free_pct,
            "used_pct": used_pct,
            "total_str": format_size(total),
            "free_str": format_size(free),
            "used_str": format_size(used),
        }
    except Exception:
        return {
            "total": 0,
            "used": 0,
            "free": 0,
            "free_pct": 0,
            "used_pct": 0,
            "total_str": "0 B",
            "free_str": "0 B",
            "used_str": "0 B",
        }


def load_clean_stats() -> dict:
    """Membaca riwayat akumulasi pembersihan ruang penyimpanan."""
    try:
        if STATS_FILE.exists():
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "total_freed_bytes": int(data.get("total_freed_bytes", 0)),
                    "clean_count": int(data.get("clean_count", 0)),
                }
    except Exception:
        pass
    return {"total_freed_bytes": 0, "clean_count": 0}


def save_clean_stats(stats: dict) -> None:
    """Menyimpan riwayat akumulasi pembersihan ruang penyimpanan."""
    try:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
    except Exception:
        pass


def record_freed_bytes(freed: int) -> dict:
    """Menambahkan bytes yang baru dibersihkan ke akumulasi riwayat."""
    stats = load_clean_stats()
    stats["total_freed_bytes"] += max(0, freed)
    stats["clean_count"] += 1
    save_clean_stats(stats)
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hapus folder Cache dan/atau Service Worker dari seluruh profil Chrome."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Lokasi Browser User Data (default: otomatis sesuai browser terpilih).",
    )
    parser.add_argument(
        "--browser",
        choices=["chrome", "brave", "edge", "firefox"],
        default="chrome",
        help="Pilih browser yang ingin dipindai/dibersihkan: chrome (default), brave, edge, atau firefox.",
    )
    parser.add_argument(
        "--brave",
        action="store_true",
        help="Shortcut untuk memilih Brave Browser (--browser brave).",
    )
    parser.add_argument(
        "--type",
        choices=["all", "service-worker", "cache"],
        default="all",
        help="Jenis target yang dipindai: 'all' (default), 'service-worker', atau 'cache'.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Lakukan penghapusan; tanpa opsi ini hanya menampilkan target.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Lewati konfirmasi (gunakan dengan --delete).",
    )
    parser.add_argument(
        "--clean-panther",
        action="store_true",
        help="Bersihkan folder C:\\Windows\\Panther\\monitor (membutuhkan hak Administrator).",
    )
    parser.add_argument(
        "--panther-info",
        action="store_true",
        help="Tampilkan info file log di C:\\Windows\\Panther.",
    )
    parser.add_argument(
        "--windows-info",
        action="store_true",
        help="Tampilkan kategori cache/temp Windows yang dapat dibersihkan.",
    )
    parser.add_argument(
        "--clean-windows",
        choices=list(WINDOWS_CLEANUP_TARGETS),
        help="Bersihkan satu kategori Windows (gunakan --yes untuk melewati konfirmasi).",
    )
    parser.add_argument(
        "--capcut-path",
        type=Path,
        default=DEFAULT_CAPCUT_CACHE,
        help=f"Lokasi folder Cache CapCut (default: {DEFAULT_CAPCUT_CACHE})",
    )
    parser.add_argument(
        "--capcut-projects-path",
        type=Path,
        default=DEFAULT_CAPCUT_PROJECTS,
        help=f"Lokasi folder Projects CapCut (default: {DEFAULT_CAPCUT_PROJECTS})",
    )
    parser.add_argument(
        "--capcut-apps-path",
        type=Path,
        default=DEFAULT_CAPCUT_APPS,
        help=f"Lokasi folder Apps CapCut (default: {DEFAULT_CAPCUT_APPS})",
    )
    parser.add_argument(
        "--capcut-info",
        action="store_true",
        help="Tampilkan info folder dan file cache serta projects CapCut.",
    )
    parser.add_argument(
        "--capcut-versions-info",
        action="store_true",
        help="Tampilkan daftar versi CapCut di folder Apps terurut dari baru ke lama.",
    )
    parser.add_argument(
        "--clean-capcut",
        action="store_true",
        help="Bersihkan seluruh folder dan file di dalam folder Cache CapCut.",
    )
    parser.add_argument(
        "--clean-capcut-projects",
        action="store_true",
        help="Bersihkan seluruh folder dan file di dalam folder Projects CapCut.",
    )
    parser.add_argument(
        "--clean-capcut-old-versions",
        action="store_true",
        help="Bersihkan seluruh versi lama CapCut di folder Apps, menyisakan versi terbaru.",
    )
    parser.add_argument(
        "--close-capcut",
        action="store_true",
        help="Tutup paksa proses CapCut.exe jika sedang berjalan sebelum membersihkan cache/projects/versi lama.",
    )
    parser.add_argument(
        "--dev-cache-info",
        action="store_true",
        help="Tampilkan info cache developer (Playwright, NPM, PIP, PNPM, Node-Gyp).",
    )
    parser.add_argument(
        "--clean-dev-cache",
        action="store_true",
        help="Bersihkan seluruh item cache developer yang direkomendasikan.",
    )
    args = parser.parse_args()

    if args.windows_info or args.clean_windows:
        info = get_windows_cleanup_info()
        if args.windows_info:
            for key, item in info.items():
                print(f"{item['name']}: {len(item['files'])} file, {format_size(item['total_size'])}")
        if args.clean_windows:
            item = info[args.clean_windows]
            if not item["files"]:
                print(f"Tidak ada file {item['name']} yang perlu dibersihkan.")
                return 0
            print(f"Ditemukan {len(item['files'])} file {item['name']} ({format_size(item['total_size'])}).")
            if not args.yes:
                answer = input("Ketik HAPUS untuk melanjutkan: ")
                if answer.strip().upper() != "HAPUS":
                    print("Dibatalkan.")
                    return 0
            removed, freed, failed = clean_windows_cleanup_target(args.clean_windows)
            print(f"Berhasil menghapus {removed} file ({format_size(freed)}).")
            if failed:
                print(f"Gagal/terkunci: {len(failed)} file")
        return 0

    if args.dev_cache_info:
        info = get_dev_cache_info()
        print(f"=== Dev & Package Cache ({LOCAL_APPDATA}) ===")
        print(f"Total ukuran terdeteksi: {format_size(info['total_size'])}")
        print(f"Ukuran aman direkomendasikan: {format_size(info['recommended_size'])}")
        print(f"Jumlah item: {info['item_count']}")
        for it in info["items"]:
            tag = "[REKOMENDASI]" if it["is_recommended"] else "[OPSIONAL]"
            print(f"  {tag:15} {it['category']:15} {it['name']:32} {it['size_str']:>10} ({it['files']} files) - {it['recommendation']}")
        return 0

    if args.clean_dev_cache:
        info = get_dev_cache_info()
        rec_targets = [it["path"] for it in info["items"] if it["is_recommended"]]
        if not rec_targets:
            print("Tidak ada cache developer yang perlu dibersihkan.")
            return 0
        print(f"Ditemukan {len(rec_targets)} item cache developer rekomendasi ({format_size(info['recommended_size'])}):")
        for it in info["items"]:
            if it["is_recommended"]:
                print(f"  - [{it['category']}] {it['name']} ({it['size_str']})")

        if not args.yes:
            answer = input(f"\nHAPUS SEMUA {len(rec_targets)} item cache di atas? Ketik HAPUS untuk melanjutkan: ")
            if answer.strip() != "HAPUS":
                print("Dibatalkan; tidak ada perubahan.")
                return 0

        print("Sedang membersihkan cache developer...")
        removed, failed_cnt, failed_list = clean_dev_cache_targets(rec_targets)
        print(f"Selesai: {removed} item dihapus, {failed_cnt} gagal.")
        if failed_list:
            print("Gagal dihapus:")
            for fp in failed_list:
                print(f"  - {fp}")
            return 1
        return 0

    if args.close_capcut or ((args.clean_capcut or args.clean_capcut_projects or args.clean_capcut_old_versions) and is_capcut_running()):
        if is_capcut_running():
            print("Mendeteksi CapCut sedang berjalan. Menghentikan proses...")
            ok, msg = kill_capcut_process()
            print(f"Hasil: {msg}")

    if args.capcut_versions_info:
        v_info = get_capcut_versions_info(args.capcut_apps_path)
        print(f"=== CapCut Versions ({v_info['path']}) ===")
        print(f"Status: Exists={v_info['exists']}")
        print(f"Versi Aktif/Terbaru: {v_info['latest_version'] or 'Tidak terdeteksi'}")
        print(f"Total ukuran semua versi: {format_size(v_info['total_size'])}")
        print(f"Ukuran versi lama yang bisa dihemat: {format_size(v_info['old_versions_size'])}")
        for it in v_info["versions"]:
            tag = "[TERBARU - DILINDUNGI]" if it["is_latest"] else "[VERSI LAMA]"
            print(f"  {tag} {it['name']} ({format_size(it['size'])}, {it['files']} files, mod: {it['modified']})")
        return 0

    if args.clean_capcut_old_versions:
        v_info = get_capcut_versions_info(args.capcut_apps_path)
        if not v_info["exists"]:
            print(f"Folder Apps CapCut tidak ditemukan di: {args.capcut_apps_path}")
            return 1
        old_vers = [v for v in v_info["versions"] if not v["is_latest"]]
        if not old_vers:
            print(f"Tidak ada versi lama yang ditemukan. Versi saat ini ({v_info['latest_version']}) adalah satu-satunya versi.")
            return 0

        print(f"Versi terbaru yang dilindungi: {v_info['latest_version']}")
        print(f"Ditemukan {len(old_vers)} versi lama yang akan dihapus ({format_size(v_info['old_versions_size'])}):")
        for ov in old_vers:
            print(f"  - {ov['name']} ({format_size(ov['size'])})")

        if not args.yes:
            answer = input(f"\nHAPUS SEMUA {len(old_vers)} versi lama di atas? Ketik HAPUS untuk melanjutkan: ")
            if answer.strip() != "HAPUS":
                print("Dibatalkan; tidak ada perubahan.")
                return 0

        print("Sedang membersihkan versi lama CapCut...")
        removed, failed_cnt, failed_list = clean_capcut_old_versions(args.capcut_apps_path)
        print(f"Selesai: {removed} versi lama dihapus, {failed_cnt} gagal.")
        if failed_list:
            print("Gagal dihapus:")
            for fp in failed_list:
                print(f"  - {fp}")
            return 1
        return 0

    if args.capcut_info:
        cache_info = get_capcut_cache_info(args.capcut_path)
        print(f"=== CapCut Cache ({cache_info['path']}) ===")
        print(f"Status: Exists={cache_info['exists']}")
        print(f"Total ukuran Cache: {format_size(cache_info['total_size'])}")
        print(f"Jumlah item: {len(cache_info['items'])} ({cache_info['total_files']} file)")
        for it in cache_info["items"][:10]:
            print(f"  [{it['type']}] {it['name']} ({format_size(it['size'])}, {it['files']} files)")
        if len(cache_info["items"]) > 10:
            print(f"  ... dan {len(cache_info['items']) - 10} item lainnya.")

        proj_info = get_capcut_projects_info(args.capcut_projects_path)
        print(f"\n=== CapCut Projects ({proj_info['path']}) ===")
        print(f"Status: Exists={proj_info['exists']}")
        print(f"Total ukuran Projects: {format_size(proj_info['total_size'])}")
        print(f"Jumlah item: {len(proj_info['items'])} ({proj_info['total_files']} file)")
        for it in proj_info["items"]:
            print(f"  [{it['type']}] {it['name']} ({format_size(it['size'])}, {it['files']} files)")
        return 0

    if args.clean_capcut_projects:
        info = get_capcut_projects_info(args.capcut_projects_path)
        if not info["exists"]:
            print(f"Folder Projects CapCut tidak ditemukan di: {args.capcut_projects_path}")
            return 1
        if not info["items"]:
            print("Folder Projects CapCut sudah bersih (kosong).")
            return 0

        print(f"Ditemukan {len(info['items'])} item di Projects CapCut ({format_size(info['total_size'])}):")
        for it in info["items"]:
            print(f"  - [{it['type']}] {it['name']} ({format_size(it['size'])})")

        if not args.yes:
            answer = input(f"\nHAPUS SEMUA {len(info['items'])} folder/file di Projects CapCut? Ketik HAPUS untuk melanjutkan: ")
            if answer.strip() != "HAPUS":
                print("Dibatalkan; tidak ada perubahan.")
                return 0

        print("Sedang membersihkan folder Projects CapCut...")
        removed, failed_cnt, failed_list = clean_capcut_projects(args.capcut_projects_path)
        print(f"Selesai: {removed} item dihapus, {failed_cnt} gagal.")
        if failed_list:
            print("Item gagal:")
            for fp in failed_list:
                print(f"  - {fp}")
            return 1
        return 0

    if args.clean_capcut:
        info = get_capcut_cache_info(args.capcut_path)
        if not info["exists"]:
            print(f"Folder cache CapCut tidak ditemukan di: {args.capcut_path}")
            return 1
        if not info["items"]:
            print("Folder cache CapCut sudah bersih (kosong).")
            return 0

        print(f"Ditemukan {len(info['items'])} item cache CapCut ({format_size(info['total_size'])}):")
        for it in info["items"]:
            print(f"  - [{it['type']}] {it['name']} ({format_size(it['size'])})")

        if not args.yes:
            answer = input(f"\nHapus semua {len(info['items'])} folder/file cache CapCut di atas? Ketik HAPUS untuk melanjutkan: ")
            if answer.strip() != "HAPUS":
                print("Dibatalkan; tidak ada perubahan.")
                return 0

        print("Sedang membersihkan folder cache CapCut...")
        removed, failed_cnt, failed_list = clean_capcut_cache(args.capcut_path)
        print(f"Selesai: {removed} item dihapus, {failed_cnt} gagal.")
        if failed_list:
            print("Item gagal (kemungkinan sedang digunakan):")
            for fp in failed_list:
                print(f"  - {fp}")
            return 1
        return 0

    if args.panther_info:
        info = get_panther_info()
        print(f"Status C:\\Windows\\Panther: Exists={info['exists']}")
        print(f"Total ukuran Panther: {format_size(info['total_size'])}")
        print(f"Ukuran folder monitor: {format_size(info['monitor_size'])}")
        for fn, sz, is_mon in info["files"]:
            tag = "[MONITOR]" if is_mon else "[OTHER]"
            print(f"  {tag} {fn} ({format_size(sz)})")
        return 0

    if args.clean_panther:
        print("Membersihkan log di C:\\Windows\\Panther\\monitor...")
        ok, msg = clean_panther_logs(include_all_panther=True)
        if ok:
            print(f"BERHASIL: {msg}")
            return 0
        else:
            print(f"GAGAL: {msg}", file=sys.stderr)
            return 1

    if args.brave:
        args.browser = "brave"

    if args.path is None:
        args.path = BROWSER_PATHS.get(args.browser, DEFAULT_CHROME_USER_DATA)

    if args.delete and is_browser_running(args.browser):
        print(f"Mendeteksi proses {args.browser} sedang berjalan. Menghentikan proses...")
        ok, msg = kill_browser_process(args.browser)
        print(f"Hasil: {msg}")

    type_filter = None
    if args.type == "service-worker":
        type_filter = {TYPE_SERVICE_WORKER}
    elif args.type == "cache":
        type_filter = CHROME_CACHE_NAMES

    try:
        targets = find_targets(args.path, target_types=type_filter)
    except (FileNotFoundError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    type_desc = "Cache dan/atau Service Worker"
    if args.type == "service-worker":
        type_desc = "Service Worker"
    elif args.type == "cache":
        type_desc = "Cache"

    if not targets:
        print(f"Tidak ditemukan folder '{type_desc}'.")
        return 0

    print(f"Ditemukan {len(targets)} folder target ({type_desc}):")
    total_size = 0
    for target in targets:
        sz = get_dir_size(target)
        total_size += sz
        print(f"  [{categorize_target(target)}] ({format_size(sz)}) {target}")

    print(f"\nTotal ukuran: {format_size(total_size)}")

    if not args.delete:
        print("\nMode pratinjau: tidak ada yang dihapus. Gunakan --delete untuk menghapus.")
        return 0

    if not args.yes:
        answer = input(f"\nHapus semua {len(targets)} folder {type_desc} di atas? Ketik HAPUS untuk melanjutkan: ")
        if answer.strip() != "HAPUS":
            print("Dibatalkan; tidak ada perubahan.")
            return 0

    removed = 0
    failed = 0
    for target in targets:
        try:
            remove_target(target)
            print(f"Dihapus: {target}")
            removed += 1
        except (OSError, PermissionError) as exc:
            print(f"GAGAL: {exc}", file=sys.stderr)
            failed += 1

    print(f"\nSelesai: {removed} dihapus, {failed} gagal.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
