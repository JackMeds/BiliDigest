import json
import wave
from types import SimpleNamespace

import pytest

from tools.agent import qwen_asr, media, platform
from tools.agent.service import Service
from tools.agent.store import AgentError, Store


@pytest.fixture
def model(tmp_path):
    root = tmp_path / "model"
    root.mkdir()
    config = {"model_type": "qwen3_asr", "quantization": {"bits": 8},
              "thinker_config": {"text_config": {"hidden_size": 1024, "num_hidden_layers": 28},
                                 "audio_config": {"d_model": 896, "encoder_layers": 18}}}
    (root / "config.json").write_text(json.dumps(config))
    for name in ("tokenizer_config.json", "preprocessor_config.json", "vocab.json", "merges.txt", "model.safetensors"):
        (root / name).write_text("{}")
    return root


def test_configure_qwen_replaces_whisper_and_sets_plan_default(tmp_path, model):
    service = Service(Store(tmp_path / "data", tmp_path / "out"), SimpleNamespace(cookies={}))
    old = tmp_path / "whisper.bin"
    old.write_bytes(b"old")
    service.configure(str(old))
    result = service.configure(asr_backend="qwen3-asr", asr_model=str(model))
    assert result["asr_backend"] == "qwen3-asr"
    assert "whisper_model" not in service.settings()
    assert old.exists()  # configuring a backend must not delete user files
    snap = service.store.save_resource("snapshots", {"source": "BV1234567890", "complete": True,
        "items": [{"bvid": "BV1234567890", "title": "sample"}]})
    assert service.plan(snap["id"])["options"]["asr"] == "qwen3-asr"
    assert service.plan(snap["id"], asr="none")["options"]["asr"] == "none"


@pytest.mark.parametrize("change", ["4bit", "1.7b", "python"])
def test_rejects_wrong_model_or_remote_code(model, change):
    p = model / "config.json"
    config = json.loads(p.read_text())
    if change == "4bit":
        config["quantization"]["bits"] = 4
    elif change == "1.7b":
        config["thinker_config"]["text_config"]["hidden_size"] = 2048
    else:
        (model / "modeling.py").write_text("raise RuntimeError()")
    p.write_text(json.dumps(config))
    with pytest.raises(AgentError):
        qwen_asr.model_config(model)


def test_identity_tracks_weights_and_tokenizer(model):
    first = qwen_asr.model_identity(model)
    (model / "model.safetensors").write_bytes(b"changed")
    second = qwen_asr.model_identity(model)
    assert second != first
    (model / "vocab.json").write_text('{"new":1}')
    assert qwen_asr.model_identity(model) != second


def test_chunk_resume_timestamps_and_last_partial_chunk(tmp_path):
    pytest.importorskip("numpy")
    wav = tmp_path / "sample.wav"
    with wave.open(str(wav), "wb") as f:
        f.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        f.writeframes(b"\0\0" * (16000 * 45))
    cache = tmp_path / "chunks"
    cache.mkdir()
    seen = []
    def first(audio, **kwargs):
        seen.append(len(audio))
        assert kwargs["language"] == "Chinese"
        if len(seen) == 2:
            raise RuntimeError("interrupted")
        return SimpleNamespace(text="第一段", generation_tokens=3)
    with pytest.raises(RuntimeError, match="interrupted"):
        qwen_asr.run_chunks(wav, cache, first, "zh")
    seen.clear()
    def resumed(audio, **kwargs):
        seen.append(len(audio))
        return SimpleNamespace(text="继续", generation_tokens=2)
    result = qwen_asr.run_chunks(wav, cache, resumed, "zh")
    assert seen == [320000, 80000]
    assert result["chunk_cache_hits"] == 1
    assert [(x["from"], x["to"]) for x in result["body"]] == [(0, 20), (20, 40), (40, 45)]


def test_qwen_failure_resume_keeps_download(tmp_path, monkeypatch, model):
    from test_agent_workflow import fake_pipeline, make_plan
    service = Service(Store(tmp_path / "data", tmp_path / "out"), SimpleNamespace(cookies={}))
    service.configure(asr_backend="qwen3-asr", asr_model=str(model))
    calls = fake_pipeline(monkeypatch, service, pages=1)
    monkeypatch.setattr(media, "existing_subtitle", lambda *a: None)
    monkeypatch.setattr(qwen_asr, "transcribe", lambda *a, **kw: (_ for _ in ()).throw(AgentError("ASR_UNAVAILABLE", "missing runtime")))
    job = service.start(make_plan(service)["id"], background=False)
    assert job["state"] == "partial"
    monkeypatch.setattr(qwen_asr, "transcribe", lambda *a, **kw: {"source": "qwen3-asr-mlx", "timestamp_kind": "chunk_boundaries", "body": [{"from": 0, "to": 5, "content": "中文测试"}]})
    resumed = service.resume(job["id"], background=False)
    assert resumed["state"] == "complete"
    assert calls["download"] == [10]
    transcript = next(iter(resumed["parts"].values()))["transcript"]
    assert json.loads((service.store.job_dir(job["id"]) / transcript).read_text())["timestamp_kind"] == "chunk_boundaries"
