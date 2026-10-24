import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import {
  closeSync,
  ftruncateSync,
  mkdtempSync,
  openSync,
  readFileSync,
  rmSync,
  writeFileSync,
  writeSync
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const testsDir = dirname(fileURLToPath(import.meta.url));
const skillDir = dirname(testsDir);
const rendererPath = join(skillDir, 'scripts', 'render_title_cover.mjs');
const coverPath = join(skillDir, 'examples', 'cover-input.json');
const invalidCoverPath = join(skillDir, 'examples', 'invalid-cover-input.json');
const workDir = mkdtempSync(join(tmpdir(), 'tietu-marriage-render-'));
let caseIndex = 0;

after(() => rmSync(workDir, { recursive: true, force: true }));

function writeJson(data, name) {
  caseIndex += 1;
  const path = join(workDir, `${String(caseIndex).padStart(2, '0')}-${name}.json`);
  writeFileSync(path, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
  return path;
}

function runRenderer(inputPath, name) {
  const outputPath = join(workDir, `${name}.svg`);
  const result = spawnSync(process.execPath, [rendererPath, '--input', inputPath, '--output', outputPath], {
    encoding: 'utf8'
  });
  return { ...result, outputPath };
}

function combinedOutput(result) {
  return `${result.stdout ?? ''}${result.stderr ?? ''}`;
}

function expectRenderFailure(input, name, pattern) {
  const result = runRenderer(writeJson(input, name), name);
  assert.notEqual(result.status, 0, combinedOutput(result));
  assert.match(combinedOutput(result), pattern);
}

test('主封面流程渲染标签、箭头并安全转义', () => {
  const result = runRenderer(coverPath, 'main-cover');
  assert.equal(result.status, 0, combinedOutput(result));
  const svg = readFileSync(result.outputPath, 'utf8');
  assert.match(svg, /width="1200" height="1600"/u);
  assert.match(svg, /摊开的作业本/u);
  assert.match(svg, /手机屏幕朝下/u);
  assert.match(svg, /marker-end="url\(#code-arrow-head-0\)"/u);
});

test('越界标签输入以中文错误退出', () => {
  const result = runRenderer(invalidCoverPath, 'invalid-cover');
  assert.notEqual(result.status, 0, combinedOutput(result));
  assert.match(combinedOutput(result), /labels\[0\]\.x.*0—1200/u);
});

for (const [field, character] of [
  ['title', '\u0000'],
  ['subtitle', '\u0001']
]) {
  test(`${field} 拒绝 XML 1.0 非法控制字符`, () => {
    const input = { title: '安全标题', palette: 'leaf' };
    input[field] = `含${character}控制字符`;
    expectRenderFailure(input, `illegal-${field}`, new RegExp(`${field}.*XML 1\\.0.*U\\+000[01]`, 'u'));
  });
}

test('label text 拒绝 XML 1.0 非法控制字符', () => {
  expectRenderFailure({
    title: '安全标题',
    palette: 'leaf',
    labels: [{ text: '标签\u0002文字', x: 120, y: 900 }]
  }, 'illegal-label', /labels\[0\]\.text.*XML 1\.0.*U\+0002/u);
});

test('arrow label 拒绝 XML 1.0 非法控制字符', () => {
  expectRenderFailure({
    title: '安全标题',
    palette: 'leaf',
    arrows: [{ x1: 100, y1: 1000, x2: 500, y2: 800, label: '箭头\u0003说明' }]
  }, 'illegal-arrow-label', /arrows\[0\]\.label.*XML 1\.0.*U\+0003/u);
});

test('伪装成 PNG 的文本文件被签名校验拒绝', () => {
  const imagePath = join(workDir, 'fake.png');
  writeFileSync(imagePath, 'not an image', 'utf8');
  expectRenderFailure({ title: '签名检查', imagePath, palette: 'leaf' }, 'fake-png', /文件签名.*PNG|PNG.*文件签名/u);
});

test('扩展名与真实签名不一致时拒绝', () => {
  const imagePath = join(workDir, 'jpeg-disguised-as-png.png');
  writeFileSync(imagePath, Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46]));
  expectRenderFailure({ title: '签名不一致', imagePath, palette: 'leaf' }, 'mismatched-signature', /扩展名.*文件签名.*不一致/u);
});

test('PNG 文件按签名识别并嵌入正确 MIME', () => {
  const imagePath = join(workDir, 'tiny.png');
  writeFileSync(imagePath, Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]));
  const result = runRenderer(writeJson({ title: 'PNG签名', imagePath, palette: 'leaf' }, 'valid-png'), 'valid-png');
  assert.equal(result.status, 0, combinedOutput(result));
  assert.match(readFileSync(result.outputPath, 'utf8'), /data:image\/png;base64,/u);
});

test('JPEG 和 WebP 文件签名均受支持', () => {
  const cases = [
    ['tiny.jpg', Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46]), 'image/jpeg'],
    ['tiny.webp', Buffer.from([0x52, 0x49, 0x46, 0x46, 0x04, 0x00, 0x00, 0x00, 0x57, 0x45, 0x42, 0x50]), 'image/webp']
  ];
  for (const [filename, bytes, mime] of cases) {
    const imagePath = join(workDir, filename);
    writeFileSync(imagePath, bytes);
    const result = runRenderer(writeJson({ title: '签名支持', imagePath, palette: 'leaf' }, filename), filename);
    assert.equal(result.status, 0, combinedOutput(result));
    assert.match(readFileSync(result.outputPath, 'utf8'), new RegExp(`data:${mime.replace('/', '\\/')};base64,`, 'u'));
  }
});

test('超过 15MB 的图片在读取前被拒绝', () => {
  const imagePath = join(workDir, 'too-large.png');
  const descriptor = openSync(imagePath, 'w');
  writeSync(descriptor, Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), 0, 8, 0);
  ftruncateSync(descriptor, 15 * 1024 * 1024 + 1);
  closeSync(descriptor);
  expectRenderFailure({ title: '大小限制', imagePath, palette: 'leaf' }, 'too-large', /超过.*15MB/u);
});

test('十个全角字按安全宽度换行且不越过右边界', () => {
  const title = '一二三四五六七八九十';
  const result = runRenderer(writeJson({ title, palette: 'leaf' }, 'ten-cjk-title'), 'ten-cjk-title');
  assert.equal(result.status, 0, combinedOutput(result));
  const svg = readFileSync(result.outputPath, 'utf8');
  const titleBlock = svg.match(/<g id="cover-title"[^>]*x="([0-9.]+)"[^>]*data-safe-right="([0-9.]+)"[^>]*>([\s\S]*?)<\/g>/u);
  assert.ok(titleBlock, 'SVG 缺少 cover-title 布局元数据');
  const x = Number(titleBlock[1]);
  const safeRight = Number(titleBlock[2]);
  const widths = [...titleBlock[3].matchAll(/data-estimated-width="([0-9.]+)"/gu)].map((match) => Number(match[1]));
  assert.ok(widths.length >= 1 && widths.length <= 3, `十个全角字应为 1—3 行，实际 ${widths.length} 行`);
  for (const width of widths) {
    assert.ok(x + width <= safeRight + 0.01, `标题行越界：${x} + ${width} > ${safeRight}`);
  }
});
