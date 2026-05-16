from tools.bili_library import normalize_video


def test_normalize_watch_later_item():
    item = {
        "title": "测试视频",
        "bvid": "BV1234567890",
        "aid": 1,
        "cid": 2,
        "duration": 60,
        "pubdate": 100,
    }

    result = normalize_video(item, "watch-later")

    assert result["source"] == "watch-later"
    assert result["title"] == "测试视频"
    assert result["bvid"] == "BV1234567890"
    assert result["url"] == "https://www.bilibili.com/video/BV1234567890"
    assert result["raw"] == item
