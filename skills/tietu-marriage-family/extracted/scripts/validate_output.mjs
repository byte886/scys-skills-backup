#!/usr/bin/env node

import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const profilePath = fileURLToPath(new URL('../assets/track-profile.json', import.meta.url));
const allowedImageRoles = new Set(['cover', 'detail', 'evidence', 'process']);
const allowedSourceTypes = new Set(['source_material', 'source_material_crop', 'visual_illustration', 'code_rendered_graphic']);
const allowedAuthenticityStates = new Set(['verified', 'unverified']);
const allowedSourcePriorities = new Set(['must_use_source', 'prefer_source', 'can_generate']);

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--input') {
      const value = argv[index + 1];
      if (!value || value.startsWith('--')) {
        throw new Error('参数 --input 后必须提供 JSON 文件路径');
      }
      args.input = value;
      index += 1;
      continue;
    }
    throw new Error(`不支持的参数：${token}`);
  }
  if (!args.input) {
    throw new Error('缺少必填参数 --input <json>');
  }
  return args;
}

async function readJson(path, label) {
  let raw;
  try {
    raw = await readFile(path, 'utf8');
  } catch (error) {
    throw new Error(`无法读取${label}：${path}（${error.message}）`);
  }
  try {
    return JSON.parse(raw.replace(/^\uFEFF/u, ''));
  } catch (error) {
    throw new Error(`${label}不是有效 JSON：${error.message}`);
  }
}

function countChineseChars(text) {
  return (String(text).match(/[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]/gu) ?? []).length;
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function validateImageSource(source, position) {
  const errors = [];
  if (!isPlainObject(source)) {
    return [`${position}.source 必填且必须是对象`];
  }
  if (!allowedSourceTypes.has(source.type)) {
    errors.push(`${position}.source.type 必须是 source_material、source_material_crop、visual_illustration 或 code_rendered_graphic`);
    return errors;
  }
  if (source.type === 'visual_illustration') {
    if (source.isHistoricalEvidence !== false) {
      errors.push(`${position}.source.isHistoricalEvidence 必须明确为 false`);
    }
    if (!isNonEmptyString(source.description) && !isNonEmptyString(source.notice)) {
      errors.push(`${position}.source 必须提供非空 description 或 notice，说明合成范围`);
    } else if (!/(?:示意|合成|重建|AI)/u.test(`${source.description ?? ''}${source.notice ?? ''}`)) {
      errors.push(`${position}.source.description 或 notice 必须明确标注为画面示意/合成范围`);
    }
    return errors;
  }
  if (source.type === 'code_rendered_graphic') {
    if (source.isHistoricalEvidence !== false) {
      errors.push(`${position}.source.isHistoricalEvidence 必须明确为 false`);
    }
    if (!isNonEmptyString(source.description) && !isNonEmptyString(source.notice)) {
      errors.push(`${position}.source 必须说明代码排版的信息范围`);
    } else if (!/(?:代码|排版|信息图|文案卡|对比卡|步骤卡)/u.test(`${source.description ?? ''}${source.notice ?? ''}`)) {
      errors.push(`${position}.source.description 或 notice 必须明确为代码排版的信息图或文案卡`);
    }
    return errors;
  }
  if (!allowedAuthenticityStates.has(source.historicalAuthenticity)) {
    errors.push(`${position}.source.historicalAuthenticity 必须是 verified 或 unverified`);
  }
  if (!isNonEmptyString(source.note)) {
    errors.push(`${position}.source.note 必填，用于说明原图或裁切边界`);
  }
  return errors;
}

function validateVisualRouting(image, position, profile) {
  const errors = [];
  const strategy = profile.images?.visualStrategy;
  const allowedModes = strategy?.allowedModes ?? [];
  if (!isNonEmptyString(image.visualMode)) {
    errors.push(`${position}.visualMode 必填`);
  } else if (!allowedModes.includes(image.visualMode)) {
    errors.push(`${position}.visualMode 不在本赛道允许范围：${allowedModes.join('、')}`);
  }

  if (!allowedSourcePriorities.has(image.sourcePriority)) {
    errors.push(`${position}.sourcePriority 必须是 must_use_source、prefer_source 或 can_generate`);
  }

  const sourceType = image.source?.type;
  const exactSourceByMode = {
    source_photo: 'source_material',
    source_crop: 'source_material_crop',
    documentary_illustration: 'visual_illustration',
    text_card: 'code_rendered_graphic',
    comparison_card: 'code_rendered_graphic'
  };
  const expectedSource = exactSourceByMode[image.visualMode];
  if (expectedSource && sourceType !== expectedSource) {
    errors.push(`${position}.visualMode=${image.visualMode} 时 source.type 必须是 ${expectedSource}`);
  }
  if (image.sourcePriority === 'must_use_source'
    && sourceType !== 'source_material'
    && sourceType !== 'source_material_crop') {
    errors.push(`${position}.sourcePriority=must_use_source 时必须使用来源原图或原图裁切`);
  }
  return errors;
}


function hasPositiveTextInstruction(prompt) {
  const commandPattern = /(?:要生成|请生成|请添加|添加|写上|带有)/gu;
  const targetPattern = /(?:新增)?(?:中文|汉字|文字|标题|标签|箭头(?:文字|说明|标注)?)/u;
  for (const match of prompt.matchAll(commandPattern)) {
    const prefix = prompt.slice(Math.max(0, match.index - 12), match.index);
    if (/(?:不|不得|不要|禁止|勿|无须|无需)[^，。；;！!？?\n]{0,8}$/u.test(prefix)) {
      continue;
    }
    const suffix = prompt.slice(match.index + match[0].length, match.index + match[0].length + 18);
    if (targetPattern.test(suffix)) return true;
  }
  return false;
}

function clauseHasNegatedTarget(clause, targetPattern) {
  const negativePattern = /(?:不(?:再)?(?:生成|添加|写上)|不要(?:生成|添加|写上)?|不得(?:生成|添加|写上)|禁止(?:生成|添加|写上)|勿(?:生成|添加|写上)|无)/gu;
  const negatives = [...clause.matchAll(negativePattern)];
  if (negatives.length === 0) return false;
  for (const target of clause.matchAll(targetPattern)) {
    for (const negative of negatives) {
      const negativeEnd = negative.index + negative[0].length;
      if (negativeEnd <= target.index && target.index - negativeEnd <= 36) {
        return true;
      }
    }
  }
  return false;
}

function validateNoGeneratedTextPrompt(prompt, position) {
  const errors = [];
  if (hasPositiveTextInstruction(prompt)) {
    errors.push(`${position}.prompt 含有要求生成或添加文字的反向指令`);
  }
  const clauses = prompt.split(/[，。；;！!？?\n]/u).filter(Boolean);
  const categories = [
    /(?:中文|汉字|文字|字底图)/gu,
    /标题/gu,
    /标签/gu,
    /箭头(?:文字|说明|标注)?/gu
  ];
  const covered = categories.map((targetPattern) => (
    clauses.some((clause) => clauseHasNegatedTarget(clause, targetPattern))
  ));
  if (covered.some((value) => !value)) {
    errors.push(`${position}.prompt 必须分别明确否定生成中文或文字、标题、标签和箭头文字`);
  }
  return errors;
}

function validateImageExceptionReason(reason) {
  const errors = [];
  const normalized = reason.trim();
  if (/(?:更丰富|画面丰富|丰富画面|更好看|为了好看|凑图|增加氛围|增强氛围|更有氛围)/u.test(normalized)) {
    errors.push('imageException.reason 不能用“更丰富／更好看／凑图／增加氛围”等泛化理由');
  }
  const hasProcessOrEvidence = /(?:连续|步骤|节点|证据)/u.test(normalized);
  const hasNamedSequence = (
    /(?:分别|依次|包括|是)[^。；\n]{1,48}(?:、|，)[^。；\n]{1,48}(?:、|和|与|以及)[^。；\n]{1,48}/u.test(normalized)
    || /先[^。；\n]{1,32}再[^。；\n]{1,32}(?:最后|然后)[^。；\n]{1,32}/u.test(normalized)
  );
  if (!hasProcessOrEvidence || !hasNamedSequence) {
    errors.push('imageException.reason 必须明确列出至少三个连续步骤或证据节点');
  }
  const explainsTwoImagesInsufficient = (
    /两张(?:图|图片)?[^。；\n]{0,28}(?:不足|不够|无法|不能|会漏|缺少)/u.test(normalized)
    || /(?:不足|不够|无法|不能|会漏|缺少)[^。；\n]{0,28}两张(?:图|图片)?/u.test(normalized)
  );
  if (!explainsTwoImagesInsufficient) {
    errors.push('imageException.reason 必须明确说明两张图为何不足');
  }
  return errors;
}

function validateCore(output, profile) {
  const errors = [];
  const warnings = [];

  if (!output || typeof output !== 'object' || Array.isArray(output)) {
    return { errors: ['顶层内容必须是 JSON 对象'], warnings, bodyCount: 0, imageCount: 0 };
  }

  if (!isNonEmptyString(output.title)) {
    errors.push('title 必填且必须是非空字符串');
  } else {
    const titleCount = countChineseChars(output.title);
    if (titleCount < 7) {
      warnings.push('标题过短，可能缺少人物身份、关系动作、婚龄或冲突中的具体钩子');
    }
    if (/^(?:那些年|旧时光|难忘的回忆|曾经的温暖)[！!。.]?$/u.test(output.title.trim())) {
      warnings.push('标题过于泛化，没有落到具体关系、家庭动作或冲突证据');
    }
  }

  if (!Array.isArray(output.titleCandidates) || output.titleCandidates.length < 5) {
    errors.push('titleCandidates 至少需要 5 个候选标题，并应跨不同标题公式');
  } else if (output.titleCandidates.some((candidate) => !isNonEmptyString(candidate))) {
    errors.push('titleCandidates 中每一项都必须是非空字符串');
  }

  if (!isPlainObject(output.sourceBasis)) {
    errors.push('sourceBasis 必填且必须记录 visible、reported、uncertain 等事实层');
  } else {
    for (const field of ['visible', 'reported', 'uncertain']) {
      if (!Array.isArray(output.sourceBasis[field])) {
        errors.push(`sourceBasis.${field} 必须是数组`);
      }
    }
    if (!Array.isArray(output.sourceBasis.riskNotes)) {
      errors.push('sourceBasis.riskNotes 必须是数组；没有风险时也请填空数组');
    }
  }

  if (!isNonEmptyString(output.perspective)) {
    errors.push('perspective 必填，需说明固定的婚姻家庭观察者视角');
  } else {
    if (!/(?:42|四十二)/u.test(output.perspective)) {
      errors.push('perspective 必须体现 42 岁人设');
    }
    if (!/(?:社区行政文员)/u.test(output.perspective)) {
      errors.push('perspective 必须体现社区行政文员身份');
    }
    if (!/(?:结婚17年|结婚十七年|17年婚姻)/u.test(output.perspective)) {
      errors.push('perspective 必须体现结婚17年');
    }
    if (!/(?:初中孩子|上初中|初中的孩子)/u.test(output.perspective)) {
      errors.push('perspective 必须体现有初中孩子');
    }
  }

  if (!Array.isArray(output.keywords) || output.keywords.length < 3 || output.keywords.some((keyword) => !isNonEmptyString(keyword))) {
    errors.push('keywords 至少需要 3 个具体、非空的人物/关系/生活动作关键词');
  }
  if (!Array.isArray(output.failureNotes)) {
    errors.push('failureNotes 必须是数组；没有失败原因时请填空数组');
  }

  if (!isNonEmptyString(output.formattedText)) {
    errors.push('formattedText 必填，需提供面向读者的排版交付');
  } else if (isNonEmptyString(output.title) && isNonEmptyString(output.body)) {
    const lines = output.formattedText.split(/\r?\n/u);
    if (lines[0]?.trim() !== output.title.trim()) {
      errors.push('formattedText 首行必须等于 title');
    }
    if (lines[1]?.trim() !== '') {
      errors.push('formattedText 标题后必须有空行');
    }
    if (!output.formattedText.includes(output.body)) {
      errors.push('formattedText 必须同步包含 body 原文');
    }
    if (!output.formattedText.includes('候选标题：')) {
      errors.push('formattedText 必须包含“候选标题：”段');
    }
    for (const candidate of output.titleCandidates ?? []) {
      if (!output.formattedText.includes(candidate)) {
        errors.push(`formattedText 必须同步包含 titleCandidates：${candidate}`);
        break;
      }
    }
  }

  if (!isPlainObject(output.breakdownAnalysis)) {
    errors.push('breakdownAnalysis 必填且必须是对象');
  } else {
    for (const field of ['angle', 'keywords', 'titleStructure', 'emotionLanding', 'factBoundary', 'imageStrategy']) {
      const value = output.breakdownAnalysis[field];
      const valid = field === 'keywords'
        ? Array.isArray(value) && value.length >= 3 && value.every((item) => isNonEmptyString(item))
        : isNonEmptyString(value);
      if (!valid) errors.push(`breakdownAnalysis.${field} 必填且不可为空`);
    }
  }

  const modes = profile.body?.modes ?? {};
  if (!isNonEmptyString(output.mode) || !Object.hasOwn(modes, output.mode)) {
    errors.push(`mode 必须是以下值之一：${Object.keys(modes).join('、')}`);
  }

  let bodyCount = 0;
  if (!isNonEmptyString(output.body)) {
    errors.push('body 必填且必须是非空字符串');
  } else {
    bodyCount = countChineseChars(output.body);
    const absoluteMax = profile.body.absoluteMaxChineseChars;
    if (bodyCount > absoluteMax) {
      errors.push(`正文含 ${bodyCount} 个汉字，超过绝对上限 ${absoluteMax}`);
    }
    const modeRule = modes[output.mode];
    if (modeRule && bodyCount < modeRule.minChineseChars) {
      errors.push(`${modeRule.label}正文至少需要 ${modeRule.minChineseChars} 个汉字，当前为 ${bodyCount}；请补足本题事实或切换更合适的模式`);
    }
    if (modeRule && Number.isFinite(modeRule.preferredMinChineseChars) && Number.isFinite(modeRule.preferredMaxChineseChars)
      && (bodyCount < modeRule.preferredMinChineseChars || bodyCount > modeRule.preferredMaxChineseChars)) {
      warnings.push(`${modeRule.label}正文当前 ${bodyCount} 个汉字，偏离常用参考 ${modeRule.preferredMinChineseChars}—${modeRule.preferredMaxChineseChars}；以素材完整性和读感为准，不要机械补字`);
    }
    if (!/(?:下班|早晨|晚上|餐桌|厨房|客厅|楼道|办公室|社区|公交|校服|作业|书包|手机|门口)/u.test(output.body)) {
      errors.push('正文必须包含具体动态生活场景');
    }
  }

  if (!isNonEmptyString(output.emotion)) {
    errors.push('emotion 必填且必须只写一个主情绪');
  } else {
    const emotion = output.emotion.trim();
    if (/[、,，;；/]|(?:以及|和|与|加上)/u.test(emotion)) {
      errors.push('emotion 只能落一个主情绪，不能并列多个情绪');
    }
    if (countChineseChars(emotion) > profile.emotion.maxChineseChars) {
      errors.push(`emotion 应是单一、简短的情绪词，最多 ${profile.emotion.maxChineseChars} 个汉字`);
    }
  }

  const images = output.images;
  let imageCount = 0;
  if (!Array.isArray(images)) {
    errors.push('images 必填且必须是数组');
  } else {
    imageCount = images.length;
    const imageRules = profile.images;
    const allowedOverlayModes = imageRules.finishedOutput?.allowedOverlayModes ?? ['none', 'title', 'title_and_annotations'];
    if (imageCount < imageRules.defaultMin) {
      errors.push(`至少需要 ${imageRules.defaultMin} 张图片计划`);
    }
    if (imageCount > imageRules.extendedMax) {
      errors.push(`图片最多 ${imageRules.extendedMax} 张，当前为 ${imageCount}`);
    }
    if (imageCount > imageRules.defaultMax) {
      const exception = output.imageException;
      const kindAllowed = exception && imageRules.exceptionKinds.includes(exception.kind);
      if (!kindAllowed || !isNonEmptyString(exception?.reason)) {
        errors.push(`普通内容只能有 ${imageRules.defaultMin}—${imageRules.defaultMax} 张图；3—${imageRules.extendedMax} 张仅限真实家庭连续节点，并须填写 imageException.kind 与 reason`);
      } else {
        errors.push(...validateImageExceptionReason(exception.reason));
      }
    }

    if (imageCount > 0) {
      const cover = images[0];
      if (!cover || typeof cover !== 'object' || Array.isArray(cover)) {
        errors.push('首图必须是图片计划对象');
      } else {
        if (cover.overlayMode === 'none') {
          if (cover.overlay?.method !== 'none') {
            errors.push('纯图首图 overlay.method 必须为 none，不得叠加标题');
          }
        } else {
          if (!cover.overlay || cover.overlay.method !== 'code') {
            errors.push('需要文字的首图 overlay.method 必须为 code，中文标题须由代码叠加');
          }
          if (!isNonEmptyString(cover.overlay?.text)) {
            errors.push('需要文字的首图 overlay.text 必填');
          } else if (isNonEmptyString(output.title) && cover.overlay.text.trim() !== output.title.trim()) {
            errors.push('首图 overlay.text 必须与 title 完全一致');
          }
        }
      }
    }

    images.forEach((image, index) => {
      const position = `images[${index}]`;
      if (!image || typeof image !== 'object' || Array.isArray(image)) {
        errors.push(`${position} 必须是对象`);
        return;
      }
      if (!allowedImageRoles.has(image.role)) {
        errors.push(`${position}.role 必须是 cover、detail、evidence 或 process`);
      } else if (index === 0 && image.role !== 'cover') {
        errors.push('首图 role 必须是 cover');
      } else if (index > 0 && image.role === 'cover') {
        errors.push(`${position} 后续图片不得再次使用 cover role`);
      }
      if (!allowedOverlayModes.includes(image.overlayMode)) {
        errors.push(`${position}.overlayMode 必须是 ${allowedOverlayModes.join('、')} 之一`);
      } else if (index === 0 && image.overlayMode === 'none' && image.hasTitle !== false) {
        errors.push('纯图首图 hasTitle 必须为 false');
      } else if (index === 0 && image.overlayMode !== 'none' && image.hasTitle !== true) {
        errors.push('叠字首图 hasTitle 必须为 true');
      } else if (index > 0 && image.overlayMode !== 'none') {
        errors.push(`${position}.overlayMode 必须为 none`);
      } else if (index > 0 && image.hasTitle !== false) {
        errors.push(`${position}.hasTitle 必须为 false`);
      }
      if (!isNonEmptyString(image.purpose)) {
        errors.push(`${position}.purpose 必填且必须是非空字符串`);
      }
      errors.push(...validateImageSource(image.source, position));
      errors.push(...validateVisualRouting(image, position, profile));
      if (imageCount > 1 && !isNonEmptyString(image.continuityKey)) {
        errors.push(`${position}.continuityKey 必填，多图必须锁定同一生活场景的人物、器皿和光线`);
      }
      if (!isNonEmptyString(image.prompt)) {
        errors.push(`${position}.prompt 必填`);
        return;
      }
      const prompt = image.prompt.trim();
      errors.push(...validateNoGeneratedTextPrompt(prompt, position));
      if (index === 0) {
        for (const [slot, signals] of Object.entries(profile.visualPrompt.requiredCoverSlots)) {
          if (!signals.some((signal) => prompt.includes(signal))) {
            warnings.push(`首图提示词未明显体现动态槽位：${slot}`);
          }
        }
      }
      const positiveFilterText = prompt.replace(/(?:不要|避免|拒绝)[^，。；;\n]{0,18}(?:暖黄|复古滤镜|电影感|电影级打光)/gu, '');
      if (/(?:暖黄(?:色)?|复古滤镜|电影感|电影级打光)/u.test(positiveFilterText)) {
        warnings.push(`${position}.prompt 可能使用固定化或商业化滤镜，请按当前家庭环境选择真实光线`);
      }
    });
  }

  const toneText = [
    output.title,
    output.body,
    ...(output.titleCandidates ?? [])
  ].filter((value) => isNonEmptyString(value)).join('\n');
  if (toneText) {
    for (const item of profile.aiTone.blockedPatterns ?? []) {
      if (new RegExp(item.pattern, 'u').test(toneText)) {
        warnings.push(`正文可能存在模板化 AI 腔，建议结合上下文人工判断：${item.label}`);
      }
    }
    for (const item of profile.aiTone.warningPatterns ?? []) {
      if (new RegExp(item.pattern, 'u').test(toneText)) {
        warnings.push(`正文可能存在高风险 AI 腔或无依据推断：${item.label}`);
      }
    }
  }

  const riskText = [
    output.title,
    output.body,
    output.perspective,
    ...(output.keywords ?? []),
    ...(output.titleCandidates ?? [])
  ]
    .filter((value) => typeof value === 'string')
    .join('\n');
  for (const item of profile.contentRisks?.blockedPatterns ?? []) {
    if (new RegExp(item.pattern, 'u').test(riskText)) {
      errors.push(`内容触发婚姻家庭安全闸门：${item.label}`);
    }
  }
  for (const item of profile.contentRisks?.warningPatterns ?? []) {
    if (new RegExp(item.pattern, 'u').test(riskText)) {
      warnings.push(`内容可能需要来源或上下文：${item.label}`);
    }
  }

  return { errors, warnings: [...new Set(warnings)], bodyCount, imageCount };
}

function printWarnings(warnings) {
  if (warnings.length === 0) return;
  console.warn(`警告（${warnings.length} 条）：`);
  for (const warning of warnings) {
    console.warn(`- ${warning}`);
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const [output, profile] = await Promise.all([
    readJson(args.input, '输入文件'),
    readJson(profilePath, '赛道配置')
  ]);
  const result = validateCore(output, profile);
  printWarnings(result.warnings);
  if (result.errors.length > 0) {
    console.error(`校验失败（${result.errors.length} 项）：`);
    for (const error of result.errors) {
      console.error(`- ${error}`);
    }
    process.exitCode = 1;
    return;
  }
  const modeLabel = profile.body.modes[output.mode].label;
  console.log(`校验通过：${modeLabel}，正文 ${result.bodyCount} 个汉字，图片 ${result.imageCount} 张，警告 ${result.warnings.length} 条。`);
}

main().catch((error) => {
  console.error(`校验失败：${error.message}`);
  process.exitCode = 1;
});
