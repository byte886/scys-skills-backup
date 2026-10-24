import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const testsDir = dirname(fileURLToPath(import.meta.url));
const skillDir = dirname(testsDir);
const renderer = join(skillDir, 'scripts', 'render_finished_image.mjs');
const exampleInput = join(skillDir, 'examples', 'cover-input.json');

test('直接输出 1200×1600 的完成图 PNG', () => {
  const workDir = mkdtempSync(join(tmpdir(), 'tietu-finished-image-'));
  const input = join(workDir, 'input.json');
  const output = join(workDir, 'finished.png');
  const payload = JSON.parse(readFileSync(exampleInput, 'utf8'));
  payload.overlayMode = 'title';
  writeFileSync(input, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  const result = spawnSync(process.execPath, [renderer, '--input', input, '--output', output], {
    encoding: 'utf8'
  });
  assert.equal(result.status, 0, `${result.stdout ?? ''}${result.stderr ?? ''}`);
  assert.ok(existsSync(output), '未生成 PNG 文件');
  assert.deepEqual([...readFileSync(output).subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  const dimensions = spawnSync('/usr/bin/sips', ['-g', 'pixelWidth', '-g', 'pixelHeight', output], {
    encoding: 'utf8'
  });
  assert.equal(dimensions.status, 0, dimensions.stderr);
  assert.match(dimensions.stdout, /pixelWidth:\s*1200/u);
  assert.match(dimensions.stdout, /pixelHeight:\s*1600/u);
  rmSync(workDir, { recursive: true, force: true });
});

test('拒绝把完成图伪装成非 PNG 文件', () => {
  const workDir = mkdtempSync(join(tmpdir(), 'tietu-finished-image-'));
  const output = join(workDir, 'finished.jpg');
  const result = spawnSync(process.execPath, [renderer, '--input', exampleInput, '--output', output], {
    encoding: 'utf8'
  });
  assert.notEqual(result.status, 0);
  assert.match(`${result.stdout ?? ''}${result.stderr ?? ''}`, /output.*\.png|完成图.*PNG/iu);
  rmSync(workDir, { recursive: true, force: true });
});

