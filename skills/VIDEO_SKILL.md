# Video Transcriber Skill

You have access to a local toolkit for downloading and transcribing videos. Use this skill when the user asks to process video content from URLs (YouTube/Bilibili) or local files.

## 🛠️ Tools

Execute these tools using `python -m <tool_name> <args>`.

### 1. Download Video
**Command**: `tools.download`
**Purpose**: Download video or audio from a URL.
**Arguments**:
- `URL`: The video link (supports YouTube, Bilibili, TikTok, etc.)
- `--cookies-browser <browser>`: (Optional) Use 'chrome' or 'edge' cookies for age-gated/premium content.
- `--video`: (Optional) Download video file (default is audio-only for transcription).

**Example**:
```bash
python -m tools.download "https://www.bilibili.com/video/BVxxx" --cookies-browser chrome
```

### 2. Transcribe Audio
**Command**: `tools.transcribe`
**Purpose**: Convert audio/video files to text and subtitles.
**Arguments**:
- `FILE_PATH`: Path to the file (usually in `output/` directory).
- `-m <model>`: 
  - `openai`: Fast, requires `.env`.
  - `Qwen/Qwen3-ASR-0.6B`: High accuracy for Chinese.
  - (Default): Local Whisper.

**Example**:
```bash
python -m tools.transcribe "output/video.m4a" -m openai
```

### 3. Bilibili Authentication
**Command**: `tools.auth`
**Purpose**: Log in to Bilibili via QR code to access private "Watch Later" lists.

## 🧠 Workflow Patterns

### Pattern A: "Summarize this video"
1. **Download**: `python -m tools.download "<URL>"`
2. **Observe**: Capture the output filename (e.g., `output/title.m4a`).
3. **Transcribe**: `python -m tools.transcribe "output/title.m4a"`
4. **Action**: Read the generated `.txt` file and summarize it for the user.

### Pattern B: "Bilibili Watch Later Analysis"
1. **Fetch**: `python -m tools.list --watch-later --limit 5`
2. **Batch**: `python -m tools.batch_run`
3. **Action**: Analyze the transcripts in `output/`.
