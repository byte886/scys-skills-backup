# 阶段 1–3：检索与深读协议

## §1 需求澄清与检索规划

先判断素材范围类型，决定主检索通道：

| 教程类型 | 主通道 | 辅助通道 |
|---|---|---|
| 人物教程 | `userSearch` 定位账号（先消歧，同名昵称逐个核对简介）→ `searchTopic(targetUserId, isDigested=true)` 收集精华帖 | `getProfileInfo` / `getUserComments` 补画像 |
| 航海手册教程 | `activitySearch` 找航海 → `activityManualToc` 拿目录 → `activityManualDetail` 逐节读正文 | 官宣帖 + 精华复盘帖（手册锁定时替代） |
| 主题/方向调研 | `searchTopic` 多组关键词（可叠加 isDigested / isHot / 时间窗 / 标签 includeMenuIdList） | `contentSearch` 分区：good 精华 / winBid 中标 / fxb 风向标 / square 广场 |
| 项目案例调研 | `projectLibSearch` / `searchProjectCases`（筛选项 ID 必须先 `listProjectCaseFilters` 获取，禁止猜 ID） | `projectLibDetail` 深取单个项目 |

关键词规划：把用户主题拆成 3–6 组同义词 / 口语词 / 平台词（例：「贴图号」→「图片消息 / 小绿书 / 公众号图片」），轮换使用避免总命中同一批。注意 `searchTopic` 至少需要一个过滤维度（keyword / targetUserId / 时间窗 / 标签 / isHot / isDigested / isFavorite 之一）。

## §2 候选池与候选索引

- 多组关键词检索结果合并去重，形成候选池（建议 ≥20 篇；人物教程 = 其全部符合条件帖）。
- 每条记录：entityType / entityId、标题、作者、发布时间、阅读/点赞等数据、是否精华、一句话相关性、**入选或排除理由**。
- 排除类别显式记录：通知/活动帖、搬运、纯情绪无干货、违规灰产类（灰产违规帖直接排除并在索引中标注）。
- 落盘 `notes/00-候选索引.md`。
- 系列化产出时（同一方向多期教程）维护「已用帖 ID 索引」文件，跨期、跨系列避重；查占用时除索引文件外，还要 grep 其他系列成品的「数据说明」节。

## §3 全文深读

### 深读池筛选
- 标准：相关性 × 数据完整度 × 多样性。方法论 / 正面案例 / 反面教训都要有，**正反案例必须兼收**（反面案例单独做卡）。
- 默认 8–15 篇 `topicDetail` 全文深读；其余候选做标题+摘要要点级阅读并注明。

### 深读动作
- `topicDetail`：正文在 `topicDTO.articleContent`；`articleContentContainFeishuDoc` 缺失或空 ≠ 无正文，不得误判。正文大量存于飞书外链时，匿名访问会被登录墙拦截——读不到就如实标注，不猜内容。
- `activityManualDetail`：长文用 offset / nextOffset 分段续读直到 truncated=false；断点可能落在图片引用中间，上下段拼接需去重重叠字符（仅用于判断该节是否有图，不落盘完整带签名的访问地址）。
- 深读笔记逐篇记录：作者 / 链接 / 核心数据 / 方法论框架 / 金句与关键段落**原文**（终版引用需完整原文）/ 建议进入教程的章节。
- 单帖接口偶发报错（如 NATIVE_OUTPUT_CONTRACT_INVALID，连续重试无效）：改用 `contentSearch` 摘要 + 站内转述帖做基线，并如实标注「全文未读到」。

### 子代理编排
- 每个子代理负责一批篇目（3–6 篇），提示词必须**自包含**：篇目 ID 清单、笔记格式、落盘路径（子代理看不到主对话上下文）。
- 子代理只向主线程回传每篇 2–3 行摘要，全文笔记由子代理直接落盘——防止大回答撑爆主上下文。
- 并发触发 user concurrency limit 时改串行；MCP 调用约 40 次/分钟，批间加 sleep。

## §4 补充素材与缺口处理

- 站内素材不足处，用模型世界知识或联网检索补齐，产出中显式标注【补充】及依据类型。
- 平台规则类事实优先用站内一手案例佐证；联网检索不可用时不编造，改用站内数据并注明口径。
- 数据有同步延迟（新帖可能滞后一天），取数时间窗如实记录到「数据说明」。
- `searchTopic` 返回是包装对象，帖子字段在 `items[i].topicDTO` 下；搜索结果不含飞书合并全文，需要全文时用 entityType + entityId 调 `topicDetail`。
