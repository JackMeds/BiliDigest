"""Local Qwen3-ASR 0.6B MLX 8-bit adapter; never loads Hub Python code."""
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import time
import wave
from pathlib import Path

from .store import AgentError, atomic_json, sha256

BACKEND = "qwen3-asr"
RUNTIME_VERSION = "0.5.8"
CHUNK_SECONDS = 20
MAX_TOKENS = 768


def model_config(path):
    root = Path(path or "").expanduser()
    try:
        config = json.loads((root / "config.json").read_text())
        thinker = config["thinker_config"]
        text, audio = thinker["text_config"], thinker["audio_config"]
        quant = config.get("quantization") or config["quantization_config"]
        valid = (config["model_type"] == "qwen3_asr" and quant["bits"] == 8
                 and text["hidden_size"] == 1024 and text["num_hidden_layers"] == 28
                 and audio["d_model"] == 896 and audio["encoder_layers"] == 18)
        assert valid
        assert list(root.glob("*.safetensors"))
        for name in ("tokenizer_config.json", "preprocessor_config.json", "vocab.json", "merges.txt"):
            assert (root / name).is_file()
        # The supported model is data-only. No pickle weights or Hub code.
        assert not list(root.glob("*.py")) and not list(root.glob("*.bin"))
    except (OSError, ValueError, KeyError, TypeError, AssertionError):
        raise AgentError("INVALID_MODEL", "Expected a local Qwen3-ASR 0.6B MLX 8-bit safetensors directory")
    return root.resolve(), config


def runtime_ready():
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return False
    try:
        return (importlib.metadata.version("mlx-audio") == RUNTIME_VERSION
                and bool(importlib.metadata.version("mlx")))
    except importlib.metadata.PackageNotFoundError:
        return False


def model_identity(path):
    root, _ = model_config(path)
    files = sorted(p for p in root.iterdir() if p.suffix in (".json", ".txt", ".safetensors"))
    digest = hashlib.sha256()
    for p in files:
        digest.update(p.name.encode())
        digest.update(sha256(p).encode())
    return digest.hexdigest()


def normalize_language(language):
    return {"auto": None, "zh": "Chinese", "en": "English", "yue": "Cantonese",
            "ja": "Japanese", "ko": "Korean"}.get(language, language)


def transcribe(path, cache_dir, work_dir, *, model=None, language="auto", cancelled=lambda: False):
    from .media import checked_process
    root, config = model_config(model)
    if not runtime_ready():
        raise AgentError("ASR_UNAVAILABLE", "Qwen requires Apple Silicon and the bilidigest[qwen] runtime; install it, then resume")
    audio_hash, model_hash = sha256(path), model_identity(root)
    identity = {"backend": BACKEND, "model_sha256": model_hash, "language": language,
                "mlx_audio": RUNTIME_VERSION, "mlx": importlib.metadata.version("mlx"),
                "adapter_sha256": sha256(Path(__file__)), "chunk_seconds": CHUNK_SECONDS,
                "max_tokens": MAX_TOKENS, "timestamp_kind": "chunk_boundaries"}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    cache_dir, work_dir = Path(cache_dir), Path(work_dir)
    cache = cache_dir / (audio_hash + "-" + key + ".json")
    if cache.is_file():
        result = json.loads(cache.read_text())
        return {**result, "cache_hit": True}
    work_dir.mkdir(parents=True, exist_ok=True)
    chunks = cache_dir / "qwen-chunks" / (audio_hash + "-" + key)
    chunks.mkdir(parents=True, exist_ok=True)
    wav, output = work_dir / "qwen-audio.wav", work_dir / "qwen-result.json"
    checked_process(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-ar", "16000",
                     "-ac", "1", "-c:a", "pcm_s16le", str(wav)], cancelled)
    try:
        checked_process([sys.executable, "-m", "tools.agent.qwen_asr", str(root), str(wav),
                         str(chunks), str(output), language], cancelled, log=work_dir / "qwen-asr.log")
        result = json.loads(output.read_text())
        if not result["body"]:
            raise AgentError("ASR_FAILED", "Qwen produced no text", retryable=True)
        result.update(source="qwen3-asr-mlx", model=root.name, model_sha256=model_hash,
                      audio_sha256=audio_hash, machine_generated=True, cache_identity=identity,
                      quantization=config["quantization"], timestamp_kind="chunk_boundaries")
        atomic_json(cache, result)
        return result
    finally:
        wav.unlink(missing_ok=True)


def load_local_model(root):
    """Bypass mlx-audio's auto loader (its post_load_hook enables remote code)."""
    import mlx.core as mx
    from mlx_audio.stt.models.qwen3_asr.config import ModelConfig
    from mlx_audio.stt.models.qwen3_asr.qwen3_asr import Qwen3ASRModel
    from mlx_audio.utils import apply_quantization
    from transformers import AutoTokenizer, WhisperFeatureExtractor
    root, config = model_config(root)
    model = Qwen3ASRModel(ModelConfig.from_dict(config))
    weights = {}
    for p in sorted(root.glob("*.safetensors")):
        weights.update(mx.load(str(p)))
    weights = model.sanitize(weights)
    apply_quantization(model, config, weights, model.model_quant_predicate)
    model.load_weights(list(weights.items()), strict=True)
    mx.eval(model.parameters())
    model.eval()
    model._tokenizer = AutoTokenizer.from_pretrained(str(root), local_files_only=True, trust_remote_code=False)
    # Qwen uses this log-mel frontend; it is not a Whisper ASR model/runtime.
    model._feature_extractor = WhisperFeatureExtractor.from_pretrained(str(root), local_files_only=True)
    return model


def run_chunks(wav_path, chunk_dir, generate, language):
    """Persist each finished 20s chunk so an interrupted long job can resume."""
    import numpy as np
    body, hits = [], 0
    with wave.open(str(wav_path), "rb") as wav:
        assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) == (16000, 1, 2)
        total, rate = wav.getnframes(), wav.getframerate()
        for index, start in enumerate(range(0, total, rate * CHUNK_SECONDS)):
            end = min(total, start + rate * CHUNK_SECONDS)
            raw = wav.readframes(end - start)
            cache = Path(chunk_dir) / f"{index:06d}.json"
            saved = json.loads(cache.read_text()) if cache.is_file() else None
            if saved is not None and saved.get("from") == start / rate and saved.get("to") == end / rate:
                hits += 1
            else:
                audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
                output = generate(audio, language=normalize_language(language), max_tokens=MAX_TOKENS,
                                  temperature=0.0, verbose=False)
                if output.generation_tokens >= MAX_TOKENS:
                    raise RuntimeError("Qwen token limit reached; refusing a truncated transcript")
                saved = {"from": start / rate, "to": end / rate, "content": output.text.strip()}
                atomic_json(cache, saved)
            if saved["content"]:
                body.append(saved)
    return {"body": body, "language": language, "duration_seconds": total / rate, "chunk_cache_hits": hits}


def worker(model_path, wav_path, chunk_dir, output_path, language):
    # No network or model-side Python code is needed for inference.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    import resource
    import mlx.core as mx
    started = time.monotonic()
    model = load_local_model(model_path)
    loaded = time.monotonic()
    result = run_chunks(wav_path, chunk_dir, model.generate, language)
    result["metrics"] = {"load_seconds": loaded - started, "total_seconds": time.monotonic() - started,
                         "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                         "mlx_peak_bytes": mx.get_peak_memory()}
    atomic_json(output_path, result)


if __name__ == "__main__":
    worker(*sys.argv[1:])
