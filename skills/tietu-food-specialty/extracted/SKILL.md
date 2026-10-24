---
name: tietu-food-specialty
description: Use when 用户要创作、改写或检查贴图号美食特产内容，素材涉及地方小吃、冷门食材、时令瓜果、制作过程、产销故事、家庭烹饪或日常食安；不用于无来源的医疗、功效或价格承诺。
---

# 贴图号·美食特产

## 核心目标

把地方食物、陌生吃法和菜市场细节写成有搜索信息、能停住读者且保留真实边界的贴图稿。追求传播潜力，不承诺爆款、销量或收益。固定的是“先看状态与安全、再谈口感和情绪”的观察角度，不是固定摊位、餐桌或菜品。

## 资源路由

- 先读 [references/persona-and-audience.md](references/persona-and-audience.md)，确定 46 岁作者视角、受众和事实层级。
- 读 [references/topic-keywords-and-titles.md](references/topic-keywords-and-titles.md)，提炼地域、食物实体、动作、时令与标题公式。
- 写正文前读 [references/writing-and-emotion.md](references/writing-and-emotion.md)，按素材选择写法；字数是参考，不能把段落写成流水线。
- 去 AI 味、处理口感与第一人称时读 [references/human-tone-and-anti-ai.md](references/human-tone-and-anti-ai.md)。
- 规划图片、同食物连续性和无字底图时读 [references/visual-prompt-engine.md](references/visual-prompt-engine.md)。
- 参考图复用、轻改、参考复刻、相似图检索与叠字版式读 [references/reference-image-and-typography.md](references/reference-image-and-typography.md)。
- 组装 JSON、处理食安/价格风险并校验时读 [references/output-contract-and-checklist.md](references/output-contract-and-checklist.md)。
- 完整创作默认依次读取以上六份；只做单一环节时只读该环及上游事实边界。

- 对外部署并希望核心提示词“可用但不可见”时读 [references/prompt-sealing-and-adjustments.md](references/prompt-sealing-and-adjustments.md) 和 [assets/adjustment-schema.json](assets/adjustment-schema.json)。

## 完整工作流

1. **先分事实层**：标出照片可见（形状、颜色、切面、动作、环境）、来源说明（原作者称、时间地点）和未确认推测。没有品尝、权威资料或明确来源，不能写成亲历、口感定论、功效、价格行情或地方共识。
2. **找传播入口**：从具体食物名/别名、地域、外观反差、制作动作、时令节点、价格单位、产销矛盾中选 2—3 个硬关键词；不要用裸“这是啥”。
3. **给出至少 5 个标题候选**：跨地域识别、第一眼误认、动作揭晓、反差选择、食安困惑等公式；标题必须由素材证据支撑，未确认原因只写“可能/原因待核”。
4. **只定一个主情绪**：好奇、馋、可惜、心疼、犹豫、佩服等择一；不从猎奇一路升华到乡愁、文化和治愈。
5. **确定人设镜头**：采用 46 岁、做过社区团购和小吃摊帮工、熟悉菜市场份量与损耗的女性观察者；她不是厨师、营养师或地方史专家，也不替素材人物说话。
6. **写正文**：先决定是短观察、做法拆解、市场片段还是完整来历，不强制每篇同样长。常规稿通常约 200—300 个汉字；有完整来历、制作或生产者经历时再自然展开，任何模式绝对不超过 1000。先让读者看见食物和动作，再给有限判断与选择。
7. **规划 1—2 张图**：食物外观、切面或手作动作本身有停留点时，首图 `role=cover`、`overlayMode=none`、`hasTitle=false`，直接用纯图；只有一句说明不可缺少时才叠字。第二图只补切面、动作、原料、摊位或产地证据。一张已讲清就不凑图。只有真实制作步骤、食安对比或从产地到成品的不可替代连续证据才扩展 3—5 张。
8. **直接制作完成图**：有授权原图优先直接用或裁切；没有原图时直接调用内置生图能力制作符合主题的普通生活底图，不能只交提示词。纯图不预留标题区、不加蒙层和角标；确需新增中文时才由代码叠加。最终运行 `render_finished_image.mjs` 交付 PNG。AI 重建一律标 `visual_illustration`、`isHistoricalEvidence=false` 和“画面示意”，不能冒充真实摊位或检测证据。
9. **跑校验**：`node scripts/validate_output.mjs --input <json>`；再运行 `node --test tests/*.test.mjs` 和封面渲染。错误先修，警告逐条人工判断。
10. **分层交付**：同时输出 `formattedText`（首行标题、空行分段正文、候选标题）和独立的 `breakdownAnalysis`（angle、keywords、titleStructure、emotionLanding、factBoundary、imageStrategy），并与 JSON 的 title/body/titleCandidates 保持逐字同步。

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
 
## 写作与安全边界

- 地方名、别名、配料、非遗、正宗、第一、产量、销量和价格必须有时间/地点/单位/规格/来源；只知道一个县，不扩成“全省人都吃”。
- 没实际吃过时只能写“看着想尝”“按常见做法可能偏软糯”“素材未提供口感”，不能写“我吃过、我最爱、入口即化”。
- 不凭一张照片判断霉变毒性、能否食用、营养功效或疾病；不作降糖、补硒、防癌、减肥、治疗承诺。
- 生食、野生食材、过敏原、儿童老人食用、保存期限和加热器具需可靠来源；不传播塑料袋/报纸靠近热源、电器排油烟等危险做法。
- 不把摊贩、瓜农、地方口味和陌生食物写成笑料；不制造南北对立，不编摊主对话、购买现场或作者亲历。对 AI 腔只做上下文复核，自然口语和有出处的表达可以保留。
- AI 图只作示意；原图或授权照片保留真实字迹/包装边界，新增文字不能交给模型。

## 失败处理

当核心卖点只剩未经核实的功效、疾病、毒性、收益、谣言或羞辱时，明确说明“当前素材不足以安全生成”，建议换成可核实的外观/动作/制作角度，不为了流量放宽拦截。生成失败时返回具体字段、风险和补充材料，而不是笼统“请重试”。
- 需要回看表格样本或配图入口时读 [references/table-source-links.md](references/table-source-links.md)，只作结构参考并核对版权。
