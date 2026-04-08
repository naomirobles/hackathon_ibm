"""Integración con IBM Speech to Text para SeñalCDMX."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Tuple

import requests


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_local_env()


def _parse_data_uri(contents: str) -> Tuple[str, bytes]:
    header, encoded = contents.split(",", 1)
    mime_type = "audio/wav"
    if ":" in header and ";" in header:
        mime_type = header.split(":", 1)[1].split(";", 1)[0] or mime_type
    return mime_type, base64.b64decode(encoded)


def transcribe_audio(contents: str, filename: str | None = None) -> str:
    """Transcribe an uploaded audio file using IBM Speech to Text."""
    _load_local_env()

    api_key = (
        os.getenv("IBM_STT_API_KEY", "").strip()
        or os.getenv("API_KEY", "").strip()
    )
    service_url = (
        os.getenv("IBM_STT_URL", "").strip()
        or os.getenv("URL", "").strip()
    ).rstrip("/")
    model = (
        os.getenv("IBM_STT_MODEL", "").strip()
        or os.getenv("MODEL", "").strip()
        or "es-LA_Telephony"
    )

    if not api_key or not service_url:
        raise RuntimeError(
            "Falta configurar IBM STT. Define IBM_STT_API_KEY e IBM_STT_URL como variables de entorno."
        )

    content_type, audio_bytes = _parse_data_uri(contents)
    if filename:
        lowered = filename.lower()
        if lowered.endswith(".wav"):
            content_type = "audio/wav"
        elif lowered.endswith(".mp3"):
            content_type = "audio/mpeg"
        elif lowered.endswith(".flac"):
            content_type = "audio/flac"
        elif lowered.endswith(".ogg"):
            content_type = "audio/ogg"
        elif lowered.endswith(".m4a"):
            content_type = "audio/mp4"

    response = requests.post(
        f"{service_url}/v1/recognize",
        params={"model": model},
        auth=("apikey", api_key),
        headers={"Content-Type": content_type},
        data=audio_bytes,
        timeout=120,
    )
    response.raise_for_status()

    payload = response.json()
    transcripts: list[str] = []
    for result in payload.get("results", []):
        alternatives = result.get("alternatives", [])
        if alternatives:
            transcript = alternatives[0].get("transcript", "").strip()
            if transcript:
                transcripts.append(transcript)

    return " ".join(transcripts).strip()
