"""
Latency benchmarking script for Gemini Live API audio sessions.

This utility runs a configurable number of Live API turns against both the
Gemini Developer API backend and the Vertex AI Gemini backend so you can
compare connection latency, time-to-first-byte, and total response time.

Example:
    python performance/live_api_latency_benchmark.py \\
        --iterations 5 --prompt "Give me a one sentence news update."

Requirements:
    pip install google-genai
    export GEMINI_API_KEY="..."  # required for Gemini Developer API runs
    gcloud auth application-default login  # required for Vertex runs
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from google import genai
from google.genai import types


DEFAULT_MODEL = "gemini-2.5-flash-preview-native-audio-dialog"
DEFAULT_PROMPT = "Respond with the single word hello."
DEFAULT_PROJECT = os.environ.get("VERTEX_PROJECT", "sascha-playground-doit")
DEFAULT_LOCATION = os.environ.get("VERTEX_LOCATION", "us-central1")
DEFAULT_VERTEX_MODEL = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash-live-preview-04-09")
DEFAULT_VERTEX_API_VERSION = os.environ.get("VERTEX_API_VERSION", "v1")
TARGET_SAMPLE_RATE = 24_000
SAMPLE_WIDTH_BYTES = 2


@dataclass
class TrialMetrics:
    """Container for a single benchmark run."""

    backend: str
    run_index: int
    connect_time_s: float
    first_chunk_latency_s: Optional[float]
    total_latency_s: Optional[float]
    chunk_count: int
    bytes_received: int
    token_usage: Optional[int]
    audio_path: Optional[str] = None

    def to_row(self) -> Tuple[int, float, Optional[float], Optional[float], int, int, Optional[int]]:
        return (
            self.run_index,
            self.connect_time_s * 1_000,
            None if self.first_chunk_latency_s is None else self.first_chunk_latency_s * 1_000,
            None if self.total_latency_s is None else self.total_latency_s * 1_000,
            self.chunk_count,
            self.bytes_received,
            self.token_usage,
        )


def _parse_backends(raw: str) -> List[str]:
    backends = [candidate.strip().lower() for candidate in raw.split(",")]
    seen: List[str] = []
    for backend in backends:
        if backend not in {"developer", "vertex"}:
            raise argparse.ArgumentTypeError(f"Unsupported backend '{backend}'. Use developer or vertex.")
        if backend not in seen:
            seen.append(backend)
    return seen


def _build_config(
    *, modality: str, voice: Optional[str], media_resolution: Optional[str], enable_thoughts: bool
) -> types.LiveConnectConfig:
    response_modalities = [modality.upper()]
    speech_config = None
    if modality.upper() == "AUDIO" and voice:
        speech_config = types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))
        )

    # Disable thinking by default to avoid extra tokens; enable via flag.
    thinking_budget = 0
    thinking_kwargs: Dict[str, Any] = {"thinking_budget": thinking_budget}
    if enable_thoughts:
        thinking_kwargs.update({"thinking_budget": 1024, "include_thoughts": True})
    thinking_config = types.ThinkingConfig(**thinking_kwargs)

    kwargs: Dict[str, Any] = {"response_modalities": response_modalities}
    if speech_config:
        kwargs["speech_config"] = speech_config
    if media_resolution:
        kwargs["media_resolution"] = getattr(types.MediaResolution, media_resolution)
    if thinking_config:
        kwargs["thinking_config"] = thinking_config

    return types.LiveConnectConfig(**kwargs)


def _configure_client(
    backend: str,
    *,
    api_version: str,
    project: str,
    location: str,
    http_timeout_s: float,
) -> genai.Client:
    http_options: Dict[str, Any] = {"api_version": api_version}
    if http_timeout_s:
        http_options["timeout"] = http_timeout_s

    if backend == "developer":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY must be set for developer backend runs.")
        return genai.Client(http_options=http_options, api_key=api_key)

    return genai.Client(
        vertexai=True,
        project=project,
        location=location,
        http_options=http_options,
    )


async def _send_prompt_and_measure(
    *,
    session: genai.aio.live._LiveSession,  # type: ignore[attr-defined]
    prompt: Optional[str],
    audio_blob: Optional[bytes],
    audio_mime_type: str,
) -> Tuple[Optional[float], Optional[float], int, int, Optional[int], bytes]:
    """Send the payload and measure first-byte and total latency."""

    send_start = time.perf_counter()

    if audio_blob:
        await session.send(input={"data": audio_blob, "mime_type": audio_mime_type})

    if prompt:
        await session.send(input=prompt, end_of_turn=True)
    else:
        await session.send(end_of_turn=True)

    first_chunk_latency_s: Optional[float] = None
    chunk_count = 0
    bytes_received = 0
    token_usage: Optional[int] = None
    last_timestamp = send_start
    audio_chunks: List[bytes] = []

    turn = session.receive()
    async for response in turn:
        now = time.perf_counter()
        had_payload = False

        if response.data:
            chunk_count += 1
            bytes_received += len(response.data)
            had_payload = True
            audio_chunks.append(response.data)

        if response.text:
            chunk_count += 1
            had_payload = True

        if response.usage_metadata:
            token_usage = response.usage_metadata.total_token_count

        if had_payload and first_chunk_latency_s is None:
            first_chunk_latency_s = now - send_start

        last_timestamp = now

    total_latency_s = None if chunk_count == 0 else last_timestamp - send_start
    audio_payload = b"".join(audio_chunks)
    return first_chunk_latency_s, total_latency_s, chunk_count, bytes_received, token_usage, audio_payload


async def _run_single_trial(
    *,
    backend: str,
    run_index: int,
    client: genai.Client,
    model: str,
    config: types.LiveConnectConfig,
    prompt: Optional[str],
    audio_blob: Optional[bytes],
    audio_mime_type: str,
    artifact_dir: Optional[Path],
) -> TrialMetrics:
    connect_start = time.perf_counter()
    async with client.aio.live.connect(model=model, config=config) as session:
        connect_time = time.perf_counter() - connect_start

        (
            first_chunk_latency,
            total_latency,
            chunk_count,
            bytes_received,
            token_usage,
            audio_payload,
        ) = await _send_prompt_and_measure(
            session=session,
            prompt=prompt,
            audio_blob=audio_blob,
            audio_mime_type=audio_mime_type,
        )

    audio_file: Optional[str] = None
    if artifact_dir and run_index > 0 and audio_payload:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        audio_path = artifact_dir / f"{backend}_run{run_index}.wav"
        with wave.open(str(audio_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(SAMPLE_WIDTH_BYTES)
            wf.setframerate(TARGET_SAMPLE_RATE)
            wf.writeframes(audio_payload)
        audio_file = str(audio_path.resolve())

    return TrialMetrics(
        backend=backend,
        run_index=run_index,
        connect_time_s=connect_time,
        first_chunk_latency_s=first_chunk_latency,
        total_latency_s=total_latency,
        chunk_count=chunk_count,
        bytes_received=bytes_received,
        token_usage=token_usage,
        audio_path=audio_file,
    )


async def _run_backend_trials(
    *,
    backend: str,
    client: genai.Client,
    iterations: int,
    warmup: int,
    delay_between_s: float,
    model: str,
    config: types.LiveConnectConfig,
    prompt: Optional[str],
    audio_blob: Optional[bytes],
    audio_mime_type: str,
    artifact_dir: Optional[Path],
) -> List[TrialMetrics]:
    # Warmup runs are executed but not recorded; they help remove initial jitters.
    for _ in range(warmup):
        await _run_single_trial(
            backend=backend,
            run_index=-1,
            client=client,
            model=model,
            config=config,
            prompt=prompt,
            audio_blob=audio_blob,
            audio_mime_type=audio_mime_type,
            artifact_dir=None,
        )
        if delay_between_s:
            await asyncio.sleep(delay_between_s)

    results: List[TrialMetrics] = []
    for run_index in range(1, iterations + 1):
        metrics = await _run_single_trial(
            backend=backend,
            run_index=run_index,
            client=client,
            model=model,
            config=config,
            prompt=prompt,
            audio_blob=audio_blob,
            audio_mime_type=audio_mime_type,
            artifact_dir=artifact_dir,
        )
        results.append(metrics)
        if delay_between_s:
            await asyncio.sleep(delay_between_s)

    return results


def _render_table(metrics: Sequence[TrialMetrics]) -> str:
    headers = ("Run", "Connect (ms)", "First Chunk (ms)", "Total (ms)", "Chunks", "Bytes", "Tokens")
    rows = [metric.to_row() for metric in metrics]

    # Compute column widths.
    cols = list(zip(headers, *rows))
    widths = [max(len(str(val)) for val in column) for column in cols]

    def render_row(values: Iterable[Any]) -> str:
        pieces = []
        for idx, value in enumerate(values):
            formatted = "—" if value is None else f"{value:.2f}" if isinstance(value, float) else str(value)
            pieces.append(formatted.rjust(widths[idx]))
        return " | ".join(pieces)

    lines = [render_row(headers)]
    lines.append("-" * len(lines[0]))
    for row in rows:
        lines.append(render_row(row))
    return "\n".join(lines)


def _summarize(metrics: Sequence[TrialMetrics]) -> Dict[str, Optional[float]]:
    def safe_mean(values: List[Optional[float]]) -> Optional[float]:
        filtered = [value for value in values if value is not None]
        return None if not filtered else statistics.mean(filtered)

    return {
        "connect_ms": safe_mean([m.connect_time_s * 1_000 for m in metrics]),
        "first_chunk_ms": safe_mean([None if m.first_chunk_latency_s is None else m.first_chunk_latency_s * 1_000 for m in metrics]),
        "total_ms": safe_mean([None if m.total_latency_s is None else m.total_latency_s * 1_000 for m in metrics]),
        "chunks": statistics.mean([m.chunk_count for m in metrics]),
        "bytes": statistics.mean([m.bytes_received for m in metrics]),
    }


def _print_summary(backend: str, metrics: Sequence[TrialMetrics]) -> None:
    print(f"\nBackend: {backend}")
    if not metrics:
        print("  No metrics recorded.")
        return
    print(_render_table(metrics))
    summary = _summarize(metrics)
    fmt_opt = lambda value: "—" if value is None else f"{value:.2f}"
    print("\nAverages:")
    print(
        f"  connect: {fmt_opt(summary['connect_ms'])} ms | "
        f"first chunk: {fmt_opt(summary['first_chunk_ms'])} ms | "
        f"total: {fmt_opt(summary['total_ms'])} ms | "
        f"chunks: {fmt_opt(summary['chunks'])} | "
        f"bytes: {fmt_opt(summary['bytes'])}"
    )


def _write_output(path: Path, metrics: Dict[str, List[TrialMetrics]]) -> None:
    serializable = {
        backend: [asdict(result) for result in backend_results] for backend, backend_results in metrics.items()
    }
    path.write_text(json.dumps(serializable, indent=2) + "\n", encoding="utf-8")


def _load_audio_blob(path: Optional[Path]) -> Tuple[Optional[bytes], str]:
    if not path:
        return None, "audio/pcm"
    data = path.read_bytes()
    # Assume the file is already PCM 16k mono. Users can convert separately.
    return data, "audio/pcm;rate=16000"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Gemini Live API latency.")
    parser.add_argument(
        "--backends",
        type=_parse_backends,
        default="developer,vertex",
        help="Comma separated list of backends to benchmark: developer, vertex.",
    )
    parser.add_argument("--iterations", type=int, default=3, help="Number of recorded runs per backend.")
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup runs per backend.")
    parser.add_argument("--delay-between", type=float, default=0.5, help="Delay between runs in seconds.")
    parser.add_argument("--prompt", type=str, default=DEFAULT_PROMPT, help="Text prompt to send with the request.")
    parser.add_argument("--prompt-file", type=Path, help="Optional path to a file whose contents override --prompt.")
    parser.add_argument("--input-audio", type=Path, help="Optional PCM audio file to send with each request.")
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help="Primary model identifier (used for all backends unless overridden).",
    )
    parser.add_argument(
        "--vertex-model",
        type=str,
        default=DEFAULT_VERTEX_MODEL,
        help="Optional model identifier to use specifically for Vertex AI runs (defaults to env VERTEX_MODEL or built-in).",
    )
    parser.add_argument(
        "--modality",
        choices=("AUDIO", "TEXT"),
        default="AUDIO",
        help="Desired response modality.",
    )
    parser.add_argument("--voice", type=str, default="Zephyr", help="Voice name for audio modality.")
    parser.add_argument(
        "--media-resolution",
        choices=("MEDIA_RESOLUTION_LOW", "MEDIA_RESOLUTION_MEDIUM", "MEDIA_RESOLUTION_HIGH"),
        default="MEDIA_RESOLUTION_MEDIUM",
        help="Media resolution hint for video inputs.",
    )
    parser.add_argument(
        "--enable-thoughts",
        action="store_true",
        help="Enable thinking outputs (uses additional tokens and latency).",
    )
    parser.add_argument("--api-version", type=str, default="v1beta", help="Gemini Developer API version to target.")
    parser.add_argument(
        "--vertex-api-version",
        type=str,
        default=DEFAULT_VERTEX_API_VERSION,
        help="Vertex AI Live API version (defaults to env VERTEX_API_VERSION or v1).",
    )
    parser.add_argument("--project", type=str, default=DEFAULT_PROJECT, help="Vertex AI project id.")
    parser.add_argument("--location", type=str, default=DEFAULT_LOCATION, help="Vertex AI location.")
    parser.add_argument(
        "--http-timeout",
        type=float,
        default=300.0,
        help="HTTP timeout (seconds) for Live API connections.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("artifacts"),
        help="Base directory for saving captured audio artifacts (subfolders per backend).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write raw metrics as JSON.",
    )

    args = parser.parse_args(argv)
    if isinstance(args.backends, list):
        args.backends = args.backends
    else:
        args.backends = _parse_backends(args.backends)

    if args.prompt_file:
        args.prompt = args.prompt_file.read_text(encoding="utf-8").strip()

    return args


async def main_async(args: argparse.Namespace) -> int:
    config = _build_config(
        modality=args.modality,
        voice=args.voice,
        media_resolution=args.media_resolution,
        enable_thoughts=args.enable_thoughts,
    )
    audio_blob, audio_mime = _load_audio_blob(args.input_audio)
    artifact_root: Optional[Path] = args.artifact_dir if args.artifact_dir else None

    all_metrics: Dict[str, List[TrialMetrics]] = {}
    for backend in args.backends:
        try:
            api_version = args.api_version
            if backend == "vertex":
                api_version = args.vertex_api_version or args.api_version
            client = _configure_client(
                backend,
                api_version=api_version,
                project=args.project,
                location=args.location,
                http_timeout_s=args.http_timeout,
            )
        except Exception as exc:  # pragma: no cover - configuration errors
            print(f"Skipping backend '{backend}' due to configuration error: {exc}", file=sys.stderr)
            continue

        model_name = args.model
        if backend == "vertex" and args.vertex_model:
            model_name = args.vertex_model

        print(f"Running backend '{backend}' with model '{model_name}' ...")
        backend_artifact_dir = artifact_root.joinpath(backend) if artifact_root else None
        metrics = await _run_backend_trials(
            backend=backend,
            client=client,
            iterations=args.iterations,
            warmup=args.warmup,
            delay_between_s=args.delay_between,
            model=model_name,
            config=config,
            prompt=args.prompt,
            audio_blob=audio_blob,
            audio_mime_type=audio_mime,
            artifact_dir=backend_artifact_dir,
        )
        _print_summary(backend, metrics)
        all_metrics[backend] = metrics

    if args.output and all_metrics:
        _write_output(args.output, all_metrics)
        print(f"\nRaw metrics written to {args.output}")

    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:  # pragma: no cover - interactive usage
        print("\nInterrupted, exiting.")
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
