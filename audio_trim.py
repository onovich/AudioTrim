# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import locale
import math
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import (
    BooleanVar,
    Canvas,
    DoubleVar,
    IntVar,
    StringVar,
    Tk,
    filedialog,
    messagebox,
    scrolledtext,
)
from tkinter import ttk


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "audio_trim_config.json"
PREVIEW_DIR = SCRIPT_DIR / ".preview"
ANALYSIS_SAMPLE_RATE = 48000
ANALYSIS_CHANNELS = 2
WAVEFORM_SAMPLE_RATE = 8000
WAVEFORM_CHANNELS = 1

MODE_TRIM_EDGES = "trim_edges"
MODE_FIRST_SEGMENT = "first_segment"
MODE_KEEP_RATIO = "keep_ratio"

MODE_LABELS = {
    MODE_TRIM_EDGES: "Trim head/tail silence",
    MODE_FIRST_SEGMENT: "Keep first segment only",
    MODE_KEEP_RATIO: "Keep first percent",
}

MODE_BY_LABEL = {label: mode for mode, label in MODE_LABELS.items()}


@dataclass(frozen=True)
class CurveOption:
    label: str
    ffmpeg_name: str


CURVE_OPTIONS = (
    CurveOption("Linear    ▁▂▄▆█", "tri"),
    CurveOption("SinIn     ▁▁▂▄█", "cub"),
    CurveOption("SinOut    ▂▄▆▇█", "squ"),
    CurveOption("S-Curve   ▁▂▄▆█", "desi"),
    CurveOption("Log       ▃▅▆▇█", "log"),
)

CURVE_BY_LABEL = {curve.label: curve for curve in CURVE_OPTIONS}
CURVE_BY_FFMPEG = {curve.ffmpeg_name: curve for curve in CURVE_OPTIONS}

# Clean runtime curve definitions. The old text-ramp labels above are kept only
# for backwards-compatible config loading in older working copies.
CURVE_OPTIONS = (
    CurveOption("linear", "tri"),
    CurveOption("ease_in", "cub"),
    CurveOption("ease_out", "squ"),
    CurveOption("smooth", "desi"),
    CurveOption("log", "log"),
)
CURVE_BY_KEY = {curve.label: curve for curve in CURVE_OPTIONS}
CURVE_BY_LABEL = CURVE_BY_KEY
CURVE_BY_FFMPEG = {curve.ffmpeg_name: curve for curve in CURVE_OPTIONS}

LANGUAGE_LABELS = {
    "zh": "中文",
    "en": "English",
}

I18N = {
    "en": {
        "app_title": "AudioTrim",
        "app_subtitle": "Batch trim, preview, and review game SFX.",
        "language": "Language",
        "source": "Source",
        "input": "Input",
        "output": "Output",
        "browse": "Browse",
        "default": "Default",
        "tooling": "Tooling",
        "ffmpeg": "FFmpeg",
        "ffprobe": "FFprobe",
        "processing": "Processing",
        "formats": "Formats",
        "recursive": "Recursive",
        "threshold": "Threshold dB",
        "window": "Window ms",
        "ogg_quality": "OGG quality",
        "mode": "Mode",
        "segment_gap": "Segment gap ms",
        "keep_percent": "Keep %",
        "fade_in": "Fade in",
        "fade_out": "Fade out",
        "duration_ms": "Duration ms",
        "curve": "Curve",
        "tasks": "Tasks",
        "use": "Use",
        "edge_trim": "Edge Trim",
        "absolute_silence": "Absolute Silence",
        "file": "File",
        "task_mode": "Mode",
        "target": "Target",
        "status": "Status",
        "waveform_review": "Waveform Review",
        "scan": "Scan Input",
        "toggle_selected": "Toggle",
        "toggle_edge_trim": "Edge Trim",
        "select_all": "All",
        "select_none": "None",
        "play_selected_file": "Play",
        "loop_playback": "Loop",
        "preview_selected": "Preview Trim",
        "stop_preview": "Stop",
        "process_checked": "Export Checked",
        "open_output": "Open Output",
        "mode_trim_edges": "Trim head/tail",
        "mode_first_segment": "First segment only",
        "mode_keep_ratio": "First percent",
        "curve_linear": "Linear",
        "curve_ease_in": "Ease In",
        "curve_ease_out": "Ease Out",
        "curve_smooth": "S-Curve",
        "curve_log": "Log",
        "ready_hint": "Ready. Choose an input folder; the list scans automatically. Use Play or Preview Trim to audition.",
        "select_waveform": "Select a row to draw its waveform.",
        "no_audio_found": "No audio files found in the output directory.",
        "scan_done": "Scanned {count} task(s).",
        "needs_ffmpeg": "ffmpeg.exe is required.",
        "waveform_loading": "Loading waveform: {name}",
        "waveform_status": "{name}  |  {duration:.3f}s  |  press Play to audition",
        "busy_task": "A task is already running.",
        "busy_play": "A file is already being prepared for playback.",
        "no_selection_preview": "Select one task to preview.",
        "no_selection_play": "Select one audio file to play.",
        "no_tasks": "No checked tasks to process.",
        "missing_output": "Output directory does not exist yet.",
        "missing_input": "Choose an input directory before scanning.",
        "preview_stopped": "Preview stopped.",
        "edge_auto": "Edge trim is automatic in first-segment mode.",
        "yes": "Yes",
        "no": "No",
        "auto": "Auto",
    },
    "zh": {
        "app_title": "AudioTrim",
        "app_subtitle": "批量剪辑、试听和验收游戏音效。",
        "language": "语言",
        "source": "来源",
        "input": "输入",
        "output": "输出",
        "browse": "选择",
        "default": "默认",
        "tooling": "工具",
        "ffmpeg": "FFmpeg",
        "ffprobe": "FFprobe",
        "processing": "处理",
        "formats": "格式",
        "recursive": "递归",
        "threshold": "阈值 dB",
        "window": "窗口 ms",
        "ogg_quality": "OGG 质量",
        "mode": "模式",
        "segment_gap": "段间静音 ms",
        "keep_percent": "保留 %",
        "fade_in": "淡入",
        "fade_out": "淡出",
        "duration_ms": "时长 ms",
        "curve": "曲线",
        "tasks": "任务",
        "use": "启用",
        "edge_trim": "裁边",
        "absolute_silence": "绝对静帧",
        "file": "文件",
        "task_mode": "模式",
        "target": "目标",
        "status": "状态",
        "waveform_review": "波形验收",
        "scan": "扫描输入",
        "toggle_selected": "切换",
        "toggle_edge_trim": "裁边",
        "select_all": "全选",
        "select_none": "全不选",
        "play_selected_file": "播放",
        "loop_playback": "循环",
        "preview_selected": "预览剪辑",
        "stop_preview": "停止",
        "process_checked": "导出勾选",
        "open_output": "打开输出",
        "mode_trim_edges": "裁头尾",
        "mode_first_segment": "只取第一段",
        "mode_keep_ratio": "保留前百分比",
        "curve_linear": "线性",
        "curve_ease_in": "缓入",
        "curve_ease_out": "缓出",
        "curve_smooth": "S 曲线",
        "curve_log": "Log",
        "ready_hint": "就绪。选择输入目录后会自动扫描；用“播放”或“预览剪辑”试听。",
        "select_waveform": "选择一行以显示波形。",
        "no_audio_found": "输出目录中没有找到音频文件。",
        "scan_done": "已扫描 {count} 个任务。",
        "needs_ffmpeg": "需要 ffmpeg.exe。",
        "waveform_loading": "正在读取波形：{name}",
        "waveform_status": "{name}  |  {duration:.3f}s  |  点击播放试听",
        "busy_task": "已有任务正在运行。",
        "busy_play": "正在准备另一个文件播放。",
        "no_selection_preview": "请选择一个任务进行预览。",
        "no_selection_play": "请选择一个音频文件播放。",
        "no_tasks": "没有勾选的任务。",
        "missing_output": "输出目录尚不存在。",
        "missing_input": "请先选择输入目录再扫描。",
        "preview_stopped": "已停止播放。",
        "edge_auto": "只取第一段模式下裁边会自动开启。",
        "yes": "是",
        "no": "否",
        "auto": "自动",
    },
}


def detect_system_language() -> str:
    language = ""
    try:
        language = locale.getlocale()[0] or ""
    except ValueError:
        language = ""
    if not language:
        try:
            language = locale.getdefaultlocale()[0] or ""
        except Exception:
            language = ""
    return "zh" if language.lower().startswith("zh") else "en"


def language_from_label(label: str) -> str:
    for language, language_label in LANGUAGE_LABELS.items():
        if language_label == label:
            return language
    return "en"


@dataclass
class TrimConfig:
    input_dir: Path
    output_dir: Path
    ffmpeg_path: Path
    ffprobe_path: Path
    recursive: bool
    extensions: tuple[str, ...]
    threshold_db: float
    silence_window_ms: int
    mode: str
    segment_gap_ms: int
    keep_ratio_percent: float
    fade_in_enabled: bool
    fade_in_ms: int
    fade_in_curve: str
    fade_out_enabled: bool
    fade_out_ms: int
    fade_out_curve: str
    ogg_quality: int


@dataclass
class EdgeSilenceAnalysis:
    head_ms: float = 0.0
    tail_ms: float = 0.0
    status: str = "Not analyzed"


@dataclass
class AudioTask:
    source: Path
    output: Path
    relative_source: Path
    edge_trim_enabled: bool = True
    edge_analysis: EdgeSilenceAnalysis = field(default_factory=EdgeSilenceAnalysis)
    enabled: bool = True
    status: str = "Pending"


class AudioTrimError(RuntimeError):
    pass


def find_tool(name: str) -> Path:
    executable = f"{name}.exe" if os.name == "nt" else name
    candidates = (
        SCRIPT_DIR / "vendor" / executable,
        SCRIPT_DIR / "vendor" / "bin" / executable,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate

    from_path = shutil.which(name) or shutil.which(executable)
    if from_path:
        return Path(from_path)
    return candidates[0]


def normalize_extension(ext: str) -> str:
    ext = ext.strip().lower()
    if not ext:
        return ext
    return ext if ext.startswith(".") else f".{ext}"


def parse_extensions(value: str) -> tuple[str, ...]:
    extensions = tuple(
        ext
        for ext in (normalize_extension(part) for part in value.split(","))
        if ext
    )
    if not extensions:
        raise AudioTrimError("At least one input extension is required.")
    return extensions


def seconds_from_ms(ms: int | float) -> str:
    seconds = max(0.0, float(ms) / 1000.0)
    text = f"{seconds:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def threshold_text(threshold_db: float) -> str:
    return f"{threshold_db:g}dB"


def default_output_dir(input_dir: Path) -> Path:
    if not input_dir:
        return Path()
    return input_dir.with_name(f"{input_dir.name}_trimmed_ogg")


def path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def start_trim_filter(config: TrimConfig) -> str:
    window = seconds_from_ms(config.silence_window_ms)
    threshold = threshold_text(config.threshold_db)
    return (
        "silenceremove="
        "start_periods=1:"
        f"start_threshold={threshold}:"
        "start_silence=0:"
        "detection=rms:"
        f"window={window}"
    )


def first_segment_stop_filter(config: TrimConfig) -> str:
    gap = seconds_from_ms(config.segment_gap_ms)
    window = seconds_from_ms(config.silence_window_ms)
    threshold = threshold_text(config.threshold_db)
    return (
        "silenceremove="
        "stop_periods=1:"
        f"stop_duration={gap}:"
        f"stop_threshold={threshold}:"
        "stop_silence=0:"
        "detection=rms:"
        f"window={window}"
    )


def normalize_config_for_mode(config: TrimConfig) -> TrimConfig:
    if config.mode != MODE_FIRST_SEGMENT:
        return config
    fade_out_ms = config.fade_out_ms if config.fade_out_ms > 0 else 10
    return TrimConfig(
        input_dir=config.input_dir,
        output_dir=config.output_dir,
        ffmpeg_path=config.ffmpeg_path,
        ffprobe_path=config.ffprobe_path,
        recursive=config.recursive,
        extensions=config.extensions,
        threshold_db=config.threshold_db,
        silence_window_ms=config.silence_window_ms,
        mode=config.mode,
        segment_gap_ms=config.segment_gap_ms,
        keep_ratio_percent=config.keep_ratio_percent,
        fade_in_enabled=config.fade_in_enabled,
        fade_in_ms=config.fade_in_ms,
        fade_in_curve=config.fade_in_curve,
        fade_out_enabled=True,
        fade_out_ms=fade_out_ms,
        fade_out_curve=config.fade_out_curve,
        ogg_quality=config.ogg_quality,
    )


def build_filtergraph(
    config: TrimConfig,
    task: AudioTask | None = None,
    source_duration_seconds: float | None = None,
) -> str:
    config = normalize_config_for_mode(config)
    edge_trim_enabled = True if config.mode == MODE_FIRST_SEGMENT else (
        task.edge_trim_enabled if task else True
    )
    filters: list[str] = []

    if edge_trim_enabled:
        filters.append(start_trim_filter(config))

    if config.mode == MODE_FIRST_SEGMENT:
        filters.append(first_segment_stop_filter(config))
        if edge_trim_enabled:
            filters.extend(("areverse", start_trim_filter(config), "areverse"))
    elif config.mode == MODE_KEEP_RATIO:
        keep_duration = resolve_keep_ratio_duration(config, task, source_duration_seconds)
        filters.append(f"atrim=start=0:end={seconds_from_float(keep_duration)}")
        filters.append("asetpts=PTS-STARTPTS")
    else:
        if edge_trim_enabled:
            filters.extend(("areverse", start_trim_filter(config), "areverse"))

    if config.fade_in_enabled and config.fade_in_ms > 0:
        duration = seconds_from_ms(config.fade_in_ms)
        filters.append(
            f"afade=t=in:st=0:d={duration}:curve={config.fade_in_curve}"
        )

    if config.fade_out_enabled and config.fade_out_ms > 0:
        duration = seconds_from_ms(config.fade_out_ms)
        filters.extend(
            (
                "areverse",
                f"afade=t=in:st=0:d={duration}:curve={config.fade_out_curve}",
                "areverse",
            )
        )

    return ",".join(filters) if filters else "anull"


def resolve_keep_ratio_duration(
    config: TrimConfig,
    task: AudioTask | None,
    source_duration_seconds: float | None,
) -> float:
    ratio = min(100.0, max(0.1, config.keep_ratio_percent)) / 100.0
    if source_duration_seconds is None:
        if task is None:
            raise AudioTrimError("Keep-ratio mode needs a source task or duration.")
        source_duration_seconds = probe_duration_seconds(config.ffprobe_path, task.source)
    return max(0.001, source_duration_seconds * ratio)


def seconds_from_float(seconds: float) -> str:
    text = f"{max(0.0, seconds):.6f}".rstrip("0").rstrip(".")
    return text or "0"


def scan_tasks(config: TrimConfig) -> list[AudioTask]:
    input_dir = config.input_dir
    output_dir = config.output_dir or default_output_dir(input_dir)

    if not input_dir.exists() or not input_dir.is_dir():
        raise AudioTrimError(f"Input directory does not exist: {input_dir}")

    iterator = input_dir.rglob("*") if config.recursive else input_dir.glob("*")
    sources = []
    for path in iterator:
        if not path.is_file():
            continue
        if output_dir and path_is_relative_to(path, output_dir):
            continue
        if path.suffix.lower() in config.extensions:
            sources.append(path)

    sources.sort(key=lambda item: str(item.relative_to(input_dir)).lower())

    tasks: list[AudioTask] = []
    used_outputs: set[str] = set()
    for source in sources:
        relative_source = source.relative_to(input_dir)
        output = output_dir / relative_source.with_suffix(".ogg")
        output = unique_output_path(output, source.suffix, used_outputs)
        tasks.append(
            AudioTask(
                source=source,
                output=output,
                relative_source=relative_source,
            )
        )
    return tasks


def unique_output_path(path: Path, source_suffix: str, used_outputs: set[str]) -> Path:
    key = str(path).lower()
    if key not in used_outputs:
        used_outputs.add(key)
        return path

    source_tag = source_suffix.lower().lstrip(".") or "audio"
    base = path.with_name(f"{path.stem}__from_{source_tag}{path.suffix}")
    candidate = base
    index = 2
    while str(candidate).lower() in used_outputs:
        candidate = base.with_name(f"{base.stem}_{index}{base.suffix}")
        index += 1
    used_outputs.add(str(candidate).lower())
    return candidate


def validate_ffmpeg(config: TrimConfig) -> None:
    if not config.ffmpeg_path.exists():
        raise AudioTrimError(
            "ffmpeg.exe was not found. Put it in Tools/AudioTrim/vendor/ "
            "or choose its path in the tool."
        )


def run_subprocess(command: list[str]) -> str:
    creationflags = 0
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creationflags,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        raise AudioTrimError(details[-2000:] or "ffmpeg failed without output.")
    return (result.stderr or result.stdout or "").strip()


def probe_duration_seconds(ffprobe_path: Path, source: Path) -> float:
    if not ffprobe_path.exists():
        raise AudioTrimError(
            "ffprobe.exe was not found. Keep-ratio mode needs ffprobe."
        )
    output = run_subprocess(
        [
            str(ffprobe_path),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source),
        ]
    )
    try:
        duration = float(output.strip().splitlines()[-1])
    except (IndexError, ValueError) as exc:
        raise AudioTrimError(f"Could not read duration for {source}.") from exc
    if duration <= 0.0:
        raise AudioTrimError(f"Invalid duration for {source}: {duration}")
    return duration


def run_subprocess_bytes(command: list[str]) -> bytes:
    creationflags = 0
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or b"").decode(
            "utf-8",
            errors="replace",
        ).strip()
        raise AudioTrimError(details[-2000:] or "ffmpeg failed without output.")
    return result.stdout


def analyze_absolute_edge_silence(config: TrimConfig, task: AudioTask) -> EdgeSilenceAnalysis:
    command = [
        str(config.ffmpeg_path),
        "-hide_banner",
        "-v",
        "error",
        "-i",
        str(task.source),
        "-vn",
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        str(ANALYSIS_CHANNELS),
        "-ar",
        str(ANALYSIS_SAMPLE_RATE),
        "pipe:1",
    ]
    data = run_subprocess_bytes(command)
    sample_count = len(data) // 2
    if sample_count == 0:
        return EdgeSilenceAnalysis(status="No PCM")

    leading_samples = count_zero_samples_from_start(data)
    trailing_samples = count_zero_samples_from_end(data)
    head_ms = samples_to_ms(leading_samples)
    tail_ms = samples_to_ms(trailing_samples)
    return EdgeSilenceAnalysis(
        head_ms=head_ms,
        tail_ms=tail_ms,
        status="Analyzed",
    )


def count_zero_samples_from_start(data: bytes) -> int:
    count = 0
    limit = len(data) - 1
    for offset in range(0, limit, 2):
        if data[offset] != 0 or data[offset + 1] != 0:
            break
        count += 1
    return count


def count_zero_samples_from_end(data: bytes) -> int:
    count = 0
    offset = len(data) - 2
    while offset >= 0:
        if data[offset] != 0 or data[offset + 1] != 0:
            break
        count += 1
        offset -= 2
    return count


def samples_to_ms(sample_count: int) -> float:
    frames = sample_count / ANALYSIS_CHANNELS
    return frames / ANALYSIS_SAMPLE_RATE * 1000.0


def has_absolute_edge_silence(analysis: EdgeSilenceAnalysis) -> bool:
    return analysis.head_ms > 0.0 or analysis.tail_ms > 0.0


def format_ms(value: float) -> str:
    if value <= 0.0:
        return "0ms"
    if value < 1.0:
        return "<1ms"
    return f"{value:.0f}ms"


def format_edge_analysis(analysis: EdgeSilenceAnalysis) -> str:
    if analysis.status != "Analyzed":
        return analysis.status
    parts = []
    if analysis.head_ms > 0.0:
        parts.append(f"Head {format_ms(analysis.head_ms)}")
    if analysis.tail_ms > 0.0:
        parts.append(f"Tail {format_ms(analysis.tail_ms)}")
    return " / ".join(parts) if parts else "None"


def build_output_command(config: TrimConfig, task: AudioTask) -> list[str]:
    filtergraph = build_filtergraph(config, task)
    return [
        str(config.ffmpeg_path),
        "-hide_banner",
        "-y",
        "-i",
        str(task.source),
        "-vn",
        "-af",
        filtergraph,
        "-map_metadata",
        "-1",
        "-c:a",
        "libvorbis",
        "-q:a",
        str(config.ogg_quality),
        str(task.output),
    ]


def build_preview_command(config: TrimConfig, task: AudioTask, preview_path: Path) -> list[str]:
    filtergraph = build_filtergraph(config, task)
    return [
        str(config.ffmpeg_path),
        "-hide_banner",
        "-y",
        "-i",
        str(task.source),
        "-vn",
        "-af",
        filtergraph,
        "-map_metadata",
        "-1",
        "-c:a",
        "pcm_s16le",
        str(preview_path),
    ]


def process_task(config: TrimConfig, task: AudioTask) -> None:
    task.output.parent.mkdir(parents=True, exist_ok=True)
    command = build_output_command(config, task)
    run_subprocess(command)
    if not task.output.exists() or task.output.stat().st_size == 0:
        raise AudioTrimError("Output file was not created.")


def build_preview_file(config: TrimConfig, task: AudioTask) -> Path:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    preview_name = f"preview_{int(time.time() * 1000)}_{task.source.stem}.wav"
    preview_path = PREVIEW_DIR / preview_name
    command = build_preview_command(config, task, preview_path)
    run_subprocess(command)
    if not preview_path.exists() or preview_path.stat().st_size == 0:
        raise AudioTrimError("Preview file was not created.")
    return preview_path


def build_direct_play_file(config: TrimConfig, source: Path) -> Path:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    preview_name = f"play_{int(time.time() * 1000)}_{source.stem}.wav"
    preview_path = PREVIEW_DIR / preview_name
    command = [
        str(config.ffmpeg_path),
        "-hide_banner",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-map_metadata",
        "-1",
        "-c:a",
        "pcm_s16le",
        str(preview_path),
    ]
    run_subprocess(command)
    if not preview_path.exists() or preview_path.stat().st_size == 0:
        raise AudioTrimError("Playback file was not created.")
    return preview_path


def read_wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        frame_rate = wav_file.getframerate()
        if frame_rate <= 0:
            return 0.0
        return wav_file.getnframes() / frame_rate


def build_waveform_peaks(ffmpeg_path: Path, source: Path, bucket_count: int) -> tuple[list[float], float]:
    if not ffmpeg_path.exists():
        raise AudioTrimError("ffmpeg.exe was not found. Waveform view needs ffmpeg.")
    command = [
        str(ffmpeg_path),
        "-hide_banner",
        "-v",
        "error",
        "-i",
        str(source),
        "-vn",
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        str(WAVEFORM_CHANNELS),
        "-ar",
        str(WAVEFORM_SAMPLE_RATE),
        "pipe:1",
    ]
    data = run_subprocess_bytes(command)
    sample_count = len(data) // 2
    duration = sample_count / WAVEFORM_SAMPLE_RATE if sample_count else 0.0
    return calculate_waveform_peaks(data, bucket_count), duration


def calculate_waveform_peaks(data: bytes, bucket_count: int) -> list[float]:
    sample_count = len(data) // 2
    if sample_count <= 0 or bucket_count <= 0:
        return []

    bucket_count = min(bucket_count, sample_count)
    samples_per_bucket = max(1, sample_count // bucket_count)
    peaks: list[float] = []
    offset = 0
    for _index in range(bucket_count):
        peak = 0
        end_sample = min(sample_count, (len(peaks) + 1) * samples_per_bucket)
        while offset < end_sample * 2:
            sample = int.from_bytes(data[offset:offset + 2], "little", signed=True)
            peak = max(peak, abs(sample))
            offset += 2
        peaks.append(min(1.0, peak / 32768.0))

    if offset < len(data) and peaks:
        peak = 0
        while offset < len(data):
            sample = int.from_bytes(data[offset:offset + 2], "little", signed=True)
            peak = max(peak, abs(sample))
            offset += 2
        peaks[-1] = max(peaks[-1], min(1.0, peak / 32768.0))
    return peaks


def cleanup_preview_files() -> None:
    if not PREVIEW_DIR.exists():
        return
    for path in PREVIEW_DIR.glob("*.wav"):
        try:
            path.unlink()
        except OSError:
            pass


def load_config_file() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config_file(data: dict) -> None:
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class AudioTrimApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Audio Trim Batch Tool")
        self.root.geometry("1280x800")
        self.events: queue.Queue[tuple] = queue.Queue()
        self.tasks: list[AudioTask] = []
        self.worker: threading.Thread | None = None
        self.play_worker: threading.Thread | None = None
        self.waveform_worker: threading.Thread | None = None
        self.waveform_request_id = 0
        self.playback_started_at: float | None = None
        self.playback_duration_seconds = 0.0
        self.playback_after_id: str | None = None
        self.playback_loop = False
        self.last_scan_key = ""

        data = load_config_file()
        default_input = Path(data.get("input_dir", "")).expanduser()
        default_output = Path(data.get("output_dir", "")).expanduser()
        language = data.get("language", detect_system_language())
        if language not in I18N:
            language = "en"

        self.language_code = StringVar(value=language)
        self.language_label = StringVar(value=LANGUAGE_LABELS[language])
        self.input_dir = StringVar(value=str(default_input) if str(default_input) != "." else "")
        self.output_dir = StringVar(value=str(default_output) if str(default_output) != "." else "")
        self.ffmpeg_path = StringVar(value=data.get("ffmpeg_path", str(find_tool("ffmpeg"))))
        self.ffprobe_path = StringVar(value=data.get("ffprobe_path", str(find_tool("ffprobe"))))
        self.recursive = BooleanVar(value=data.get("recursive", True))
        extensions = set(data.get("extensions", [".ogg", ".mp3"]))
        self.ext_ogg = BooleanVar(value=".ogg" in extensions)
        self.ext_mp3 = BooleanVar(value=".mp3" in extensions)
        self.ext_wav = BooleanVar(value=".wav" in extensions)
        self.threshold_db = DoubleVar(value=data.get("threshold_db", -45.0))
        self.silence_window_ms = IntVar(value=data.get("silence_window_ms", 20))
        mode = data.get("mode", MODE_TRIM_EDGES)
        self.mode_label = StringVar(value=self.mode_label_for(mode))
        self.segment_gap_ms = IntVar(value=data.get("segment_gap_ms", 120))
        self.keep_ratio_percent = DoubleVar(value=data.get("keep_ratio_percent", 25.0))
        self.fade_in_enabled = BooleanVar(value=data.get("fade_in_enabled", False))
        self.fade_in_ms = IntVar(value=data.get("fade_in_ms", 5))
        self.fade_in_curve = StringVar(value=self.curve_label(data.get("fade_in_curve", "tri")))
        self.fade_out_enabled = BooleanVar(value=data.get("fade_out_enabled", False))
        self.fade_out_ms = IntVar(value=data.get("fade_out_ms", 10))
        self.fade_out_curve = StringVar(value=self.curve_label(data.get("fade_out_curve", "cub")))
        self.ogg_quality = IntVar(value=data.get("ogg_quality", 5))
        self.loop_playback = BooleanVar(value=data.get("loop_playback", False))
        self.waveform_status = StringVar(value=self.tr("select_waveform"))

        self.build_modern_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.pump_events)
        if self.input_dir.get().strip():
            self.root.after(200, lambda: self.auto_scan_input(force=True))

    def tr(self, key: str) -> str:
        language = self.language_code.get()
        return I18N.get(language, I18N["en"]).get(key, I18N["en"].get(key, key))

    def mode_label_for(self, mode: str) -> str:
        mode_keys = {
            MODE_TRIM_EDGES: "mode_trim_edges",
            MODE_FIRST_SEGMENT: "mode_first_segment",
            MODE_KEEP_RATIO: "mode_keep_ratio",
        }
        return self.tr(mode_keys.get(mode, "mode_trim_edges"))

    def mode_values(self) -> tuple[str, ...]:
        return tuple(self.mode_label_for(mode) for mode in (MODE_TRIM_EDGES, MODE_FIRST_SEGMENT, MODE_KEEP_RATIO))

    def mode_from_label(self, label: str) -> str:
        for mode in (MODE_TRIM_EDGES, MODE_FIRST_SEGMENT, MODE_KEEP_RATIO):
            if label in (self.mode_label_for(mode), MODE_LABELS.get(mode), mode):
                return mode
        return MODE_TRIM_EDGES

    def curve_label(self, ffmpeg_name: str) -> str:
        if ffmpeg_name in CURVE_BY_KEY:
            key = ffmpeg_name
        else:
            key = CURVE_BY_FFMPEG.get(ffmpeg_name, CURVE_OPTIONS[0]).label
        return self.tr(f"curve_{key}")

    def curve_values(self) -> tuple[str, ...]:
        return tuple(self.tr(f"curve_{curve.label}") for curve in CURVE_OPTIONS)

    def curve_key_from_label(self, label: str) -> str:
        for curve in CURVE_OPTIONS:
            if label in (curve.label, curve.ffmpeg_name, self.tr(f"curve_{curve.label}")):
                return curve.label
        return CURVE_OPTIONS[0].label

    def on_language_changed(self) -> None:
        language = language_from_label(self.language_label.get())
        if language == self.language_code.get():
            return
        mode = self.mode_from_label(self.mode_label.get())
        fade_in_key = self.curve_key_from_label(self.fade_in_curve.get())
        fade_out_key = self.curve_key_from_label(self.fade_out_curve.get())
        self.language_code.set(language)
        self.mode_label.set(self.mode_label_for(mode))
        self.fade_in_curve.set(self.curve_label(fade_in_key))
        self.fade_out_curve.set(self.curve_label(fade_out_key))
        self.rebuild_ui()

    def rebuild_ui(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()
        self.build_modern_ui()
        try:
            config = self.read_config_from_ui(require_input_dir=False)
            self.refresh_task_table(config)
        except Exception:
            pass
        self.draw_waveform_message(self.tr("select_waveform"))


    def build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        settings = ttk.LabelFrame(self.root, text="Settings")
        settings.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        for column in range(8):
            settings.columnconfigure(column, weight=1 if column in (1, 4) else 0)

        ttk.Label(settings, text="Input").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(settings, textvariable=self.input_dir).grid(row=0, column=1, columnspan=3, sticky="ew", padx=6)
        ttk.Button(settings, text="Browse", command=self.browse_input).grid(row=0, column=4, sticky="w", padx=6)

        ttk.Label(settings, text="Output").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(settings, textvariable=self.output_dir).grid(row=1, column=1, columnspan=3, sticky="ew", padx=6)
        ttk.Button(settings, text="Browse", command=self.browse_output).grid(row=1, column=4, sticky="w", padx=6)
        ttk.Button(settings, text="Default", command=self.fill_default_output).grid(row=1, column=5, sticky="w", padx=6)

        ttk.Label(settings, text="FFmpeg").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(settings, textvariable=self.ffmpeg_path).grid(row=2, column=1, columnspan=3, sticky="ew", padx=6)
        ttk.Button(settings, text="Browse", command=self.browse_ffmpeg).grid(row=2, column=4, sticky="w", padx=6)

        ttk.Label(settings, text="FFprobe").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(settings, textvariable=self.ffprobe_path).grid(row=3, column=1, columnspan=3, sticky="ew", padx=6)
        ttk.Button(settings, text="Browse", command=self.browse_ffprobe).grid(row=3, column=4, sticky="w", padx=6)

        ttk.Checkbutton(settings, text="Recursive", variable=self.recursive).grid(row=4, column=0, sticky="w", padx=6)
        ttk.Checkbutton(settings, text=".ogg", variable=self.ext_ogg).grid(row=4, column=1, sticky="w", padx=6)
        ttk.Checkbutton(settings, text=".mp3", variable=self.ext_mp3).grid(row=4, column=2, sticky="w", padx=6)
        ttk.Checkbutton(settings, text=".wav", variable=self.ext_wav).grid(row=4, column=3, sticky="w", padx=6)

        ttk.Label(settings, text="Threshold dB").grid(row=5, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(settings, textvariable=self.threshold_db, width=8).grid(row=5, column=1, sticky="w", padx=6)
        ttk.Label(settings, text="Window ms").grid(row=5, column=2, sticky="w", padx=6)
        ttk.Entry(settings, textvariable=self.silence_window_ms, width=8).grid(row=5, column=3, sticky="w", padx=6)
        ttk.Label(settings, text="OGG q").grid(row=5, column=4, sticky="w", padx=6)
        ttk.Spinbox(settings, from_=0, to=10, textvariable=self.ogg_quality, width=6).grid(row=5, column=5, sticky="w", padx=6)

        ttk.Label(settings, text="Mode").grid(row=6, column=0, sticky="w", padx=6, pady=4)
        mode_box = ttk.Combobox(settings, textvariable=self.mode_label, values=tuple(MODE_BY_LABEL), state="readonly", width=24)
        mode_box.grid(row=6, column=1, columnspan=2, sticky="w", padx=6)
        mode_box.bind("<<ComboboxSelected>>", lambda _event: self.on_mode_changed())
        ttk.Label(settings, text="Segment gap ms").grid(row=6, column=3, sticky="w", padx=6)
        ttk.Entry(settings, textvariable=self.segment_gap_ms, width=8).grid(row=6, column=4, sticky="w", padx=6)
        ttk.Label(settings, text="Keep %").grid(row=6, column=5, sticky="w", padx=6)
        ttk.Entry(settings, textvariable=self.keep_ratio_percent, width=8).grid(row=6, column=6, sticky="w", padx=6)

        ttk.Checkbutton(settings, text="Fade in", variable=self.fade_in_enabled).grid(row=7, column=0, sticky="w", padx=6)
        ttk.Entry(settings, textvariable=self.fade_in_ms, width=8).grid(row=7, column=1, sticky="w", padx=6)
        ttk.Combobox(settings, textvariable=self.fade_in_curve, values=tuple(CURVE_BY_LABEL), state="readonly", width=20).grid(row=7, column=2, sticky="w", padx=6)

        ttk.Checkbutton(settings, text="Fade out", variable=self.fade_out_enabled).grid(row=7, column=3, sticky="w", padx=6)
        ttk.Entry(settings, textvariable=self.fade_out_ms, width=8).grid(row=7, column=4, sticky="w", padx=6)
        ttk.Combobox(settings, textvariable=self.fade_out_curve, values=tuple(CURVE_BY_LABEL), state="readonly", width=20).grid(row=7, column=5, sticky="w", padx=6)

        main = ttk.Frame(self.root)
        main.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        columns = ("use", "edge", "absolute", "source", "mode", "output", "status")
        self.tree = ttk.Treeview(main, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("use", text="Use")
        self.tree.heading("edge", text="Edge Trim")
        self.tree.heading("absolute", text="Absolute Silence")
        self.tree.heading("source", text="Source")
        self.tree.heading("mode", text="Mode")
        self.tree.heading("output", text="Output")
        self.tree.heading("status", text="Status")
        self.tree.column("use", width=52, stretch=False, anchor="center")
        self.tree.column("edge", width=78, stretch=False, anchor="center")
        self.tree.column("absolute", width=150, stretch=False)
        self.tree.column("source", width=280)
        self.tree.column("mode", width=165, stretch=False)
        self.tree.column("output", width=360)
        self.tree.column("status", width=160, stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", lambda _event: self.toggle_selected())
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self.on_selection_changed())

        scrollbar = ttk.Scrollbar(main, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        waveform = ttk.LabelFrame(self.root, text="Waveform Review")
        waveform.grid(row=2, column=0, sticky="ew", padx=10, pady=4)
        waveform.columnconfigure(0, weight=1)
        ttk.Label(waveform, textvariable=self.waveform_status).grid(row=0, column=0, sticky="w", padx=8, pady=(4, 0))
        self.waveform_canvas = Canvas(
            waveform,
            height=120,
            background="#101214",
            highlightthickness=1,
            highlightbackground="#30343a",
        )
        self.waveform_canvas.grid(row=1, column=0, sticky="ew", padx=8, pady=6)

        buttons = ttk.Frame(self.root)
        buttons.grid(row=3, column=0, sticky="ew", padx=10, pady=6)
        buttons.columnconfigure(10, weight=1)
        ttk.Button(buttons, text="Play Selected File", command=self.play_selected_file).grid(row=0, column=0, padx=4)
        ttk.Checkbutton(buttons, text="Loop", variable=self.loop_playback).grid(row=0, column=1, padx=4)
        ttk.Button(buttons, text="Preview Selected", command=self.preview_selected).grid(row=0, column=2, padx=4)
        ttk.Button(buttons, text="Stop Preview", command=self.stop_preview).grid(row=0, column=3, padx=4)
        ttk.Button(buttons, text="Process Checked", command=self.process_checked).grid(row=0, column=4, padx=4)
        ttk.Button(buttons, text="Toggle Selected", command=self.toggle_selected).grid(row=0, column=5, padx=4)
        ttk.Button(buttons, text="Toggle Edge Trim", command=self.toggle_edge_trim_selected).grid(row=0, column=6, padx=4)
        ttk.Button(buttons, text="Select All", command=lambda: self.set_all_enabled(True)).grid(row=0, column=7, padx=4)
        ttk.Button(buttons, text="Select None", command=lambda: self.set_all_enabled(False)).grid(row=0, column=8, padx=4)
        ttk.Button(buttons, text="Open Output", command=self.open_output_dir).grid(row=0, column=9, padx=4)

        self.log_box = scrolledtext.ScrolledText(self.root, height=8, wrap="word")
        self.log_box.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.log("Ready. Put ffmpeg.exe in Tools/AudioTrim/vendor/ before previewing or processing.")
        self.draw_waveform_message("Select a row to draw its waveform.")

    def build_modern_ui(self) -> None:
        self.root.title(self.tr("app_title"))
        self.root.geometry("1280x840")
        self.root.configure(background="#f5f5f7")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        self.root.option_add("*Font", "{Segoe UI} 10")
        self.setup_style()

        header = ttk.Frame(self.root, style="App.TFrame", padding=(18, 14, 18, 4))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=self.tr("app_title"), style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=self.tr("app_subtitle"), style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))
        language_frame = ttk.Frame(header, style="App.TFrame")
        language_frame.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Label(language_frame, text=self.tr("language"), style="Muted.TLabel").grid(row=0, column=0, sticky="e", padx=(0, 8))
        language_box = ttk.Combobox(
            language_frame,
            textvariable=self.language_label,
            values=tuple(LANGUAGE_LABELS.values()),
            state="readonly",
            width=10,
        )
        language_box.grid(row=0, column=1, sticky="e")
        language_box.bind("<<ComboboxSelected>>", lambda _event: self.on_language_changed())

        cards = ttk.Frame(self.root, style="App.TFrame", padding=(18, 8, 18, 8))
        cards.grid(row=1, column=0, sticky="ew")
        for column in range(3):
            cards.columnconfigure(column, weight=1, uniform="cards")

        source = ttk.Frame(cards, style="Card.TFrame", padding=14)
        source.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        source.columnconfigure(1, weight=1)
        ttk.Label(source, text=self.tr("source"), style="Section.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        input_entry = self.path_row(source, 1, self.tr("input"), self.input_dir, self.browse_input)
        input_entry.bind("<Return>", lambda _event: self.auto_scan_input(force=True))
        input_entry.bind("<FocusOut>", lambda _event: self.auto_scan_input())
        output_entry = self.path_row(source, 2, self.tr("output"), self.output_dir, self.browse_output)
        output_entry.bind("<Return>", lambda _event: self.auto_scan_input(force=True))
        output_entry.bind("<FocusOut>", lambda _event: self.auto_scan_input())
        ttk.Button(source, text=self.tr("default"), command=self.fill_default_output).grid(row=3, column=2, sticky="e", pady=(8, 0))

        processing = ttk.Frame(cards, style="Card.TFrame", padding=14)
        processing.grid(row=0, column=1, sticky="nsew", padx=8)
        processing.columnconfigure(1, weight=1)
        ttk.Label(processing, text=self.tr("processing"), style="Section.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        ttk.Label(processing, text=self.tr("mode"), style="Muted.TLabel").grid(row=1, column=0, sticky="w")
        mode_box = ttk.Combobox(
            processing,
            textvariable=self.mode_label,
            values=self.mode_values(),
            state="readonly",
            width=20,
        )
        mode_box.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(8, 0))
        mode_box.bind("<<ComboboxSelected>>", lambda _event: self.on_mode_changed())

        self.segment_gap_frame = ttk.Frame(processing, style="Card.TFrame")
        ttk.Label(self.segment_gap_frame, text=self.tr("segment_gap"), style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.segment_gap_frame, textvariable=self.segment_gap_ms, width=8).grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.keep_percent_frame = ttk.Frame(processing, style="Card.TFrame")
        ttk.Label(self.keep_percent_frame, text=self.tr("keep_percent"), style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.keep_percent_frame, textvariable=self.keep_ratio_percent, width=8).grid(row=0, column=1, sticky="w", padx=(8, 0))

        formats = ttk.Frame(processing, style="Card.TFrame")
        formats.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        ttk.Label(formats, text=self.tr("formats"), style="Muted.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Checkbutton(formats, text=".ogg", variable=self.ext_ogg, command=lambda: self.auto_scan_input(force=True)).grid(row=0, column=1, sticky="w")
        ttk.Checkbutton(formats, text=".mp3", variable=self.ext_mp3, command=lambda: self.auto_scan_input(force=True)).grid(row=0, column=2, sticky="w", padx=(8, 0))
        ttk.Checkbutton(formats, text=".wav", variable=self.ext_wav, command=lambda: self.auto_scan_input(force=True)).grid(row=0, column=3, sticky="w", padx=(8, 0))
        ttk.Checkbutton(formats, text=self.tr("recursive"), variable=self.recursive, command=lambda: self.auto_scan_input(force=True)).grid(row=0, column=4, sticky="w", padx=(16, 0))

        compact = ttk.Frame(processing, style="Card.TFrame")
        compact.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        ttk.Label(compact, text=self.tr("threshold"), style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(compact, textvariable=self.threshold_db, width=7).grid(row=0, column=1, sticky="w", padx=(8, 16))
        ttk.Label(compact, text=self.tr("window"), style="Muted.TLabel").grid(row=0, column=2, sticky="w")
        ttk.Entry(compact, textvariable=self.silence_window_ms, width=7).grid(row=0, column=3, sticky="w", padx=(8, 16))
        ttk.Label(compact, text=self.tr("ogg_quality"), style="Muted.TLabel").grid(row=0, column=4, sticky="w")
        ttk.Spinbox(compact, from_=0, to=10, textvariable=self.ogg_quality, width=5).grid(row=0, column=5, sticky="w", padx=(8, 0))

        fade = ttk.Frame(cards, style="Card.TFrame", padding=14)
        fade.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        fade.columnconfigure(0, weight=1)
        ttk.Label(fade, text=self.tr("fade_in") + " / " + self.tr("fade_out"), style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Checkbutton(fade, text=self.tr("fade_in"), variable=self.fade_in_enabled, command=self.refresh_fade_dependencies).grid(row=1, column=0, sticky="w")
        self.fade_in_detail = ttk.Frame(fade, style="Card.TFrame")
        self.fade_in_detail.grid(row=2, column=0, sticky="ew", pady=(6, 12))
        self.fade_controls(self.fade_in_detail, self.fade_in_ms, self.fade_in_curve, "in")
        ttk.Checkbutton(fade, text=self.tr("fade_out"), variable=self.fade_out_enabled, command=self.refresh_fade_dependencies).grid(row=3, column=0, sticky="w")
        self.fade_out_detail = ttk.Frame(fade, style="Card.TFrame")
        self.fade_out_detail.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        self.fade_controls(self.fade_out_detail, self.fade_out_ms, self.fade_out_curve, "out")

        tooling = ttk.Frame(fade, style="Card.TFrame")
        tooling.grid(row=5, column=0, sticky="ew", pady=(14, 0))
        tooling.columnconfigure(1, weight=1)
        ttk.Label(tooling, text=self.tr("tooling"), style="Muted.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        self.path_row(tooling, 1, self.tr("ffmpeg"), self.ffmpeg_path, self.browse_ffmpeg)
        self.path_row(tooling, 2, self.tr("ffprobe"), self.ffprobe_path, self.browse_ffprobe)

        main = ttk.Frame(self.root, style="App.TFrame", padding=(18, 0, 18, 0))
        main.grid(row=2, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)
        columns = ("use", "edge", "absolute", "source", "mode", "output", "status")
        self.tree = ttk.Treeview(main, columns=columns, show="headings", selectmode="extended")
        headings = {
            "use": self.tr("use"),
            "edge": self.tr("edge_trim"),
            "absolute": self.tr("absolute_silence"),
            "source": self.tr("file"),
            "mode": self.tr("task_mode"),
            "output": self.tr("target"),
            "status": self.tr("status"),
        }
        for column, heading in headings.items():
            self.tree.heading(column, text=heading)
        self.tree.column("use", width=58, stretch=False, anchor="center")
        self.tree.column("edge", width=78, stretch=False, anchor="center")
        self.tree.column("absolute", width=150, stretch=False)
        self.tree.column("source", width=300)
        self.tree.column("mode", width=160, stretch=False)
        self.tree.column("output", width=390)
        self.tree.column("status", width=140, stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", lambda _event: self.toggle_selected())
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self.on_selection_changed())
        scrollbar = ttk.Scrollbar(main, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        waveform = ttk.Frame(self.root, style="Card.TFrame", padding=(14, 10, 14, 12))
        waveform.grid(row=3, column=0, sticky="ew", padx=18, pady=(10, 0))
        waveform.columnconfigure(0, weight=1)
        ttk.Label(waveform, text=self.tr("waveform_review"), style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(waveform, textvariable=self.waveform_status, style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.waveform_canvas = Canvas(waveform, height=124, background="#101214", highlightthickness=0)
        self.waveform_canvas.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        buttons = ttk.Frame(self.root, style="App.TFrame", padding=(18, 10, 18, 8))
        buttons.grid(row=4, column=0, sticky="ew")
        buttons.columnconfigure(10, weight=1)
        ttk.Button(buttons, text=self.tr("play_selected_file"), command=self.play_selected_file, style="Primary.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Checkbutton(buttons, text=self.tr("loop_playback"), variable=self.loop_playback).grid(row=0, column=1, padx=4)
        ttk.Button(buttons, text=self.tr("preview_selected"), command=self.preview_selected).grid(row=0, column=2, padx=4)
        ttk.Button(buttons, text=self.tr("process_checked"), command=self.process_checked).grid(row=0, column=3, padx=4)
        ttk.Button(buttons, text=self.tr("stop_preview"), command=self.stop_preview).grid(row=0, column=4, padx=4)
        ttk.Button(buttons, text=self.tr("toggle_selected"), command=self.toggle_selected).grid(row=0, column=5, padx=4)
        ttk.Button(buttons, text=self.tr("toggle_edge_trim"), command=self.toggle_edge_trim_selected).grid(row=0, column=6, padx=4)
        ttk.Button(buttons, text=self.tr("select_all"), command=lambda: self.set_all_enabled(True)).grid(row=0, column=7, padx=4)
        ttk.Button(buttons, text=self.tr("select_none"), command=lambda: self.set_all_enabled(False)).grid(row=0, column=8, padx=4)
        ttk.Button(buttons, text=self.tr("open_output"), command=self.open_output_dir).grid(row=0, column=9, padx=(4, 0))

        self.log_box = scrolledtext.ScrolledText(self.root, height=5, wrap="word", relief="flat")
        self.log_box.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.log(self.tr("ready_hint"))
        self.refresh_mode_dependencies()
        self.refresh_fade_dependencies()
        self.draw_waveform_message(self.tr("select_waveform"))

    def setup_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", font=("Segoe UI", 10))
        style.configure("App.TFrame", background="#f5f5f7")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#f5f5f7", foreground="#1d1d1f", font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", background="#f5f5f7", foreground="#6e6e73", font=("Segoe UI", 10))
        style.configure("Section.TLabel", background="#ffffff", foreground="#1d1d1f", font=("Segoe UI", 11, "bold"))
        style.configure("Muted.TLabel", background="#ffffff", foreground="#6e6e73", font=("Segoe UI", 9))
        style.configure("TButton", padding=(10, 6))
        style.configure("Primary.TButton", padding=(12, 6))
        style.configure("Treeview", rowheight=28, borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def path_row(self, parent: ttk.Frame, row: int, label: str, variable: StringVar, command) -> ttk.Entry:
        ttk.Label(parent, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=4)
        ttk.Button(parent, text=self.tr("browse"), command=command).grid(row=row, column=2, sticky="e", pady=4)
        return entry

    def fade_controls(self, parent: ttk.Frame, duration_var: IntVar, curve_var: StringVar, tag: str) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text=self.tr("duration_ms"), style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(parent, textvariable=duration_var, width=8).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Label(parent, text=self.tr("curve"), style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        curve_box = ttk.Combobox(parent, textvariable=curve_var, values=self.curve_values(), state="readonly", width=14)
        curve_box.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        canvas = Canvas(parent, width=92, height=48, background="#ffffff", highlightthickness=0)
        canvas.grid(row=0, column=2, rowspan=2, sticky="e", padx=(10, 0))
        curve_box.bind("<<ComboboxSelected>>", lambda _event, fade_tag=tag: self.draw_curve_preview(fade_tag))
        if tag == "in":
            self.fade_in_curve_canvas = canvas
            self.fade_in_curve_box = curve_box
        else:
            self.fade_out_curve_canvas = canvas
            self.fade_out_curve_box = curve_box

    def refresh_mode_dependencies(self) -> None:
        mode = self.mode_from_label(self.mode_label.get())
        self.segment_gap_frame.grid_remove()
        self.keep_percent_frame.grid_remove()
        if mode == MODE_FIRST_SEGMENT:
            self.segment_gap_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))
        elif mode == MODE_KEEP_RATIO:
            self.keep_percent_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))

    def refresh_fade_dependencies(self) -> None:
        if self.fade_in_enabled.get():
            self.fade_in_detail.grid()
            self.draw_curve_preview("in")
        else:
            self.fade_in_detail.grid_remove()
        if self.fade_out_enabled.get():
            self.fade_out_detail.grid()
            self.draw_curve_preview("out")
        else:
            self.fade_out_detail.grid_remove()

    def draw_curve_preview(self, tag: str) -> None:
        canvas = self.fade_in_curve_canvas if tag == "in" else self.fade_out_curve_canvas
        curve_value = self.fade_in_curve.get() if tag == "in" else self.fade_out_curve.get()
        curve_key = self.curve_key_from_label(curve_value)
        canvas.delete("all")
        width = max(60, int(canvas["width"]))
        height = max(32, int(canvas["height"]))
        pad = 6
        canvas.create_line(pad, height - pad, width - pad, height - pad, fill="#d0d3d8")
        canvas.create_line(pad, pad, pad, height - pad, fill="#d0d3d8")
        points = []
        for index in range(36):
            t = index / 35
            value = self.curve_sample(curve_key, t)
            x = pad + (width - pad * 2) * t
            y = height - pad - (height - pad * 2) * value
            points.extend((x, y))
        canvas.create_line(*points, fill="#007aff", width=2, smooth=True)

    def curve_sample(self, curve_key: str, t: float) -> float:
        t = min(1.0, max(0.0, t))
        if curve_key == "ease_in":
            return t ** 3
        if curve_key == "ease_out":
            return 1.0 - (1.0 - t) ** 2
        if curve_key == "smooth":
            return t * t * (3.0 - 2.0 * t)
        if curve_key == "log":
            return math.log10(1.0 + 9.0 * t)
        return t

    def browse_input(self) -> None:
        path = filedialog.askdirectory(title="Choose input directory")
        if path:
            self.input_dir.set(path)
            self.fill_default_output()
            self.auto_scan_input(force=True)

    def browse_output(self) -> None:
        path = filedialog.askdirectory(title="Choose output directory")
        if path:
            self.output_dir.set(path)
            self.auto_scan_input(force=True)

    def browse_ffmpeg(self) -> None:
        path = filedialog.askopenfilename(title="Choose ffmpeg.exe", filetypes=(("ffmpeg", "ffmpeg.exe"), ("All files", "*.*")))
        if path:
            self.ffmpeg_path.set(path)

    def browse_ffprobe(self) -> None:
        path = filedialog.askopenfilename(title="Choose ffprobe.exe", filetypes=(("ffprobe", "ffprobe.exe"), ("All files", "*.*")))
        if path:
            self.ffprobe_path.set(path)

    def fill_default_output(self) -> None:
        input_text = self.input_dir.get().strip()
        if input_text:
            self.output_dir.set(str(default_output_dir(Path(input_text))))

    def should_reset_output_for_input(self, input_dir: Path) -> bool:
        output_text = self.output_dir.get().strip()
        if not output_text:
            return True
        output_dir = Path(output_text).expanduser()
        return path_is_relative_to(input_dir, output_dir)

    def scan_key_from_config(self, config: TrimConfig) -> str:
        try:
            input_key = str(config.input_dir.resolve())
        except OSError:
            input_key = str(config.input_dir)
        try:
            output_key = str(config.output_dir.resolve())
        except OSError:
            output_key = str(config.output_dir)
        return "|".join((
            input_key,
            output_key,
            str(config.recursive),
            ",".join(config.extensions),
        ))

    def auto_scan_input(self, force: bool = False) -> None:
        input_text = self.input_dir.get().strip()
        if not input_text:
            return
        input_dir = Path(input_text).expanduser()
        if not input_dir.exists() or not input_dir.is_dir():
            return
        if self.should_reset_output_for_input(input_dir):
            self.output_dir.set(str(default_output_dir(input_dir)))
        try:
            config = self.read_config_from_ui()
        except Exception:
            return
        scan_key = self.scan_key_from_config(config)
        if not force and scan_key == self.last_scan_key:
            return
        self.scan()

    def read_config_from_ui(
        self,
        require_input_dir: bool = True,
    ) -> TrimConfig:
        extensions = []
        if self.ext_ogg.get():
            extensions.append(".ogg")
        if self.ext_mp3.get():
            extensions.append(".mp3")
        if self.ext_wav.get():
            extensions.append(".wav")
        if not extensions:
            raise AudioTrimError("Choose at least one input format.")

        input_text = self.input_dir.get().strip()
        if input_text:
            input_dir = Path(input_text).expanduser()
        elif require_input_dir:
            raise AudioTrimError(self.tr("missing_input"))
        else:
            input_dir = Path()

        output_text = self.output_dir.get().strip()
        if output_text:
            output_dir = Path(output_text).expanduser()
        elif input_text:
            output_dir = default_output_dir(input_dir)
        else:
            output_dir = Path()
        fade_in_curve = CURVE_BY_KEY[self.curve_key_from_label(self.fade_in_curve.get())].ffmpeg_name
        fade_out_curve = CURVE_BY_KEY[self.curve_key_from_label(self.fade_out_curve.get())].ffmpeg_name
        mode = self.mode_from_label(self.mode_label.get())

        config = TrimConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            ffmpeg_path=Path(self.ffmpeg_path.get().strip()).expanduser(),
            ffprobe_path=Path(self.ffprobe_path.get().strip()).expanduser(),
            recursive=self.recursive.get(),
            extensions=tuple(extensions),
            threshold_db=float(self.threshold_db.get()),
            silence_window_ms=max(0, int(self.silence_window_ms.get())),
            mode=mode,
            segment_gap_ms=max(1, int(self.segment_gap_ms.get())),
            keep_ratio_percent=min(100.0, max(0.1, float(self.keep_ratio_percent.get()))),
            fade_in_enabled=self.fade_in_enabled.get(),
            fade_in_ms=max(0, int(self.fade_in_ms.get())),
            fade_in_curve=fade_in_curve,
            fade_out_enabled=self.fade_out_enabled.get(),
            fade_out_ms=max(0, int(self.fade_out_ms.get())),
            fade_out_curve=fade_out_curve,
            ogg_quality=min(10, max(0, int(self.ogg_quality.get()))),
        )
        return normalize_config_for_mode(config)

    def config_to_json(self, config: TrimConfig) -> dict:
        input_text = self.input_dir.get().strip()
        output_text = self.output_dir.get().strip()
        return {
            "language": self.language_code.get(),
            "input_dir": str(config.input_dir) if input_text else "",
            "output_dir": str(config.output_dir) if output_text or input_text else "",
            "ffmpeg_path": str(config.ffmpeg_path),
            "ffprobe_path": str(config.ffprobe_path),
            "recursive": config.recursive,
            "extensions": list(config.extensions),
            "threshold_db": config.threshold_db,
            "silence_window_ms": config.silence_window_ms,
            "mode": config.mode,
            "segment_gap_ms": config.segment_gap_ms,
            "keep_ratio_percent": config.keep_ratio_percent,
            "fade_in_enabled": config.fade_in_enabled,
            "fade_in_ms": config.fade_in_ms,
            "fade_in_curve": config.fade_in_curve,
            "fade_out_enabled": config.fade_out_enabled,
            "fade_out_ms": config.fade_out_ms,
            "fade_out_curve": config.fade_out_curve,
            "ogg_quality": config.ogg_quality,
            "loop_playback": self.loop_playback.get(),
        }

    def scan(self) -> None:
        try:
            config = self.read_config_from_ui()
            scan_key = self.scan_key_from_config(config)
            self.output_dir.set(str(config.output_dir))
            self.tasks = scan_tasks(config)
            self.last_scan_key = scan_key
            save_config_file(self.config_to_json(config))
            self.refresh_task_table(config)
            self.log(self.tr("scan_done").format(count=len(self.tasks)))
            self.start_edge_silence_analysis(config)
        except Exception as exc:
            messagebox.showerror("Scan failed", str(exc))
            self.log(f"Scan failed: {exc}")

    def start_edge_silence_analysis(self, config: TrimConfig) -> None:
        if not self.tasks:
            return
        if not config.ffmpeg_path.exists():
            for index, task in enumerate(self.tasks):
                task.edge_analysis.status = "Needs FFmpeg"
                task.status = "Ready"
                self.update_task_row(index)
            self.log("Skipped absolute silence analysis because ffmpeg.exe was not found.")
            return
        self.worker = threading.Thread(
            target=self.edge_silence_analysis_worker,
            args=(config,),
            daemon=True,
        )
        self.worker.start()

    def edge_silence_analysis_worker(self, config: TrimConfig) -> None:
        review_count = 0
        auto_count = 0
        for index, task in enumerate(self.tasks):
            try:
                self.events.put(("status", index, "Analyzing silence"))
                analysis = analyze_absolute_edge_silence(config, task)
                if has_absolute_edge_silence(analysis):
                    if config.mode == MODE_FIRST_SEGMENT:
                        auto_count += 1
                        status = "Auto edge trim"
                    else:
                        review_count += 1
                        status = "Review edge trim"
                else:
                    status = "Ready"
                self.events.put(("edge_analysis", index, analysis, status))
            except Exception as exc:
                analysis = EdgeSilenceAnalysis(status="Analysis failed")
                self.events.put(("edge_analysis", index, analysis, "Ready"))
                self.events.put(("log", f"Silence analysis failed for {task.relative_source}: {exc}"))
        self.events.put((
            "log",
            f"Absolute silence analysis complete. {review_count} task(s) need review, {auto_count} auto-handled by mode.",
        ))

    def refresh_task_table(self, config: TrimConfig) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        mode_label = self.mode_label_for(config.mode)
        for index, task in enumerate(self.tasks):
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=self.task_row_values(task, mode_label, config.mode),
            )

    def update_task_row(self, index: int) -> None:
        if index < 0 or index >= len(self.tasks):
            return
        task = self.tasks[index]
        if not self.tree.exists(str(index)):
            return
        mode_label = self.tree.set(str(index), "mode")
        mode = self.mode_from_label(mode_label)
        self.tree.item(str(index), values=self.task_row_values(task, mode_label, mode))

    def task_row_values(self, task: AudioTask, mode_label: str, mode: str) -> tuple[str, ...]:
        return (
            "Yes" if task.enabled else "No",
            self.edge_trim_label(task, mode),
            format_edge_analysis(task.edge_analysis),
            str(task.relative_source),
            mode_label,
            str(task.output),
            task.status,
        )

    def edge_trim_label(self, task: AudioTask, mode: str) -> str:
        if mode == MODE_FIRST_SEGMENT:
            return self.tr("auto")
        return self.tr("yes") if task.edge_trim_enabled else self.tr("no")

    def on_mode_changed(self) -> None:
        mode_label = self.mode_label.get()
        mode = self.mode_from_label(mode_label)
        for item in self.tree.get_children():
            self.tree.set(item, "mode", mode_label)
        for index in range(len(self.tasks)):
            if mode == MODE_FIRST_SEGMENT and self.tasks[index].status == "Review edge trim":
                self.tasks[index].status = "Auto edge trim"
            self.update_task_row(index)
        self.refresh_mode_dependencies()

    def selected_indices(self) -> list[int]:
        return [int(item) for item in self.tree.selection()]

    def selected_audio_path(self, index: int) -> Path:
        task = self.tasks[index]
        return task.output if task.output.exists() else task.source

    def on_selection_changed(self) -> None:
        indices = self.selected_indices()
        if not indices:
            return
        self.start_waveform_load(indices[0])

    def start_waveform_load(self, index: int) -> None:
        if index < 0 or index >= len(self.tasks):
            return
        try:
            config = self.read_config_from_ui(require_input_dir=False)
            source = self.selected_audio_path(index)
            if not source.exists():
                self.draw_waveform_message(f"Audio file does not exist: {source}")
                return
            if not config.ffmpeg_path.exists():
                self.draw_waveform_message(self.tr("needs_ffmpeg"))
                return
        except Exception as exc:
            self.draw_waveform_message(self.tr("waveform_unavailable").format(message=exc))
            return

        width = max(240, self.waveform_canvas.winfo_width())
        self.waveform_request_id += 1
        request_id = self.waveform_request_id
        self.draw_waveform_message(self.tr("waveform_loading").format(name=source.name))
        self.waveform_worker = threading.Thread(
            target=self.waveform_worker_fn,
            args=(request_id, index, config.ffmpeg_path, source, width),
            daemon=True,
        )
        self.waveform_worker.start()

    def waveform_worker_fn(
        self,
        request_id: int,
        index: int,
        ffmpeg_path: Path,
        source: Path,
        width: int,
    ) -> None:
        try:
            peaks, duration = build_waveform_peaks(ffmpeg_path, source, width)
            self.events.put(("waveform", request_id, index, source, peaks, duration))
        except Exception as exc:
            self.events.put(("waveform_error", request_id, f"Waveform failed: {exc}"))

    def toggle_selected(self) -> None:
        indices = self.selected_indices()
        if not indices:
            return
        for index in indices:
            self.tasks[index].enabled = not self.tasks[index].enabled
            self.update_task_row(index)

    def toggle_edge_trim_selected(self) -> None:
        indices = self.selected_indices()
        if not indices:
            return
        if self.mode_from_label(self.mode_label.get()) == MODE_FIRST_SEGMENT:
            self.log(self.tr("edge_auto"))
            return
        for index in indices:
            self.tasks[index].edge_trim_enabled = not self.tasks[index].edge_trim_enabled
            self.update_task_row(index)

    def set_all_enabled(self, enabled: bool) -> None:
        for index, task in enumerate(self.tasks):
            task.enabled = enabled
            self.update_task_row(index)

    def preview_selected(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo(self.tr("status"), self.tr("busy_task"))
            return
        indices = self.selected_indices()
        if not indices:
            messagebox.showinfo(self.tr("status"), self.tr("no_selection_preview"))
            return
        index = indices[0]
        try:
            config = self.read_config_from_ui()
            validate_ffmpeg(config)
            save_config_file(self.config_to_json(config))
        except Exception as exc:
            messagebox.showerror("Preview failed", str(exc))
            return

        self.worker = threading.Thread(
            target=self.preview_worker,
            args=(config, index),
            daemon=True,
        )
        self.worker.start()

    def play_selected_file(self) -> None:
        if self.play_worker and self.play_worker.is_alive():
            messagebox.showinfo(self.tr("status"), self.tr("busy_play"))
            return
        indices = self.selected_indices()
        if not indices:
            messagebox.showinfo(self.tr("status"), self.tr("no_selection_play"))
            return
        index = indices[0]
        try:
            config = self.read_config_from_ui(require_input_dir=False)
            validate_ffmpeg(config)
            source = self.selected_audio_path(index)
            if not source.exists():
                raise AudioTrimError(f"Audio file does not exist: {source}")
        except Exception as exc:
            messagebox.showerror("Playback failed", str(exc))
            return

        self.play_worker = threading.Thread(
            target=self.play_selected_file_worker,
            args=(config, index, source),
            daemon=True,
        )
        self.play_worker.start()

    def play_selected_file_worker(self, config: TrimConfig, index: int, source: Path) -> None:
        try:
            self.events.put(("status", index, "Preparing playback"))
            preview_path = build_direct_play_file(config, source)
            self.events.put(("status", index, "Review"))
            self.events.put(("play", str(preview_path)))
            self.events.put(("log", f"Play file: {source}"))
        except Exception as exc:
            self.events.put(("status", index, "Playback failed"))
            self.events.put(("log", f"Playback failed for {source}: {exc}"))

    def preview_worker(self, config: TrimConfig, index: int) -> None:
        task = self.tasks[index]
        try:
            self.events.put(("status", index, "Building preview"))
            preview_path = build_preview_file(config, task)
            self.events.put(("status", index, "Preview ready"))
            self.events.put(("play", str(preview_path)))
            self.events.put(("log", f"Preview: {task.relative_source}"))
        except Exception as exc:
            self.events.put(("status", index, "Preview failed"))
            self.events.put(("log", f"Preview failed for {task.relative_source}: {exc}"))

    def stop_preview(self) -> None:
        try:
            if os.name == "nt":
                import winsound

                winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
        self.stop_playback_progress(reset=True)
        cleanup_preview_files()
        self.log(self.tr("preview_stopped"))

    def process_checked(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo(self.tr("status"), self.tr("busy_task"))
            return
        checked = [index for index, task in enumerate(self.tasks) if task.enabled]
        if not checked:
            messagebox.showinfo(self.tr("status"), self.tr("no_tasks"))
            return
        try:
            config = self.read_config_from_ui()
            validate_ffmpeg(config)
            save_config_file(self.config_to_json(config))
        except Exception as exc:
            messagebox.showerror("Process failed", str(exc))
            return

        self.worker = threading.Thread(
            target=self.process_worker,
            args=(config, checked),
            daemon=True,
        )
        self.worker.start()

    def process_worker(self, config: TrimConfig, indices: list[int]) -> None:
        succeeded = 0
        failed = 0
        for index in indices:
            task = self.tasks[index]
            try:
                self.events.put(("status", index, "Processing"))
                process_task(config, task)
                succeeded += 1
                self.events.put(("status", index, "Done"))
                self.events.put(("log", f"Done: {task.output}"))
            except Exception as exc:
                failed += 1
                self.events.put(("status", index, "Failed"))
                self.events.put(("log", f"Failed: {task.relative_source}: {exc}"))
        self.events.put(("log", f"Finished. {succeeded} succeeded, {failed} failed."))

    def open_output_dir(self) -> None:
        output_text = self.output_dir.get().strip()
        if not output_text:
            return
        output = Path(output_text)
        if not output.exists():
            messagebox.showinfo(self.tr("status"), self.tr("missing_output"))
            return
        if os.name == "nt":
            os.startfile(output)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(output)])

    def pump_events(self) -> None:
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            kind = event[0]
            if kind == "status":
                _, index, status = event
                self.tasks[index].status = status
                self.update_task_row(index)
            elif kind == "edge_analysis":
                _, index, analysis, status = event
                self.tasks[index].edge_analysis = analysis
                self.tasks[index].status = status
                self.update_task_row(index)
            elif kind == "log":
                _, message = event
                self.log(message)
            elif kind == "play":
                _, path = event
                self.play_preview(Path(path))
            elif kind == "waveform":
                _, request_id, _index, source, peaks, duration = event
                if request_id == self.waveform_request_id:
                    self.draw_waveform(source, peaks, duration)
            elif kind == "waveform_error":
                _, request_id, message = event
                if request_id == self.waveform_request_id:
                    self.draw_waveform_message(message)
        self.root.after(100, self.pump_events)

    def play_preview(self, path: Path) -> None:
        try:
            duration = read_wav_duration_seconds(path)
            loop = self.loop_playback.get()
            if os.name == "nt":
                import winsound

                flags = winsound.SND_FILENAME | winsound.SND_ASYNC
                if loop:
                    flags |= winsound.SND_LOOP
                winsound.PlaySound(str(path), flags)
            else:
                subprocess.Popen(["xdg-open", str(path)])
            self.start_playback_progress(duration, loop=loop)
        except Exception as exc:
            self.log(f"Could not play preview: {exc}")

    def start_playback_progress(self, duration: float, loop: bool = False) -> None:
        self.stop_playback_progress(reset=False)
        self.playback_started_at = time.monotonic()
        self.playback_duration_seconds = max(0.001, duration)
        self.playback_loop = loop
        self.draw_playhead(0.0)
        self.schedule_playback_progress()

    def schedule_playback_progress(self) -> None:
        self.playback_after_id = self.root.after(50, self.update_playback_progress)

    def update_playback_progress(self) -> None:
        if self.playback_started_at is None:
            return
        elapsed = time.monotonic() - self.playback_started_at
        if self.playback_loop:
            fraction = (elapsed % self.playback_duration_seconds) / self.playback_duration_seconds
        else:
            fraction = min(1.0, elapsed / self.playback_duration_seconds)
        self.draw_playhead(fraction)
        if self.playback_loop or fraction < 1.0:
            self.schedule_playback_progress()
        else:
            self.playback_started_at = None
            self.playback_after_id = None

    def stop_playback_progress(self, reset: bool) -> None:
        if self.playback_after_id is not None:
            try:
                self.root.after_cancel(self.playback_after_id)
            except Exception:
                pass
        self.playback_after_id = None
        self.playback_started_at = None
        self.playback_duration_seconds = 0.0
        self.playback_loop = False
        if reset:
            self.draw_playhead(0.0)

    def draw_waveform_message(self, message: str) -> None:
        self.stop_playback_progress(reset=False)
        self.waveform_status.set(message)
        self.waveform_canvas.delete("all")
        width = max(240, self.waveform_canvas.winfo_width())
        height = max(80, self.waveform_canvas.winfo_height())
        self.waveform_canvas.create_line(0, height / 2, width, height / 2, fill="#394048")
        self.waveform_canvas.create_text(
            width / 2,
            height / 2,
            text=message,
            fill="#9aa4ad",
        )

    def draw_waveform(self, source: Path, peaks: list[float], duration: float) -> None:
        self.stop_playback_progress(reset=False)
        self.waveform_canvas.delete("all")
        width = max(240, self.waveform_canvas.winfo_width())
        height = max(80, self.waveform_canvas.winfo_height())
        left, right, top, axis_y = self.waveform_plot_bounds(width, height)
        center = top + (axis_y - top) / 2
        half_height = max(1.0, (axis_y - top) * 0.42)
        plot_width = max(1.0, right - left)
        self.waveform_canvas.create_rectangle(0, 0, width, height, fill="#101214", outline="#30343a")
        self.waveform_canvas.create_line(left, center, right, center, fill="#394048")

        if not peaks:
            self.draw_waveform_message(f"No waveform data: {source.name}")
            return

        x_scale = plot_width / max(1, len(peaks) - 1)
        for index, peak in enumerate(peaks):
            x = left + index * x_scale
            y1 = center - peak * half_height
            y2 = center + peak * half_height
            self.waveform_canvas.create_line(x, y1, x, y2, fill="#58c7f3")

        self.draw_time_axis(duration)
        self.draw_playhead(0.0)
        self.waveform_status.set(
            self.tr("waveform_status").format(name=source.name, duration=duration)
        )

    def waveform_plot_bounds(self, width: int, height: int) -> tuple[float, float, float, float]:
        left = 8.0
        right = max(left + 1.0, width - 8.0)
        top = 8.0
        axis_y = max(top + 40.0, height - 24.0)
        return left, right, top, axis_y

    def draw_time_axis(self, duration: float) -> None:
        width = max(240, self.waveform_canvas.winfo_width())
        height = max(80, self.waveform_canvas.winfo_height())
        left, right, _top, axis_y = self.waveform_plot_bounds(width, height)
        self.waveform_canvas.create_line(left, axis_y, right, axis_y, fill="#5a626d", tags=("axis",))
        ticks = (0.0, 0.5, 1.0)
        for fraction in ticks:
            x = left + (right - left) * fraction
            self.waveform_canvas.create_line(x, axis_y - 4, x, axis_y + 4, fill="#5a626d", tags=("axis",))
            seconds = duration * fraction
            label = f"{seconds:.2f}s" if duration < 10.0 else f"{seconds:.1f}s"
            anchor = "w" if fraction == 0.0 else ("e" if fraction == 1.0 else "center")
            self.waveform_canvas.create_text(
                x,
                axis_y + 14,
                text=label,
                fill="#9aa4ad",
                anchor=anchor,
                tags=("axis",),
            )

    def draw_playhead(self, fraction: float) -> None:
        self.waveform_canvas.delete("playhead")
        width = max(240, self.waveform_canvas.winfo_width())
        height = max(80, self.waveform_canvas.winfo_height())
        left, right, top, axis_y = self.waveform_plot_bounds(width, height)
        fraction = min(1.0, max(0.0, fraction))
        x = left + (right - left) * fraction
        self.waveform_canvas.create_line(
            x,
            top,
            x,
            axis_y,
            fill="#ff5b57",
            width=2,
            tags=("playhead",),
        )
        if self.playback_duration_seconds > 0.0:
            label = f"{self.playback_duration_seconds * fraction:.2f}s"
            self.waveform_canvas.create_text(
                x + 4,
                top + 8,
                text=label,
                fill="#ffb1ae",
                anchor="w",
                tags=("playhead",),
            )

    def log(self, message: str) -> None:
        self.log_box.insert("end", f"{time.strftime('%H:%M:%S')}  {message}\n")
        self.log_box.see("end")

    def on_close(self) -> None:
        try:
            config = self.read_config_from_ui(require_input_dir=False)
            save_config_file(self.config_to_json(config))
        except Exception:
            pass
        self.stop_preview()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def config_from_args(args: argparse.Namespace) -> TrimConfig:
    input_dir = Path(args.input).expanduser()
    output_dir = Path(args.output).expanduser() if args.output else default_output_dir(input_dir)
    extensions = parse_extensions(args.formats)
    fade_in_curve = args.fade_in_curve
    fade_out_curve = args.fade_out_curve
    if fade_in_curve not in CURVE_BY_FFMPEG:
        raise AudioTrimError(f"Unsupported fade-in curve: {fade_in_curve}")
    if fade_out_curve not in CURVE_BY_FFMPEG:
        raise AudioTrimError(f"Unsupported fade-out curve: {fade_out_curve}")

    config = TrimConfig(
        input_dir=input_dir,
        output_dir=output_dir,
        ffmpeg_path=Path(args.ffmpeg).expanduser() if args.ffmpeg else find_tool("ffmpeg"),
        ffprobe_path=Path(args.ffprobe).expanduser() if args.ffprobe else find_tool("ffprobe"),
        recursive=args.recursive,
        extensions=extensions,
        threshold_db=args.threshold_db,
        silence_window_ms=args.silence_window_ms,
        mode=args.mode,
        segment_gap_ms=args.segment_gap_ms,
        keep_ratio_percent=args.keep_ratio_percent,
        fade_in_enabled=args.fade_in_ms > 0,
        fade_in_ms=args.fade_in_ms,
        fade_in_curve=fade_in_curve,
        fade_out_enabled=args.fade_out_ms > 0,
        fade_out_ms=args.fade_out_ms,
        fade_out_curve=fade_out_curve,
        ogg_quality=args.ogg_quality,
    )
    return normalize_config_for_mode(config)


def run_cli(args: argparse.Namespace) -> int:
    config = config_from_args(args)
    tasks = scan_tasks(config)
    apply_cli_task_overrides(tasks, args)
    if args.dry_run:
        print(f"Found {len(tasks)} task(s).")
        print(f"Filter: {build_filtergraph(config, tasks[0]) if tasks else build_filtergraph(config)}")
        for task in tasks:
            print(f"{task.source} -> {task.output}")
        return 0

    validate_ffmpeg(config)
    failed = 0
    for task in tasks:
        try:
            print(f"Processing {task.relative_source}")
            process_task(config, task)
        except Exception as exc:
            failed += 1
            print(f"Failed: {task.relative_source}: {exc}", file=sys.stderr)
    print(f"Finished. {len(tasks) - failed} succeeded, {failed} failed.")
    return 1 if failed else 0


def apply_cli_task_overrides(tasks: list[AudioTask], args: argparse.Namespace) -> None:
    if not getattr(args, "edge_trim", True):
        for task in tasks:
            task.edge_trim_enabled = False


def run_self_tests() -> int:
    temp_root = Path(tempfile.mkdtemp(prefix="audio_trim_test_"))
    try:
        input_dir = temp_root / "in"
        output_dir = temp_root / "out"
        input_dir.mkdir()
        (input_dir / "page.mp3").touch()
        (input_dir / "page.ogg").touch()

        base_config = TrimConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            ffmpeg_path=Path("ffmpeg.exe"),
            ffprobe_path=Path("ffprobe.exe"),
            recursive=True,
            extensions=(".ogg", ".mp3"),
            threshold_db=-45.0,
            silence_window_ms=20,
            mode=MODE_TRIM_EDGES,
            segment_gap_ms=120,
            keep_ratio_percent=25.0,
            fade_in_enabled=False,
            fade_in_ms=0,
            fade_in_curve="tri",
            fade_out_enabled=False,
            fade_out_ms=0,
            fade_out_curve="cub",
            ogg_quality=5,
        )

        tasks = scan_tasks(base_config)
        assert len(tasks) == 2, tasks
        outputs = {task.output.name for task in tasks}
        assert len(outputs) == 2, outputs
        assert all(name.endswith(".ogg") for name in outputs), outputs

        edge_filter = build_filtergraph(base_config)
        assert "areverse" in edge_filter, edge_filter
        assert "stop_periods=1" not in edge_filter, edge_filter

        tasks[0].edge_trim_enabled = False
        no_edge_filter = build_filtergraph(base_config, tasks[0])
        assert no_edge_filter == "anull", no_edge_filter

        pcm_data = (b"\x00\x00" * 4) + b"\x01\x00" + (b"\x00\x00" * 2)
        assert count_zero_samples_from_start(pcm_data) == 4
        assert count_zero_samples_from_end(pcm_data) == 2
        assert format_edge_analysis(EdgeSilenceAnalysis(1.0, 2.0, "Analyzed")) == "Head 1ms / Tail 2ms"
        waveform_peaks = calculate_waveform_peaks(
            b"\x00\x00" + b"\xff\x7f" + b"\x00\x80" + b"\x00\x00",
            2,
        )
        assert len(waveform_peaks) == 2, waveform_peaks
        assert max(waveform_peaks) > 0.9, waveform_peaks
        wav_path = temp_root / "duration.wav"
        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8000)
            wav_file.writeframes(b"\x00\x00" * 4000)
        assert abs(read_wav_duration_seconds(wav_path) - 0.5) < 0.001

        first_config = TrimConfig(
            **{
                **base_config.__dict__,
                "mode": MODE_FIRST_SEGMENT,
                "fade_out_enabled": True,
                "fade_out_ms": 10,
            }
        )
        first_filter = build_filtergraph(first_config)
        assert "stop_periods=1" in first_filter, first_filter
        assert "stop_duration=0.12" in first_filter, first_filter
        assert first_filter.count("areverse") >= 2, first_filter
        assert "afade=t=in" in first_filter, first_filter
        tasks[0].edge_trim_enabled = False
        forced_first_filter = build_filtergraph(first_config, tasks[0])
        assert "start_periods=1" in forced_first_filter, forced_first_filter
        assert "stop_periods=1" in forced_first_filter, forced_first_filter
        ratio_config = TrimConfig(
            **{
                **base_config.__dict__,
                "mode": MODE_KEEP_RATIO,
                "keep_ratio_percent": 25.0,
                "fade_out_enabled": True,
                "fade_out_ms": 8,
            }
        )
        ratio_filter = build_filtergraph(ratio_config, tasks[0], source_duration_seconds=4.0)
        assert "atrim=start=0:end=1" in ratio_filter, ratio_filter
        assert "afade=t=in" in ratio_filter, ratio_filter
        assert CURVE_BY_KEY["ease_in"].ffmpeg_name == "cub"
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    print("Self-test passed.")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch trim silence from audio files.")
    parser.add_argument("--gui", action="store_true", help="Launch the GUI.")
    parser.add_argument("--self-test", action="store_true", help="Run lightweight tests.")
    parser.add_argument("--input", help="Input directory.")
    parser.add_argument("--output", help="Output directory. Defaults to <input>_trimmed_ogg.")
    parser.add_argument("--ffmpeg", help="Path to ffmpeg.exe.")
    parser.add_argument("--ffprobe", help="Path to ffprobe.exe.")
    parser.add_argument("--formats", default=".ogg,.mp3", help="Comma-separated input extensions.")
    parser.add_argument("--recursive", dest="recursive", action="store_true", default=True)
    parser.add_argument("--no-recursive", dest="recursive", action="store_false")
    parser.add_argument("--threshold-db", type=float, default=-45.0)
    parser.add_argument("--silence-window-ms", type=int, default=20)
    parser.add_argument("--mode", choices=(MODE_TRIM_EDGES, MODE_FIRST_SEGMENT, MODE_KEEP_RATIO), default=MODE_TRIM_EDGES)
    parser.add_argument("--segment-gap-ms", type=int, default=120)
    parser.add_argument("--keep-ratio-percent", type=float, default=25.0)
    parser.add_argument("--edge-trim", dest="edge_trim", action="store_true", default=True)
    parser.add_argument("--no-edge-trim", dest="edge_trim", action="store_false")
    parser.add_argument("--fade-in-ms", type=int, default=0)
    parser.add_argument("--fade-in-curve", choices=tuple(CURVE_BY_FFMPEG), default="tri")
    parser.add_argument("--fade-out-ms", type=int, default=0)
    parser.add_argument("--fade-out-curve", choices=tuple(CURVE_BY_FFMPEG), default="cub")
    parser.add_argument("--ogg-quality", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_tests()

    if args.gui or not args.input:
        app = AudioTrimApp()
        app.run()
        return 0

    try:
        return run_cli(args)
    except Exception as exc:
        print(f"AudioTrim failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
