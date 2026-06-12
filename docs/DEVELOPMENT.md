# Development Notes

## Architecture

`audio_trim.py` intentionally remains a single-file Python/Tkinter application
for easy distribution and quick patching during SFX production. Keep heavy
runtime dependencies out of the repository.

Core areas:

- scan and task modeling for source files;
- silence/segment planning;
- FFmpeg/ffprobe command construction;
- Tkinter UI and bilingual text;
- waveform extraction, playback, loop, and playhead display;
- self-tests for command planning and edge cases.

## Local State

Local runtime state is ignored by git:

- `vendor/`: FFmpeg executables;
- `output/`: batch workspaces, originals, processed review files;
- `.preview/`: temporary preview WAV files;
- `audio_trim_config.json`: GUI preferences and last paths.

When moving AudioTrim between machines, copy `vendor/` only if the FFmpeg build
license/distribution choice permits it. Otherwise reinstall FFmpeg locally.

## Release Model

Current release model is source-first:

1. commit and push to `git@github.com:onovich/AudioTrim.git`;
2. users clone or update a checkout;
3. users provide FFmpeg in `vendor/` or configure paths.

Future options:

- GitHub Release zip with source, launchers, README, and `.gitignore`;
- PyInstaller Windows build for non-developers;
- optional installer that writes `%APPDATA%\AudioTrim\install.json`.

Do not bundle FFmpeg in a release unless the licensing and binary provenance are
explicitly reviewed.

## Integration Contract

The stable executable entrypoint is:

```powershell
python <AudioTrimRoot>\audio_trim.py --gui
python <AudioTrimRoot>\audio_trim.py --self-test
```

Consumers should first read `%APPDATA%\AudioTrim\install.json`, then fall back
to `%LOCALAPPDATA%\Programs\AudioTrim`. A marker should contain at least:

```json
{
  "install_path": "%LOCALAPPDATA%\\Programs\\AudioTrim",
  "audio_trim_py": "%LOCALAPPDATA%\\Programs\\AudioTrim\\audio_trim.py",
  "repo_url": "git@github.com:onovich/AudioTrim.git"
}
```

A consuming project may also keep an ignored local override such as
`.codex/audio-trim.local.json` for a developer's personal checkout. Do not commit
that file unless it contains only portable, non-user-specific values.

If a game project needs custom behavior, prefer changing AudioTrim here and
upstreaming it. Only embed a project-local copy when the project must pin a
non-upstream variant.