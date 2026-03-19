# STATE.md

> **Current Position**: Phase 34 Completed
> **Last Updated**: 2026-03-18

### Current Position
- **Phase**: 34 (Report & UI Refinement & Launcher)
- **Status**: Completed
- **Last Action**: Fixed Dividend PIL discrepancy, added Excel formulas, and resolved standalone launcher crash + download issues.

## Last Session Summary
- Fixed 1,112€ discrepancy in KAP Line 7 (PIL Dividends).
- Implemented **Standalone Launcher Fixes**:
  - Silent launch via `pythonw.exe`.
  - Redirected output to `os.devnull` to prevent windowless crashes.
  - Replaced browser downloads with a native **Tkinter Save Dialog** to fix filename issues in QtWebEngine.
- Verified all UI and report changes with user feedback.

## Next Steps
- [ ] Plan Phase 35.
