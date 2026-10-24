# SkillHub 安装指引

下文中的“我”始终指正在与你对话、作出确认的人；不得把“我”理解为你自己。

## 开始执行

本文件承接安装提示词中的操作要求。以下操作中的 `packageId` 必须使用我在提示词中给出的 Skill 标识，逐字保留大小写、连字符、下划线及其他字符，不改写、不猜测替换、不把名称或 code 当成 packageId。只移除 Markdown 展示转义，例如 `skl\_Ab-C_d` 应还原为 `skl_Ab-C_d`，不能删除下划线；包标识外侧的引号或反引号是展示边界，不属于标识。

确认已接入生财 MCP（https://scys.com/mcp），读取当前会话真实的工具列表和参数说明，再调用 `skillhubInstallGuide(packageId=原样标识, operation=install)`。不要猜测工具参数或申请扩大权限；缺工具、权限或无法读取指南时，停止并说明阻塞原因。取得有效返回后，完成下文适用分支的本机核对、确认、安装与验证；不要循环读取本文件或重复调用 guide 代替安装。有真实阻塞或需要用户确认时明确说明，等待解决后从该步骤继续。

## 读取本次返回

调用 `skillhubInstallGuide(packageId=本次 Skill 标识, operation=install)` 后，先读取本次返回的 `packageId`、`version`。正常安装时再读取 `capabilityCard`、`runtimeTargets`、`environmentHints` 和 `installTargetDecision`；平台托管包还使用 `artifactDownloadUrl`、`artifactSha256`、`expiresAt`、`sourceStore`、`downloadPlan`。外部收录包与安装包缺失分支没有这些下载字段。下载地址、校验值、版本、目录与本次实际采用的 `targets` 均以本次返回或本机核对结果为准，不从这份文件里猜。

`capabilityCard.isOriginal=false` 时走「外部收录包」，使用 MCP 本次返回的官方来源及下文可核对的上游版本证据，不能因没有平台下载字段就判为包丢失。没有 `capabilityCard` 且没有下载链接、并明确返回安装包在存储中不存在时走「安装包缺失」，停止安装；确实缺少适用分支所需的安装信息、来源不明或相互矛盾时，停止并报告本次无法核验，不自行补造。独立 `sourceRevision` 是可选信息，缺席时按外部分支的官方链接核对路径继续。

## 安装目标与目录核对

服务端不为客户端目录背书，也不会生成 writePlan 或 symlinkPlan。请先报告当前客户端及已核对到的全局/项目级 Skill 目录、已有安装与覆盖影响，向用户确认后由你在本机决定写入位置；把最终采用的客户端:范围标识填入 targets 用于审计/上报。已有同名目录或版本时，不擅自覆盖、删除或改动无关文件。未知或新客户端同样不得回退到 Claude Code 目录。

【目录参考（非平台确认，必须以本机实际客户端规则为准）】
全局：Claude Code ~/.claude/skills/；Cursor ~/.cursor/skills/；Windsurf ~/.codeium/windsurf/skills/；Codex ~/.agents/skills/；Google Antigravity ~/.gemini/antigravity/skills/；Gemini CLI ~/.gemini/skills/；QoderWork ~/.qoderwork/skills/；WorkBuddy ~/.workbuddy/skills/。
项目级候选：.agents/skills、.claude/skills、.cline/skills、.codebuddy/skills、.codex/skills、.commandcode/skills、.continue/skills、.factory/skills、.github/skills、.goose/skills、.grok/skills、.iflow/skills、.junie/skills、.kilo/skills、.kilocode/skills、.kimchi/skills、.kiro/skills、.minimax/skills、.mux/skills、.neovate/skills、.opencode/skills、.openhands/skills、.pi/skills、.posit/assistant/skills、.qoder/skills、.roo/skills、.trae/skills、.windsurf/skills、.zcode/skills、.zencoder/skills。

`installTargetDecision.clientFamily` 仅是凭证上的客户端族，不作为识别结论或行动依据。`installTargetDecision.targetsExplicit` 和 `installTargetDecision.appliedTargets` 是本次审计信息，不决定写入路径。实际采用的 `targets` 以本机确认后的客户端:范围标识为准。

## 平台托管包

服务端提供托管包下载与校验数据，以及平台源存储的解压和 current 指向计划；客户端 Skill 目录与客户端写入、软链接方式由本机核对并经用户确认后决定。

使用本次返回的 `downloadPlan.zipUrl`、`downloadPlan.sha256`、`downloadPlan.extractTo`、`downloadPlan.afterExtract` 和 `sourceStore`；`artifactDownloadUrl` 与 `artifactSha256` 是同次返回的下载地址和校验值。向我展示 `capabilityCard`、安装目录及写入影响并取得确认，再执行下载和本机安装。下载后核对本次 SHA-256，SHA-256 校验不符时停止，不得继续解压或写入客户端目录；地址过期或返回不完整时报告原因，不拼下载地址。按本次计划处理平台源存储，再按已确认的本机规则安装到客户端目录，检查解压内容、Skill 入口文件与客户端可识别性，不能只下载就算完成。

## 外部收录包

外部收录：平台未托管此包。以 MCP 本次返回的官方来源（`authorSourceUrl` 或本次指令明确给出的原作者官方链接）为准，打开原作者的官方安装说明，核对来源、实际取得的上游版本与适用客户端；不能用平台 `version` 冒充上游 commit/tag，也不从旧页面、记忆或相似名称猜来源。缺少独立 `sourceRevision` 字段本身不构成安装阻塞，按以下版本依据依次选择核对路径：

| 版本依据                | 本次返回必需字段                    | 后续核对                                                                                                                               |
| ----------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| MCP 明确 revision       | `authorSourceUrl`、`sourceRevision` | 优先按本次明确返回的 revision 核对实际取得的版本；与官方来源不一致时报告卡点，不静默换版。                                             |
| 官方链接固定 commit/tag | `authorSourceUrl`                   | 没有独立 revision 时，从官方链接所含 commit/tag 核对实际取得的版本，不要求额外的 sourceRevision 字段。                                 |
| 官方浮动链接            | `authorSourceUrl`                   | 没有明确 revision 且链接未固定版本时，按官方方式解析并记录实际取得的 commit/tag 或可验证版本；分支名或 latest 本身不能当作已固定版本。 |

向我展示实际官方来源、上游版本、安装步骤、目标目录与影响，经确认后执行原作者的官方安装方式。官方步骤需要下载或解压时，可以按官方方式执行，但不能套用平台托管包的下载/解压计划，不执行平台 `downloadPlan`、`symlinkPlan` 或 `writePlan`；不得伪造平台包、下载地址、校验值或落盘计划。不得为适配平台擅自修改原 repo、重打包或改变其原有安装方式。安装后按官方方式核对取得的来源和 revision、入口文件及当前客户端可识别性；官方提供校验值时须核验，不把不存在的托管包 SHA-256 当校验依据。

`authorSourceUrl` 取自本次实际返回，独立 `sourceRevision` 仅在本次返回明确提供时使用；不假定固定字段层级，不补造缺席字段或新增工具参数。若未提供原始链接，告知我「（收录信息未提供原始链接，请联系原作者）」。无法核对来源、上游版本或官方步骤时停止；这里的上游版本指按上述路径实际取得并可核对的版本，不是要求返回独立 sourceRevision。确有卡点时如实报告，请我或原作者补充；不要改用平台托管包分支兜底。

## 验证与回报

原创与外部收录都必须先完成实际安装和本机校验，再调用 `skillhubReportInstalled` 上报安装结果；不能把读到说明、拿到下载地址或复制提示词当作已安装。按当前真实工具参数说明传入 `packageId=本次 packageId`、`operation=installed`、`installedVersion=本次 version`、`targets=实际采用的 targets`。托管包同时使用 `artifactSha256=本次 artifactSha256`；不要为外部包补造 artifactSha256，也不要将 sourceRevision 擅自塞进工具未声明的参数。

如客户端要求确认，请按其安全流程完成确认后调用。上报调用失败时，不得重试、回滚本机安装或将安装判定为失败；安装结果不受上报失败影响。向我分别报告实际目录、版本/上游 revision、校验结果与未验证项，以及上报成功或失败；未完成安装时说明卡点，不提前调用 installed 或宣称安装完成。

## 安装包缺失

若本次没有下发下载链接与落盘计划，且返回说明安装包在存储中不存在：installGuide 无法生成:包 `packageId` 的版本 `version` 的安装包在存储中不存在,无法安装。这不是 packageId 写错——包与版本都查得到,是产物本身丢了,所以重试、重查 id、换 targets 都不会成功;本次没有下发任何下载链接与落盘计划,请勿自行拼装下载。请告知用户联系该包作者重新发布该版本。

## 装好后看详情

装好后先打开网页 https://scys.com/skillhub/skills/<packageId>（`<packageId>` 用本次返回的 `packageId` 原样替换），查看这个 Skill 的详情，里面有 README、使用场景和示例提示词。工具列表里有 `skillhubGetReadme` 时，也可以调用 `skillhubGetReadme(packageId=本次返回的 packageId)` 直接读详情；没有就用网页，不要因为找不到该工具而停下或报错。
