from tools.bili_subtitle import body_to_markdown, body_to_srt, choose_subtitle, srt_time


def test_srt_time_formats_milliseconds():
    assert srt_time(65.432) == "00:01:05,432"


def test_body_to_srt():
    body = [{"from": 1.0, "to": 2.5, "content": "第一句"}]

    assert body_to_srt(body) == "1\n00:00:01,000 --> 00:00:02,500\n第一句\n"


def test_body_to_markdown_links_timestamps():
    video = {"title": "标题", "bvid": "BV1234567890"}
    subtitle = {"lan": "ai-zh", "lan_doc": "中文自动字幕"}
    body = [{"from": 61.0, "to": 62.0, "content": "一句字幕"}]

    text = body_to_markdown(video, subtitle, body)

    assert "# 标题" in text
    assert "- Subtitle: 中文自动字幕" in text
    assert "https://www.bilibili.com/video/BV1234567890?t=61" in text
    assert "一句字幕" in text


def test_choose_subtitle_prefers_chinese_auto_subtitle():
    subtitles = [
        {"lan": "en", "subtitle_url": "//example/en.json"},
        {"lan": "ai-zh", "subtitle_url": "//example/zh.json"},
    ]

    assert choose_subtitle(subtitles)["lan"] == "ai-zh"
