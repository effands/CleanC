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
                   is_dir=False, skipped=False)
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
