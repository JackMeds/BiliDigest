import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from ..bili_client import BiliError, RiskControl
from ..bili_subtitle import choose_subtitle, body_to_srt
from .platform import public_get
from .store import AgentError, atomic_json, sha256


def checked_process(args, cancelled=lambda: False, *, log=None):
    if not shutil.which(args[0]):
        raise AgentError("DEPENDENCY_MISSING", f"Required executable is missing: {args[0]}")
    # Subprocess output goes to disk, never an undrained PIPE.
    log = Path(log or os.devnull)
    with log.open("w", encoding="utf-8") as f:
        process = subprocess.Popen(args, stdout=f, stderr=f, stdin=subprocess.DEVNULL)
        try:
            while process.poll() is None:
                if cancelled():
                    raise AgentError("CANCELLED", "Job cancelled; completed artifacts retained")
                time.sleep(0.25)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        if process.returncode:
            raise AgentError("PROCESS_FAILED", f"{Path(args[0]).name} failed (exit {process.returncode}); inspect the local job log", retryable=True)


def validate_media(path, duration, cancelled=lambda: False):
    if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
        raise AgentError("DEPENDENCY_MISSING", "ffmpeg and ffprobe are required for media validation")
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name", "-of", "json", str(path)], capture_output=True, text=True, timeout=60)
    try:
        info = json.loads(result.stdout)
        actual = float(info["format"]["duration"])
        assert result.returncode == 0 and any(s["codec_type"] == "audio" for s in info["streams"])
        assert not duration or abs(actual - duration) <= max(5, duration * .02)
    except (ValueError, KeyError, AssertionError):
        raise AgentError("VALIDATION_FAILED", "Missing audio stream or media duration does not match the source", retryable=True)
    checked_process(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"], cancelled)
    return {"seconds": actual, "bytes": Path(path).stat().st_size, "sha256": sha256(path), "full_decode": True}


def download_file(urls, path, cancelled=lambda: False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    control = path.with_name(path.name + ".transfer.json")
    for url in urls:
        if not url:
            continue
        try:
            if cancelled():
                raise AgentError("CANCELLED", "Job cancelled")
            offset = partial.stat().st_size if partial.exists() else 0
            headers = {}
            if offset:
                headers["Range"] = f"bytes={offset}-"
                if control.exists():
                    etag = json.loads(control.read_text()).get("etag")
                    if etag:
                        headers["If-Range"] = etag
            with public_get(url, headers=headers) as response:
                if response.status_code == 416:
                    # Do not treat a stale oversized partial as a complete file.
                    total = response.headers.get("Content-Range", "").split("/")[-1]
                    if total.isdigit() and offset == int(total):
                        partial.replace(path)
                        return path
                    partial.unlink(missing_ok=True)
                    continue
                response.raise_for_status()
                append = response.status_code == 206 and offset > 0
                if append and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                    raise AgentError("DOWNLOAD_FAILED", "Server returned an unexpected byte range", retryable=True)
                atomic_json(control, {"etag": response.headers.get("ETag")})
                size = 0
                with partial.open("ab" if append else "wb") as f:
                    for chunk in response.iter_content(1024 * 1024):
                        if cancelled():
                            raise AgentError("CANCELLED", "Job cancelled; partial transfer retained")
                        f.write(chunk)
                        size += len(chunk)
                expected = response.headers.get("Content-Length")
                if expected and size != int(expected):
                    raise AgentError("DOWNLOAD_FAILED", "Incomplete media response", retryable=True)
                if partial.stat().st_size == 0:
                    raise AgentError("DOWNLOAD_FAILED", "Empty media response", retryable=True)
                partial.replace(path)
                control.unlink(missing_ok=True)
                return path
        except (AgentError, RiskControl):
            raise
        except Exception:
            # Refreshing expiring URLs is done on job resume. Do not log signed URLs.
            continue
    raise AgentError("DOWNLOAD_FAILED", "Media download failed; resume to refresh its URLs", retryable=True)


def _urls(stream):
    return [stream.get("baseUrl") or stream.get("base_url") or stream.get("url")] + (stream.get("backupUrl") or stream.get("backup_url") or [])


def download_media(client, video, page, mode, folder, cancelled=lambda: False):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stem = f'{video["bvid"]}_P{page["page"]:02d}_{page["cid"]}'
    data = client.request_json("https://api.bilibili.com/x/player/wbi/playurl", {"bvid": video["bvid"], "cid": page["cid"], "fnval": 4048, "qn": 64}, wbi=True)["data"]
    dash = data.get("dash") or {}
    audios = dash.get("audio") or []
    if audios:
        # Prefer broadly playable AAC; fall back to an advertised alternative with its true extension.
        aac = [s for s in audios if str(s.get("codecs", "")).startswith("mp4a")]
        audio = max(aac or audios, key=lambda s: s.get("bandwidth", 0))
        codec = str(audio.get("codecs", ""))
        ext = ".flac" if "flac" in codec else ".m4a"
        audio_path = folder / (stem + ext)
        download_file(_urls(audio), audio_path, cancelled)
        if mode != "video":
            return audio_path
        videos = dash.get("video") or []
        if not videos:
            raise AgentError("NO_PLAYABLE_MEDIA", "No video track is available")
        chosen = max(videos, key=lambda s: (s.get("height", 0), s.get("bandwidth", 0)))
        video_path = folder / (stem + ".video.m4s")
        download_file(_urls(chosen), video_path, cancelled)
        result = folder / (stem + ".mkv")
        temp = folder / (stem + ".muxing.mkv")
        checked_process(["ffmpeg", "-v", "error", "-y", "-i", str(video_path), "-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", str(temp)], cancelled)
        temp.replace(result)
        video_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)
        return result
    segments = data.get("durl") or []
    if not segments:
        raise AgentError("NO_PLAYABLE_MEDIA", "No accessible audio or combined video is available")
    extension = ".flv" if "flv" in str(data.get("format", "")) else ".mp4"
    paths = []
    for i, segment in enumerate(segments):
        path = folder / f"{stem}.segment{i:03d}{extension}"
        download_file(_urls(segment), path, cancelled)
        paths.append(path)
    result = folder / (stem + (".m4a" if mode == "audio" else ".mkv"))
    temp = folder / (stem + (".muxing.m4a" if mode == "audio" else ".muxing.mkv"))
    listing = folder / (stem + ".concat.txt")
    listing.write_text("\n".join(f"file '{p.name}'" for p in paths), encoding="utf-8")
    options = ["-vn", "-c:a", "aac", "-b:a", "192k"] if mode == "audio" else ["-c", "copy"]
    checked_process(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "1", "-i", str(listing), *options, str(temp)], cancelled)
    temp.replace(result)
    for p in paths:
        p.unlink(missing_ok=True)
    listing.unlink(missing_ok=True)
    return result


def existing_subtitle(client, video, page):
    player = client.player_info(video["aid"], page["cid"])
    options = (player.get("subtitle") or {}).get("subtitles") or []
    if not options:
        return None
    picked = choose_subtitle(options)
    url = picked["subtitle_url"]
    if url.startswith("//"):
        url = "https:" + url
    client.throttle()
    with public_get(url) as response:
        response.raise_for_status()
        body = response.json().get("body") or []
    if not body:
        return None
    return {"body": body, "source": "bilibili_subtitle", "language": picked.get("lan"), "machine_generated": str(picked.get("lan", "")).startswith("ai-")}


def transcribe(path, cache_dir, work_dir, *, model=None, language="auto", cancelled=lambda: False):
    model = Path(model or os.getenv("BILIDIGEST_WHISPER_MODEL", "")).expanduser()
    if not model.is_file() or not shutil.which("whisper-cli"):
        raise AgentError("ASR_UNAVAILABLE", "Install whisper.cpp and set BILIDIGEST_WHISPER_MODEL to a local GGML model, then resume")
    digest = sha256(path)
    version = f"{sha256(model)}:{language}:{sha256(shutil.which('whisper-cli'))}:json-v1"
    cache = Path(cache_dir) / (digest + "-" + hashlib.sha256(version.encode()).hexdigest()[:16] + ".json")
    if cache.is_file():
        result = json.loads(cache.read_text(encoding="utf-8"))
        return {**result, "cache_hit": True}
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    wav, prefix = work_dir / "audio.wav", work_dir / "whisper"
    checked_process(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)], cancelled)
    try:
        checked_process(["whisper-cli", "-m", str(model), "-f", str(wav), "-l", language, "-t", "6", "-oj", "-of", str(prefix)], cancelled, log=work_dir / "asr.log")
        raw = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
        body = [{"from": r["offsets"]["from"] / 1000, "to": r["offsets"]["to"] / 1000, "content": r["text"].strip()} for r in raw["transcription"] if r["text"].strip()]
        if not body:
            raise AgentError("ASR_FAILED", "ASR produced no text", retryable=True)
        result = {"body": body, "source": "whisper.cpp", "language": language, "model": model.name, "model_sha256": version.split(":")[0], "audio_sha256": digest, "machine_generated": True}
        atomic_json(cache, result)
        return result
    finally:
        wav.unlink(missing_ok=True)


def write_transcript(path, transcript, video, page):
    path = Path(path)
    body = transcript["body"]
    if not all(float(r["to"]) >= float(r["from"]) >= 0 for r in body):
        raise AgentError("TRANSCRIPT_INVALID", "Invalid subtitle timestamps")
    value = {**transcript, "video": video, "page": page["page"], "cid": page["cid"]}
    atomic_json(path, value)
    path.with_suffix(".srt").write_text(body_to_srt(body), encoding="utf-8")
    url = f'https://www.bilibili.com/video/{video["bvid"]}?p={page["page"]}'
    lines = [f'# {video["title"]} · P{page["page"]}', "", f"来源：{url}", f'文本来源：{transcript["source"]}；自动文本未经逐句校对。', ""]
    for row in body:
        t = int(row["from"])
        lines.append(f'- [{t // 60:02d}:{t % 60:02d}]({url}&t={t}) {row["content"]}')
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return value
