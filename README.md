# AudioTrim

AudioTrim is a standalone Python/Tkinter tool for batch-trimming game SFX. It
can trim silent heads/tails, keep only the first audible segment, keep a source
percentage, add fades with selectable curves, preview results, and inspect
waveforms before export.

It is independent from Unity. Game projects should either keep a project-local
copy when they deliberately need to pin/customize AudioTrim, or rely on the
machine-level install marker so multiple projects can share one installation.
Do not commit developer-specific absolute paths into consuming projects.

## Setup

1. Install Python 3.10+.
2. Download a Windows FFmpeg build.
3. Put `ffmpeg.exe` and `ffprobe.exe` in `vendor/` next to `audio_trim.py`, or
   choose their paths in the GUI.
4. Double-click `RunAudioTrim.cmd`, or run `python audio_trim.py --gui`.

The following folders/files are local-only and intentionally ignored by git:

- `vendor/`
- `output/`
- `.preview/`
- `audio_trim_config.json`
- `__pycache__/`

## Distribution And Discovery

Canonical source repo:

```text
git@github.com:onovich/AudioTrim.git
```

Recommended generic per-user install path on Windows:

```text
%LOCALAPPDATA%\Programs\AudioTrim
```

Record the active machine install in:

```text
%APPDATA%\AudioTrim\install.json
```

A typical user install marker:

```json
{
  "install_path": "%LOCALAPPDATA%\\Programs\\AudioTrim",
  "audio_trim_py": "%LOCALAPPDATA%\\Programs\\AudioTrim\\audio_trim.py",
  "repo_url": "git@github.com:onovich/AudioTrim.git",
  "distribution": "git",
  "commit": "<short-sha>"
}
```

Developers may keep a source checkout in any stable local folder. That personal
path should be recorded in the machine marker or in a consuming project's
ignored `.codex/audio-trim.local.json`, not in a committed project config.

## Workflow

The GUI defaults to the current system language and can be switched between
Chinese and English from the language picker.

1. Choose an input directory. The task list scans automatically.
2. Choose an output directory if the default sibling output folder is not what
   you want.
3. Review the `Absolute Silence` column. In `Trim head/tail silence` mode, rows
   with exact silent heads or tails default to `Edge Trim = Yes`.
4. If a normal trim row should keep its edge silence, select it and click
   `Toggle Edge Trim`.
5. Select a row and click `Preview Selected` to hear the processed result.
6. Click `Play Selected File` to audition the listed source file directly. Turn
   on `Loop` beside the play button for repeated playback while checking the
   waveform.
7. Toggle rows on/off.
8. Click `Process Checked` to write final `.ogg` files.

Outputs keep the input relative folder layout and are always encoded as OGG
Vorbis. Name collisions are resolved by adding a suffix.

## Important Options

- `Threshold dB`: Audio below this level is treated as silence. A useful first
  pass for game SFX is around `-45dB`.
- `Window ms`: Detection window for silence scanning. `20ms` is a conservative
  default for short sound effects.
- `Trim head/tail silence`: Removes only leading and trailing silence while
  keeping quiet gaps in the middle.
- `Keep first segment only`: After trimming the head, stops at the first quiet
  gap that is at least `Segment gap ms`. This is useful for assets like a page
  flip followed by silence and another page flip.
- `Keep first percent`: Keeps the first percentage of the source, useful for
  quick truncation such as keeping the first quarter of a signature sound.
- `Absolute Silence`: Scan-time report for exact zero-sample silence at the
  head or tail. It is informational and meant for review before exporting.
- `Edge Trim`: Per-row switch that controls whether head/tail trimming is used
  for preview and export.
- `Fade in` / `Fade out`: Adds a small envelope to avoid harsh cuts. Duration
  and curve controls are shown only after the corresponding fade option is
  enabled.
- `Waveform Review`: Shows a downsampled peak waveform with a simple time axis
  and playhead while auditioning.

## CLI Examples

Dry-run all OGG/MP3 files:

```bat
python audio_trim.py --input D:\SFX --dry-run
```

Convert to OGG without trimming edges:

```bat
python audio_trim.py --input D:\SFX --no-edge-trim
```

Keep only the first segment and fade out over 20ms:

```bat
python audio_trim.py --input D:\SFX --mode first_segment --segment-gap-ms 120 --fade-out-ms 20 --fade-out-curve cub
```

Keep the first quarter and add a very short fade-out:

```bat
python audio_trim.py --input D:\SFX --mode keep_ratio --keep-ratio-percent 25 --fade-out-ms 8 --fade-out-curve cub
```

Run lightweight internal tests:

```bat
python audio_trim.py --self-test
```

Or use the launcher:

```bat
RunAudioTrim.cmd
RunAudioTrim.ps1 -DryRun
RunAudioTrim.ps1 -SelfTest
```