# BiliDigest Agent 工具

0.4 版提供同一个处理核心的两种入口：**JSON CLI** 和 **带 Bearer 认证的 HTTP API**。Skill 说明如何调用。无需 MCP，也不要求调用者使用某一种模型。

有终端工具的 Codex、Hermes、Grok Bot 等宿主可以直接使用 CLI；能配置 HTTP 自定义工具的宿主可以使用 OpenAPI。纯聊天界面如果既不能执行命令也不能发工具请求，就必须先由宿主接入一种能力。安装本项目不会自动获得 Dot 或 Grok Bot 的调用权限。

## 安装与体检

需要 Python 3.10+：

```sh
python -m pip install '.[http]'
bili doctor
```

安装系统的 FFmpeg（含 ffprobe）。无字幕时希望本机转写，再安装 whisper.cpp，准备多语言 GGML 模型并配置：

```sh
bili configure --whisper-model /absolute/path/ggml-large-v3-turbo-q5_0.bin
```

模型不随程序打包，也不会静默下载。`BILIDIGEST_WHISPER_MODEL` 可覆盖保存的配置。额外安装 `.[llm]` 开启完整文本摘要；安装 `.[browser]` 开启旧浏览器登录导入。默认安装不需要 PyTorch。旧转写模型可以通过 `.[legacy]` 安装。

`bili` 是新命令，`bilidigest agent ...` 与它等价。旧 `bilidigest auth/list/transcript/summary/batch` 保留。

## 一次完整采集

```sh
bili auth status
bili auth import-bilitools
# 也可以让用户用 B站 App 扫码：
bili auth login
bili auth poll QRCODE_KEY

bili discover 'https://space.bilibili.com/38291171' --limit 1000
bili snapshot SNAPSHOT_ID --offset 0 --limit 100
bili plan SNAPSHOT_ID --mode audio-preferred --asr whisper-cpp --language zh
bili start PLAN_ID --key my-collection-2026-09-30
bili status JOB_ID
bili export JOB_ID --include-media
```

ID 来自前一条命令返回的 `data.id`。所有操作默认返回 JSON：`{"ok":true,"data":...}` 或 `{"ok":false,"error":{"code":"...","message":"...","retryable":false}}`。`ok` 只代表命令成功；判断采集是否完成，要检查作业的 `state` 和 `errors`。

`start` 默认启动独立后台进程并返回作业ID，终端或聊天退出后仍可继续。`--foreground` 等待执行结束。系统关机后需重新 `resume`，不是系统常驻调度器。

支持 BV、AV、视频链接、b23短链、UP空间、`mid:UID`、`fav:FID`、带fid的收藏夹链接和 `watch-later`。新采集器当前不包含番剧、付费课程、直播和互动视频分支。

发现结果先返回20条预览，完整条目用 `snapshot` 分页读取。主题筛选可以使用重复的 `--select BV`、`--exclude BV`；`--keyword TEXT` 是标题和简介的字面包含过滤，不是语义分类。复杂主题应由Agent看完列表后明确选BV。默认处理选中投稿的**全部分P**。发现列表不完整时默认不建计划，除非明确指定 `--allow-partial`。

## 媒体与文本策略

| 参数 | 行为 |
|---|---|
| `--mode audio-preferred` | 有独立音轨时只下音轨，否则保存完整带音轨视频 |
| `--mode audio` | 只保留音频；必要时从完整媒体提取音频 |
| `--mode video` | 保存视频与音轨合并结果 |
| `--asr none` | 默认；没字幕时保留媒体，并注明没有文字稿 |
| `--asr whisper-cpp` | 优先现成字幕，无字幕才本地转写 |
| `--summarize` | 按完整文本分块生成摘要；需要llm依赖与API配置，可能产生模型费用 |

摘要配置沿用 `BILIDIGEST_LLM_API_KEY`、`BILIDIGEST_LLM_BASE_URL`、`BILIDIGEST_LLM_MODEL` 或现有DeepSeek配置。不开启summarize时不调用云端模型。

## 状态、恢复与导出

```sh
bili jobs
bili cancel JOB_ID
bili resume JOB_ID
bili status JOB_ID
```

- `queued/running`：等待或运行。
- `complete`：所选策略完成；ASR关闭时仍可能有“无文字稿”的明确记录。
- `partial`：个别分P／阶段失败，错误包含阶段和原因，可恢复。
- `blocked`：登录或平台风控，需要处理后恢复。
- `cancelled/failed`：保留已完成文件，可以检查后恢复。

取消是协作式的，已发出的有限时长请求可能先结束。恢复会校验媒体哈希，跳过已验证阶段。同一个幂等key不会新建重复任务；重试旧任务要用resume。同一数据目录一次运行一个采集worker，减少多任务叠加请求。工具保留原有的慢速API策略，不会自动破解验证。

输出目录含：`README.md`、`manifest.json`、`catalog.csv`、`transcripts.md`、`knowledge.jsonl`、`media/`、`transcripts/`、可选`summaries/`和公开`metadata/`。文字稿有JSON、Markdown和SRT。manifest记录BV/CID、来源、错误、哈希、音轨和时长验证。每个媒体做完整FFmpeg解码检查。

相同音频哈希可复用转写，缓存同时包含模型文件哈希和语言；JSONL按约3分钟／1800字分片，并对完全相同音轨去重，保留各自来源。自动文本未逐句人工校对；纯音频处理不代表已经分析命盘、牌阵或视频画面。

`export` 生成文档包，`--include-media` 生成完整资料包。可以导出明确标注缺口的部分结果；运行中不能同时打包。后台日志保存在私有data目录中，模型调用结果与进度在作业中查询。

## 给远程 Agent 的 HTTP API

```sh
bili serve --host 127.0.0.1 --port 8765
```

首次启动会把随机token写入私有数据目录的 `agent/http.token`，仅当前用户可读，token本身不打印。也可设置至少32字符的 `BILIDIGEST_API_TOKEN`。仅 `/health` 公开且只返回版本和存活状态，其余接口、OpenAPI、文件下载都要求 `Authorization: Bearer TOKEN`。

带认证请求 `/openapi.json` 可获取标准接口定义，内含Bearer安全方案，方便配置自定义HTTP工具。远程使用应放在可信HTTPS反向代理或私有网络之后；绑定非本机地址需显式 `--allow-remote`。不要发布旧的无认证 `tools/api_server.py`；使用本入口。

| 操作 | 接口 |
|---|---|
| 体检 | `GET /v1/doctor` |
| 登录状态／扫码／轮询 | `GET /v1/auth`、`POST /v1/auth/login`、`GET /v1/auth/poll?key=...` |
| 发现／查看列表 | `POST /v1/discover`、`GET /v1/snapshots/{id}` |
| 建计划 | `POST /v1/plans` |
| 启动／列作业 | `POST /v1/jobs`、`GET /v1/jobs` |
| 状态 | `GET /v1/jobs/{id}` |
| 取消／恢复 | `POST /v1/jobs/{id}/cancel`、`POST /v1/jobs/{id}/resume` |
| 导出 | `POST /v1/jobs/{id}/export` |
| 取文件 | `GET /v1/jobs/{id}/artifact?path=documents.zip` |

附带的 `scripts/agent_http_client.py` 只需要Python标准库，可放到另一台机器：

```sh
export BILIDIGEST_URL=https://your-private-service.example
export BILIDIGEST_TOKEN_FILE=/path/to/token
python scripts/agent_http_client.py GET /v1/doctor
python scripts/agent_http_client.py POST /v1/discover --json '{"source":"mid:38291171"}'
python scripts/agent_http_client.py POST /v1/plans --json '{"snapshot_id":"ID","mode":"audio-preferred","asr":"whisper-cpp"}'
python scripts/agent_http_client.py POST /v1/jobs --json '{"plan_id":"ID","idempotency_key":"my-collection"}'
python scripts/agent_http_client.py GET /v1/jobs/JOB_ID
python scripts/agent_http_client.py POST /v1/jobs/JOB_ID/export --json '{"include_media":false}'
python scripts/agent_http_client.py GET '/v1/jobs/JOB_ID/artifact?path=documents.zip' --save documents.zip
```

文件下载仅限作业产物清单，HTTP调用者不能提供任意本地文件路径或输出目录。独立客户端拒绝重定向，避免把认证信息发送给其他来源。

## 目录与迁移

`bili --data-dir PATH --output-dir PATH ...` 或 `BILIDIGEST_DATA_DIR` / `BILIDIGEST_OUTPUT_DIR` 可指定部署目录。凭据和作业状态在data目录；可分享产物在output目录。默认支持macOS Application Support、Windows LocalAppData与Linux XDG目录。

BiliTools登录导入仅以只读方式读取其Cookie表，验证后写入BiliDigest自己的会话。两个程序不共同修改GUI数据库。分享资料包时不要包含私有data目录。
