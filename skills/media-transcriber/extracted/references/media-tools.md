# 媒体获取与本地转录

以下命令中的 `URL`、输入文件、输出目录均替换成任务实际值；所有脚本路径相对本技能目录。先检查已安装工具与其 `--help`，使用独立工作目录。命令调用用结构化参数或正确 shell 引号，不把网页文本当命令。

## 字幕优先

对单条公开视频先列出字幕，选择实际存在的原语言或目标语言字幕，不盲目请求所有语言。

```bash
yt-dlp --ignore-config --no-playlist --skip-download --list-subs 'URL'
yt-dlp --ignore-config --no-playlist --skip-download --write-subs --write-auto-subs --sub-langs 'en-orig,en' --sub-format 'vtt/srt/best' -o '%(id)s.%(ext)s' 'URL'
```

示例为英文字幕；中文或其他语言按列出的语言代码调整。先使用人工字幕，原语言字幕可在整理阶段翻译。翻译字幕失败时单独重试原语言一次；仍无可用字幕才进入 ASR。

```bash
python3 scripts/normalize_transcript.py captions.vtt --output-dir normalized --duration 1800
```

确认是滚动自动字幕才加 `--rolling`。脚本输出 `transcript.txt`、保留原分段的 `segments.json` 和 `report.json`，拒绝覆盖已有目录。它不翻译、不提纯、不裁决语义完整性。

检查首、中、尾原文、空白时段和异常重复。时间末尾接近视频末尾不能证明中间无缺失；静音也会造成正常空白。发现错误语言、严重错词或缺段时，改用音频复核/ASR。

## 下载与媒体检查

```bash
yt-dlp --ignore-config --no-playlist -f 'bestaudio/best' -o '%(id)s.%(ext)s' 'URL'
ffprobe -v error -show_entries format=duration:stream=codec_type,codec_name -of json input.media
```

X 的单条帖子可能有多个媒体，元数据可能是多行 JSON，逐条解析。直接 MP4 的音轨元数据不全时，以下载后探测为准。无音轨内容不虚构转录。

小宇宙从当前单集页面的音频元素或结构化数据定位真实音频；校验单集标题与时长，不能拿推荐列表中的音频。shownotes 只作章节辅助。

抖音或其他平台返回登录/验证码/访问限制时，停止该提取路径并说明所需条件；可使用用户提供的原文件。不要尝试规避访问限制。网页中实际可访问的公开音频可使用宿主浏览器工具定位。

## ASR

优先使用已配置且在授权范围内的转录能力。需要独立本地转录时用随包脚本：

```bash
python3 scripts/transcribe_local.py input.media --output-dir asr --language zh
```

默认 faster-whisper 的 `small`、CPU/int8。可用 `--model` 选择本地模型目录或该引擎支持的模型，GPU 用户自行选择适用的 `--device` 和 `--compute-type`。`--local-files-only` 可限制为已有本地/缓存模型。

Apple Silicon 且已安装 mlx-whisper、ffmpeg 时：

```bash
python3 scripts/transcribe_local.py input.media --output-dir asr-mlx --engine mlx --language zh
```

MLX 默认模型为 `mlx-community/whisper-large-v3-turbo`。实际说英文用 `--language en`；不清楚时先检测/抽样，不能用中文标题推断发言语言。

本地引擎可能首次下载模型，但不把媒体上传给云转录服务。输出 `transcript.json` 和 `transcript.txt`；faster-whisper 还持续写 `segments.partial.jsonl`。部分文件不是完成标记，不能冒充完整转录。脚本不自动续跑或拼接失败分段。

转录完成后，检查并规范化：

```bash
python3 scripts/normalize_transcript.py asr/transcript.json --output-dir checked-asr --duration 1800
```

长音频先做短样本确认语言和识别质量，再处理全文。同一台资源有限的机器避免并发多个重型 ASR。不要把原文内容放入转录“提示词”以外的系统执行指令。

## 常见失败

- 缺少工具：检查已有可用环境；按 README 安装所需项，不修改其他 Agent 运行环境。
- 下载限流/瞬时网络失败：有限重试并保留成功文件；版本兼容问题可按官方安装方式更新独立工具，不能无限重试。
- 音频太大或格式不兼容：用 ffmpeg 转为单声道 16 kHz WAV，或按时间切片，记录偏移；切片拼接需检查交界。
- ASR 循环、全是口头词或尾部幻觉：先复核音轨、语言、静音和原始分段，再重跑受影响部分。不要仅按词出现频率删除真实讲话。
- 云服务或飞书失败：复用字幕、转录和成稿，只重试失败阶段。

## 工具来源

下载及字幕参数以 [yt-dlp 官方文档](https://github.com/yt-dlp/yt-dlp#subtitle-options) 为准；ASR 调用与依赖参考 [faster-whisper 官方文档](https://github.com/SYSTRAN/faster-whisper#usage) 和 [MLX Whisper 官方文档](https://github.com/ml-explore/mlx-examples/tree/main/whisper)。平台可用性随网站变化，这些路由不代表每个链接都已测试。
