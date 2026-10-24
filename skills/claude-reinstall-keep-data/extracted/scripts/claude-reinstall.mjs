#!/usr/bin/env node
// Claude Code 卸载重装（保留数据）—— macOS / Windows 通用，需要 Node.js 22+
//
// 用法：
//   node claude-reinstall.mjs                    完整流程：备份 → 退出登录 → 卸载 → 重装 → 恢复（需在独立终端运行）
//   node claude-reinstall.mjs --dry-run          只列出会备份 / 移除的路径和预估体积，不做任何改动
//   node claude-reinstall.mjs --backup-only      只备份，不需要确认，可在 Claude Code 会话里运行
//   node claude-reinstall.mjs --restore <备份目录>
//   完整流程和 --restore 可加 --yes 跳过确认，供非 Claude 的 AI 工具在用户同意后代为执行（Claude Code 会话中一律拒绝）
//
// 被移除的文件不会直接删除：macOS 移入废纸篓，Windows 移入 ~/claude-uninstalled/<时间戳>。

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import readline from 'node:readline/promises';
import { spawnSync } from 'node:child_process';

const IS_WIN = process.platform === 'win32';
const IS_MAC = process.platform === 'darwin';
const HOME = os.homedir();
const CONFIG_DIR_ENV = process.env.CLAUDE_CONFIG_DIR;
const CLAUDE_DIR = CONFIG_DIR_ENV ? path.resolve(CONFIG_DIR_ENV) : path.join(HOME, '.claude');
const CLAUDE_JSON = CONFIG_DIR_ENV ? path.join(CLAUDE_DIR, '.claude.json') : path.join(HOME, '.claude.json');
const PACKAGE_NAME = '@anthropic-ai/claude-code';
const KEYCHAIN_PREFIX = 'Claude Code-credentials'; // 设置 CLAUDE_CONFIG_DIR 时条目名可能带后缀，按前缀清理
const DESKTOP_KEYCHAIN = 'Claude Safe Storage';
const BACKUP_MARKER = 'backup-info.json';

const STAMP = new Date().toISOString().replace(/[:T.]/g, '-').slice(0, 23);
const BACKUP_ROOT = path.join(HOME, 'claude-backups');
const BACKUP_DIR = path.join(BACKUP_ROOT, STAMP);
// 放在备份目录之外，避免用户清理备份时连同唯一的 ~/.claude.json 副本一起删掉
const REMOVED_DIR = IS_MAC
  ? path.join(HOME, '.Trash', `claude-uninstall-${STAMP}`)
  : path.join(HOME, 'claude-uninstalled', STAMP);

// Claude Desktop 数据目录：含登录会话（Cookies / Local Storage）和 MCP 配置。
// Windows 上安装版在 %APPDATA%\Claude；Microsoft Store 版被重定向到 Packages\Claude_*\LocalCache\Roaming\Claude
function findStoreDesktopData() {
  const packages = path.join(process.env.LOCALAPPDATA || path.join(HOME, 'AppData', 'Local'), 'Packages');
  try {
    for (const name of fs.readdirSync(packages)) {
      const dir = path.join(packages, name, 'LocalCache', 'Roaming', 'Claude');
      if (/^Claude_/i.test(name) && fs.existsSync(dir)) return dir;
    }
  } catch {}
  return null;
}
const WIN_DESKTOP_DATA = path.join(process.env.APPDATA || path.join(HOME, 'AppData', 'Roaming'), 'Claude');
const STORE_DESKTOP_DATA = IS_WIN && !fs.existsSync(WIN_DESKTOP_DATA) ? findStoreDesktopData() : null;
const DESKTOP_DATA = IS_WIN
  ? STORE_DESKTOP_DATA || WIN_DESKTOP_DATA
  : path.join(HOME, 'Library', 'Application Support', 'Claude');
// 备份 / 恢复清单：[源路径, 备份内相对路径]。不含登录凭据、遥测和缓存类文件；
// 清单之外的 ~/.claude 内容既不备份也不会被删除。
const BACKUP_ITEMS = [
  ['projects', '会话/projects'],
  ['history.jsonl', '会话/history.jsonl'],
  ['plans', '会话/plans'],
  ['memory', '全局记忆/memory'],
  ['skills', 'Skill/skills'],
  ['agents', 'Skill/agents'],
  ['commands', 'Skill/commands'],
  ['plugins', 'Skill/plugins'],
  ['settings.json', '全局配置/settings.json'],
  ['settings.local.json', '全局配置/settings.local.json'],
  ['keybindings.json', '全局配置/keybindings.json'],
  ['CLAUDE.md', '全局配置/CLAUDE.md'],
].map(([rel, dst]) => [path.join(CLAUDE_DIR, rel), dst]);

// Desktop 的 MCP 配置、Cowork 会话与 Code 标签页会话索引：数据目录整体移走前先备份，恢复时写回。
// 路径写成相对 Desktop 数据目录，是因为 Windows Store 版每次运行时探测到的绝对路径可能不同——
// 备份时用当次探测到的 DESKTOP_DATA，恢复时改用备份记录里的路径（见 backup-info.json 的 desktopData 字段），
// 避免备份和恢复各自探测出两个不同的目录、把数据写去 Store 版实际读取不到的地方。
const DESKTOP_ITEMS = [
  ['claude_desktop_config.json', 'MCP/claude_desktop_config.json'],
  ['local-agent-mode-sessions', 'Desktop/local-agent-mode-sessions'],
  ['claude-code-sessions', 'Desktop/claude-code-sessions'],
];
const resolvedDesktopItems = (desktopData) => DESKTOP_ITEMS.map(([rel, dst]) => [path.join(desktopData, rel), dst]);
const allBackupItems = (desktopData = DESKTOP_DATA) => [...BACKUP_ITEMS, ...resolvedDesktopItems(desktopData)];

// 单独运行 --restore 时，覆盖前先给这些配置文件存快照，便于撤回
const PRE_RESTORE_FILES = ['settings.json', 'settings.local.json', 'keybindings.json', 'CLAUDE.md', 'history.jsonl'];

// ~/.claude.json 里只恢复这两段（MCP 服务与各项目设置），账号标识不恢复
const CLAUDE_JSON_PARTIAL = 'MCP/claude.json-可恢复部分.json';
const CLAUDE_JSON_FULL = '账号状态（不恢复）/claude.json';

// 退出登录后要移走的本地账号状态
const AUTH_STATE_FILES = [...new Set([
  CLAUDE_JSON,
  path.join(HOME, '.claude.json'),
  path.join(CLAUDE_DIR, '.credentials.json'),
  path.join(CLAUDE_DIR, '.claude.json'),
  path.join(CLAUDE_DIR, 'backups'), // Claude Code 自动保存的 .claude.json 快照，含旧账号信息
])];

// 原生安装：可执行文件 + 版本目录
const NATIVE_INSTALL = [
  path.join(HOME, '.local', 'bin', IS_WIN ? 'claude.exe' : 'claude'),
  path.join(HOME, '.local', 'share', 'claude'),
  path.join(HOME, '.claude', 'local'), // 旧版 claude migrate-installer 的本地安装
];

const MAC_DESKTOP_APPS = ['/Applications/Claude.app', path.join(HOME, 'Applications', 'Claude.app')];
const BREW_CODE_CASKS = ['claude-code', 'claude-code@latest'];
const WINGET_CODE_ID = 'Anthropic.ClaudeCode';
const WINGET_FLAGS = ['--id', WINGET_CODE_ID, '--exact', '--accept-source-agreements', '--disable-interactivity'];

// 出错或中断时提示用户如何恢复
let recoveryHint = '';
let copyWarnings = 0;
let preservedLinks = 0;
let walkErrors = 0; // 无论 count 模式与否都计数，用于校验阶段判断某一项统计时是否曾读取失败（count 模式不打印警告，容易被误判为"体积恰好一致"）

// ---------- 工具函数 ----------

function run(cmd, args, { inherit = true, timeout } = {}) {
  // Windows 上 npm / claude 是 .cmd，需要经过 shell 才能找到；本脚本传入的参数都不含空格
  const r = spawnSync(cmd, args, { stdio: inherit ? 'inherit' : 'pipe', shell: IS_WIN, encoding: 'utf8', timeout });
  return { ok: r.status === 0, stdout: r.stdout || '' };
}

function hasCommand(cmd) {
  return run(IS_WIN ? 'where' : 'which', [cmd], { inherit: false }).ok;
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (e) {
    warn(`无法解析 ${file}（${e.message}），跳过其中的 MCP / 项目设置。`);
    return null;
  }
}

function writeJson(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.tmp.${process.pid}`;
  fs.writeFileSync(tmp, JSON.stringify(data, null, 2), { mode: 0o600 });
  fs.renameSync(tmp, file);
}

function isSymlink(p) {
  try {
    return fs.lstatSync(p).isSymbolicLink();
  } catch {
    return false;
  }
}

function exists(p) {
  return fs.existsSync(p) || isSymlink(p);
}

function isInside(child, parent) {
  const rel = path.relative(parent, child);
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
}

function warn(message) {
  copyWarnings++;
  console.log(`警告：${message}`);
}

// 逐项遍历复制，跟随软链接存真实内容。
// 备份时跳过失效链接、循环链接和指向备份目录的链接；恢复时目标已是软链接则保留不写穿（避免覆盖链接指向的源仓库）。
// count 模式只累计体积不复制。单项出错只告警，不中断整体流程。
function walk(src, dst, opts, ancestors = new Set()) {
  const report = (m) => opts.count || warn(m); // 估算体积时不重复告警
  let st;
  try {
    st = fs.statSync(src);
  } catch (e) {
    // 失效链接的错误码因平台和链接形态而异（ENOENT/ELOOP/ENOTDIR/ENAMETOOLONG 等），逐一列举容易漏；
    // 反过来只认 EACCES/EPERM 这两个明确的"权限被拒绝"为真正问题，计入 walkErrors 供校验阶段识别，其余一律当正常跳过
    if (e.code === 'EACCES' || e.code === 'EPERM') walkErrors++;
    report(`跳过失效的软链接或无法访问的路径：${src}（${e.code || e.message}）`);
    return 0;
  }
  if (opts.restore && isSymlink(dst)) {
    preservedLinks++;
    console.log(`保留现有软链接，未覆盖：${dst}`);
    return 0;
  }
  try {
    if (st.isFile()) {
      if (!opts.count) fs.copyFileSync(src, dst);
      return st.size;
    }
    if (!st.isDirectory()) return 0;
    const real = fs.realpathSync(src);
    if (ancestors.size === 0) opts = { ...opts, rootReal: real };
    // 指向自身、祖先目录（如 ~ 或 ~/.claude）或备份目录的软链接都跳过，否则会整棵复制甚至无限递归
    const loops = ancestors.has(real) || (ancestors.size > 0 && isInside(opts.rootReal, real));
    if (loops || (!opts.restore && !opts.insideBackup && isInside(real, opts.backupRootReal))) {
      report(`跳过循环或指向备份目录的软链接：${src}`);
      return 0;
    }
    if (!opts.count) fs.mkdirSync(dst, { recursive: true });
    ancestors.add(real);
    let total = 0;
    for (const name of fs.readdirSync(src)) total += walk(path.join(src, name), path.join(dst, name), opts, ancestors);
    ancestors.delete(real);
    return total;
  } catch (e) {
    walkErrors++;
    report(`无法处理 ${src}（${e.code || e.message}），已跳过。`);
    return 0;
  }
}

function walkOptions(extra = {}) {
  let backupRootReal = path.resolve(BACKUP_ROOT);
  try {
    backupRootReal = fs.realpathSync(BACKUP_ROOT);
  } catch {}
  return { backupRootReal, ...extra };
}

function copyPath(src, dst, extra = {}) {
  if (!exists(src)) return;
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  const [w, l] = [copyWarnings, preservedLinks];
  walk(src, dst, walkOptions(extra));
  const notes = [];
  if (copyWarnings > w) notes.push(`${copyWarnings - w} 条警告`);
  if (preservedLinks > l) notes.push(`${preservedLinks - l} 个软链接保留未覆盖`);
  console.log(`${notes.length ? '部分复制' : '已复制'}：${src} → ${dst}${notes.length ? `（${notes.join('，')}）` : ''}`);
}

function estimateBackupBytes() {
  const opts = walkOptions({ count: true });
  let total = 0;
  for (const [src] of allBackupItems()) if (exists(src)) total += walk(src, '', opts);
  if (fs.existsSync(CLAUDE_JSON)) total += fs.statSync(CLAUDE_JSON).size;
  return total;
}

function freeBytes() {
  try {
    const s = fs.statfsSync(HOME);
    return s.bavail * s.bsize;
  } catch {
    return Infinity;
  }
}

const mb = (n) => `${(n / 1024 / 1024).toFixed(1)} MB`;

// 目标名保留相对 HOME 的路径层级，避免 ~/.claude.json 与 ~/.claude/.claude.json 同名互相覆盖
function moveAside(src) {
  if (!exists(src)) return true;
  const rel = path.relative(HOME, src);
  const name = rel.startsWith('..') || path.isAbsolute(rel) ? src.replace(/[:\\/]+/g, '__') : rel.replace(/[\\/]+/g, '__');
  let dst = path.join(REMOVED_DIR, name);
  for (let i = 1; exists(dst); i++) dst = path.join(REMOVED_DIR, `${name}.${i}`);
  try {
    fs.mkdirSync(REMOVED_DIR, { recursive: true });
    fs.renameSync(src, dst);
  } catch (e) {
    try {
      if (e.code === 'EXDEV') {
        // 用 walk() 而不是 fs.cpSync：cpSync 遇到树里有不可读目录时会在原生层面直接 abort，
        // try/catch 接不住、整个脚本被杀掉；walk() 逐项 try/catch，天然容错
        const errorsBefore = walkErrors;
        walk(src, dst, walkOptions());
        if (walkErrors > errorsBefore) {
          try {
            fs.rmSync(dst, { recursive: true, force: true }); // 清掉不完整的复制，不留半成品
          } catch {
            // 清理失败不重要：核心是源文件没删，dst 留个残余顶多占点空间，不掩盖下面这句更有用的错误
          }
          throw new Error('跨设备复制时部分内容读取失败，可能未完整复制，已放弃移走（源文件保留原位，详见上方警告）');
        }
        fs.rmSync(src, { recursive: true, force: true });
      } else {
        throw e;
      }
    } catch (e2) {
      // 不再自动用 sudo 提权移走：脚本自己发起权限升级是额外的信任风险，
      // 权限不足时改为明确提示，交给用户自己决定要不要手动 sudo 处理
      const hint =
        e2.code === 'EBUSY'
          ? '，文件被占用，请确认 Claude 已全部退出'
          : e2.code === 'EACCES' || e2.code === 'EPERM'
            ? '，权限不足；如需要可自行在终端用 sudo 移走或删除'
            : '';
      warn(`无法移走，请手动处理：${src}（${e2.code || e2.message}${hint}）`);
      return false;
    }
  }
  console.log(`已移走：${src} → ${dst}`);
  return true;
}

// 预检能否移走：目标目录可写，且源文件可原地改名（Windows 上文件被占用时改名会失败）
function canMoveAside(src) {
  if (!exists(src)) return true;
  const probe = `${src}.move-check-${process.pid}`;
  try {
    fs.mkdirSync(REMOVED_DIR, { recursive: true });
    fs.accessSync(REMOVED_DIR, fs.constants.W_OK);
    fs.renameSync(src, probe);
    fs.renameSync(probe, src);
    return true;
  } catch (e) {
    if (exists(probe) && !exists(src)) {
      try {
        fs.renameSync(probe, src);
      } catch {
        warn(`预检改名后未能还原，请手动把 ${probe} 改回 ${src}`);
      }
    }
    warn(`无法移走：${src}（${e.code || e.message}${e.code === 'EBUSY' ? '，文件被占用，请确认 Claude 已全部退出' : ''}）`);
    return false;
  }
}

async function confirm(rl, question) {
  try {
    const answer = (await rl.question(`${question}（输入 y 继续）：`)).trim();
    return /^y(es)?$/i.test(answer);
  } catch {
    return false; // Ctrl+C / Ctrl+D 视为不继续
  }
}

async function confirmPhrase(rl, question, phrase) {
  try {
    // 去掉首尾标点和全半角空格差异，避免因为多打一个句号/逗号就误判为不确认——
    // 这个通道本就是给用户在紧张场景下用的，不该在这种细节上卡人
    const strip = (s) => s.trim().replace(/^[，。,.\s]+|[，。,.\s]+$/g, '');
    const answer = strip(await rl.question(question));
    return answer === strip(phrase);
  } catch {
    return false; // Ctrl+C / Ctrl+D 视为不继续
  }
}

function fail(message, code = 1) {
  console.log(message);
  process.exitCode = code;
}

// ---------- 备份 ----------

function latestPartialBackup(excludeDir) {
  if (!fs.existsSync(BACKUP_ROOT)) return null;
  const dirs = fs.readdirSync(BACKUP_ROOT).sort().reverse();
  for (const d of dirs) {
    const dir = path.join(BACKUP_ROOT, d);
    const f = path.join(dir, CLAUDE_JSON_PARTIAL);
    if (dir === excludeDir || !fs.existsSync(f)) continue;
    // 只沿用本机本用户的备份，避免把别的机器 / 账号的项目设置合并进来
    let info = null;
    try {
      info = JSON.parse(fs.readFileSync(path.join(dir, BACKUP_MARKER), 'utf8'));
    } catch {}
    if (info && info.home === HOME && info.platform === process.platform && info.configDir === CLAUDE_DIR) return f;
  }
  return null;
}

function backupClaudeJson(backupDir) {
  const homeJson = path.join(HOME, '.claude.json');
  if (homeJson !== CLAUDE_JSON && fs.existsSync(homeJson)) {
    copyPath(homeJson, path.join(backupDir, '账号状态（不恢复）/home-claude.json')); // 它也会被移走，留一份兜底
  }
  // 缺失或损坏时沿用本机最近一次备份里的 MCP 与项目设置
  const usePrevious = (reason) => {
    const prev = latestPartialBackup(backupDir);
    if (prev) {
      copyPath(prev, path.join(backupDir, CLAUDE_JSON_PARTIAL));
      warn(`${CLAUDE_JSON} ${reason}，已沿用之前备份中的 MCP 与项目设置：${prev}`);
    } else {
      warn(`${CLAUDE_JSON} ${reason}，且没有可沿用的旧备份，本次备份不含 MCP 服务与项目设置。`);
    }
  };
  if (!fs.existsSync(CLAUDE_JSON)) return usePrevious('不存在（可能上次运行已移走）');
  // 完整原件单独存放、只用于兜底，不参与恢复（里面有旧账号标识）
  copyPath(CLAUDE_JSON, path.join(backupDir, CLAUDE_JSON_FULL));
  const data = readJson(CLAUDE_JSON);
  if (!data) return usePrevious('无法解析');
  writeJson(path.join(backupDir, CLAUDE_JSON_PARTIAL), {
    mcpServers: data.mcpServers || {},
    projects: data.projects || {},
  });
  console.log('已备份 ~/.claude.json 中的 MCP 服务与项目设置。');
}

// 备份和快照含 MCP 密钥和旧账号信息，收紧为仅当前用户可访问
function tightenPermissions(dir) {
  if (!IS_WIN) {
    if (!run('chmod', ['-R', 'go-rwx', dir]).ok) warn(`未能收紧备份目录权限，其中含 MCP 密钥和旧账号信息，请妥善保管：${dir}`);
  }
  else {
    const { USERDOMAIN, USERNAME } = process.env;
    const account = USERDOMAIN ? `${USERDOMAIN}\\${USERNAME}` : USERNAME;
    const r = USERNAME
      ? spawnSync('icacls', [dir, '/inheritance:r', '/grant:r', `${account}:(OI)(CI)F`], { stdio: 'ignore' })
      : { status: 1 };
    if (r.status !== 0) warn(`未能收紧备份目录权限，其中含 MCP 密钥和旧账号信息，请妥善保管：${dir}`);
  }
}

// 逐项比对源与备份的体积（与复制使用同一套跳过规则），不一致说明有内容没备份进去
// strict：完整流程（Claude 已退出）不一致即停止；只备份时 Claude 可能仍在写会话文件，只告警
function verifyBackup(backupDir, strict) {
  const opts = walkOptions({ count: true });
  const mismatched = [];
  const size = (n) => (n < 1024 * 1024 ? `${n} 字节` : mb(n));
  for (const [src, rel] of allBackupItems()) {
    if (!exists(src)) continue;
    const errBefore = walkErrors;
    const a = walk(src, '', opts);
    const b = walk(path.join(backupDir, rel), '', { ...opts, insideBackup: true }); // 统计的就是备份目录本身
    if (walkErrors > errBefore) mismatched.push(`${src}（统计时读取出错，无法确认是否完整备份，见上方警告）`);
    else if (a !== b) mismatched.push(`${src}（源 ${size(a)}，备份 ${size(b)}）`);
  }
  // .claude.json 是单个文件的原样复制，不走 walk，单独比对大小
  if (fs.existsSync(CLAUDE_JSON)) {
    const fullCopy = path.join(backupDir, CLAUDE_JSON_FULL);
    if (!fs.existsSync(fullCopy)) mismatched.push(`${CLAUDE_JSON}（未生成完整备份副本）`);
    else {
      const a = fs.statSync(CLAUDE_JSON).size;
      const b = fs.statSync(fullCopy).size;
      if (a !== b) mismatched.push(`${CLAUDE_JSON}（源 ${size(a)}，备份 ${size(b)}）`);
    }
  }
  if (!mismatched.length) {
    console.log('备份校验通过：各项体积与源一致。');
    return true;
  }
  if (!strict) {
    warn(`备份校验：以下内容与源不一致，可能是 Claude 仍在运行、文件在备份期间有变化，或有文件不可读：\n  ${mismatched.join('\n  ')}`);
    return true;
  }
  fail(`备份校验未通过，已停止（未做任何卸载或清理）。以下内容没有完整备份，请检查上方警告（如文件不可读、磁盘写满）后重试：\n  ${mismatched.join('\n  ')}`);
  return false;
}

function backup(backupDir, strict = false) {
  const need = estimateBackupBytes();
  const free = freeBytes();
  if (need * 1.1 > free) {
    fail(`磁盘空间不足：备份预计需要 ${mb(need)}，当前可用 ${mb(free)}。请先清理空间。`);
    return false;
  }
  console.log(`\n开始备份 Claude 数据（预计 ${mb(need)}）：${backupDir}`);
  fs.mkdirSync(backupDir, { recursive: true });
  for (const [src, rel] of allBackupItems()) copyPath(src, path.join(backupDir, rel));
  backupClaudeJson(backupDir);
  tightenPermissions(backupDir); // 校验前先收紧一次：校验失败时半成品备份目录也不会留默认权限
  if (!verifyBackup(backupDir, strict)) return false;
  writeJson(path.join(backupDir, BACKUP_MARKER), {
    createdAt: new Date().toISOString(),
    platform: process.platform,
    home: HOME,
    configDir: CLAUDE_DIR,
    desktopData: DESKTOP_DATA, // 恢复时优先按这个路径写回，而不是重新探测（Windows Store 版每次探测结果可能不同）
  });
  console.log(`备份完成：${backupDir}${copyWarnings ? `（有 ${copyWarnings} 条警告，见上方）` : ''}`);
  return true;
}

// ---------- 卸载 ----------

function logoutClaude() {
  const serverSessionWarning = '服务端的登录会话可能仍然有效（本地凭据仍会照常清理）。建议之后手动执行 claude auth logout，或到 claude.ai 的账号设置里查看并撤销会话。';
  if (!hasCommand('claude')) {
    warn(`PATH 中找不到 claude 命令，无法执行 claude auth logout。${serverSessionWarning}`);
  } else if (run('claude', ['auth', 'logout']).ok) {
    console.log('Claude 账号退出完成。');
  } else {
    warn(`claude auth logout 失败（可能未登录或网络问题）。${serverSessionWarning}`);
  }
  // macOS 凭据存在钥匙串里，logout 失败或找不到命令时这里兜底
  if (IS_MAC) deleteKeychainItems(KEYCHAIN_PREFIX);
}

// 删除服务名以 prefix 开头的全部钥匙串条目（同名多条时循环删到查不到为止）
function deleteKeychainItems(prefix) {
  const dump = run('security', ['dump-keychain'], { inherit: false });
  if (!dump.ok) warn(`无法列出钥匙串条目（钥匙串可能已锁定），只清理了「${prefix}」本身，带后缀的同类条目请在「钥匙串访问」中手动检查。`);
  // 字面量名称始终清理，不依赖 dump 能否列出（服务名含非 ASCII 时 dump 输出为十六进制，匹配不到）
  const services = new Set([prefix, ...[...dump.stdout.matchAll(/"svce"<blob>="([^"]*)"/g)].map((m) => m[1]).filter((n) => n.startsWith(prefix))]);
  for (const service of services) {
    let removed = 0;
    while (removed < 20 && run('security', ['find-generic-password', '-s', service], { inherit: false }).ok) {
      if (!run('security', ['delete-generic-password', '-s', service], { inherit: false }).ok) break;
      removed++;
    }
    if (run('security', ['find-generic-password', '-s', service], { inherit: false }).ok) {
      warn(`删除钥匙串条目失败，请在「钥匙串访问」中手动删除「${service}」。`);
    } else if (removed) {
      console.log(`已删除钥匙串条目：${service}${removed > 1 ? `（${removed} 条）` : ''}`);
    }
  }
}

function npmGlobalRoot() {
  const root = run('npm', ['root', '-g'], { inherit: false }).stdout.trim();
  if (root) return root;
  return IS_WIN
    ? path.join(process.env.APPDATA || path.join(HOME, 'AppData', 'Roaming'), 'npm', 'node_modules')
    : '/opt/homebrew/lib/node_modules';
}

function uninstallNpmClaudeCode() {
  if (!hasCommand('npm')) {
    warn('PATH 中找不到 npm，无法检查 / 卸载 npm 安装的 Claude Code。若 npm 版仍在，本地登录凭据已清理，重新登录即可继续用，不一定需要卸载重装；如确实要清掉这份 npm 安装，请之后手动执行：npm uninstall -g ' + PACKAGE_NAME);
    return;
  }
  if (!run('npm', ['list', '-g', '--depth=0'], { inherit: false, timeout: 15000 }).stdout.includes(PACKAGE_NAME)) return;

  console.log('检测到 npm 安装的 Claude Code。');
  if (run('npm', ['uninstall', '-g', PACKAGE_NAME]).ok) return console.log('npm 卸载完成。');

  console.log('npm 卸载遇到问题，清理 npm 残留临时目录后重试。');
  const scope = path.join(npmGlobalRoot(), '@anthropic-ai');
  if (fs.existsSync(scope)) {
    for (const name of fs.readdirSync(scope)) {
      if (name.startsWith('.claude-code-')) moveAside(path.join(scope, name));
    }
  }
  if (run('npm', ['uninstall', '-g', PACKAGE_NAME]).ok) return console.log('清理临时目录后，npm 卸载完成。');

  console.log('npm 重试仍然失败，直接移走安装目录。');
  moveAside(path.join(scope, 'claude-code'));
}

// 是否原本装过 Claude Code 命令行版：覆盖卸载阶段实际会检测到的几种安装方式，
// 不能只看 PATH（PATH 可能因为 shell 配置文件未加载而找不到已安装的 claude）
function detectClaudeCodeInstalled() {
  if (hasCommand('claude') || NATIVE_INSTALL.some(exists)) return true;
  if (hasCommand('npm') && run('npm', ['list', '-g', '--depth=0'], { inherit: false, timeout: 15000 }).stdout.includes(PACKAGE_NAME)) return true;
  if (IS_MAC && hasCommand('brew') && BREW_CODE_CASKS.some((c) => run('brew', ['list', '--cask', c], { inherit: false }).ok)) return true;
  if (IS_WIN && hasCommand('winget') && run('winget', ['list', ...WINGET_FLAGS], { inherit: false }).ok) return true;
  return false;
}

function uninstallPackageManagers() {
  if (IS_MAC && hasCommand('brew')) {
    for (const cask of BREW_CODE_CASKS) {
      if (run('brew', ['list', '--cask', cask], { inherit: false }).ok) run('brew', ['uninstall', '--cask', cask]);
    }
  }
  if (IS_WIN && hasCommand('winget')) {
    if (run('winget', ['list', ...WINGET_FLAGS], { inherit: false }).ok) {
      run('winget', ['uninstall', ...WINGET_FLAGS, '--silent']);
    }
  }
}

// 清掉 Desktop 的登录会话（其 MCP 配置已备份，恢复阶段写回）
function uninstallDesktop() {
  const hadDesktop = exists(DESKTOP_DATA) || MAC_DESKTOP_APPS.some(exists);
  if (IS_MAC) {
    if (hasCommand('brew') && run('brew', ['list', '--cask', 'claude'], { inherit: false }).ok) {
      run('brew', ['uninstall', '--cask', 'claude']);
    }
    MAC_DESKTOP_APPS.forEach(moveAside);
    deleteKeychainItems(DESKTOP_KEYCHAIN);
  } else if (IS_WIN && hadDesktop) {
    const kind = STORE_DESKTOP_DATA ? '（Microsoft Store 版）' : '';
    console.log(`提示：Windows 上的 Claude Desktop 程序${kind}需在「设置 → 应用 → 已安装的应用」中手动卸载。`);
  }
  moveAside(DESKTOP_DATA);
  if (hadDesktop) console.log('提示：Claude Desktop 的登录数据已清理；如需继续使用 Desktop，请从 https://claude.ai/download 重新安装后登录新账号。');
}

function uninstall() {
  console.log('\n开始卸载 Claude Code。');
  logoutClaude();

  console.log('清理本地账号状态文件。');
  // 先全部预检再移走：避免移走一半后中止，导致重跑时 ~/.claude.json 已不在、备份不到 MCP 配置
  // 账号状态清不掉就不继续卸载：否则重装后旧账号会原样留在机器上
  const abort = (what) =>
    console.log(`\n错误：账号状态文件没有清理干净，已停止。${what}已执行退出登录（macOS 钥匙串凭据已删除），程序尚未卸载，备份已完成。请结束所有 Claude 进程后重新运行本脚本。`);
  if (!AUTH_STATE_FILES.map(canMoveAside).every(Boolean)) {
    try {
      fs.rmdirSync(REMOVED_DIR); // 预检建的空目录，非空时不删
    } catch {}
    abort('所有账号状态文件都保持原位；');
    return false;
  }
  if (!AUTH_STATE_FILES.map(moveAside).every(Boolean)) {
    abort(`部分文件已移到 ${REMOVED_DIR}（见上方「已移走」），重跑时会沿用本次备份；`);
    return false;
  }

  uninstallPackageManagers();
  uninstallNpmClaudeCode();
  NATIVE_INSTALL.forEach(moveAside);
  uninstallDesktop();
  console.log('卸载完成。');
  return true;
}

// ---------- 重装与恢复 ----------

function install() {
  if (!hasCommand('npm')) {
    console.log('错误：未找到 npm，无法重新安装 Claude Code。');
    return false;
  }
  console.log('\n开始通过 npm 重新安装 Claude Code。');
  if (run('npm', ['install', '-g', PACKAGE_NAME]).ok) {
    // npm install 本身已经对下载内容做过注册表级别的完整性校验（SRI 哈希），这里额外查一次
    // 实际装上的版本号，只是为了在输出里留一条可审计的安装记录，不是重复造轮子
    const installedVersion = run('npm', ['list', '-g', PACKAGE_NAME, '--depth=0', '--json'], { inherit: false, timeout: 15000 }).stdout;
    let versionLabel = '';
    try {
      const v = JSON.parse(installedVersion).dependencies?.[PACKAGE_NAME]?.version;
      if (v) versionLabel = `（版本 ${v}）`;
    } catch {}
    console.log(`Claude Code 安装完成${versionLabel}。`);
    if (!hasCommand('claude')) {
      const prefix = run('npm', ['prefix', '-g'], { inherit: false }).stdout.trim();
      const bin = prefix ? (IS_WIN ? prefix : path.join(prefix, 'bin')) : 'npm 全局安装目录（`npm prefix -g` 查看）';
      warn(`当前 PATH 中找不到 claude 命令。请把 ${bin} 加入 PATH，并删除 shell 配置里指向旧安装位置的 claude alias，然后重开终端。`);
    }
    return true;
  }
  console.log('Claude Code 安装失败，暂不恢复备份。');
  return false;
}

// mcpServers：按服务名合并，当前已有的同名服务优先（可能是重新配置过的）。
// projects：按项目路径合并，同一项目内按字段合并、备份优先（重装后生成的多是空壳默认值）。
function restoreClaudeJson(backupDir) {
  const src = path.join(backupDir, CLAUDE_JSON_PARTIAL);
  if (!fs.existsSync(src)) return;
  const saved = readJson(src);
  if (!saved) return;
  const current = fs.existsSync(CLAUDE_JSON) ? readJson(CLAUDE_JSON) : {};
  if (!current) return warn(`当前 ${CLAUDE_JSON} 无法解析，未恢复 MCP 配置，可手动从 ${src} 合并。`);
  current.mcpServers = { ...(saved.mcpServers || {}), ...(current.mcpServers || {}) };
  const projects = { ...(current.projects || {}) };
  for (const [p, v] of Object.entries(saved.projects || {})) projects[p] = { ...(projects[p] || {}), ...v };
  current.projects = projects;
  writeJson(CLAUDE_JSON, current);
  console.log('已恢复 ~/.claude.json 中的 MCP 服务与项目设置。');
}

function snapshotBeforeRestore() {
  const dir = path.join(BACKUP_ROOT, `${STAMP}-pre-restore`);
  const items = [...PRE_RESTORE_FILES.map((f) => path.join(CLAUDE_DIR, f)), CLAUDE_JSON].filter((p) => fs.existsSync(p));
  if (!items.length) return;
  for (const src of items) copyPath(src, path.join(dir, path.basename(src)));
  tightenPermissions(dir);
  console.log(`恢复前已保存当前配置快照：${dir}（如需撤回，把其中文件复制回原位置）`);
}

function restore(backupDir, before = copyWarnings) {
  console.log(`\n使用备份恢复：${backupDir}`);
  let info = null;
  try {
    info = JSON.parse(fs.readFileSync(path.join(backupDir, BACKUP_MARKER), 'utf8'));
  } catch {}
  const desktopData = info?.desktopData || DESKTOP_DATA;
  for (const [dst, rel] of allBackupItems(desktopData)) copyPath(path.join(backupDir, rel), dst, { restore: true });
  restoreClaudeJson(backupDir);
  if (copyWarnings > before) {
    console.log(`\n恢复结束，但恢复阶段有 ${copyWarnings - before} 条警告，部分内容未恢复，请逐条检查上方「警告」。`);
  } else {
    console.log('\n数据恢复完成。');
  }
  console.log('登录凭据未恢复，请在 Claude Code 中重新登录。');
  console.log('注意：使用 OAuth 授权的 MCP 服务（令牌与登录凭据存在一起）需要重新授权，MCP 服务配置本身已保留。');
}

// ---------- 入口 ----------

function dryRun() {
  const mark = (p) => (exists(p) ? '存在' : '不存在');
  console.log(`平台：${process.platform}\n配置目录：${CLAUDE_DIR}${CONFIG_DIR_ENV ? '（来自 CLAUDE_CONFIG_DIR）' : ''}`);
  console.log(`备份目录（将创建）：${BACKUP_DIR}\n移走的文件去向：${REMOVED_DIR}\n`);
  console.log('会备份（软链接会复制成真实内容）：');
  for (const [src] of allBackupItems()) console.log(`  [${mark(src)}] ${src}`);
  console.log(`  [${mark(CLAUDE_JSON)}] ${CLAUDE_JSON}（恢复时只合并 mcpServers、projects）`);
  console.log(`预计备份体积：${mb(estimateBackupBytes())}，当前可用空间：${mb(freeBytes())}`);
  console.log('\n会移走：');
  const removals = [...AUTH_STATE_FILES, ...NATIVE_INSTALL, ...(IS_MAC ? MAC_DESKTOP_APPS : []), DESKTOP_DATA];
  for (const p of removals) console.log(`  [${mark(p)}] ${p}`);
  if (IS_MAC) console.log(`  钥匙串中以「${KEYCHAIN_PREFIX}」开头的条目、「${DESKTOP_KEYCHAIN}」`);
  const managers = IS_MAC ? `、brew cask ${[...BREW_CODE_CASKS, 'claude'].join(' / ')}` : IS_WIN ? `、winget ${WINGET_CODE_ID}` : '';
  console.log(`\n会检测并卸载：npm 全局包 ${PACKAGE_NAME}${managers}`);
}

// 还在运行的 Claude Code / Claude Desktop 进程（按进程名识别）。
// 完整流程会移走它们正在使用的文件，进程不退出时移走后可能被重新写回。
// 返回 { checked, processes }：checked=false 表示检测本身失败（如 tasklist/ps 不可用或被占用），
// 这种"无法确认"的状态调用方必须当作"可能在运行"处理，绝不能当成"确认没有"而放行。
function runningClaudeProcesses() {
  if (IS_WIN) {
    const r = spawnSync('tasklist', ['/FO', 'CSV', '/NH'], { encoding: 'utf8' });
    if (r.error || r.status !== 0 || !r.stdout) return { checked: false, processes: [] };
    const processes = r.stdout
      .split(/\r?\n/)
      .map((l) => l.split('","'))
      .filter((c) => /^"?claude(-desktop)?\.exe$/i.test(c[0] || ''))
      .map((c) => `${c[0].replace(/"/g, '')} (PID ${c[1]})`);
    return { checked: true, processes };
  }
  const ps = spawnSync('ps', ['-axo', 'pid=,comm='], { encoding: 'utf8' });
  if (ps.error || ps.status !== 0 || !ps.stdout) return { checked: false, processes: [] };
  const list = [];
  const comm = ps.stdout;
  for (const line of comm.split('\n')) {
    const m = line.trim().match(/^(\d+)\s+(.+)$/);
    if (m && /^claude$/i.test(path.basename(m[2]))) list.push(`${m[2]} (PID ${m[1]})`);
  }
  // 旧版 npm 包以 node cli.js 方式运行，进程名是 node
  const psArgs = spawnSync('ps', ['-axo', 'pid=,args='], { encoding: 'utf8' });
  if (psArgs.error || psArgs.status !== 0 || !psArgs.stdout) return { checked: false, processes: [] };
  for (const line of psArgs.stdout.split('\n')) {
    const m = line.trim().match(/^(\d+)\s+(.+)$/);
    // 只认 node / bun 进程，避免把 grep 这类带该路径的排查命令当成 Claude
    const exe = m && path.basename(m[2].split(/\s+/)[0]);
    if (m && Number(m[1]) !== process.pid && /^(node|nodejs|bun)$/.test(exe) && /@anthropic-ai\/claude-code\/cli/.test(m[2])) list.push(`${m[2].slice(0, 80)} (PID ${m[1]})`);
  }
  return { checked: true, processes: list };
}

async function main() {
  const [major, minor] = process.versions.node.split('.').map(Number);
  if (major < 18 || (major === 18 && minor < 15)) return fail(`需要 Node.js 18.15 或更高版本（当前 ${process.versions.node}）。`);

  if (path.resolve(CLAUDE_DIR) === path.resolve(HOME)) return fail('CLAUDE_CONFIG_DIR 不能设置为用户主目录，请检查该环境变量。');

  const args = process.argv.slice(2);
  const yes = args.includes('--yes');
  if (args.includes('--dry-run')) return dryRun();
  if (args.includes('--backup-only')) return void backup(BACKUP_DIR);

  // 以下模式会卸载或覆盖 Claude Code 本身：Claude Code 会话里一律拒绝（包括 --yes），其他 AI 工具可用 --yes 执行
  if (process.env.CLAUDECODE || process.env.CLAUDE_CODE_ENTRYPOINT || process.env.CLAUDE_CODE_SESSION_ID) {
    return fail('检测到正在 Claude Code 会话中运行。本脚本会卸载 Claude Code 本身，不能由 Claude 执行。请退出 Claude Code，在独立终端或其他 AI 工具中运行（可先用 --dry-run / --backup-only）。', 2);
  }
  if (!yes && !process.stdin.isTTY) {
    return fail('需要在交互式终端中运行（要输入确认）；由 AI 工具代为执行时，在用户明确同意后加 --yes 跳过确认。', 2);
  }
  const restoreIdx = args.indexOf('--restore');
  if (major < 22 && restoreIdx < 0) {
    return fail(`完整流程需要 Node.js 22+（Claude Code 本身的要求，当前 ${process.versions.node}）。可先用 --backup-only 备份，再升级 Node。`);
  }

  const refuseIfClaudeRunning = async () => {
    const { checked, processes } = runningClaudeProcesses();
    if (processes.length) {
      fail(`检测到仍在运行的 Claude 进程，请全部退出后重试（未做任何改动）：\n  ${processes.join('\n  ')}`);
      return true;
    }
    if (checked) return false;
    // 进程检查本身失败：不能当成"确认没有"而放行。--yes 场景没有人在看输出，一律拒绝；
    // 交互模式下给用户一次门槛更高的手动确认（要求输入完整短语，不是简单的 y），由用户自己担保
    if (yes || !rl) {
      fail('无法确认 Claude 是否仍在运行（进程检查本身失败，如 tasklist/ps 被占用或不可用），为安全起见已停止，未做任何改动。请手动确认 Claude Code 和 Claude Desktop 已全部退出后，在交互式终端里重试。');
      return true;
    }
    warn('无法确认 Claude 是否仍在运行（进程检查本身失败，如 tasklist/ps 被占用或不可用）。');
    const sure = await confirmPhrase(rl, '如果你已经手动确认 Claude Code 和 Claude Desktop 全部退出，请输入「确认继续」四个字继续，否则直接回车中止：', '确认继续');
    if (!sure) {
      fail('已停止，未做任何改动。');
      return true;
    }
    console.log('已按你的确认继续。');
    return false;
  };
  const rl = yes ? null : readline.createInterface({ input: process.stdin, output: process.stdout });
  const ask = async (question) => {
    if (yes) {
      console.log(`${question}（--yes，自动确认）`);
      return true;
    }
    return confirm(rl, question);
  };
  try {
    if (restoreIdx >= 0) {
      const dir = args[restoreIdx + 1] && !args[restoreIdx + 1].startsWith('--') && path.resolve(args[restoreIdx + 1]);
      if (!dir || !fs.existsSync(path.join(dir, BACKUP_MARKER))) {
        return fail(`用法：--restore <备份目录>。目录中需有 ${BACKUP_MARKER}，请指向 ${BACKUP_ROOT} 下的某个时间戳目录。`);
      }
      console.log('恢复会用备份覆盖 ~/.claude 下的同名文件（如 settings.json、CLAUDE.md、history.jsonl），会回退这些文件在备份之后的改动；');
      console.log('MCP 服务按名称合并（当前优先），项目设置按字段合并（备份优先）；已存在的软链接保留不覆盖。');
      if (!(await ask('确认恢复？'))) return console.log('已停止。');
      if (await refuseIfClaudeRunning()) return;
      const before = copyWarnings;
      snapshotBeforeRestore();
      return restore(dir, before);
    }

    console.log('请先退出所有 Claude Code 会话和 Claude Desktop。');
    if (!(await ask('确认已经退出？'))) return console.log('已停止。');
    if (await refuseIfClaudeRunning()) return;

    if (!backup(BACKUP_DIR, true)) return;

    if (!(await ask('\n即将退出登录并卸载 Claude。'))) return console.log('已保留程序和备份。');
    rl?.close(); // 之后不再需要输入；关闭后终端恢复正常模式，npm 卡住时可按 Ctrl+C 中断
    const hadClaudeCode = detectClaudeCodeInstalled(); // 只装 Desktop、没用过命令行版的用户，重装时不应该被顺带装上它；检测会跑 npm/brew/winget，放在 rl 关闭之后避免期间 Ctrl+C 不生效
    recoveryHint = [
      '如果流程中途中断，可按以下步骤恢复：',
      hadClaudeCode ? `  1. npm install -g ${PACKAGE_NAME}` : null,
      `  ${hadClaudeCode ? 2 : 1}. node "${process.argv[1]}" --restore "${BACKUP_DIR}"`,
    ].filter(Boolean).join('\n');
    console.log(`\n${recoveryHint}`);
    if (!uninstall()) return void (process.exitCode = 1);
    let installed = true;
    if (hadClaudeCode) {
      installed = install();
    } else {
      warn('未检测到已安装的 Claude Code 命令行版，跳过重新安装（本次只处理 Claude Desktop 数据）。检测依赖 PATH / npm，非标准安装路径可能检测不到；如果你确实用过命令行版，请之后手动执行：npm install -g ' + PACKAGE_NAME);
    }
    const warningsBeforeRestore = copyWarnings;
    if (!installed) return fail(`请解决 npm 安装问题后执行：node "${process.argv[1]}" --restore "${BACKUP_DIR}"`);
    restore(BACKUP_DIR);
    if (warningsBeforeRestore) {
      console.log(`另外，备份 / 卸载 / 安装阶段有 ${warningsBeforeRestore} 条警告（如跳过失效软链接、PATH 提示），请在上方输出中查看。`);
    }
    console.log(`本次备份目录：${BACKUP_DIR}`);
  } finally {
    rl?.close();
  }
}

main().catch((e) => {
  console.log(`\n出错：${e.message}`);
  if (recoveryHint) console.log(recoveryHint);
  process.exitCode = 1;
});
