"""
voice.py — entrada por voz (transcrição local) via Faster-Whisper.

Tier 3 (CA-300). Opt-in e opcional: o Whisper local NÃO é dependência do mad
(é pesado). Se `faster-whisper` estiver instalado, transcreve um arquivo de áudio
localmente (privado, sem enviar pra nuvem). Senão, instrui a instalar.

Gravação de microfone é específica de plataforma (sounddevice/ffmpeg) e fica fora
do core; aqui transcrevemos um arquivo que o usuário já gravou. TTS (CA-301) é
roadmap.

Uso: python scripts/mad.py voice <audio.wav|mp3|m4a> [--model small]
Instalar:  pip install faster-whisper
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402

DEFAULT_MODEL = "small"


def available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ModuleNotFoundError:
        return False


def transcribe(audio_path: str, model_size: str = DEFAULT_MODEL) -> str | None:
    if not available():
        return None
    from faster_whisper import WhisperModel  # type: ignore
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(audio_path)
    return " ".join(seg.text.strip() for seg in segments).strip()


def cli(args) -> int:
    if not available():
        print(u.c("○ Voz não disponível: falta 'faster-whisper'.", "yellow"))
        print("  Instale (opt-in, roda 100% local): pip install faster-whisper")
        return 1
    audio = getattr(args, "audio", None)
    if not audio or not Path(audio).is_file():
        print(u.c(f"✗ Arquivo de áudio não encontrado: {audio}", "red"))
        return 1
    model = getattr(args, "model", None) or DEFAULT_MODEL
    print(u.c(f"⏳ transcrevendo {audio} (modelo {model}, local)…", "dim"))
    text = transcribe(audio, model)
    if not text:
        print(u.c("▲ transcrição vazia.", "yellow"))
        return 1
    print(u.c("\n  texto transcrito:", "bold"))
    print("  " + text)
    u.emit_span("voice.transcribed", {"chars": len(text), "model": model})
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("--model", default=DEFAULT_MODEL)
    sys.exit(cli(p.parse_args()))
