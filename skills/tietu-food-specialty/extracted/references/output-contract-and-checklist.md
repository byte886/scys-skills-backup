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
  "perspective": "46岁菜市场熟客的观察位置，不冒充素材人物",
  "body": "正文",
  "formattedText": "最终标题\n\n正文\n\n候选标题：\n1. 候选标题一",
  "breakdownAnalysis": {
    "angle": "具体停留入口",
    "keywords": ["食物关键词", "地域或外观关键词", "动作关键词"],
    "titleStructure": "硬关键词及标题组合关系",
    "emotionLanding": "单一情绪如何由具体处境触发",
    "factBoundary": "未确认事实与处理方式",
    "imageStrategy": "封面、证据图和代码叠字边界"
  },
  "images": [],
  "imageException": null,
  "failureNotes": []
}
```

`mode` 使用配置中的模式名。常规稿通常约 200—300 个汉字，故事/来历稿按素材信息量自然展开；这是编辑参考，不是逐段填空的硬模板。配置中的最低字数只防止内容过短，偏离常用区间时给提示而不自动判失败；绝对上限为 1000。标题候选至少 5 个，最好跨 3 种公式。`emotion` 只能一个简短情绪词，不把好奇、温暖、乡愁和感动串在一起。

`formattedText` 是可直接复制的发布稿：首行必须逐字等于 `title`，第二行必须为空，随后包含完整 `body`，并逐字列出全部 `titleCandidates`（放在“候选标题：”区）。它不是另写一版文案，任何标题或正文变更都要同步更新。

`breakdownAnalysis` 是给编辑复盘的结构化拆解，六项均为非空：`angle`、`keywords`、`titleStructure`、`emotionLanding`、`factBoundary`、`imageStrategy`；其中 `keywords` 至少 3 个具体词。每项都要回答本次食物素材“为什么这样写、这样画、这样避险”，不得用空泛评价代替。

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

默认 1—2 张。超过 2 张时，`imageException.kind` 只能是 `food_process`、`food_safety_comparison` 或 `origin_to_product`，理由必须列出至少三个连续步骤/证据节点，并解释两张图为什么不足；“更丰富、好看、增加氛围、凑图”会失败。最多 5 张。

## 内容闸门

- 标题含具体食物或原料，且由正文事实支撑；没有主体的“这是啥”不通过。
- 事实分成 visible/reported/uncertain；未品尝不能写“我吃过/我最爱/入口即化”。
- 地方、价格、数量、正宗、销量、滞销和功效有来源；不能从单个摊位扩大到全省或所有人。
- 生食、野生、霉变、过敏、儿童老人和热源做法需要安全说明；不提供诊断、药物剂量或治疗承诺。
- 开头宜有即时反应；按素材自然安排食物专属动作/细节，不要求机械的字数密度；允许犹豫或改口。
- AI 腔规则用于发现空泛重复，需结合上下文人工判断；不误伤自然口语、地方叫法、有出处的引语和普通否定句。
- 不把摊贩、瓜农、陌生食物、地域口味写成笑料，不编作者亲历和摊主对话。
- 发布前核对两层交付：`formattedText` 与 `title`、`body`、候选标题逐字同步；`breakdownAnalysis` 六项齐全且能落到本次素材。

## 失败说明

无法安全生成时，`failureNotes` 写明缺少的来源或风险字段，例如“图片只显示绿色外皮，无法确认馅料与口感；请补充切面或把标题改成外观疑问”。不要用笼统“生成失败，请重试”。

## 命令

```bash
node scripts/validate_output.mjs --input examples/valid-output.json
node scripts/validate_output.mjs --input examples/invalid-output.json
node --test tests/*.test.mjs
node scripts/render_title_cover.mjs --input examples/cover-input.json --output /tmp/tietu-food-cover.svg
xmllint --noout /tmp/tietu-food-cover.svg
```
