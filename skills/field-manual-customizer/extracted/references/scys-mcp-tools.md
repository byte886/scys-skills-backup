# 生财 MCP 工具用法

本技能用到的工具、要传的参数、返回里要看的字段，以及实际用过之后知道的坑。工具名以生财 MCP 里的为准；不同客户端可能加前缀。

## 目录

- 一、按步骤用哪个工具
- 二、每个工具怎么用
- 三、截图怎么取
- 四、已知的坑

## 一、按步骤用哪个工具

| 做什么 | 工具 | 没报名能不能用 |
| --- | --- | --- |
| 搜最近的实操帖 | `contentSearch`、`searchTopic` | 能 |
| 读帖子全文和截图 | `topicDetail` | 能 |
| 用整句问题搜 | `searchKnowledgeBase`（客户端有才用） | 能；没有此工具就跳过并记入 `sources.md` |
| 查项目的公开参考区间 | `projectLibSearch`、`projectLibDetail` | 能，只返回公开数据 |
| 看这个方向开没开过航海 | `activityList`（按开船时间列全部航海），`activitySearch`（按关键词补更早的） | 能 |
| 看用户报没报名、要交几次作业 | `getActivityDetail`（客户端有才用） | 能；没有此工具就跳过并记入 `sources.md` |
| 按标签拉这个方向的帖子 | `searchTopic` 的 `includeMenuIdList` | 能 |
| 在所有手册里搜关键词 | `activityManualSearch` | 没验证过 |
| 读手册目录和正文 | `activityManualToc`、`activityManualDetail` | 没验证过，读不到就跳过 |
| 看这一期学员卡在哪 | `searchVisibleActivityQa` | **不能**，只对已报名的开放 |
| 看这一期学员作业 | `searchVisibleActivitySubmissions` | **不能**，只对已报名的开放 |

帖子、知识库和项目库是每个方向都能用的来源；航海相关的工具只在这个方向开过航海时才用。

## 二、每个工具怎么用

### activityList（找航海先用它）

- 参数：`startTime` / `endTime`（开船时间窗，秒级时间戳）、`pageSize`（最多 50）、`pageIndex`；可选 `platform`（`ai`、`overseas`、`media`、`ecommerce`、`xiaohongshu`、`douyin`、`wechat`、`skill`、`other`）、`status`、`keyword`
- 2026-09-22 的一次查询在最近 12 个月找到 73 期；这只是当时记录。**每次按实际返回的总数和分页继续，不固定两页**。结果按状态、再按开船时间从新到旧排；每条有 `name`、`target`（目标描述）、`platformList`、`label`（如「2026年8月实战活动」）、`joinCnt`
- 按名字和目标描述挑，不要只靠 `platform` 筛：2026 年 8 月的「AI 视频带货」讲的是视频号图书带货，方向标签却是「AI、电商」，按 `wechat` 筛不出来

### activitySearch

- 参数：`keyword`（必填）、`pageSize`（最多 50）、`pageIndex`
- 看这几个字段：`id`（航海 ID，后面的工具都要用）、`name`、`label`（如「2026年3月实战活动」）、`type`（常规航海 / Mini航海）、`startTime`（秒级时间戳）、`joinCount`、`isJoin`（当前用户有没有报名）
- 用来补 `activityList` 时间窗以外的更早期次。按匹配度排，不按时间排，要自己按 `startTime` 从新到旧排；`total` 可能有几十条，翻完所有页。
- 航海名字常常不带方向词：2025 年 12 月以后的小红书实物电商航海叫「小红书垂直小店」，搜「小红书电商」搜不到。平台名太短时换中文名：X 要搜「推特」，搜「X」会搜出名字里带「10X」的无关航海。
- 同一个方向常有好几条线，名字相近、做法完全不同。排好后列出候选，让用户确认是哪一条。

### getActivityDetail

客户端未暴露此工具时跳过，资料记录注明缺工具；不要猜报名状态或作业次数。

- 参数：`activityId`（字符串）
- 返回报名状态、航海时间范围、作业制还是旧日志制、要交几次作业（`requiredTaskCount`）。上岸条件的文字这里没有。用来判断后面哪些工具能用。
- 报名人数在 `activitySearch` 的 `joinCount` 里；结营时多少人出了单，这里没有。

### activityManualToc

- 参数：`activityId`
- 返回目录条目：`itemId`、`title`、`level`、`parentId`、`hasContent`。**只读 `hasContent=true` 的条目。**
- 想读某一章的全文：按 `parentId` 找出这一章下面所有 `hasContent=true` 的小节，逐节读。

### activityManualDetail

- 参数：`activityId`、`itemId`（必须是同一期航海目录里的）、`format`、`maxChars`（默认 20000，最多 50000）、`offset`
- **`format="markdown"`**：保留标题和列表，图片变成 `![图片](签名链接)`。只有新手册（`manualType=new`）支持；旧手册两种格式一样，都没有图片地址。
- 返回 `truncated=true` 表示没读完，把 `nextOffset` 原样作为下次的 `offset` 接着读。
- 图片链接里可能有 `&amp;`，下载前要还原成 `&`（`scripts/fetch_images.py` 会处理）。

### activityManualSearch

- 参数：`keyword`（必填）、`pageSize`（最多 50）
- 在所有航海的手册里搜，能找到别的期次写过的同一个步骤。读不到当期手册时，靠它补。

### contentSearch

- 参数：`keyword`、`pageScene`（`all` 全部 / `good` 精华 / `fxb` 风向标 / `topic` 主题帖 / `square` 广场 / `winBid` 中标）、`gmtCreateStart` / `gmtCreateEnd`（秒级时间戳，含首尾）、`pageSize`（最多 50）、`displayMode`（1 = 100 字摘要，2 = 220 字摘要加首图）
- `pageScene` 是 `all` 或不传时，`keyword` 必填。
- 关键词只用一两个词。「视频号 开通带货 橱窗」只回 1 条，换成「视频号带货中心」才出来。
- 摘要里出现 `xxxxxxxx.webp`、`image.png` 这样的文件名，说明这篇正文嵌了截图，优先读。
- 风向标（`fxb`）多是「某个品卖了多少单」的一段话线索，选品时有用，当不了操作步骤的来源。
- 返回的 `topicDTO` 里看：`entityType`、`entityId`、`showTitle`、`gmtCreate`、`isDigested`（1 是精华）、`readingCount`。

算时间窗（最近三个月）：

```bash
python3 -c "import time; e=int(time.time()); print(e-92*86400, e)"
```

### searchTopic

- 至少传一个过滤条件：`keyword`、时间窗、`isDigested=true`、`isHot=true` 等
- 适合「最近三个月这个方向的精华帖」这种组合查询：`keyword` + `isDigested=true` + 时间窗。
- **按标签拉**：`topicDetail` 和搜索结果里每篇帖子都有 `menuList`（如 `{"key": 2881345, "value": "小红书电商"}`）。找到只属于这个方向的那个标签，把 `key` 按字符串放进 `includeMenuIdList`，加时间窗拉。关键词会搜出大量只是顺带提到的帖子，按标签拉几乎都相关：X 自媒体方向按关键词「推特」加精华搜出 54 篇，一大半只是顺带提到；按 X 的标签拉出 78 篇，几乎都相关。

### topicDetail

- 参数：`entityType`（星球帖 `xq_topic`，官网帖 `forum_topic`，从搜索结果里原样拿）、`entityId`（**十进制字符串**）
- 看这几个字段：
  - `articleContentContainFeishuDoc`：完整正文，含飞书长文。**这个字段为空不代表帖子没有正文**，退回去看 `articleContent`。
  - `imageList`：截图地址列表，和正文里的图片占位按顺序对应，见第三部分。占位常常只在 `articleContentContainFeishuDoc` 里。
  - `gmtCreate`：发帖时间（秒级时间戳），出处日期就用它。
  - `detailUrl`：帖子链接，出处写这个。
  - 返回顶层 `topicUserDTO.name` 与 `topicUserDTO.avatar`（与 `topicDTO` 并列）：同一篇帖子的作者昵称与头像地址。只在这两个字段实际存在、且正文引用该作者案例时使用头像；不要从点赞人或评论人列表取头像冒充作者。
- 有的长文正文只是一个外部飞书链接，要登录才能看。读不到就如实写「原帖正文在外部文档，没读到」。

### searchKnowledgeBase

客户端未暴露此工具时跳过，资料记录注明缺工具；改用已有的只读搜索，不把缺工具误报为没有站内材料。

- 参数：`userQuestion`，用完整的问题，比如「小红书实物电商怎么找一件代发的货源」
- 返回最相关的 10 篇帖子。适合补关键词搜不到的内容。

### searchVisibleActivityQa / searchVisibleActivitySubmissions

- 只对**已报名**的航海开放，服务端会校验。没报名就跳过，不要反复试。
- 问答：`activityId`、`keyword`、`sortBy`（`newest`、`most_likes` 等）、`withLatestAnswers=true`（每题最多带 3 条回答）
- 作业：`activityId`、`pageSize`（最多 10）
- 问答里教练的回答和圈友的回答要分开标。

### projectLibSearch / projectLibDetail

- 先 `projectLibSearch`（`keyword`）拿到项目 `id`，再 `projectLibDetail`（`projectId`）
- 看启动资金、每天时长、月收入区间、案例数。这些只作为平台公开参考区间；没有统计时间、样本和方法时，不代表一般人的平均结果。

### 原文链接与作者头像

- 帖子原文使用本次 `topicDetail.detailUrl`；不要从 `entityType`、`entityId` 拼 URL。项目库和航海材料只在本次 MCP 返回实际给出可用的原文链接字段时加链接；目前本参考没有核实它们的 URL 格式，缺字段时只写来源定位文字，不猜规则。输出到 HTML 时仅保留 `https://` 的来源链接，转义后写为 `<a target="_blank" rel="noopener noreferrer">`；页内章节互引仅指向已有的 `#section-...`。链接是用户点击的导航，不能作为图片、脚本、字体或样式资源加载。
- 2026-09-30 的只读试跑 `topicDetail` 返回中，作者头像字段是与 `topicDTO` 并列的顶层 `topicUserDTO.avatar`，实际地址的主机为 `search01.shengcaiyoushu.com`；这是下文头像白名单的取值依据，不据此推断其他接口也用同一主机。将整条 `topicDetail` 原始 JSON 交给头像脚本，不移动字段。每张只接受来自该精确主机的 HTTPS 图片；若新的 MCP 返回主机不同，先核对实际返回及来源，再显式配置该精确主机，不添加泛域名或猜测地址。头像缺失或下载失败只显示作者昵称。
- 头像下载沿用 `scripts/fetch_images.py` 的公网 DNS 校验、固定 IP 建连、TLS 原域名校验、禁代理和拒绝跳转，单张限制 200 KiB；只内嵌经结构检查的 PNG/JPEG/WebP data URI，不在成品网页放远程头像地址。网页解码失败时隐藏头像、保留昵称；自动 PDF 禁用网页脚本，没有这层兜底，需检查 PDF。头像仅贴在对应作者案例的引用旁，`alt` 用作者昵称。分享给社区外的人之前，提醒手册包含其他会员的昵称与头像。

## 三、截图怎么取

### 帖子里的截图

`topicDetail` 返回的 `imageList` 是图片地址；正文里图片的位置是一个单独的文件名，写法很多：`7prIiZPJ.webp`（8 位字母数字）、`image.png`、`083fb8ce36c30466414ab4e913afd0e5.jpg`（32 位十六进制）、`ScreenShot_2026-04-15_155337_790.png`、`微信图片_xxx.jpg`。**占位和 `imageList` 按出现顺序一一对应**：正文第 1 个占位就是 `imageList` 第 1 个地址。

- 用之前先数两边的数量。**数量对不上，就别按顺序硬套**，宁可少放几张图。下载脚本会两个正文字段都数，取数量对得上的那个。
- 图片地址有两种：飞书长文转存的（`search01.shengcaiyoushu.com/upload/doc/…`）不带签名；星球帖自己上传的（`…/private/xq/images/…?Expires=…&Signature=…`）带签名，**几个小时就失效，读完就下载**。
- `imageList` 是空的，但正文里有 `<img src="https://search01.shengcaiyoushu.com/public/xq/article-images/…">`：这些是公开图，按正文里的位置下载（下载脚本认得）。两样都没有，这篇就取不到图，只能用文字。
- 数量对不上时，一张图打开后一眼能认出是什么（后台数据页、表格、剪辑软件的时间线），也可以用；图注只写图上看得到的，并写明从哪篇帖子来、原来是作者拿来说明什么的。

### 手册里的截图

只有 `format="markdown"` 时才有地址，形如 `![图片](https://...?Expires=...&Signature=...)`。

- **签名大约 24 小时后失效，读完一章就下载这章的图。**
- 图片在正文里的位置就是它说明的那段话。配到手册步骤前，先确认这张图前后那段文字讲的就是这一步。
- **手册里有装饰分隔线**：章节之间的一条横线加生财 logo（如 1280×67 像素），在正文里和截图一样是 `![图片](...)`，而且常常紧挨着重要段落。下载脚本按尺寸标出候选；打开确认是装饰线才不用于步骤，不能仅按比例删图。
- **分段读取时，图片链接可能被切在两段之间**：一段的末尾是半截链接。把各段正文接起来再提取图片，或者把 `maxChars` 调大（最多 50000）一次读完。

### 下载

运行 `scripts/fetch_images.py`，用法见脚本开头的说明。它会下载、识别格式、核对数量，并生成一份对应表。能给它的输入：

航海手册 `activityManualDetail(format="markdown")` 的图片链接若在别的主机，先从该次 MCP 原始链接读取 URL 主机，再运行 `python3 scripts/fetch_images.py <原始返回文件> --allow-host <该链接的精确主机名>`；每个额外主机各传一次 `--allow-host`，不得据示例猜主机。安全边界：脚本默认只下载 `https://search01.shengcaiyoushu.com` 的图片；其他图片域名必须先对照原资料确认，再用 `--allow-host <精确域名>` 显式追加。不要因为下载失败就把陌生域名加入名单。脚本拒绝跳转和非公网解析，单张限制 20 MiB，文件与映射不覆盖已有文件；同一 `--prefix` 重跑时需换新输出目录或前缀，不能删除旧证据后盲目重试。预览和映射不保存签名 query，但输入原文及 `_raw/` 仍可能含签名，按[私有缓存规则](records-and-review.md)保管和清理。

- **客户端把接口返回存成的文件**：返回太长时，有的客户端会存盘并告诉你路径，直接传这个文件
- **自己写的清单**：纯文本，一行一个链接，链接后面可以空一格写图注
- 手册正文存成的 Markdown，或整个 `topicDetail` 返回存成的 JSON

**接口返回只在对话里、没有存成文件时，只把准备用的那几张图的链接抄进清单**，不要把整章正文或几十个签名链接全抄一遍：链接很长，抄得越多越容易错，也越费时间。只下载一部分时，清单里不要写 `expected_count`：它是把一篇帖子的图全下载时拿来核对数量的。

## 四、已知的坑

| 现象 | 原因 | 怎么办 |
| --- | --- | --- |
| 手册正文里只有「[图片]」两个字 | 默认 `format=text` | 改传 `format="markdown"` |
| `format="markdown"` 后仍没有可用截图 | 返回或权限缺少图，不能推造后台界面 | 回到 `plan.md` 按关键动作判断是否可用已核实规则的原创流程图、明确虚构样例或有依据的纯文字；示意图不充当平台按钮证据 |
| 昨天能打开的手册图片今天打不开 | 签名过期 | 重新调 `activityManualDetail` 拿新链接 |
| 按数字传帖子 ID，读到的是别的帖子 | ID 超过 JavaScript 安全整数，被四舍五入 | 一律按字符串传 |
| 返回 `MCP_RATE_LIMITED` | 按账号限流，同一账号的所有调用共用额度 | 按 `retryAfterSeconds` 等；一次只调一个 |
| 问答、作业搜不到东西 | 没报名这一期 | 跳过，改用帖子和 `activityManualSearch` |
| 帖子正文很短，只有一个链接 | 长文放在外部飞书文档 | 如实写没读到，不要编 |
| 摘出来的一句话很干净，原文后面紧跟着违规做法 | 只看了摘要或片段 | 引用前读原帖上下文 |
| 配图位置对，打开一看是一条横线 | 手册章节之间的装饰分隔线也是图片 | 尺寸仅筛候选；打开确认是装饰线才不用，真正的界面横条可保留 |
| 手册一段正文结尾是半截图片链接 | 分段读取切在了链接中间 | 接上下一段再提取，或调大 `maxChars` |
| 按方向名搜航海，最新一期没出来 | 航海名字不带方向词；结果不按时间排 | 先用 `activityList` 列时间窗内全部页，按名字和目标挑；更早期次用别名补搜 |
| 帖子图片过了几个小时打不开 | 星球帖自己上传的图带签名 | 读完就下载；过期了重新调 `topicDetail` |
| 帖子正文占位数和 `imageList` 对不上 | 占位写法多样，或在另一个正文字段里 | 交给下载脚本数；还对不上就别按顺序硬套 |
| 按关键词搜帖，一大半只是顺带提到 | 关键词是全文搜 | 找到这个方向的标签，用 `searchTopic` 按标签拉 |
| 多个词的关键词搜出 0 条 | 词越多越窄 | 拆成一两个词 |
| 平台官方帮助页打开是 403 或空白 | 页面挡了程序访问，或要浏览器渲染 | 先读当前页面：可尝试可用的官方语言版本或已授权的只读浏览器；读不到才用网页存档；最新快照若是 Cloudflare 验证页，从存档索引另选真正可读的一份，来源条目写实际阅读的存档链接与快照日期，之后能读到现行页面时再复核；仍都读不到时保留官方摘要及其范围，记「只看到摘要」，不能据此补未显示的条件。取得过程只写进来源节、`sources.md` 和 `run_notes.md`，不写进读者正文 |
