from tools.bili_library import favorite_folders_with_total, favorite_items_with_total, normalize_video, watch_later_with_total


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


class FakeClient:
    def __init__(self, body):
        self.body = body

    def request_json(self, url, params, auth_required=True):
        return self.body

    def my_mid(self):
        return 1


def test_watch_later_with_total_reads_count_with_limit_one():
    client = FakeClient(
        {
            "data": {
                "count": 559,
                "list": [{"title": "视频", "bvid": "BV1234567890"}],
            }
        }
    )

    result = watch_later_with_total(client, 1)

    assert result["total"] == 559
    assert len(result["items"]) == 1


def test_favorite_folders_with_total_reads_count():
    client = FakeClient({"data": {"count": 26, "list": [{"id": 1, "title": "收藏夹"}]}})

    result = favorite_folders_with_total(client, "me")

    assert result["total"] == 26
    assert len(result["items"]) == 1


def test_favorite_items_with_total_reads_media_count():
    client = FakeClient(
        {
            "data": {
                "info": {"media_count": 1832},
                "medias": [{"title": "收藏视频", "bvid": "BV1234567890"}],
            }
        }
    )

    result = favorite_items_with_total(client, 1, 1)

    assert result["total"] == 1832
    assert result["items"][0]["bvid"] == "BV1234567890"
