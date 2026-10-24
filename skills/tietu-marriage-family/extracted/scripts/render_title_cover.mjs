#!/usr/bin/env node

import { mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import { extname, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const profilePath = fileURLToPath(new URL('../assets/track-profile.json', import.meta.url));
const mimeByExtension = new Map([
  ['.png', 'image/png'],
  ['.jpg', 'image/jpeg'],
  ['.jpeg', 'image/jpeg'],
  ['.webp', 'image/webp']
]);
const maxImageBytes = 15 * 1024 * 1024;
const supportedTextStyles = new Set([
  'top-gradient',
  'white-bars',
  'outlined-center',
  'keyword-accent',
  'note-card'
]);

function normalizeTextStyle(rawStyle, rawOptions, profile) {
  const fallback = profile.images?.typography?.defaultStyle ?? 'top-gradient';
  const id = rawStyle ?? fallback;
  if (typeof id !== 'string' || !supportedTextStyles.has(id)) {
    throw new Error(`textStyle 必须是 ${[...supportedTextStyles].join('、')} 之一`);
  }
  const options = rawOptions ?? {};
  if (!isPlainObject(options)) {
    throw new Error('textStyleOptions 必须是对象');
  }
  rejectUnknownFields(options, new Set([
    'placement',
    'align',
    'fontScale',
    'titleColor',
    'accentColor',
    'cardColor'
  ]), 'textStyleOptions');
  const placement = options.placement ?? null;
  if (placement !== null && !['top', 'middle', 'bottom'].includes(placement)) {
    throw new Error('textStyleOptions.placement 必须是 top、middle 或 bottom');
  }
  const align = options.align ?? null;
  if (align !== null && !['left', 'center'].includes(align)) {
    throw new Error('textStyleOptions.align 必须是 left 或 center');
  }
  const fontScale = options.fontScale === undefined
    ? 1
    : validateNumber(options.fontScale, 'textStyleOptions.fontScale', 0.75, 1.25);
  const titleColor = options.titleColor === undefined
    ? null
    : validateAnnotationColor(options.titleColor, '#FFFFFF', 'textStyleOptions.titleColor');
  const accentColor = options.accentColor === undefined
    ? null
    : validateAnnotationColor(options.accentColor, '#FFB000', 'textStyleOptions.accentColor');
  const cardColor = options.cardColor === undefined
    ? null
    : validateAnnotationColor(options.cardColor, '#FFFFFF', 'textStyleOptions.cardColor');
  return { id, placement, align, fontScale, titleColor, accentColor, cardColor };
}

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token !== '--input' && token !== '--output') {
      throw new Error(`不支持的参数：${token}`);
    }
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) {
      throw new Error(`参数 ${token} 后必须提供文件路径`);
    }
    args[token.slice(2)] = value;
    index += 1;
  }
  if (!args.input || !args.output) {
    throw new Error('用法：render_title_cover.mjs --input <json> --output <svg>');
  }
  if (extname(args.output).toLowerCase() !== '.svg') {
    throw new Error('--output 必须是 .svg 文件');
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

function validateXmlText(value, path) {
  const text = String(value);
  for (const character of text) {
    const codePoint = character.codePointAt(0);
    const allowed = (
      codePoint === 0x09
      || codePoint === 0x0a
      || codePoint === 0x0d
      || (codePoint >= 0x20 && codePoint <= 0xd7ff)
      || (codePoint >= 0xe000 && codePoint <= 0xfffd)
      || (codePoint >= 0x10000 && codePoint <= 0x10ffff)
    );
    if (!allowed) {
      const code = codePoint.toString(16).toUpperCase().padStart(4, '0');
      throw new Error(`${path} 包含 XML 1.0 不允许的控制字符 U+${code}`);
    }
  }
  return text;
}

function escapeXml(value, path = '文本') {
  return validateXmlText(value, path)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;');
}

function graphemes(text) {
  if (typeof Intl.Segmenter === 'function') {
    const segmenter = new Intl.Segmenter('zh-Hans', { granularity: 'grapheme' });
    return [...segmenter.segment(text)].map((part) => part.segment);
  }
  return Array.from(text);
}

function visualUnits(character) {
  if (/\s/u.test(character)) return 0.35;
  if (/^[\u0000-\u00FF]$/u.test(character)) return 0.56;
  return 1;
}

function lineUnits(line) {
  return graphemes(line).reduce((sum, character) => sum + visualUnits(character), 0);
}

function estimatedTextWidth(text, fontSize, letterSpacing = 2) {
  const characters = graphemes(text);
  if (characters.length === 0) return 0;
  return lineUnits(text) * fontSize + (characters.length - 1) * letterSpacing;
}

function wrapTextToWidth(text, maxWidth, fontSize, letterSpacing = 2) {
  const normalized = String(text).replace(/\s+/gu, ' ').trim();
  if (!normalized) return [];
  const lines = [];
  let current = '';
  for (const character of graphemes(normalized)) {
    const candidate = current + character;
    if (!current || estimatedTextWidth(candidate, fontSize, letterSpacing) <= maxWidth) {
      current = candidate;
      continue;
    }
    const currentCharacters = graphemes(current);
    let nextLine = character;
    if (/^[，。！？；：、）》】”’]/u.test(character) && currentCharacters.length > 1) {
      nextLine = currentCharacters.pop() + character;
    } else if (/[《（【“‘]$/u.test(current) && currentCharacters.length > 1) {
      nextLine = currentCharacters.pop() + character;
    }
    const completed = currentCharacters.join('').trimEnd();
    if (completed) lines.push(completed);
    current = nextLine.trimStart();
  }
  if (current) lines.push(current.trim());
  return lines.filter(Boolean);
}

function chooseTextLayout(text, {
  maxWidth,
  fontSizes,
  preferredMaxLines,
  absoluteMaxLines,
  letterSpacing = 2
}) {
  for (const maxLines of [preferredMaxLines, absoluteMaxLines]) {
    for (const fontSize of fontSizes) {
      const lines = wrapTextToWidth(text, maxWidth, fontSize, letterSpacing);
      const widths = lines.map((line) => estimatedTextWidth(line, fontSize, letterSpacing));
      if (lines.length <= maxLines && widths.every((width) => width <= maxWidth + 0.01)) {
        return { lines, widths, fontSize, letterSpacing };
      }
    }
  }
  throw new Error(`文字过长，无法在安全宽度内排成 ${absoluteMaxLines} 行`);
}

function validateHex(value, field) {
  if (typeof value !== 'string' || !/^#[0-9A-Fa-f]{6}$/u.test(value)) {
    throw new Error(`palette.${field} 必须是 #RRGGBB 颜色`);
  }
  return value.toUpperCase();
}

function resolvePalette(rawPalette, profile) {
  const palettes = profile.cover?.palettes ?? {};
  const requested = rawPalette ?? profile.cover?.defaultPalette;
  let palette;
  if (typeof requested === 'string') {
    palette = palettes[requested];
    if (!palette) {
      throw new Error(`未知 palette：${requested}；可用值为 ${Object.keys(palettes).join('、')}`);
    }
  } else if (requested && typeof requested === 'object' && !Array.isArray(requested)) {
    palette = requested;
  } else {
    throw new Error('palette 必须是预设名称或颜色对象');
  }
  return {
    backgroundStart: validateHex(palette.backgroundStart, 'backgroundStart'),
    backgroundEnd: validateHex(palette.backgroundEnd, 'backgroundEnd'),
    accent: validateHex(palette.accent, 'accent'),
    text: validateHex(palette.text, 'text'),
    muted: validateHex(palette.muted, 'muted')
  };
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function rejectUnknownFields(value, allowed, path) {
  const unknown = Object.keys(value).filter((key) => !allowed.has(key));
  if (unknown.length > 0) {
    throw new Error(`${path} 包含不支持的字段：${unknown.join('、')}`);
  }
}

function validateNumber(value, path, min, max) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw new Error(`${path} 必须是 ${min}—${max} 范围内的有限数字`);
  }
  return value;
}

function validateAnnotationText(value, path, { optional = false } = {}) {
  if (optional && value === undefined) return '';
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`${path} 必须是非空字符串`);
  }
  const normalized = value.trim();
  if (/[\r\n]/u.test(normalized)) {
    throw new Error(`${path} 只能是单行文字`);
  }
  if (graphemes(normalized).length > 30) {
    throw new Error(`${path} 最多 30 个字符`);
  }
  return validateXmlText(normalized, path);
}

function validateAnnotationColor(value, fallback, path) {
  if (value === undefined) return fallback;
  if (typeof value !== 'string' || !/^#[0-9A-Fa-f]{6}$/u.test(value)) {
    throw new Error(`${path} 必须是 #RRGGBB 颜色`);
  }
  return value.toUpperCase();
}

function normalizeLabels(rawLabels, width, height, palette) {
  if (rawLabels === undefined) return [];
  if (!Array.isArray(rawLabels)) {
    throw new Error('labels 必须是数组');
  }
  if (rawLabels.length > 12) {
    throw new Error('labels 最多 12 个');
  }
  const allowed = new Set(['text', 'x', 'y', 'fontSize', 'fill', 'background', 'anchor']);
  return rawLabels.map((label, index) => {
    const path = `labels[${index}]`;
    if (!isPlainObject(label)) {
      throw new Error(`${path} 必须是对象`);
    }
    rejectUnknownFields(label, allowed, path);
    const text = validateAnnotationText(label.text, `${path}.text`);
    const x = validateNumber(label.x, `${path}.x`, 0, width);
    const y = validateNumber(label.y, `${path}.y`, 0, height);
    const fontSize = label.fontSize === undefined
      ? 38
      : validateNumber(label.fontSize, `${path}.fontSize`, 18, 96);
    const anchor = label.anchor ?? 'start';
    if (!['start', 'middle', 'end'].includes(anchor)) {
      throw new Error(`${path}.anchor 必须是 start、middle 或 end`);
    }
    const fill = validateAnnotationColor(label.fill, palette.text, `${path}.fill`);
    const background = validateAnnotationColor(label.background, palette.backgroundStart, `${path}.background`);
    const textWidth = Math.max(fontSize, lineUnits(text) * fontSize);
    const boxWidth = textWidth + 36;
    const boxHeight = fontSize * 1.45;
    const boxX = anchor === 'start' ? x - 18 : anchor === 'middle' ? x - boxWidth / 2 : x - boxWidth + 18;
    const boxY = y - fontSize * 1.08;
    if (boxX < 0 || boxX + boxWidth > width || boxY < 0 || boxY + boxHeight > height) {
      throw new Error(`${path} 的文字框超出 ${width}×${height} 画布`);
    }
    return { text, x, y, fontSize, anchor, fill, background, boxX, boxY, boxWidth, boxHeight };
  });
}

function normalizeArrows(rawArrows, width, height, palette) {
  if (rawArrows === undefined) return [];
  if (!Array.isArray(rawArrows)) {
    throw new Error('arrows 必须是数组');
  }
  if (rawArrows.length > 12) {
    throw new Error('arrows 最多 12 根');
  }
  const allowed = new Set(['x1', 'y1', 'x2', 'y2', 'width', 'color', 'label']);
  return rawArrows.map((arrow, index) => {
    const path = `arrows[${index}]`;
    if (!isPlainObject(arrow)) {
      throw new Error(`${path} 必须是对象`);
    }
    rejectUnknownFields(arrow, allowed, path);
    const x1 = validateNumber(arrow.x1, `${path}.x1`, 0, width);
    const y1 = validateNumber(arrow.y1, `${path}.y1`, 0, height);
    const x2 = validateNumber(arrow.x2, `${path}.x2`, 0, width);
    const y2 = validateNumber(arrow.y2, `${path}.y2`, 0, height);
    if (Math.hypot(x2 - x1, y2 - y1) < 24) {
      throw new Error(`${path} 起点与终点至少相距 24 像素`);
    }
    const lineWidth = arrow.width === undefined
      ? 6
      : validateNumber(arrow.width, `${path}.width`, 2, 16);
    const color = validateAnnotationColor(arrow.color, palette.accent, `${path}.color`);
    const label = validateAnnotationText(arrow.label, `${path}.label`, { optional: true });
    if (label) {
      const labelX = (x1 + x2) / 2;
      const labelY = (y1 + y2) / 2 - 18;
      const labelWidth = lineUnits(label) * 32;
      if (labelX - labelWidth / 2 < 0 || labelX + labelWidth / 2 > width || labelY < 32 || labelY > height) {
        throw new Error(`${path}.label 的文字范围超出 ${width}×${height} 画布`);
      }
    }
    return { x1, y1, x2, y2, lineWidth, color, label };
  });
}

async function loadImageData(inputPath, imagePath) {
  if (!imagePath) return null;
  if (typeof imagePath !== 'string') {
    throw new Error('imagePath 必须是本地图片路径字符串');
  }
  const resolvedPath = resolve(dirname(resolve(inputPath)), imagePath);
  const extension = extname(resolvedPath).toLowerCase();
  const expectedMime = mimeByExtension.get(extension);
  if (!expectedMime) {
    throw new Error('imagePath 仅支持本地 png、jpg、jpeg 或 webp 图片');
  }
  let fileStats;
  try {
    fileStats = await stat(resolvedPath);
  } catch (error) {
    throw new Error(`无法读取底图信息：${resolvedPath}（${error.message}）`);
  }
  if (!fileStats.isFile()) {
    throw new Error(`底图路径不是普通文件：${resolvedPath}`);
  }
  if (fileStats.size > maxImageBytes) {
    throw new Error(`底图大小超过 15MB 上限：${resolvedPath}`);
  }
  let data;
  try {
    data = await readFile(resolvedPath);
  } catch (error) {
    throw new Error(`无法读取底图：${resolvedPath}（${error.message}）`);
  }
  const detectedMime = detectImageMime(data);
  if (!detectedMime) {
    throw new Error(`底图文件签名不是受支持的 PNG、JPEG 或 WebP：${resolvedPath}`);
  }
  if (detectedMime !== expectedMime) {
    throw new Error(`底图扩展名与文件签名不一致：扩展名表示 ${expectedMime}，签名表示 ${detectedMime}`);
  }
  return `data:${detectedMime};base64,${data.toString('base64')}`;
}

function detectImageMime(data) {
  if (data.length >= 8 && data.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) {
    return 'image/png';
  }
  if (data.length >= 3 && data[0] === 0xff && data[1] === 0xd8 && data[2] === 0xff) {
    return 'image/jpeg';
  }
  if (data.length >= 12 && data.subarray(0, 4).toString('ascii') === 'RIFF' && data.subarray(8, 12).toString('ascii') === 'WEBP') {
    return 'image/webp';
  }
  return null;
}

function textBlock(lines, {
  x,
  y,
  fontSize,
  lineHeight,
  fill,
  weight = 800,
  letterSpacing = 2,
  id,
  safeRight
}) {
  const lineElements = lines.map((line, index) => (
    `<text data-line-index="${index}" x="${x}" y="${y + index * lineHeight}" data-estimated-width="${estimatedTextWidth(line, fontSize, letterSpacing).toFixed(2)}" fill="${fill}" font-family="PingFang SC, Noto Sans CJK SC, Microsoft YaHei, sans-serif" font-size="${fontSize}" font-weight="${weight}" letter-spacing="${letterSpacing}">${escapeXml(line, id ?? '文本')}</text>`
  )).join('');
  const idAttribute = id ? ` id="${id}"` : '';
  const safeRightAttribute = safeRight === undefined ? '' : ` data-safe-right="${safeRight}"`;
  return `<g${idAttribute} x="${x}" y="${y}"${safeRightAttribute}>${lineElements}</g>`;
}

function resolveTextStyleLayout(textStyle, palette, width, height, title) {
  const presets = {
    'top-gradient': {
      placement: 'top', align: 'left', fontSizes: [112, 104, 96, 88, 80, 72, 64],
      preferredMaxLines: 3, absoluteMaxLines: 5, decoration: 'gradient', titleColor: palette.text
    },
    'white-bars': {
      placement: 'top', align: 'left', fontSizes: [104, 96, 88, 80, 72, 64],
      preferredMaxLines: 3, absoluteMaxLines: 5, decoration: 'bars', titleColor: '#20242A'
    },
    'outlined-center': {
      placement: 'middle', align: 'center', fontSizes: [118, 108, 100, 92, 84, 76, 68],
      preferredMaxLines: 3, absoluteMaxLines: 4, decoration: 'outline', titleColor: '#FFFFFF'
    },
    'keyword-accent': {
      placement: 'top', align: 'left', fontSizes: [112, 104, 96, 88, 80, 72, 64],
      preferredMaxLines: 3, absoluteMaxLines: 5, decoration: 'accent', titleColor: palette.text
    },
    'note-card': {
      placement: 'bottom', align: 'left', fontSizes: [96, 88, 80, 72, 64, 58],
      preferredMaxLines: 3, absoluteMaxLines: 5, decoration: 'card', titleColor: '#20242A'
    }
  };
  const preset = presets[textStyle.id];
  const placement = textStyle.placement ?? preset.placement;
  const align = textStyle.align ?? preset.align;
  const marginX = 92;
  const maxWidth = width - marginX * 2;
  const fontSizes = preset.fontSizes.map((size) => Math.round(size * textStyle.fontScale));
  const titleLayout = chooseTextLayout(title, {
    maxWidth,
    fontSizes,
    preferredMaxLines: preset.preferredMaxLines,
    absoluteMaxLines: preset.absoluteMaxLines
  });
  const lineHeight = Math.round(titleLayout.fontSize * 1.28);
  const blockHeight = titleLayout.fontSize + (titleLayout.lines.length - 1) * lineHeight;
  let y;
  if (placement === 'top') y = 240;
  else if (placement === 'middle') y = Math.round(height * 0.50 - blockHeight / 2 + titleLayout.fontSize);
  else y = Math.round(height - 210 - blockHeight + titleLayout.fontSize);
  const x = align === 'center' ? width / 2 : marginX;
  return {
    ...preset,
    ...titleStyleColors(textStyle, preset, palette),
    id: textStyle.id,
    placement,
    align,
    x,
    y,
    maxWidth,
    safeRight: width - marginX,
    lineHeight,
    titleLayout,
    cardColor: textStyle.cardColor ?? '#FFFDF8'
  };
}

function titleStyleColors(textStyle, preset, palette) {
  return {
    titleColor: textStyle.titleColor ?? preset.titleColor,
    accentColor: textStyle.accentColor ?? palette.accent
  };
}

function styledTitleBlock(style) {
  const { lines, widths, fontSize, letterSpacing } = style.titleLayout;
  const anchor = style.align === 'center' ? 'middle' : 'start';
  const common = `font-family="PingFang SC, Noto Sans CJK SC, Microsoft YaHei, sans-serif" font-size="${fontSize}" font-weight="800" letter-spacing="${letterSpacing}"`;
  const lineText = (line, index, extra = '') => `<text data-line-index="${index}" x="${style.x}" y="${style.y + index * style.lineHeight}" data-estimated-width="${widths[index].toFixed(2)}" text-anchor="${anchor}" ${common} ${extra}>${escapeXml(line, 'cover-title')}</text>`;
  let content = '';

  if (style.decoration === 'bars') {
    content = lines.map((line, index) => {
      const baseline = style.y + index * style.lineHeight;
      const boxWidth = widths[index] + 52;
      const boxX = style.align === 'center' ? style.x - boxWidth / 2 : style.x - 18;
      const boxY = baseline - fontSize * 1.02;
      return `<rect x="${boxX}" y="${boxY}" width="${boxWidth}" height="${fontSize * 1.26}" rx="12" fill="${style.cardColor}" fill-opacity="0.94"/>${lineText(line, index, `fill="${style.titleColor}"`)}`;
    }).join('');
  } else if (style.decoration === 'outline') {
    content = lines.map((line, index) => lineText(line, index, `fill="${style.titleColor}" stroke="#111111" stroke-width="5" stroke-linejoin="round"`)).join('');
  } else if (style.decoration === 'accent') {
    content = lines.map((line, index) => lineText(line, index, `fill="${index === 0 ? style.accentColor : style.titleColor}"`)).join('');
  } else if (style.decoration === 'card') {
    const cardWidth = Math.min(style.maxWidth, Math.max(...widths) + 112);
    const cardX = style.align === 'center' ? style.x - cardWidth / 2 : style.x - 28;
    const cardY = style.y - fontSize - 46;
    const cardHeight = fontSize + (lines.length - 1) * style.lineHeight + 92;
    content = `<rect x="${cardX}" y="${cardY}" width="${cardWidth}" height="${cardHeight}" rx="26" fill="${style.cardColor}" fill-opacity="0.95" stroke="#FFFFFF" stroke-opacity="0.7" stroke-width="2"/><rect x="${cardX}" y="${cardY}" width="14" height="${cardHeight}" rx="7" fill="${style.accentColor}"/>${lines.map((line, index) => lineText(line, index, `fill="${style.titleColor}"`)).join('')}`;
  } else {
    content = lines.map((line, index) => lineText(line, index, `fill="${style.titleColor}"`)).join('');
  }
  return `<g id="cover-title" x="${style.x}" y="${style.y}" data-safe-right="${style.safeRight}" data-text-style="${style.id}">${content}</g>`;
}

function buildAnnotationSvg(labels, arrows) {
  const markerDefinitions = arrows.map((arrow, index) => (
    `<marker id="code-arrow-head-${index}" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L12,6 L0,12 Z" fill="${arrow.color}"/></marker>`
  )).join('\n    ');
  const arrowElements = arrows.map((arrow, index) => {
    const line = `<line x1="${arrow.x1}" y1="${arrow.y1}" x2="${arrow.x2}" y2="${arrow.y2}" stroke="${arrow.color}" stroke-width="${arrow.lineWidth}" stroke-linecap="round" marker-end="url(#code-arrow-head-${index})"/>`;
    if (!arrow.label) return line;
    const labelX = (arrow.x1 + arrow.x2) / 2;
    const labelY = (arrow.y1 + arrow.y2) / 2 - 18;
    const labelWidth = Math.max(112, lineUnits(arrow.label) * 32 + 36);
    const labelHeight = 52;
    const labelBoxX = labelX - labelWidth / 2;
    const labelBoxY = labelY - 39;
    return `${line}<g data-arrow-label="${index}"><rect x="${labelBoxX}" y="${labelBoxY}" width="${labelWidth}" height="${labelHeight}" rx="12" fill="#111111" fill-opacity="0.82"/><text x="${labelX}" y="${labelY}" text-anchor="middle" fill="#FFFFFF" font-family="PingFang SC, Noto Sans CJK SC, Microsoft YaHei, sans-serif" font-size="32" font-weight="700">${escapeXml(arrow.label)}</text></g>`;
  }).join('\n    ');
  const labelElements = labels.map((label) => (
    `<g><rect x="${label.boxX}" y="${label.boxY}" width="${label.boxWidth}" height="${label.boxHeight}" rx="14" fill="${label.background}" opacity="0.88"/><text x="${label.x}" y="${label.y}" text-anchor="${label.anchor}" fill="${label.fill}" font-family="PingFang SC, Noto Sans CJK SC, Microsoft YaHei, sans-serif" font-size="${label.fontSize}" font-weight="700">${escapeXml(label.text)}</text></g>`
  )).join('\n    ');
  return {
    markerDefinitions,
    content: `<g id="code-arrows">\n    ${arrowElements}\n  </g>\n  <g id="code-labels">\n    ${labelElements}\n  </g>`
  };
}

function buildSvg(input, profile, palette, imageData, labels, arrows, overlayMode, textStyle) {
  const width = profile.cover.width;
  const height = profile.cover.height;
  const title = input.title.trim();
  const style = resolveTextStyleLayout(textStyle, palette, width, height, title);
  const titleLayout = style.titleLayout;
  const titleLines = titleLayout.lines;
  const subtitle = typeof input.subtitle === 'string' ? input.subtitle.trim() : '';
  const subtitleLayout = subtitle
    ? chooseTextLayout(subtitle, {
        maxWidth: style.maxWidth,
        fontSizes: [44, 40, 36, 32],
        preferredMaxLines: 2,
        absoluteMaxLines: 2
      })
    : { lines: [], fontSize: 44, letterSpacing: 2 };
  const subtitleLines = subtitleLayout.lines;

  const titleFontSize = titleLayout.fontSize;
  const titleLineHeight = style.lineHeight;
  const titleStartY = style.y;
  const titleEndY = titleStartY + (titleLines.length - 1) * titleLineHeight;
  const subtitleY = Math.min(titleEndY + 104, 1460);
  const backgroundLayer = imageData
    ? `<image x="0" y="0" width="${width}" height="${height}" preserveAspectRatio="xMidYMid slice" href="${imageData}"/>`
    : `<rect width="${width}" height="${height}" fill="url(#themeBackground)"/>
       <circle cx="1060" cy="250" r="330" fill="${palette.accent}" opacity="0.10"/>
       <path d="M0 1260 C260 1140 420 1390 690 1250 C900 1140 1060 1210 1200 1110 L1200 1600 L0 1600 Z" fill="${palette.backgroundStart}" opacity="0.42"/>`;

  if (overlayMode === 'none') {
    if (!imageData) {
      throw new Error('overlayMode=none 必须提供 imagePath；纯图模式不能用模板背景冒充完成图');
    }
    return [
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<svg xmlns="http://www.w3.org/2000/svg" width="' + width + '" height="' + height + '" viewBox="0 0 ' + width + ' ' + height + '" role="img" aria-labelledby="svg-title svg-description" data-overlay-mode="none">',
      '  <title id="svg-title">' + escapeXml(title, 'title') + '</title>',
      '  <desc id="svg-description">' + escapeXml(subtitle || (profile.trackName || '贴图号') + '纯图完成图', 'subtitle') + '</desc>',
      '  ' + backgroundLayer,
      '</svg>'
    ].join('\n') + '\n';
  }

  const subtitleBlock = subtitleLines.length > 0
    ? textBlock(subtitleLines, {
      x: 92,
      y: subtitleY,
        fontSize: subtitleLayout.fontSize,
        lineHeight: Math.round(subtitleLayout.fontSize * 1.4),
        fill: palette.muted,
        weight: 500,
        letterSpacing: subtitleLayout.letterSpacing,
        id: 'cover-subtitle',
        safeRight: style.safeRight
      })
    : '';
  const annotations = buildAnnotationSvg(labels, arrows);
  const readabilityLayer = ['top-gradient', 'keyword-accent'].includes(style.id)
    ? '<rect width="' + width + '" height="' + height + '" fill="url(#readabilityMask)"/>'
    : '';
  const accentMarker = style.id === 'top-gradient'
    ? `<rect x="92" y="166" width="118" height="12" rx="6" fill="${style.accentColor}"/>`
    : '';

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="svg-title svg-description" data-text-style="${style.id}">
  <title id="svg-title">${escapeXml(title, 'title')}</title>
  <desc id="svg-description">${escapeXml(subtitle || `${profile.trackName || '贴图号'}首图`, 'subtitle')}</desc>
  <defs>
    <linearGradient id="themeBackground" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="${palette.backgroundStart}"/>
      <stop offset="100%" stop-color="${palette.backgroundEnd}"/>
    </linearGradient>
    <linearGradient id="readabilityMask" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#000000" stop-opacity="0.76"/>
      <stop offset="58%" stop-color="#000000" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0.48"/>
    </linearGradient>
    <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000000" flood-opacity="0.58"/>
    </filter>
    ${annotations.markerDefinitions}
  </defs>
  ${backgroundLayer}
  ${readabilityLayer}
  ${accentMarker}
  <g filter="url(#softShadow)">
    ${styledTitleBlock(style)}
    ${subtitleBlock}
  </g>
  ${annotations.content}
  <text x="92" y="1500" fill="${palette.muted}" opacity="0.82" font-family="PingFang SC, Noto Sans CJK SC, Microsoft YaHei, sans-serif" font-size="30" letter-spacing="5">${escapeXml(profile.trackName || '贴图号', 'trackName')}</text>
</svg>
`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const [input, profile] = await Promise.all([
    readJson(args.input, '输入文件'),
    readJson(profilePath, '赛道配置')
  ]);
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    throw new Error('输入 JSON 顶层必须是对象');
  }
  if (typeof input.title !== 'string' || !input.title.trim()) {
    throw new Error('title 必填且必须是非空字符串');
  }
  input.title = validateXmlText(input.title.trim(), 'title');
  if (input.subtitle !== undefined) {
    if (typeof input.subtitle !== 'string') {
      throw new Error('subtitle 必须是字符串');
    }
    input.subtitle = validateXmlText(input.subtitle.trim(), 'subtitle');
  }
  const palette = resolvePalette(input.palette, profile);
  const finishedOutput = profile.images?.finishedOutput ?? {};
  const allowedOverlayModes = finishedOutput.allowedOverlayModes ?? ['none', 'title', 'title_and_annotations'];
  const inferredOverlayMode = input.labels !== undefined || input.arrows !== undefined
    ? 'title_and_annotations'
    : input.imagePath
      ? finishedOutput.defaultOverlayMode ?? 'title'
      : 'title';
  const overlayMode = input.overlayMode ?? inferredOverlayMode;
  if (!allowedOverlayModes.includes(overlayMode)) {
    throw new Error('overlayMode 必须是 ' + allowedOverlayModes.join('、') + ' 之一');
  }
  const textStyle = normalizeTextStyle(input.textStyle, input.textStyleOptions, profile);
  const labels = overlayMode === 'title_and_annotations'
    ? normalizeLabels(input.labels, profile.cover.width, profile.cover.height, palette)
    : [];
  const arrows = overlayMode === 'title_and_annotations'
    ? normalizeArrows(input.arrows, profile.cover.width, profile.cover.height, palette)
    : [];
  const imageData = await loadImageData(args.input, input.imagePath);
  const svg = buildSvg(input, profile, palette, imageData, labels, arrows, overlayMode, textStyle);
  try {
    await mkdir(dirname(resolve(args.output)), { recursive: true });
    await writeFile(args.output, svg, 'utf8');
  } catch (error) {
    throw new Error(`无法写入 SVG：${args.output}（${error.message}）`);
  }
  console.log(`首图已生成：${resolve(args.output)}（${profile.cover.width}×${profile.cover.height}；标签 ${labels.length} 个，箭头 ${arrows.length} 根）`);
}

main().catch((error) => {
  console.error(`生成失败：${error.message}`);
  process.exitCode = 1;
});
