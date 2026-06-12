# AudioTrim Agent Notes

AudioTrim is a standalone Python/Tkinter tool. Keep it independent from Unity
projects; project repos should record developer-specific paths only in ignored
local override files, or rely on the machine-level install marker.

## Repository Boundaries

- Canonical remote: `git@github.com:onovich/AudioTrim.git`.
- Generic Windows install path: `%LOCALAPPDATA%\Programs\AudioTrim`.
- Machine install marker: `%APPDATA%\AudioTrim\install.json`.
- Do not commit `vendor/`, `output/`, `.preview/`, `audio_trim_config.json`, or
  `__pycache__/`.
- FFmpeg binaries live in `vendor/` locally and are configured by path in the
  GUI/config.

## Validation

Run these before committing tool changes:

```powershell
python -m py_compile audio_trim.py
python audio_trim.py --self-test
RunAudioTrim.ps1 -DryRun
```

For GUI work, launch `RunAudioTrim.cmd` manually and smoke test scanning,
waveform preview, play/loop, preview trim, and export.

## Project Integration

Automation such as `audio-sfx-workflow` should resolve AudioTrim in this order:

1. project-local tool copy, if intentionally embedded;
2. ignored project override such as `.codex/audio-trim.local.json`;
3. machine marker `%APPDATA%\AudioTrim\install.json`;
4. generic default install path `%LOCALAPPDATA%\Programs\AudioTrim`;
5. install from the canonical remote.

When adding a feature for a game workflow, update this repository first, push it,
then update consuming project code only if the integration contract changed.
Do not commit personal absolute paths into consuming project repositories.