import json

from tools import bili_digest


def test_read_subtitle_segments_normalizes_common_asr_errors(tmp_path):
    subtitle = tmp_path / "video.subtitle.json"
    subtitle.write_text(
        json.dumps(
            {
                "video": {"title": "测试", "bvid": "BV1234567890"},
                "body": [
                    {"from": 1.0, "to": 2.0, "content": "deep sick V4pro 用在 open che 里"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    video, segments = bili_digest.read_subtitle_segments(subtitle)

    assert video["bvid"] == "BV1234567890"
    assert segments[0]["text"] == "DeepSeek V4 Pro 用在 OpenClaw 里"


def test_export_transcript_digest_writes_digest_with_fake_model(tmp_path, monkeypatch):
    subtitle = tmp_path / "video.subtitle.json"
    subtitle.write_text(
        json.dumps(
            {
                "video": {"title": "测试视频", "bvid": "BV1234567890"},
                "body": [{"from": 1.0, "to": 2.0, "content": "第一句字幕"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(bili_digest, "complete_digest", lambda prompt: "# 测试视频 - 字幕深度摘要\n\n## 字幕纠错记录\n无\n")
    monkeypatch.setattr(bili_digest, "digest_model", lambda: "fake-model")
    transcript = {"paths": {"json": str(subtitle)}}

    result = bili_digest.export_transcript_digest(transcript, out_dir=tmp_path)

    assert result["path"].endswith(".digest.md")
    assert result["segments"] == 1
    assert result["model"] == "fake-model"
    assert "字幕深度摘要" in (tmp_path / "测试视频-BV1234567890.digest.md").read_text(encoding="utf-8")


def test_digest_timeout_has_default_and_env_override(monkeypatch):
    monkeypatch.delenv("BILIDIGEST_LLM_TIMEOUT_SECONDS", raising=False)
    assert bili_digest.digest_timeout() == bili_digest.DEFAULT_TIMEOUT_SECONDS

    monkeypatch.setenv("BILIDIGEST_LLM_TIMEOUT_SECONDS", "12.5")
    assert bili_digest.digest_timeout() == 12.5

    monkeypatch.setenv("BILIDIGEST_LLM_TIMEOUT_SECONDS", "bad")
    assert bili_digest.digest_timeout() == bili_digest.DEFAULT_TIMEOUT_SECONDS
