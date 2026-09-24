# CleanC

![CleanC](CleanC.png)

**CleanC** is a focused Windows storage cleaner for browser caches, Service Worker data, CapCut leftovers, developer caches, and selected Windows logs.

## Highlights

- Chrome-first browser cleaning with support for Brave, Edge, and Firefox
- Safe cache targets: Cache, Code Cache, GPUCache, DawnCache, GrShaderCache, and ShaderCache
- Service Worker cleanup across browser profiles
- CapCut cache, project, and old-version cleanup
- Developer cache cleanup for Playwright, npm, pip, pnpm, and Node-Gyp
- Windows cleanup targets for temporary files, thumbnails, logs, and web cache
- Confirmation prompts, process checks, locked-file reporting, and freed-space statistics
- Modern dark UI with a subtle nebula accent and transparent CleanC branding

## Download

The Windows portable executable is available in the [v1.0.0 release](https://github.com/effands/CleanC/releases/tag/v1.0.0).

Run `CleanC.exe` directly. No installation is required.

## Development

```powershell
python -m py_compile clean_chrome_service_workers.py service_worker_cleaner_gui.py
python service_worker_cleaner_gui.py
```

Build the Windows executable with PyInstaller:

```powershell
pyinstaller --clean --noconfirm CleanC.spec
```

The output is written to `dist/CleanC.exe`.

## CLI examples

```powershell
python clean_chrome_service_workers.py --browser chrome --type cache
python clean_chrome_service_workers.py --windows-info
python clean_chrome_service_workers.py --clean-windows thumbnail-cache
```

## Safety

CleanC targets disposable cache and log data. Browser history, bookmarks, passwords, preferences, and CapCut project drafts are not silently removed. Close the relevant application before cleaning for the best result. Some Windows log files require Administrator permissions or may be skipped when locked by the operating system.

## License

This project is provided for personal and educational use. Review the target list before confirming a cleanup operation.
