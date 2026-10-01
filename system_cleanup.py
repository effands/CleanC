"""Conservative, file-only cleanup rules. Never traverse reparse points."""
import os
import stat
import time
from pathlib import Path

from clean_chrome_service_workers import LOCAL_APPDATA, ROAMING_APPDATA, DEFAULT_CHROME_USER_DATA

IX_BROWSER_DATA = ROAMING_APPDATA / 'ixBrowser' / 'Browser Data'


def ix_protected(path, root):
    return any(part.casefold() == 'extension' for part in path.relative_to(root).parts)


def scan_ixbrowser(root=None):
    root = root or IX_BROWSER_DATA
    item = dict(group='ixBrowser', name='Browser Data folders (extension protected)', roots=[root],
                files=[], directories=[], total_size=0, errors=[], recommended=False)
    try:
        if not root.exists() or not safe_path(root):
            return item
        def onerror(exc):
            item['errors'].append(str(exc))
        for child in root.iterdir():
            if ix_protected(child, root) or not safe_path(child) or not child.is_dir():
                continue
            for folder, dirs, files in os.walk(child, followlinks=False, onerror=onerror):
                directory = Path(folder)
                item['directories'].append(directory)
                dirs[:] = [d for d in dirs if not ix_protected(directory / d, root) and not linked(directory / d)]
                for name in files:
                    p = directory / name
                    try:
                        if not ix_protected(p, root) and not linked(p):
                            item['total_size'] += p.stat().st_size
                            item['files'].append(p)
                    except OSError as exc:
                        item['errors'].append(str(exc))
    except OSError as exc:
        item['errors'].append(str(exc))
    return item


def ixbrowser_running():
    import subprocess
    result = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True,
                            check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return any('ixbrowser' in line.casefold().split(',')[0] for line in result.stdout.splitlines())


def clean_ixbrowser(snapshot, root=None):
    root = root or IX_BROWSER_DATA
    fresh = scan_ixbrowser(root)
    allowed = set(fresh['files'])
    removed = freed = 0
    errors = list(fresh['errors'])
    for p in snapshot['files']:
        try:
            if p not in allowed or ix_protected(p, root) or not safe_path(p):
                continue
            size = p.stat().st_size
            p.unlink()
            removed += 1
            freed += size
        except OSError as exc:
            errors.append(f'{p}: {exc}')
    allowed_dirs = set(fresh['directories'])
    for p in sorted(snapshot.get('directories', []), key=lambda p: len(p.parts), reverse=True):
        try:
            if p in allowed_dirs and not ix_protected(p, root) and safe_path(p) and not any(p.iterdir()):
                p.rmdir()
        except OSError as exc:
            errors.append(f'{p}: {exc}')
    return removed, freed, errors


def rules():
    win = Path(os.environ.get('WINDIR', r'C:\Windows'))
    profiles = []
    if DEFAULT_CHROME_USER_DATA.is_dir():
        profiles = [p for p in DEFAULT_CHROME_USER_DATA.iterdir()
                    if p.name == 'Default' or p.name.startswith('Profile ')]
    return {
        'temp': ('System', 'Temporary Files', [Path(os.environ.get('TEMP', str(LOCAL_APPDATA / 'Temp'))), win / 'Temp'], '*', True),
        'dumps': ('System', 'Memory Dumps', [win / 'Minidump', LOCAL_APPDATA / 'CrashDumps', win / 'MEMORY.DMP'], '*.dmp', False),
        'logs': ('System', 'Windows Log Files', [win / 'Logs'], '*.log', False),
        'web': ('System', 'Windows Web Cache', [LOCAL_APPDATA / 'Microsoft/Windows/INetCache'], '*', True),
        'thumb': ('Windows', 'Thumbnail Cache', [LOCAL_APPDATA / 'Microsoft/Windows/Explorer'], 'thumbcache_*.db', True),
        'rdp': ('Windows', 'Remote Desktop Cache', [LOCAL_APPDATA / 'Microsoft/Terminal Server Client/Cache'], '*', True),
        'chrome': ('Google Chrome', 'Internet Cache', [p / n for p in profiles for n in ('Cache', 'Code Cache', 'GPUCache')], '*', True),
        'metrics': ('Google Chrome', 'Metrics Temp Files', [DEFAULT_CHROME_USER_DATA / 'BrowserMetrics'], '*.pma', True),
    }


def linked(path):
    s = path.lstat()
    return path.is_symlink() or bool(getattr(s, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def safe_path(path):
    return not any(linked(p) for p in (path, *path.parents))


def candidates(root, pattern, errors):
    try:
        if not root.exists() or not safe_path(root):
            return
        if root.is_file():
            if root.match(pattern):
                yield root
            return
        def walk_error(exc):
            errors.append(str(exc))
        for folder, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
            dirs[:] = [d for d in dirs if not linked(Path(folder) / d)]
            for name in files:
                p = Path(folder) / name
                if p.match(pattern) and not linked(p):
                    yield p
    except OSError as exc:
        errors.append(str(exc))


def scan():
    result = {}
    seen = set()
    for key, (group, name, roots, pattern, recommended) in rules().items():
        item = dict(group=group, name=name, roots=roots, files=[], total_size=0,
                    errors=[], recommended=recommended)
        for root in roots:
            for p in candidates(root, pattern, item['errors']):
                try:
                    identity = str(p.resolve()).casefold()
                    s = p.stat()
                    # Recently modified temporary files may belong to active installers.
                    if identity in seen or (key == 'temp' and time.time() - s.st_mtime < 86400):
                        continue
                    seen.add(identity)
                    item['files'].append(p)
                    item['total_size'] += s.st_size
                except OSError as exc:
                    item['errors'].append(str(exc))
        result[key] = item
    result['ixbrowser'] = scan_ixbrowser()
    return result


def clean(key, snapshot):
    """Only delete reviewed files that remain eligible in a fresh scan."""
    if key == 'ixbrowser':
        if ixbrowser_running():
            raise RuntimeError('Close ixBrowser before deleting Browser Data folders.')
        return clean_ixbrowser(snapshot)
    fresh = scan()[key]
    allowed = set(fresh['files'])
    removed = freed = 0
    errors = list(fresh['errors'])
    for p in snapshot['files']:
        try:
            if p not in allowed or not safe_path(p):
                continue
            size = p.stat().st_size
            p.unlink()
            removed += 1
            freed += size
        except OSError as exc:
            errors.append(f'{p}: {exc}')
    return removed, freed, errors
