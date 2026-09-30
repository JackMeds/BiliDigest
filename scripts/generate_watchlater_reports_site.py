#!/usr/bin/env python3
"""Generate grouped markdown reports and a static website for BiliDigest Watch Later results.

Reads BiliDigest state/cache files and existing transcript/summary markdown. Produces:
- ~/Documents/BiliDigest/bilidigest/reports/watch-later/report_XXX_videos_AAA-BBB.md (10 videos/report)
- ~/Documents/BiliDigest/bilidigest/reports/watch-later/summary_XXX_videos_AAA-BBB.md (100 videos/report)
- ~/Documents/BiliDigest/bilidigest/reports/watch-later/overall_summary.md
- ~/Documents/BiliDigest/bilidigest/reports/watch-later/favorites_summary.md
- ~/Documents/BiliDigest/bilidigest/site/index.html + data.json
"""
from __future__ import annotations

import html
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import bili_paths  # noqa: E402

OUT_ROOT = bili_paths.OUTPUT_DIR / "bilidigest"
STATE_PATH = bili_paths.batch_state_dir() / "watch-later.json"
CACHE_PATH = bili_paths.batch_cache_dir() / "watch-later.jsonl"
REPORT_DIR = bili_paths.reports_dir() / "watch-later"
SITE_DIR = bili_paths.site_dir()

STOPWORDS = set("""
这个 一个 就是 还是 然后 因为 所以 但是 如果 其实 可能 他们 我们 你们 大家 现在 时候 视频
什么 这样 那么 比较 觉得 进行 可以 不是 没有 以及 对于 通过 里面 这种 这里 那里 一下 一些
非常 真的 直接 问题 需要 开始 最后 今天 之后 之前 起来 已经 看到 还有 不能 不会 不是
the and for with that this from are was were have has you your about into will can not
""".split())

CATEGORY_RULES = [
    ("AI / 开发工具", ["AI", "模型", "开源", "编程", "代码", "Claude", "Codex", "Agent", "智能体", "工具", "CLI", "开发", "程序", "github", "star"]),
    ("科技 / 数码", ["手机", "芯片", "系统", "电脑", "硬件", "机器人", "汽车", "发布会", "科技", "数码", "小米", "华为", "苹果"]),
    ("历史 / 文化", ["历史", "朝代", "皇帝", "文化", "古代", "战争", "明朝", "唐朝", "汉朝", "人物", "故事"]),
    ("财经 / 商业", ["商业", "公司", "赚钱", "创业", "投资", "市场", "经济", "老板", "生意", "流量", "增长", "用户"]),
    ("学习 / 教育", ["学习", "课程", "知识", "大学", "考试", "读书", "方法", "教育", "英语", "数学"]),
    ("生活 / 心理", ["生活", "心理", "关系", "情绪", "朋友", "喜欢", "爱", "自己", "沟通", "家庭", "婚姻", "成长"]),
    ("游戏 / 娱乐", ["游戏", "守望先锋", "原神", "黑杰克", "玩家", "剧情", "角色", "动画", "电影", "音乐", "娱乐"]),
    ("美食 / 日常", ["美食", "做饭", "麻酱", "菜", "吃", "厨房", "食材", "日常"]),
    ("社会 / 时事", ["社会", "宣传", "政策", "城市", "国家", "新闻", "事件", "舆论", "基本盘"]),
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def latest_named_jsonl(name: str) -> Path | None:
    matches = sorted(OUT_ROOT.glob(f"*/{name}"), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def rel(path: str | Path | None, base: Path) -> str | None:
    if not path:
        return None
    p = Path(path)
    try:
        return os.path.relpath(p, base)
    except Exception:
        return str(p)


def extract_transcript(md_path: str | None) -> tuple[list[tuple[str, str]], str]:
    if not md_path or not Path(md_path).exists():
        return [], ""
    text = Path(md_path).read_text(encoding="utf-8", errors="ignore")
    rows: list[tuple[str, str]] = []
    in_sub = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## 字幕"):
            in_sub = True
            continue
        if not in_sub:
            continue
        m = re.match(r"^- \[([^\]]+)\]\([^)]*\)\s*(.*)$", line)
        if m:
            content = re.sub(r"\s+", " ", m.group(2)).strip()
            if content:
                rows.append((m.group(1), content))
    plain = " ".join(t for _, t in rows)
    return rows, plain


def clean_sentence(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip(" -，。,.!！?？")
    s = re.sub(r"^(啊|嗯|呃|额|那么|然后|所以|但是|就是|这个|那个)+", "", s)
    return s.strip()


def meaningful_lines(rows: list[tuple[str, str]]) -> list[str]:
    result = []
    seen = set()
    for _, line in rows:
        s = clean_sentence(line)
        if len(s) < 5:
            continue
        if s in seen:
            continue
        seen.add(s)
        # Skip filler-only fragments.
        if s in STOPWORDS:
            continue
        result.append(s)
    return result


def top_keywords(text: str, title: str, n: int = 6) -> list[str]:
    # Mixed Chinese/English phrase heuristic. Good enough for report navigation without external deps.
    words: list[str] = []
    source = f"{title} {text[:5000]}"
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_+.#-]{1,24}|[\u4e00-\u9fff]{2,6}", source):
        t = token.strip().lower()
        if len(t) < 2 or t in STOPWORDS:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]+", t):
            # Generate 2-4 char chunks from longer Chinese fragments.
            if len(t) > 4:
                for k in (2, 3, 4):
                    for i in range(0, len(t) - k + 1):
                        sub = t[i:i+k]
                        if sub not in STOPWORDS:
                            words.append(sub)
            else:
                words.append(t)
        else:
            words.append(t)
    counts = Counter(words)
    return [w for w, _ in counts.most_common(n)]


def categorize(title: str, keywords: list[str], text: str) -> str:
    hay = f"{title} {' '.join(keywords)} {text[:1200]}".lower()
    best = (0, "其他")
    for cat, keys in CATEGORY_RULES:
        score = 0
        for key in keys:
            if key.lower() in hay:
                score += 1
        if score > best[0]:
            best = (score, cat)
    return best[1]


def summarize(title: str, rows: list[tuple[str, str]], text: str) -> dict[str, Any]:
    lines = meaningful_lines(rows)
    keywords = top_keywords(text, title)
    category = categorize(title, keywords, text)
    if not lines:
        return {
            "brief": "暂无可用字幕或总结，已保留视频链接，后续可重试 B站 AI 总结。",
            "bullets": [],
            "keywords": keywords,
            "category": category,
            "timeline": [],
        }
    # Use beginning + middle + later lines to avoid only summarizing intro.
    picks: list[str] = []
    positions = [0, max(0, len(lines)//5), max(0, len(lines)//2), max(0, len(lines)*4//5)]
    for pos in positions:
        if pos < len(lines):
            s = lines[pos]
            if s not in picks:
                picks.append(s)
    brief = "；".join(picks[:2])
    if len(brief) > 180:
        brief = brief[:177] + "…"
    timeline = []
    stride = max(1, len(rows)//4)
    for ts, line in rows[::stride][:4]:
        s = clean_sentence(line)
        if len(s) >= 4:
            timeline.append({"time": ts, "text": s[:80]})
    return {
        "brief": brief or (lines[0][:180] if lines else ""),
        "bullets": [p[:160] for p in picks[:4]],
        "keywords": keywords,
        "category": category,
        "timeline": timeline,
    }


def load_items() -> list[dict[str, Any]]:
    state = load_json(STATE_PATH)
    completed = state.get("completed", {})
    failed = state.get("failed", {})
    cache_items = read_jsonl(CACHE_PATH)
    if not cache_items:
        cache_items = list(completed.values()) + list(failed.values())
    videos = []
    seen = set()
    for idx, item in enumerate(cache_items, 1):
        bvid = item.get("bvid")
        if not bvid or bvid in seen:
            continue
        seen.add(bvid)
        entry = completed.get(bvid) or failed.get(bvid) or {}
        status = "completed" if bvid in completed else ("failed" if bvid in failed else "pending")
        transcript_path = (((entry.get("transcript") or {}).get("paths") or {}).get("md"))
        digest_path = ((entry.get("digest") or {}).get("path") if isinstance(entry.get("digest"), dict) else None)
        summary_path = digest_path or ((entry.get("summary") or {}).get("path") if isinstance(entry.get("summary"), dict) else None)
        bili_summary_path = ((entry.get("bili_summary") or {}).get("path") if isinstance(entry.get("bili_summary"), dict) else None)
        rows, plain = extract_transcript(transcript_path)
        local = summarize(item.get("title") or entry.get("title") or bvid, rows, plain)
        videos.append({
            "index": idx,
            "bvid": bvid,
            "title": item.get("title") or entry.get("title") or bvid,
            "url": item.get("url") or f"https://www.bilibili.com/video/{bvid}",
            "duration": item.get("duration"),
            "pubtime": item.get("pubtime"),
            "status": status,
            "error": entry.get("error") or entry.get("transcript_error", {}).get("error"),
            "transcript_path": transcript_path,
            "summary_path": summary_path,
            "digest_path": digest_path,
            "bili_summary_path": bili_summary_path,
            "has_transcript": bool(rows),
            "has_digest": bool(digest_path),
            "has_bili_summary": bool(bili_summary_path),
            **local,
        })
    return videos


def load_favorite_folders() -> list[dict[str, Any]]:
    path = latest_named_jsonl("favorite-folders.jsonl")
    if not path:
        return []
    folders = read_jsonl(path)
    for idx, folder in enumerate(folders, 1):
        folder["index"] = idx
        folder["source_path"] = str(path)
        folder["media_count"] = int(folder.get("media_count") or 0)
    return folders


def fmt_duration(seconds: Any) -> str:
    try:
        seconds = int(seconds)
    except Exception:
        return "-"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def write_report_10(group: list[dict[str, Any]], group_no: int) -> Path:
    start, end = group[0]["index"], group[-1]["index"]
    path = REPORT_DIR / f"report_{group_no:03d}_videos_{start:03d}-{end:03d}.md"
    lines = [
        f"# 稍后再看小报告 {group_no:03d}（视频 {start:03d}-{end:03d}）",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| # | 标题 | 分类 | 状态 | 关键词 |",
        "|---:|---|---|---|---|",
    ]
    for v in group:
        status = "✅ Digest" if v["has_digest"] else ("✅ 字幕" if v["has_transcript"] else ("🟡 B站总结" if v["has_bili_summary"] else "⚠️ 待重试"))
        lines.append(f"| {v['index']} | [{v['title']}]({v['url']}) | {v['category']} | {status} | {', '.join(v['keywords'][:5])} |")
    lines.append("")
    for v in group:
        lines.extend([
            f"## {v['index']:03d}. {v['title']}",
            "",
            f"- BV：`{v['bvid']}`",
            f"- 链接：{v['url']}",
            f"- 分类：{v['category']}",
            f"- 时长：{fmt_duration(v.get('duration'))}",
            f"- 关键词：{', '.join(v['keywords']) if v['keywords'] else '暂无'}",
            f"- 状态：{'已有字幕深度摘要' if v['has_digest'] else ('已提取字幕' if v['has_transcript'] else ('已有B站AI总结' if v['has_bili_summary'] else '没有字幕/总结，建议后续手动重试'))}",
            "",
            f"**摘要**：{v['brief']}",
            "",
        ])
        if v["bullets"]:
            lines.append("**要点**：")
            for b in v["bullets"]:
                lines.append(f"- {b}")
            lines.append("")
        if v["timeline"]:
            lines.append("**时间线摘录**：")
            for t in v["timeline"]:
                lines.append(f"- `{t['time']}` {t['text']}")
            lines.append("")
        if v.get("error"):
            lines.extend([f"> 处理错误：{v['error']}", ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_summary_100(group: list[dict[str, Any]], group_no: int) -> Path:
    start, end = group[0]["index"], group[-1]["index"]
    path = REPORT_DIR / f"summary_{group_no:03d}_videos_{start:03d}-{end:03d}.md"
    cat_counts = Counter(v["category"] for v in group)
    kw_counts = Counter(k for v in group for k in v["keywords"][:5])
    ok = sum(1 for v in group if v["has_digest"] or v["has_transcript"] or v["has_bili_summary"])
    lines = [
        f"# 稍后再看百条总结 {group_no:03d}（视频 {start:03d}-{end:03d}）",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"- 视频数：{len(group)}",
        f"- 可总结：{ok}",
        f"- 待重试：{len(group) - ok}",
        "",
        "## 内容分布",
        "",
    ]
    for cat, c in cat_counts.most_common():
        lines.append(f"- **{cat}**：{c} 个")
    lines.extend(["", "## 高频关键词", "", ", ".join(k for k, _ in kw_counts.most_common(30)) or "暂无", "", "## 值得优先看的视频", ""])
    # Pick representative: longer and keyword-rich completed videos.
    ranked = sorted(group, key=lambda v: ((1 if v['has_transcript'] else 0), len(v['keywords']), int(v.get('duration') or 0)), reverse=True)[:12]
    for v in ranked:
        lines.append(f"- [{v['index']:03d}. {v['title']}]({v['url']}) — {v['category']}：{v['brief']}")
    lines.extend(["", "## 全部视频一句话索引", ""])
    for v in group:
        flag = "✅" if v["has_transcript"] else "⚠️"
        lines.append(f"- {flag} **{v['index']:03d}. [{v['title']}]({v['url']})** ｜{v['category']}｜{v['brief']}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def build_reports(videos: list[dict[str, Any]]) -> tuple[list[Path], list[Path], Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    for old in REPORT_DIR.glob("*.md"):
        old.unlink()
    small = []
    big = []
    for i in range(0, len(videos), 10):
        small.append(write_report_10(videos[i:i+10], i//10 + 1))
    for i in range(0, len(videos), 100):
        big.append(write_summary_100(videos[i:i+100], i//100 + 1))
    overall = REPORT_DIR / "overall_summary.md"
    cat_counts = Counter(v["category"] for v in videos)
    status_counts = Counter("可总结" if (v["has_digest"] or v["has_transcript"] or v["has_bili_summary"]) else "待重试" for v in videos)
    lines = [
        "# B站稍后再看总报告",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"- 总视频数：{len(videos)}",
        f"- 已有字幕/总结：{status_counts['可总结']}",
        f"- 待重试/无字幕：{status_counts['待重试']}",
        f"- 每10个视频小报告：{len(small)} 份",
        f"- 每100个视频总结报告：{len(big)} 份",
        "",
        "## 分类总览",
        "",
    ]
    for cat, c in cat_counts.most_common():
        lines.append(f"- **{cat}**：{c}")
    lines.extend(["", "## 报告目录", "", "### 每10个视频", ""])
    for p in small:
        lines.append(f"- [{p.name}]({p.name})")
    lines.extend(["", "### 每100个视频", ""])
    for p in big:
        lines.append(f"- [{p.name}]({p.name})")
    overall.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return small, big, overall


def build_favorites_report(folders: list[dict[str, Any]]) -> Path | None:
    if not folders:
        return None
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "favorites_summary.md"
    total = sum(int(f.get("media_count") or 0) for f in folders)
    non_empty = [f for f in folders if int(f.get("media_count") or 0) > 0]
    largest = sorted(non_empty, key=lambda f: int(f.get("media_count") or 0), reverse=True)[:12]
    lines = [
        "# B站收藏夹整理报告",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"- 收藏夹数：{len(folders)}",
        f"- 非空收藏夹：{len(non_empty)}",
        f"- 收藏视频合计：{total}",
        "",
        "## 优先整理对象",
        "",
    ]
    for f in largest:
        lines.append(f"- **{f.get('title') or '未命名收藏夹'}**：{f.get('media_count', 0)} 个视频")
    lines.extend(["", "## 全部收藏夹", "", "| # | 收藏夹 | 视频数 | 备注 |", "|---:|---|---:|---|"])
    for f in folders:
        note = "空文件夹，可归档或保留占位" if int(f.get("media_count") or 0) == 0 else "建议按主题继续抽样摘要"
        lines.append(f"| {f['index']} | {f.get('title') or '未命名收藏夹'} | {f.get('media_count', 0)} | {note} |")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_site(videos: list[dict[str, Any]], small: list[Path], big: list[Path], overall: Path, favorites: list[dict[str, Any]], favorites_report: Path | None) -> Path:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "stats": {
            "total": len(videos),
            "summarized": sum(1 for v in videos if v["has_digest"] or v["has_transcript"] or v["has_bili_summary"]),
            "failed": sum(1 for v in videos if v["status"] == "failed"),
            "pending": sum(1 for v in videos if v["status"] == "pending"),
            "retry": sum(1 for v in videos if not (v["has_digest"] or v["has_transcript"] or v["has_bili_summary"])),
            "small_reports": len(small),
            "big_reports": len(big),
            "categories": Counter(v["category"] for v in videos),
        },
        "reports": {
            "overall": rel(overall, SITE_DIR),
            "favorites": rel(favorites_report, SITE_DIR) if favorites_report else None,
            "small": [{"title": p.stem, "href": rel(p, SITE_DIR)} for p in small],
            "big": [{"title": p.stem, "href": rel(p, SITE_DIR)} for p in big],
        },
        "favorites": [
            {k: f.get(k) for k in ["index", "id", "fid", "title", "media_count"]}
            for f in favorites
        ],
        "videos": [
            {k: v.get(k) for k in ["index", "bvid", "title", "url", "duration", "status", "has_transcript", "has_digest", "has_bili_summary", "category", "keywords", "brief", "bullets", "timeline", "error"]}
            | {"transcript_href": rel(v.get("transcript_path"), SITE_DIR), "summary_href": rel(v.get("summary_path"), SITE_DIR)}
            for v in videos
        ],
    }
    (SITE_DIR / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    embedded_data = html.escape(json.dumps(data, ensure_ascii=False), quote=False)
    cats = Counter(v["category"] for v in videos)
    chips = "".join(f'<button class="chip" data-cat="{html.escape(cat)}">{html.escape(cat)} <span>{count}</span></button>' for cat, count in cats.most_common())
    fav_total = sum(int(f.get("media_count") or 0) for f in favorites)
    html_doc = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>B站稍后再看 · 摘要仪表盘</title>
  <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap\" rel=\"stylesheet\">
  <style>
    :root {{ --bg:#08090a; --panel:#0f1011; --surface:#191a1b; --surface2:rgba(255,255,255,.045); --text:#f7f8f8; --muted:#8a8f98; --soft:#d0d6e0; --line:rgba(255,255,255,.08); --line2:rgba(255,255,255,.05); --accent:#7170ff; --brand:#5e6ad2; --green:#10b981; --warn:#f59e0b; }}
    * {{ box-sizing:border-box }}
    body {{ margin:0; font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif; font-feature-settings:'cv01','ss03'; background: radial-gradient(circle at 20% -10%, rgba(94,106,210,.28), transparent 32%), radial-gradient(circle at 85% 5%, rgba(113,112,255,.15), transparent 26%), var(--bg); color:var(--text); }}
    a {{ color:inherit; text-decoration:none }}
    .nav {{ position:sticky; top:0; z-index:5; backdrop-filter: blur(18px); background:rgba(8,9,10,.72); border-bottom:1px solid var(--line2); }}
    .nav-inner {{ max-width:1220px; margin:auto; padding:14px 22px; display:flex; align-items:center; justify-content:space-between; gap:16px }}
    .brand {{ display:flex; align-items:center; gap:10px; font-weight:510; letter-spacing:-.2px }}
    .logo {{ width:28px; height:28px; border-radius:8px; background:linear-gradient(135deg,var(--brand),#9b8cff); box-shadow:0 0 32px rgba(113,112,255,.38); display:grid; place-items:center; font-family:'JetBrains Mono'; font-size:13px }}
    .nav-actions {{ display:flex; gap:10px; align-items:center }}
    .btn {{ border:1px solid var(--line); background:rgba(255,255,255,.03); color:var(--soft); border-radius:8px; padding:9px 12px; font-size:13px; cursor:pointer }}
    .btn.primary {{ background:var(--brand); color:white; border-color:transparent }}
    .hero {{ max-width:1220px; margin:0 auto; padding:78px 22px 34px }}
    .eyebrow {{ display:inline-flex; gap:8px; align-items:center; color:var(--soft); border:1px solid var(--line); background:rgba(255,255,255,.025); border-radius:999px; padding:6px 10px; font-size:12px; font-family:'JetBrains Mono',monospace }}
    h1 {{ font-size:clamp(38px,7vw,72px); line-height:1; letter-spacing:-1.5px; font-weight:510; margin:22px 0 16px; max-width:850px }}
    .subtitle {{ color:var(--muted); font-size:18px; line-height:1.65; max-width:760px }}
    .stats {{ max-width:1220px; margin:0 auto; padding:0 22px 26px; display:grid; grid-template-columns:repeat(5,1fr); gap:12px }}
    .stat {{ background:rgba(255,255,255,.025); border:1px solid var(--line); border-radius:14px; padding:18px; box-shadow:inset 0 0 24px rgba(0,0,0,.18) }}
    .stat b {{ display:block; font-size:30px; letter-spacing:-.7px; font-weight:510 }}
    .stat span {{ color:var(--muted); font-size:13px }}
    .shell {{ max-width:1220px; margin:0 auto; padding:16px 22px 70px; display:grid; grid-template-columns:290px 1fr; gap:18px }}
    .side,.main {{ background:rgba(15,16,17,.78); border:1px solid var(--line); border-radius:18px; min-width:0 }}
    .side {{ padding:16px; align-self:start; position:sticky; top:76px; max-height:calc(100vh - 92px); overflow:auto }}
    .main {{ padding:16px }}
    .search {{ width:100%; padding:12px 13px; border-radius:10px; border:1px solid var(--line); color:var(--text); background:rgba(255,255,255,.03); outline:none }}
    .section-title {{ margin:18px 0 10px; color:var(--soft); font-size:13px; font-weight:510 }}
    .chips {{ display:flex; flex-wrap:wrap; gap:8px }}
    .chip {{ border:1px solid var(--line); color:var(--soft); background:rgba(255,255,255,.025); border-radius:999px; padding:7px 9px; cursor:pointer; font-size:12px }}
    .chip.active {{ border-color:rgba(113,112,255,.8); color:white; background:rgba(113,112,255,.18) }}
    .chip span {{ color:var(--muted); margin-left:4px }}
    .report-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; max-height:220px; overflow:auto; padding-right:3px }}
    .report-link {{ display:block; border:1px solid var(--line2); background:rgba(255,255,255,.025); border-radius:10px; padding:10px; color:var(--soft); font-size:12px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap }}
    .toolbar {{ display:flex; justify-content:space-between; gap:12px; align-items:center; padding:4px 4px 16px }}
    .count {{ color:var(--muted); font-family:'JetBrains Mono',monospace; font-size:12px }}
    .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px }}
    .card {{ border:1px solid var(--line); background:rgba(255,255,255,.025); border-radius:14px; padding:15px; transition:.18s ease; min-width:0 }}
    .card:hover {{ background:rgba(255,255,255,.045); transform:translateY(-1px); border-color:rgba(255,255,255,.14) }}
    .meta {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; color:var(--muted); font-size:11px; font-family:'JetBrains Mono',monospace }}
    .pill {{ border:1px solid var(--line2); border-radius:999px; padding:3px 7px; background:rgba(255,255,255,.03) }}
    .ok {{ color:var(--green) }} .warn {{ color:var(--warn) }} .accent {{ color:var(--accent) }}
    .card h3 {{ font-size:17px; line-height:1.35; margin:10px 0 9px; font-weight:590; letter-spacing:-.24px }}
    .brief {{ color:var(--soft); font-size:14px; line-height:1.65; min-height:68px }}
    .keywords {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:12px }}
    .kw {{ color:#cfd3ff; background:rgba(113,112,255,.12); border:1px solid rgba(113,112,255,.2); border-radius:999px; padding:4px 7px; font-size:11px }}
    .links {{ display:flex; gap:8px; margin-top:14px; flex-wrap:wrap }}
    .mini {{ font-size:12px; color:var(--soft); border:1px solid var(--line); border-radius:8px; padding:7px 9px; background:rgba(255,255,255,.025) }}
    .empty {{ padding:36px; text-align:center; color:var(--muted) }}
    @media (max-width: 980px) {{ .stats {{ grid-template-columns:repeat(2,1fr) }} .shell {{ grid-template-columns:1fr }} .side {{ position:static }} .grid {{ grid-template-columns:1fr }} }}
    @media (max-width: 560px) {{ .stats {{ grid-template-columns:1fr }} .report-grid {{ grid-template-columns:1fr }} .nav-inner {{ flex-direction:column; align-items:flex-start }} }}
  </style>
</head>
<body>
  <nav class=\"nav\"><div class=\"nav-inner\"><div class=\"brand\"><div class=\"logo\">B</div><span>Bili Watch Later Digest</span></div><div class=\"nav-actions\"><a class=\"btn\" href=\"../reports/watch-later/overall_summary.md\">总报告</a><a class=\"btn\" href=\"../reports/watch-later/favorites_summary.md\">收藏夹</a><a class=\"btn primary\" href=\"data.json\">Data JSON</a></div></div></nav>
  <header class=\"hero\"><div class=\"eyebrow\">WATCH-LATER · GENERATED {html.escape(datetime.now().strftime('%Y-%m-%d %H:%M'))}</div><h1>把 500+ 个稍后再看，整理成可搜索的知识仪表盘。</h1><p class=\"subtitle\">每 10 个视频一份小报告，每 100 个视频一份阶段总结。支持搜索、分类筛选、原视频跳转、字幕文件跳转。</p></header>
  <section class=\"stats\">
    <div class=\"stat\"><b id=\"sTotal\">{len(videos)}</b><span>稍后再看</span></div><div class=\"stat\"><b id=\"sDone\">0</b><span>可总结</span></div><div class=\"stat\"><b id=\"sFail\">0</b><span>待重试</span></div><div class=\"stat\"><b>{len(favorites)}</b><span>收藏夹</span></div><div class=\"stat\"><b>{fav_total}</b><span>收藏视频</span></div>
  </section>
  <div class=\"shell\">
    <aside class=\"side\"><input id=\"q\" class=\"search\" placeholder=\"搜索标题 / 关键词 / 摘要…\" /><div class=\"section-title\">分类</div><div class=\"chips\"><button class=\"chip active\" data-cat=\"\">全部</button>{chips}</div><div class=\"section-title\">收藏夹</div><div class=\"report-grid\" id=\"favoriteFolders\"></div><div class=\"section-title\">百条总结</div><div class=\"report-grid\" id=\"bigReports\"></div><div class=\"section-title\">十条小报告</div><div class=\"report-grid\" id=\"smallReports\"></div></aside>
    <main class=\"main\"><div class=\"toolbar\"><div class=\"count\" id=\"count\"></div><div class=\"nav-actions\"><button class=\"btn\" id=\"prevPage\">上一页</button><button class=\"btn\" id=\"nextPage\">下一页</button><button class=\"btn\" id=\"failedOnly\">只看待重试</button></div></div><div class=\"grid\" id=\"cards\"></div></main>
  </div>
<script id="__DATA__" type="application/json">{embedded_data}</script>
<script>
let data, cat='', failedOnly=false, page=1;
const pageSize=48;
const $ = s => document.querySelector(s);
function esc(s){{return String(s??'').replace(/[&<>\"]/g, c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}}[c]))}}
function dur(sec){{sec=Number(sec||0); if(!sec) return '-'; let h=Math.floor(sec/3600), m=Math.floor(sec%3600/60), s=sec%60; return h?`${{h}}:${{String(m).padStart(2,'0')}}:${{String(s).padStart(2,'0')}}`:`${{m}}:${{String(s).padStart(2,'0')}}`;}}
function renderReports(){{
  $('#bigReports').innerHTML=data.reports.big.map(r=>`<a class=\"report-link\" href=\"${{esc(r.href)}}\">${{esc(r.title)}}</a>`).join('');
  $('#smallReports').innerHTML=data.reports.small.map(r=>`<a class=\"report-link\" href=\"${{esc(r.href)}}\">${{esc(r.title)}}</a>`).join('');
  $('#favoriteFolders').innerHTML=(data.favorites||[]).map(f=>`<a class=\"report-link\" href=\"${{esc(data.reports.favorites||'#')}}\">${{esc(f.title)}} · ${{f.media_count}}</a>`).join('');
}}
function filteredList(){{
  const q=$('#q').value.trim().toLowerCase();
  let list=data.videos.filter(v=>!cat||v.category===cat).filter(v=>!failedOnly || !(v.has_digest||v.has_transcript||v.has_bili_summary));
  if(q) list=list.filter(v=>[v.title,v.category,v.brief,(v.keywords||[]).join(' ')].join(' ').toLowerCase().includes(q));
  return list;
}}
function render(){{
  const list=filteredList();
  const pages=Math.max(1, Math.ceil(list.length/pageSize));
  if(page>pages) page=pages;
  const slice=list.slice((page-1)*pageSize, page*pageSize);
  $('#count').textContent=`显示 ${{slice.length}} / ${{list.length}} 个匹配视频 · 第 ${{page}}/${{pages}} 页`;
  $('#sDone').textContent=data.stats.summarized; $('#sFail').textContent=data.stats.retry;
  $('#prevPage').disabled=page<=1; $('#nextPage').disabled=page>=pages;
  $('#cards').innerHTML=slice.length?slice.map(v=>`<article class=\"card\"><div class=\"meta\"><span class=\"pill\">#${{String(v.index).padStart(3,'0')}}</span><span class=\"pill\">${{esc(v.category)}}</span><span class=\"pill ${{(v.has_digest||v.has_transcript||v.has_bili_summary)?'ok':'warn'}}\">${{(v.has_digest||v.has_transcript||v.has_bili_summary)?'可总结':'待重试'}}</span><span>${{dur(v.duration)}}</span></div><h3><a href=\"${{esc(v.url)}}\" target=\"_blank\">${{esc(v.title)}}</a></h3><div class=\"brief\">${{esc(v.brief)}}</div><div class=\"keywords\">${{(v.keywords||[]).slice(0,6).map(k=>`<span class=\"kw\">${{esc(k)}}</span>`).join('')}}</div><div class=\"links\"><a class=\"mini\" href=\"${{esc(v.url)}}\" target=\"_blank\">打开B站</a>${{v.transcript_href?`<a class=\"mini\" href=\"${{esc(v.transcript_href)}}\">字幕</a>`:''}}${{v.summary_href?`<a class=\"mini\" href=\"${{esc(v.summary_href)}}\">深度摘要</a>`:''}}</div></article>`).join(''):'<div class=\"empty\">没有匹配结果</div>';
}}
function resetAndRender(){{page=1; render();}}
function boot(d){{data=d; renderReports(); render();}}
try {{ boot(JSON.parse(document.getElementById('__DATA__').textContent)); }}
catch (err) {{ fetch('data.json').then(r=>r.json()).then(boot); }}
document.addEventListener('click', e=>{{ if(e.target.classList.contains('chip')){{document.querySelectorAll('.chip').forEach(x=>x.classList.remove('active')); e.target.classList.add('active'); cat=e.target.dataset.cat; resetAndRender();}} }});
$('#q').addEventListener('input', resetAndRender); $('#failedOnly').addEventListener('click', ()=>{{failedOnly=!failedOnly; $('#failedOnly').classList.toggle('primary', failedOnly); resetAndRender();}});
$('#prevPage').addEventListener('click', ()=>{{page=Math.max(1,page-1); render(); window.scrollTo({{top:0, behavior:'smooth'}});}});
$('#nextPage').addEventListener('click', ()=>{{page=page+1; render(); window.scrollTo({{top:0, behavior:'smooth'}});}});
</script>
</body>
</html>
"""
    (SITE_DIR / "index.html").write_text(html_doc, encoding="utf-8")
    return SITE_DIR / "index.html"


def main() -> None:
    videos = load_items()
    if not videos:
        raise SystemExit("No watch-later data found. Run BiliDigest batch/list first.")
    small, big, overall = build_reports(videos)
    favorites = load_favorite_folders()
    favorites_report = build_favorites_report(favorites)
    index = write_site(videos, small, big, overall, favorites, favorites_report)
    print(json.dumps({
        "videos": len(videos),
        "summarized": sum(1 for v in videos if v["has_digest"] or v["has_transcript"] or v["has_bili_summary"]),
        "failed": sum(1 for v in videos if v["status"] == "failed"),
        "pending": sum(1 for v in videos if v["status"] == "pending"),
        "retry": sum(1 for v in videos if not (v["has_digest"] or v["has_transcript"] or v["has_bili_summary"])),
        "favorite_folders": len(favorites),
        "favorite_items": sum(int(f.get("media_count") or 0) for f in favorites),
        "small_reports": len(small),
        "big_reports": len(big),
        "overall": str(overall),
        "favorites_report": str(favorites_report) if favorites_report else None,
        "site": str(index),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
