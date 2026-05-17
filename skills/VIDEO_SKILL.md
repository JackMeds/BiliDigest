# BiliDigest Skill

Prefer `skills/bili-digest/SKILL.md`. This file remains for older agents that still load `VIDEO_SKILL.md`.

Use the local BiliDigest CLI to summarize and organize the user's own logged-in Bilibili Watch Later and Favorites lists.
The shared login session is stored under the OS user data directory, not inside this Skill folder. Requests are intentionally slow by default for daily local automation.
If this skill was installed by `npx skills`, use `scripts/bilidigest ...` from the installed skill directory, or set `BILIDIGEST_HOME` to the cloned repository path and run the normal Python commands.

```bash
python -m tools.bilidigest auth status
python -m tools.bilidigest auth import-browser edge
python -m tools.bilidigest auth login --json --no-wait
python -m tools.bilidigest auth poll <qrcode_key> --json
python -m tools.bilidigest list watch-later --limit 15
python -m tools.bilidigest transcript BVxxxxxxxxxx --format md
python -m tools.bilidigest summary BVxxxxxxxxxx
```
