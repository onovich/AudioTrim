# AudioTrim Agent Notes

AudioTrim is a standalone Python/Tkinter tool. Keep it independent from Unity
projects; project repos should record paths to AudioTrim instead of carrying the
source unless they deliberately need a pinned project-local copy.

## Repository Boundaries

- Canonical remote: `git@github.com:onovich/AudioTrim.git`.
- Local development checkout on this machine: `D:\LabProjects\AudioTrim`.
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

1. project-local tool copy, if present;
2. project pointer such as `.codex/audio-trim.json`;
3. machine marker `%APPDATA%\AudioTrim\install.json`;
4. generic default install path;
5. install from the canonical remote.

When adding a feature for a game workflow, update this repository first, push it,
then update the consuming project pointer or skill notes only if the integration
contract changed.
