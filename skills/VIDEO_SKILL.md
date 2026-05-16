# BiliSubNotes Skill

Prefer `skills/bilisub-notes/SKILL.md`. This file remains for older agents that still load `VIDEO_SKILL.md`.

Use the local BiliSubNotes CLI to export Bilibili subtitles and AI summaries from the user's own logged-in account.
The shared login session is stored under the OS user data directory, not inside this Skill folder. Requests are intentionally slow by default for daily local automation.

```bash
python -m tools.bilisub auth status
python -m tools.bilisub auth import-browser edge
python -m tools.bilisub auth login --json --no-wait
python -m tools.bilisub auth poll <qrcode_key> --json
python -m tools.bilisub list watch-later --limit 15
python -m tools.bilisub transcript BVxxxxxxxxxx --format md
python -m tools.bilisub summary BVxxxxxxxxxx
```
