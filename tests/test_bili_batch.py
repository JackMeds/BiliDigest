import json
from types import SimpleNamespace

from tools import bili_batch, bilisub
from tools.bili_client import BiliError


def test_get_watch_later_items_uses_fresh_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(bili_batch, "CACHE_DIR", tmp_path)
    items_path, meta_path = bili_batch.cache_paths("watch-later")
    items_path.parent.mkdir(parents=True, exist_ok=True)
    items_path.write_text(json.dumps({"bvid": "BV1234567890", "title": "缓存视频"}) + "\n", encoding="utf-8")
    bili_batch.save_json(
        meta_path,
        {
            "count": 1,
            "exhausted": False,
            "fetched_at_epoch": 9_999_999_999,
        },
    )
    monkeypatch.setattr(bili_batch, "watch_later", lambda client, limit: (_ for _ in ()).throw(AssertionError("network called")))

    items, info = bili_batch.get_watch_later_items(object(), 1, cache_ttl=86_400)

    assert info["source"] == "cache"
    assert items[0]["bvid"] == "BV1234567890"


def test_state_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(bili_batch, "STATE_DIR", tmp_path)
    state = bili_batch.load_state("watch-later")
    state["completed"]["BV1234567890"] = {"title": "完成"}

    path = bili_batch.save_state("watch-later", state)
    loaded = bili_batch.load_state("watch-later")

    assert path == tmp_path / "watch-later.json"
    assert loaded["completed"]["BV1234567890"]["title"] == "完成"


def test_batch_fallback_summary_records_summary_only(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bili_batch, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(bilisub, "dated_output_dir", lambda: tmp_path / "out")
    monkeypatch.setattr(
        bilisub,
        "get_watch_later_items",
        lambda client, limit, cache_ttl, refresh, progress: (
            [{"bvid": "BV1234567890", "title": "无字幕视频"}],
            {"source": "cache"},
        ),
    )
    monkeypatch.setattr(
        bilisub,
        "export_transcript",
        lambda client, bvid, fmt, out_dir: (_ for _ in ()).throw(BiliError("No Bilibili subtitle is available")),
    )
    monkeypatch.setattr(
        bilisub,
        "export_summary",
        lambda client, bvid, out_dir: {"path": str(out_dir / "summary.md")},
    )
    args = SimpleNamespace(
        kind="watch-later",
        limit=1,
        with_summary=False,
        fallback_summary=True,
        cache_ttl=86_400,
        refresh_list=False,
        resume=False,
        retry_failed=False,
    )

    assert bilisub.cmd_batch(args) == 0
    output = json.loads(capsys.readouterr().out)
    state = json.loads((tmp_path / "state" / "watch-later.json").read_text(encoding="utf-8"))

    assert output["completed"] == 1
    assert state["completed"]["BV1234567890"]["status"] == "summary_only"
