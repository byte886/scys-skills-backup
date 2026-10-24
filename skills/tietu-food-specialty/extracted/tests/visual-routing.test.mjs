import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const testsDir = dirname(fileURLToPath(import.meta.url));
const skillDir = dirname(testsDir);
const validatorPath = join(skillDir, 'scripts', 'validate_output.mjs');
const profile = JSON.parse(readFileSync(join(skillDir, 'assets', 'track-profile.json'), 'utf8'));
const valid = JSON.parse(readFileSync(join(skillDir, 'examples', 'valid-output.json'), 'utf8'));

function run(data, name) {
  const workDir = mkdtempSync(join(tmpdir(), 'tietu-visual-routing-'));
  const path = join(workDir, `${name}.json`);
  writeFileSync(path, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
  const result = spawnSync(process.execPath, [validatorPath, '--input', path], { encoding: 'utf8' });
  rmSync(workDir, { recursive: true, force: true });
  return result;
}

function output(result) {
  return `${result.stdout ?? ''}${result.stderr ?? ''}`;
}

test('赛道配置声明独立视觉路由', () => {
  const strategy = profile.images?.visualStrategy;
  assert.ok(strategy, '缺少 images.visualStrategy');
  assert.ok(['source-first', 'documentary', 'hybrid', 'information'].includes(strategy.family));
  assert.equal(strategy.selectionBasis, 'topic-first', '视觉类型必须按本次主题决定');
  assert.equal(strategy.dynamicSelection, true, '不得把赛道锁成固定图片模板');
  assert.ok(Array.isArray(strategy.allowedModes) && strategy.allowedModes.length >= 4);
  assert.ok(strategy.allowedModes.includes('source_photo'));
  assert.ok(strategy.allowedModes.includes(strategy.defaultMode));
  assert.ok(['must_use_source', 'prefer_source', 'can_generate'].includes(strategy.defaultSourcePriority));
  const finishedOutput = profile.images?.finishedOutput;
  assert.equal(finishedOutput?.directBitmap, true, '默认必须交付完成图，而不是只给提示词');
  assert.equal(finishedOutput?.format, 'png');
  assert.ok(['none', 'title', 'title_and_annotations'].includes(finishedOutput?.defaultOverlayMode));
  assert.ok(Array.isArray(finishedOutput?.allowedOverlayModes));
  assert.ok(finishedOutput.allowedOverlayModes.includes(finishedOutput.defaultOverlayMode));
});

test('每张图片必须声明 visualMode 与 sourcePriority', () => {
  const data = structuredClone(valid);
  delete data.images[0].visualMode;
  delete data.images[0].sourcePriority;
  const result = run(data, 'missing-routing');
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /visualMode[\s\S]*sourcePriority|sourcePriority[\s\S]*visualMode/u);
});

test('拒绝赛道配置之外的视觉模式', () => {
  const data = structuredClone(valid);
  data.images[0].visualMode = 'generic_ai_poster';
  data.images[0].sourcePriority = 'can_generate';
  const result = run(data, 'disallowed-mode');
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /visualMode.*允许/u);
});

test('source_photo 不能冒充 AI 合成图', () => {
  const data = structuredClone(valid);
  data.images[0].visualMode = 'source_photo';
  data.images[0].sourcePriority = 'prefer_source';
  data.images[0].source = {
    type: 'visual_illustration',
    isHistoricalEvidence: false,
    description: '画面示意，不代表真实素材'
  };
  const result = run(data, 'fake-source-photo');
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /source_photo.*source_material/u);
});

test('纯图与叠字首图必须使用对应的 hasTitle 规则', () => {
  const data = structuredClone(valid);
  if (data.images[0].overlayMode === 'none') {
    data.images[0].hasTitle = true;
  } else {
    data.images[0].hasTitle = false;
  }
  const result = run(data, 'overlay-title-mismatch');
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /纯图首图 hasTitle.*false|叠字首图 hasTitle.*true/u);
});
