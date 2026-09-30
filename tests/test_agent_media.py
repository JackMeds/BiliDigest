import json
import shutil
import subprocess

import pytest

from tools.agent import media
from tools.agent.store import AgentError


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg is optional on unit-test hosts")
@pytest.mark.parametrize("mode,expect_video", [("audio-preferred", True), ("audio", False), ("video", True)])
def test_combined_media_fallback_preserves_all_segments(tmp_path, monkeypatch, mode, expect_video):
    source = tmp_path / "source.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=size=32x32:rate=10", "-f", "lavfi", "-i", "sine=frequency=400:sample_rate=16000", "-t", "1", "-c:v", "mpeg4", "-c:a", "aac", str(source)], check=True)
    class Client:
        def request_json(self, *args, **kwargs):
            return {"data": {"format": "mp4", "durl": [{"url": "https://cdn.bilivideo.com/1"}, {"url": "https://cdn.bilivideo.com/2"}]}}
    calls = []
    def download(urls, path, cancelled):
        calls.append(urls[0])
        shutil.copyfile(source, path)
    monkeypatch.setattr(media, "download_file", download)
    result = media.download_media(Client(), {"bvid": "BV1234567890"}, {"cid": 1, "page": 1}, mode, tmp_path / "out")
    info = media.validate_media(result, 2)
    assert info["full_decode"]
    assert len(calls) == 2
    streams = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(result)]))["streams"]
    assert any(s["codec_type"] == "video" for s in streams) == expect_video


def test_media_redirect_does_not_reach_an_unapproved_host(monkeypatch):
    from tools.agent import platform
    class Redirect:
        status_code = 302
        headers = {"Location": "https://localhost/private"}
        def close(self): pass
    visited = []
    def get(url, **kwargs):
        visited.append(url)
        assert "cookies" not in kwargs
        return Redirect()
    monkeypatch.setattr(platform.requests, "get", get)
    with pytest.raises(AgentError):
        platform.public_get("https://cdn.bilivideo.com/audio")
    assert visited == ["https://cdn.bilivideo.com/audio"]
