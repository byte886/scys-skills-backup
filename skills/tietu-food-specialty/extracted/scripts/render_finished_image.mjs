#!/usr/bin/env node

import { mkdir, mkdtemp, readFile, rm } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { dirname, extname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const titleRenderer = fileURLToPath(new URL('./render_title_cover.mjs', import.meta.url));
const pngSignature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token !== '--input' && token !== '--output') {
      throw new Error('不支持的参数：' + token);
    }
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) {
      throw new Error('参数 ' + token + ' 后必须提供文件路径');
    }
    args[token.slice(2)] = value;
    index += 1;
  }
  if (!args.input || !args.output) {
    throw new Error('用法：render_finished_image.mjs --input <json> --output <png>');
  }
  if (extname(args.output).toLowerCase() !== '.png') {
    throw new Error('--output 必须是 .png 完成图');
  }
  return {
    input: resolve(args.input),
    output: resolve(args.output)
  };
}

function run(command, args, label) {
  const result = spawnSync(command, args, {
    encoding: 'utf8',
    maxBuffer: 4 * 1024 * 1024
  });
  if (result.error) {
    throw new Error(label + '无法启动：' + result.error.message);
  }
  if (result.status !== 0) {
    const detail = ((result.stderr || '') + (result.stdout || '')).trim();
    throw new Error(label + '失败' + (detail ? '：' + detail : ''));
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const workDir = await mkdtemp(join(tmpdir(), 'tietu-finished-image-'));
  const svgPath = join(workDir, 'composed.svg');
  try {
    await mkdir(dirname(args.output), { recursive: true });
    run(process.execPath, [titleRenderer, '--input', args.input, '--output', svgPath], '版式合成');
    run('/usr/bin/sips', ['-s', 'format', 'png', svgPath, '--out', args.output], 'PNG 转换');
    const image = await readFile(args.output);
    if (image.length < pngSignature.length || !image.subarray(0, pngSignature.length).equals(pngSignature)) {
      throw new Error('输出文件不是有效 PNG');
    }
    console.log('完成图已生成：' + args.output);
  } finally {
    await rm(workDir, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error('生成失败：' + error.message);
  process.exitCode = 1;
});

