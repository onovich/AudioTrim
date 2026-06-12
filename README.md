# AudioTrim

Batch trims silent heads and tails from audio files. The tool is independent
from Unity and is intended for preparing SFX assets before importing them into a
game project.

## Setup

1. Install Python 3.10+.
2. Download a Windows FFmpeg build.
3. Put `ffmpeg.exe` and `ffprobe.exe` in `vendor/` next to `audio_trim.py`.
   When AudioTrim is embedded in a project, this path is commonly
   `Tools/AudioTrim/vendor/`.
4. Double-click `RunAudioTrim.cmd`.

The `vendor/` folder is intentionally ignored by git, so large FFmpeg binaries
are not committed to the repository.

## Distribution

Recommended per-user install path on Windows:

```text
%LOCALAPPDATA%\Programs\AudioTrim
```

Machine-level discovery can use either:

- `AUDIOTRIM_HOME`, pointing at the folder that contains `audio_trim.py`;
- `%APPDATA%\AudioTrim\install.json`, with an `install_path` field.

Project-local copies should still win over a machine install. That lets a game
project pin or patch AudioTrim without changing the user's global tool.

## Workflow

The GUI defaults to the current system language and can be switched between
Chinese and English from the language picker in the title area.

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
  for preview and export. It defaults to `Yes` in normal trim mode.
- In `Keep first segment only` mode, `Edge Trim` displays `Auto`: the tool
  normalizes the leading/trailing edge before finding the first segment, so the
  per-row edge switch is intentionally disabled. This keeps the result aligned
  with the user's intent: output only the first audible segment.
- `Fade in` / `Fade out`: Adds a small envelope to avoid harsh cuts. In first
  segment mode, fade-out is forced on if it is not already enabled. Duration and
  curve controls are shown only after the corresponding fade option is enabled.
- `Curve`: Curves are shown as small function previews next to the selector
  instead of text ramps, so the envelope shape is visible before export.

- `Play Selected File`: Converts the selected listed audio to a temporary WAV
  and plays it, so OGG/MP3 files can be auditioned from the list. Use `Loop`
  beside it for repeated playback.
- `Waveform Review`: Shows a downsampled peak waveform for the selected listed
  file. It includes a simple time axis and a red playhead while auditioning.
  This is meant for fast visual QA, not sample-accurate editing.

## CLI Examples

Dry-run all OGG/MP3 files from a standalone checkout:

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

If AudioTrim is embedded under `Tools/AudioTrim`, prefix the script path with
that folder. Or use the launcher:

```bat
RunAudioTrim.cmd
```
