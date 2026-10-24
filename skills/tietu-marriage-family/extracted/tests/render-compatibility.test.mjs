import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const testsDir = dirname(fileURLToPath(import.meta.url));
const skillDir = dirname(testsDir);
const rendererPath = join(skillDir, 'scripts', 'render_title_cover.mjs');
const profile = JSON.parse(readFileSync(join(skillDir, 'assets', 'track-profile.json'), 'utf8'));
const workDir = mkdtempSync(join(tmpdir(), 'tietu-render-compat-'));

after(() => rmSync(workDir, { recursive: true, force: true }));

function render() {
  const inputPath = join(workDir, 'input.json');
  const outputPath = join(workDir, 'output.svg');
  const palette = Object.keys(profile.cover.palettes)[0];
  writeFileSync(inputPath, `${JSON.stringify({
    overlayMode: 'title_and_annotations',
    title: '这是一个需要稳定换成两行显示的中文长标题',
    subtitle: '兼容实际转图工具',
    palette,
    arrows: [{ x1: 260, y1: 1120, x2: 700, y2: 880, label: '关键细节' }]
  }, null, 2)}\n`, 'utf8');
  const result = spawnSync(process.execPath, [rendererPath, '--input', inputPath, '--output', outputPath], { encoding: 'utf8' });
  assert.equal(result.status, 0, `${result.stdout ?? ''}${result.stderr ?? ''}`);
  return readFileSync(outputPath, 'utf8');
}

test('多行标题使用绝对 y 坐标，避免转图时挤回同一行', () => {
  const svg = render();
  const titleBlock = svg.match(/<g id="cover-title"[^>]*>([\s\S]*?)<\/g>/u);
  assert.ok(titleBlock);
  const lineNodes = [...titleBlock[1].matchAll(/<text\b([^>]*)data-line-index="[0-9]+"([^>]*)>/gu)]
    .map((match) => `${match[1]}${match[2]}`);
  assert.ok(lineNodes.length >= 2, '长标题没有换成多行');
  assert.ok(lineNodes.every((attrs) => /\bx="[0-9.]+"/u.test(attrs) && /\by="[0-9.]+"/u.test(attrs)), '每行标题必须是带绝对 x/y 的独立 text 节点');
  assert.doesNotMatch(titleBlock[1], /<tspan\b|\bdy=/u, '不得依赖转图工具不稳定的 tspan/dy');
});

test('箭头说明使用高对比底板，不再用粗黑描边压住文字', () => {
  const svg = render();
  assert.match(svg, /<g data-arrow-label="0">[\s\S]*?<rect[\s\S]*?<text/u);
  assert.doesNotMatch(svg, /data-arrow-label="0"[\s\S]{0,500}stroke="#000000"/u);
});

test('overlayMode=none 直接保留纯图，不叠标题、遮罩或赛道角标', () => {
  const backgroundPath = join(workDir, 'plain-source.png');
  const inputPath = join(workDir, 'plain-input.json');
  const outputPath = join(workDir, 'plain-output.svg');
  writeFileSync(
    backgroundPath,
    Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64')
  );
  writeFileSync(inputPath, `${JSON.stringify({
    title: '只用于内容记录，不显示在图片上',
    overlayMode: 'none',
    imagePath: './plain-source.png',
    palette: Object.keys(profile.cover.palettes)[0]
  }, null, 2)}\n`, 'utf8');
  const result = spawnSync(process.execPath, [rendererPath, '--input', inputPath, '--output', outputPath], { encoding: 'utf8' });
  assert.equal(result.status, 0, `${result.stdout ?? ''}${result.stderr ?? ''}`);
  const svg = readFileSync(outputPath, 'utf8');
  assert.match(svg, /data-overlay-mode="none"/u);
  assert.match(svg, /<image\b/u);
  assert.doesNotMatch(svg, /id="cover-title"|fill="url\(#readabilityMask\)"|id="code-labels"/u);
});
