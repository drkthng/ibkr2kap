# Debug Session: Download Button in Webview

## Symptom
When opening the app with the batch-file (not in the browser) then the creation of the excel file does not work. when I click the button, the window to set up the place where it should be saved does not open up (as it does when doing it in the browser).

**When:** Clicking an `st.download_button` in the pywebview container (`launcher.py`).
**Expected:** The native OS save file dialog should trigger, or the file should be saved in the default Downloads folder.
**Actual:** Nothing happens in the UI; no save dialog appears.

## Hypotheses

| # | Hypothesis | Likelihood | Status |
|---|------------|------------|--------|
| 1 | `pywebview` with `gui='qt'` does not support downloads natively without custom signals | 70% | UNTESTED |
| 2 | `pywebview` supports downloads but requires an explicit parameter / setting like `allow_downloads=True` | 20% | UNTESTED |
| 3 | Switching the GUI engine to `edgechromium` automatically solves it | 80% | UNTESTED |

## Attempts

### Attempt 1
**Testing:** H2 — `pywebview` supports downloads but requires an explicit parameter / setting like `allow_downloads=True`
**Action:** Added `webview.settings['ALLOW_DOWNLOADS'] = True` to `src/ibkr_tax/launcher.py`.
**Result:** Download button fixed (save dialog appears), but filename was cryptic when using Qt engine.
**Conclusion:** Partial success; engine change required for full fix.

### Attempt 2
**Testing:** H3 — Switching the GUI engine to EdgeChromium (WebView2)
**Action:** Removed forced `gui='qt'` in `launcher.py` to allow `pywebview` to use the default `webview2` backend on Windows.
**Result:** Resulted in application crash upon startup.

### Attempt 3
**Testing:** H4 — `pythonw.exe` crash due to `sys.stdout` being `None`
**Action:** Added check in `launcher.py` to redirect `sys.stdout` and `sys.stderr` to `os.devnull` when running windowless.
**Result:** Code added but application still crashed! Logging exception to `launcher_crash.log` revealed `WebViewException: You must have pythonnet installed in order to use pywebview.`
**Conclusion:** Crash was actually caused by missing dependency for the Edge Chromium backend.

### Attempt 4
**Testing:** H5 — Install `pythonnet` to use default `webview2` engine
**Action:** Added `pythonnet>=3.0.3` to `pyproject.toml` and installed it via pip.
**Result:** Pythonnet failed to install because no prebuilt wheels exist for Python 3.14, and local build failed.
**Conclusion:** Cannot use `webview2` on this environment.

### Attempt 6
**Testing:** H7 — Streamlit Static File Serving
**Action:** The Data URI caused QtWebEngine to native crash! Replaced the download mechanism entirely. Added `--server.enableStaticServing=true` to `launcher.py` and modified `app.py` to write the `.xlsx` into a `static/` directory, exposing it via `/app/static/{fname}`.
**Result:** Created 2 KB `.tmp` files. The `static/` folder was being created in `src/static/` but Streamlit expects it in the current working directory (`d:\Antigravity\IBKR2KAP\static`). This resulted in a 404 error, crashing the download.
**Conclusion:** Fixed the path using `os.path.dirname(os.path.dirname(__file__))` to map to the project root.

### Attempt 7
**Testing:** H8 — Complete Download Bypass via Native Tkinter
**Action:** Since QtWebEngine drops `.tmp` files on any interaction, we removed the Streamlit download link entirely. Replaced it with a standard Streamlit button that invokes Python's native `tkinter.filedialog.asksaveasfilename()`.
**Result:** TBD
**Conclusion:** TBD

## Resolution

**Root Cause:** 
1. `pythonw.exe` crashes standard Python print statements because `sys.stdout` is `None` (Attempt 3).
2. Edge Chromium (`webview2`) requires `pythonnet` which fails to compile on Python 3.14.
3. QtWebEngine handles URL downloads poorly dropping `.tmp` files.

**Fix:**
1. Redirected `sys.stdout/stderr` to `os.devnull` in `launcher.py`.
2. Reverted the `pywebview` engine to natively supported `gui='qt'`.
3. In `src/app.py`, completely bypassed the browser download manager by using a native Python (`tkinter`) save dialog to write the exporter buffer straight to the hard drive on button click.
4. Preserved `pythonw.exe` in `launch_windows.bat` so the batch file hides correctly.
**Verified:** TBD
**Regression Check:** TBD
