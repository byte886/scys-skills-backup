import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const skillDir = dirname(dirname(fileURLToPath(import.meta.url)));
const renderer = join(skillDir, 'scripts/render_title_cover.mjs');
const profile = JSON.parse(readFileSync(join(skillDir, 'assets/track-profile.json'), 'utf8'));
const workDir = mkdtempSync(join(tmpdir(), 'tietu-typography-'));
const styles = ['top-gradient', 'white-bars', 'outlined-center', 'keyword-accent', 'note-card'];

after(() => rmSync(workDir, { recursive: true, force: true }));

function render(style, options = undefined) {
  const input = join(workDir, `${style}-${Math.random()}.json`);
  const output = join(workDir, `${style}-${Math.random()}.svg`);
  writeFileSync(input, `${JSON.stringify({
    title: '同一张图测试五种标题排版',
    palette: profile.cover.defaultPalette,
    overlayMode: 'title',
    textStyle: style,
    ...(options ? { textStyleOptions: options } : {})
  }, null, 2)}\n`, 'utf8');
  const result = spawnSync(process.execPath, [renderer, '--input', input, '--output', output], { encoding: 'utf8' });
  return { result, output };
}

for (const style of styles) {
  test(`可渲染文字样式 ${style}`, () => {
    const { result, output } = render(style);
    assert.equal(result.status, 0, `${result.stdout ?? ''}${result.stderr ?? ''}`);
    const svg = readFileSync(output, 'utf8');
    assert.match(svg, new RegExp(`data-text-style="${style}"`, 'u'));
    assert.match(svg, /id="cover-title"/u);
  });
}

test('参考图提取后的自定义排版选项可渲染', () => {
  const { result, output } = render('outlined-center', {
    placement: 'top',
    align: 'center',
    fontScale: 0.9,
    titleColor: '#FFFFFF',
    accentColor: '#FFB000',
    cardColor: '#FFFDF8'
  });
  assert.equal(result.status, 0, `${result.stdout ?? ''}${result.stderr ?? ''}`);
  assert.match(readFileSync(output, 'utf8'), /data-text-style="outlined-center"/u);
});

test('拒绝未知文字样式', () => {
  const { result } = render('unknown-style');
  assert.notEqual(result.status, 0);
  assert.match(`${result.stdout ?? ''}${result.stderr ?? ''}`, /textStyle 必须是/u);
});
