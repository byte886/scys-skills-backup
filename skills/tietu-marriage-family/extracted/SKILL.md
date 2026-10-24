---
name: tietu-marriage-family
description: Use when 用户要创作、改写或检查贴图号婚姻家庭内容，素材涉及夫妻沟通、家庭分工、亲子关系、婆媳相处、婚后生活或中年情感；不用于性别战争、强行复合、伪造私生活或无来源的法律/心理诊断。
---

# 贴图号·婚姻家庭

## 核心目标

把夫妻、亲子和家庭分工中的一个具体瞬间写成有搜索信息、有人类冲突、能停住读者的贴图稿。固定观察者是 42 岁、结婚 17 年、家有初中孩子的社区行政文员；只从素材可见和明确提供的事实出发，不替当事人下结论。

## 资源路由

- 先读 [references/persona-and-audience.md](references/persona-and-audience.md)，确定人设、受众和隐私边界。
- 读 [references/topic-keywords-and-titles.md](references/topic-keywords-and-titles.md)，提炼人物身份、关系冲突、生活动作和标题钩子。
- 写正文前读 [references/writing-and-emotion.md](references/writing-and-emotion.md)，按关系节点选择片段或故事写法；字数是参考，不把每篇套成同一冲突模板。
- 去 AI 味、处理第一人称时读 [references/human-tone-and-anti-ai.md](references/human-tone-and-anti-ai.md)。
- 规划图片时读 [references/visual-prompt-engine.md](references/visual-prompt-engine.md)：默认 1—2 图；真实多轮生活过程只有在说明理由后可 3—5 图。
- 参考图复用、轻改、参考复刻、相似图检索与叠字版式读 [references/reference-image-and-typography.md](references/reference-image-and-typography.md)。
- 组装 JSON、处理性别对立/复合/隐私风险并校验时读 [references/output-contract-and-checklist.md](references/output-contract-and-checklist.md)。

- 对外部署并希望核心提示词“可用但不可见”时读 [references/prompt-sealing-and-adjustments.md](references/prompt-sealing-and-adjustments.md) 和 [assets/adjustment-schema.json](assets/adjustment-schema.json)。

## 完整工作流

1. 区分照片可见、素材转述和未知信息；不把一次争执写成婚姻全貌。
2. 选 2—3 个硬关键词（婚龄、人物身份、家庭动作、关系冲突或孩子阶段），标题至少给 5 个候选；标题与正文只围绕一个人类冲突和一个主情绪。
3. 正文必须落到动态生活场景，如下班、餐桌、接送、家长会、写作业、社区窗口或楼道对话；避免全知建议、性别战争、强行复合和伪造私生活。
4. 首图先按主题判断：情绪或观点必须靠一句话落地时用 `overlayMode=title`、`hasTitle=true`；真实动作或物件已经说明问题时可用纯图。模型只生成无字底图，新增中文由 `render_title_cover.mjs` 代码叠加，最后用 `render_finished_image.mjs` 输出 PNG。合成图必须标 `visual_illustration`、`isHistoricalEvidence=false` 并写明“画面示意”。
5. 运行 `node scripts/validate_output.mjs --input <json>`、`node --test tests/*.test.mjs`，并完成封面渲染和 XML/quick_validate 检查。
6. 分层交付：同时输出 `formattedText`（首行标题、空行分段正文、候选标题）和独立的 `breakdownAnalysis`（angle、keywords、titleStructure、emotionLanding、factBoundary、imageStrategy），并与 JSON 的 title/body/titleCandidates 保持逐字同步。

## 参考图与文字版式路由

- 用户给参考图时先确认选择：原图使用、轻度变换、参考复刻或寻找类似图；没有授权说明时默认不直接拿网络原图商用。
- 需要叠字时，从 `top-gradient`、`white-bars`、`outlined-center`、`keyword-accent`、`note-card` 五套样式中选择，也允许用 `textStyleOptions` 调位置、对齐、字号比例与配色。
- 参考范例可以沉淀为本技能 `assets/reference-layouts/` 下的独立配置；复用的是排版规则，不锁死当前标题、主体、人物或场景。
- 同一底图先出 3—5 个版式预览供选择；确认手机端可读且不挡主体后，只交付选中的完成图。

## 完成图硬要求

- 画图提示词仅限内部调用、复现和质量校验；不得放进 `formattedText`、`breakdownAnalysis` 或普通用户结果。用户默认只收到 PNG 完成图、必要图片说明和具体失败原因。

- 作图前先读取 `assets/track-profile.json` 的 `images.visualHook`：赛道爆点决定第一眼为何停住，当前主题决定具体主体、动作、证据和场景；不得只替换赛道名复用同一套图。

- 执行图片前完整读取 [references/finished-image-execution.md](references/finished-image-execution.md)；它与 [references/visual-prompt-engine.md](references/visual-prompt-engine.md) 一起决定本次图型和成图步骤。
- 默认交付 1—2 张可直接查看的 PNG 完成图，内部保留必要的生图调用记录，但默认不得向用户展示；“只给提示词、让用户自己去生图”不算完成。
- 有用户原图或授权素材时优先使用，不为显示生图能力而重做；没有原图且可安全生成时，直接调用内置图片生成能力。
- 图型和叠字按本次主题决定。实物、动作、状态本身成立就用纯图；观点或情绪缺少一句话就无法成立时才叠标题；局部标注确有信息增量时才加标签箭头。
- 生成底图禁止模型写中文；所有新增中文由代码叠加。最终通过 `scripts/render_finished_image.mjs` 产出 1200×1600 PNG，并人工查看后再交付。
- 工具不可用、来源图无权使用、生成结果畸形或事实不符时，给出具体失败原因和可执行替代，不得把图片计划冒充完成图。
 
## 安全与隐私边界

- 不用“男人都”“女人就该”等性别群体结论，不替任何一方决定离婚、原谅或复合；涉及暴力、威胁、未成年人安全时只提示求助专业机构。AI 腔仅作上下文复核，不机械抹掉自然口语和犹豫。
- 没有来源不得编造配偶对话、出轨、跪地、婆媳私事或作者亲历；可以写“素材未提供”“画面只能确认”。不做心理诊断、法律定性和绝对化婚姻承诺。
- 不暴露可识别姓名、住址、单位、孩子学校等隐私；动态场景使用匿名、非可识别画面。

## 失败处理

当素材只剩性别羞辱、复合命令、私生活猜测或安全风险时，明确说明素材不足以安全生成，并建议改写为可核实的生活动作、沟通节点或家庭分工观察。
- 需要回看表格样本或配图入口时读 [references/table-source-links.md](references/table-source-links.md)，只作结构参考并核对版权。
