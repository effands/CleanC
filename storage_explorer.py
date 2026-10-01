"""Read-only folder size analysis, excluding symbolic links and junctions."""
import os
import stat
from pathlib import Path


def redirected(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def scan_directory(root, cancel, progress=None, on_row=None):
    root = Path(root)
    if any(redirected(p.lstat()) for p in (root, *root.parents)):
        raise ValueError('Redirected folders are excluded from analysis.')
    rows = []
    with os.scandir(root) as entries:
        children = list(entries)
    for index, child in enumerate(children, 1):
        if cancel.is_set():
            return None
        row = dict(path=Path(child.path), name=child.name, size=0, files=0, errors=0,
                   is_dir=False, skipped=False, has_subfolders=False)
        try:
            info = child.stat(follow_symlinks=False)
            row['is_dir'] = stat.S_ISDIR(info.st_mode)
            row['skipped'] = redirected(info)
            if row['skipped']:
                rows.append(row)
                if on_row:
                    on_row(dict(row))
                if progress:
                    progress(index, len(children), child.name)
                continue
            if not row['is_dir']:
                row['size'], row['files'] = info.st_size, 1
            else:
                pending = [Path(child.path)]
                while pending:
                    if cancel.is_set():
                        return None
                    folder = pending.pop()
                    try:
                        with os.scandir(folder) as descendants:
                            for entry in descendants:
                                if cancel.is_set():
                                    return None
                                try:
                                    info = entry.stat(follow_symlinks=False)
                                    if redirected(info):
                                        row['skipped'] = True
                                        continue
                                    if stat.S_ISDIR(info.st_mode):
                                        if folder == Path(child.path):
                                            row['has_subfolders'] = True
                                        pending.append(Path(entry.path))
                                    elif stat.S_ISREG(info.st_mode):
                                        row['size'] += info.st_size
                                        row['files'] += 1
                                except OSError:
                                    row['errors'] += 1
                    except OSError:
                        row['errors'] += 1
        except OSError:
            row['errors'] += 1
        rows.append(row)
        if on_row:
            on_row(dict(row))
        if progress:
            progress(index, len(children), child.name)
    return sorted(rows, key=lambda r: (-r['size'], r['name'].casefold()))


def recycle_item(path, current_directory):
    """Move a reviewed direct child to Windows Recycle Bin."""
    import ctypes
    from ctypes import wintypes
    path, parent = Path(path), Path(current_directory)
    if path.parent.resolve() != parent.resolve():
        raise ValueError('Target is outside the displayed directory.')
    protected = {Path.home().resolve(), Path.home().parent.resolve(),
                 (Path.home() / 'AppData').resolve()}
    for variable in ('WINDIR', 'ProgramFiles', 'ProgramFiles(x86)', 'ProgramData', 'LOCALAPPDATA', 'APPDATA'):
        if os.environ.get(variable):
            protected.add(Path(os.environ[variable]).resolve())
    protected.add((Path.home() / 'AppData/LocalLow').resolve())
    resolved = path.resolve()
    if resolved == Path(resolved.anchor) or resolved in protected:
        raise ValueError('This root/system directory cannot be deleted from Explorer.')
    if any(redirected(p.lstat()) for p in (path, *path.parents)):
        raise ValueError('Junctions and symbolic links cannot be deleted here.')
    if path.is_dir():
        def walk_error(exc):
            raise exc
        for folder, dirs, files in os.walk(path, followlinks=False, onerror=walk_error):
            if any(redirected((Path(folder) / name).lstat()) for name in dirs + files):
                raise ValueError('Folder contains a junction or symbolic link; deletion blocked.')
    class SHFILEOPSTRUCT(ctypes.Structure):
        _fields_ = [('hwnd', wintypes.HWND), ('wFunc', wintypes.UINT),
                    ('pFrom', wintypes.LPCWSTR), ('pTo', wintypes.LPCWSTR),
                    ('fFlags', wintypes.WORD), ('fAnyOperationsAborted', wintypes.BOOL),
                    ('hNameMappings', ctypes.c_void_p), ('lpszProgressTitle', wintypes.LPCWSTR)]
    source = ctypes.create_unicode_buffer(str(path.absolute()) + '\0\0')
    operation = SHFILEOPSTRUCT()
    operation.wFunc = 3  # FO_DELETE
    operation.pFrom = ctypes.cast(source, wintypes.LPCWSTR)
    operation.fFlags = 0x40 | 0x10 | 0x400  # ALLOWUNDO, NOCONFIRMATION, NOERRORUI
    shell = ctypes.windll.shell32
    shell.SHFileOperationW.argtypes = [ctypes.POINTER(SHFILEOPSTRUCT)]
    shell.SHFileOperationW.restype = ctypes.c_int
    code = shell.SHFileOperationW(ctypes.byref(operation))
    if code or operation.fAnyOperationsAborted or path.exists():
        raise OSError(f'Recycle Bin operation failed or cancelled ({code}): {path}')
