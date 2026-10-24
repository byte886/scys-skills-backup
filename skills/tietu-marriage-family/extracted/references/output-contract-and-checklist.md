# 输出契约与验收清单

## 顶层 JSON

```json
{
  "mode": "standard|story",
  "sourceBasis": {"visible": [], "reported": [], "uncertain": [], "riskNotes": []},
  "keywords": [],
  "titleCandidates": [],
  "title": "最终标题",
  "emotion": "一个主情绪",
  "perspective": "42岁社区行政文员、结婚17年且有初中孩子的观察位置，不冒充素材人物",
  "body": "正文",
  "formattedText": "最终标题\n\n正文原文\n\n候选标题：\n候选标题1\n候选标题2",
  "breakdownAnalysis": {"angle": "切入角度", "keywords": ["关键词1", "关键词2", "关键词3"], "titleStructure": "标题结构", "emotionLanding": "情绪落点", "factBoundary": "事实边界", "imageStrategy": "图片策略"},
  "images": [],
  "imageException": null,
  "failureNotes": []
}
```

`mode` 使用配置中的模式名。常规稿通常约 200—300 个汉字，故事稿按关系节点和信息量自然展开；这是编辑参考，不是逐段填空的硬模板。配置中的最低字数只防止空洞短稿，偏离常用区间时给提示而不自动判失败；绝对上限 1000。标题候选至少 5 个，最好跨 3 种公式。`emotion` 只能一个简短情绪词，不把多种情绪串在一起。

`formattedText` 是可直接发布的同步成稿：首行等于 `title`，第二行为空行，必须包含完整 `body`，并在“候选标题：”段列出全部 `titleCandidates`。`breakdownAnalysis` 是编辑复核层，统一六字段均必填，`keywords` 至少 3 项。

## 内部结构与用户结果分离

- 内部结构继续保留每张图的 `prompt`，只供生图调用、质量校验和管理员调试。
- 对外不得返回图片对象中的 `prompt`、assembledPrompt、系统提示词或密钥。
- 普通用户只接收 `role`、`purpose`、`sourceNotice`、`overlayMode`、`finalImage`，以及必要的具体失败原因。
- 只有管理员明确选择 `admin_debug` 时，才可在受控环境查看内部调用记录；不得进入公开网页响应。

## 图片对象

### 当前完成图契约

以下规则覆盖本文中“首图固定为标题图”的旧描述：

- 每张图必须写 `visualMode`、`sourcePriority`、`overlayMode`、`role`、`hasTitle`、`purpose`、`source` 和 `prompt`。
- `visualMode` 按主题从本赛道配置的允许列表选择；`sourcePriority` 只能是 `must_use_source`、`prefer_source` 或 `can_generate`。
- 纯图首图：`overlayMode=none`、`hasTitle=false`、`overlay.method=none`。
- 叠字首图：`overlayMode=title|title_and_annotations`、`hasTitle=true`、`overlay.method=code`，且 `overlay.text` 与最终标题逐字一致。
- 后续图统一 `overlayMode=none`、`hasTitle=false`。
- 校验通过后必须真正生成并交付 PNG；提示词和 SVG 只是中间产物。执行见 [finished-image-execution.md](finished-image-execution.md)。

```json
{
  "role": "cover|detail|evidence|process",
  "hasTitle": true,
  "purpose": "这张图承担的唯一信息职责",
  "source": {
    "type": "source_material|source_material_crop|visual_illustration",
    "historicalAuthenticity": "verified|unverified",
    "isHistoricalEvidence": false,
    "note": "来源与边界",
    "description": "合成范围（仅 visual_illustration）"
  },
  "prompt": "无字底图提示词，明确禁止新增中文、标题、标签、箭头文字",
  "overlay": {"method": "code", "text": "仅首图必填", "position": "top-left", "palette": "market"}
}
```

首图必须 role=cover；纯图用 `overlayMode=none + hasTitle=false + overlay.method=none`，叠字图才要求 `hasTitle=true + overlay.method=code` 且 overlay.text 与 title 完全一致；后续图不得再用 cover，并使用 `overlayMode=none + hasTitle=false`。每张图都必须有 purpose、source 和完整无字提示词。合成示意必须 `isHistoricalEvidence=false`，并写 description/notice；不允许冒充真实地方、品尝或检测证据。

默认 1—2 张。超过 2 张时，`imageException.kind` 只能是本赛道配置允许的真实家庭连续节点，理由必须列出至少三个连续步骤/证据节点，并解释两张图为什么不足；“更丰富、好看、增加氛围、凑图”会失败。最多 5 张。

## 内容闸门

- 标题含具体人物身份、婚龄、关系动作或冲突，且由正文事实支撑；没有主体的空泛鸡汤不通过。
- 事实分成 visible/reported/uncertain；未品尝不能写“我吃过/我最爱/入口即化”。
- 人物身份、婚龄、原话、事件和结局必须有来源；不能从一次争执扩大成所有婚姻的结论。
- 涉及暴力、威胁、未成年人安全、法律或心理诊断时，写清求助边界，不提供绝对化判决或强行复合指令。
- 开头宜有即时反应；按素材自然安排家庭生活动作/物件，不要求机械的字数密度；只保留一个人类冲突和一个主情绪。
- AI 腔扫描用于提示万能判词和重复，不机械禁止普通口语、自然否定句、幽默或有来源的原话。
- 不制造性别战争，不强行劝离婚、原谅或复合，不编作者亲历、配偶对话和私生活细节。

## 失败说明

无法安全生成时，`failureNotes` 写明缺少的关系事实或风险字段，例如“素材只有一句争吵转述，无法确认人物关系和后续结局；可改写为当下沟通节点”。不要用笼统“生成失败，请重试”。

## 命令

```bash
node scripts/validate_output.mjs --input examples/valid-output.json
node scripts/validate_output.mjs --input examples/invalid-output.json
node --test tests/*.test.mjs
node scripts/render_title_cover.mjs --input examples/cover-input.json --output /tmp/tietu-marriage-cover.svg
xmllint --noout /tmp/tietu-marriage-cover.svg
```
