import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const testsDir = dirname(fileURLToPath(import.meta.url));
const skillDir = dirname(testsDir);
const validatorPath = join(skillDir, 'scripts', 'validate_output.mjs');
const validPath = join(skillDir, 'examples', 'valid-output.json');
const invalidReasonPath = join(skillDir, 'examples', 'invalid-image-exception.json');
const baseValid = JSON.parse(readFileSync(validPath, 'utf8'));
const workDir = mkdtempSync(join(tmpdir(), 'tietu-marriage-validate-'));
let fixtureIndex = 0;

after(() => rmSync(workDir, { recursive: true, force: true }));

function cloneValid() {
  return structuredClone(baseValid);
}

function writeFixture(data, name) {
  fixtureIndex += 1;
  const path = join(workDir, `${String(fixtureIndex).padStart(2, '0')}-${name}.json`);
  writeFileSync(path, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
  return path;
}

function runValidator(inputPath) {
  return spawnSync(process.execPath, [validatorPath, '--input', inputPath], {
    encoding: 'utf8'
  });
}

function combinedOutput(result) {
  return `${result.stdout ?? ''}${result.stderr ?? ''}`;
}

function expectFailure(data, name, pattern) {
  const result = runValidator(writeFixture(data, name));
  assert.notEqual(result.status, 0, combinedOutput(result));
  assert.match(combinedOutput(result), pattern);
}

test('主有效夹具通过校验', () => {
  const result = runValidator(validPath);
  assert.equal(result.status, 0, combinedOutput(result));
  assert.match(result.stdout, /校验通过/u);
});

test('泛化的扩展图片理由被拒绝', () => {
  const result = runValidator(invalidReasonPath);
  assert.notEqual(result.status, 0, combinedOutput(result));
  assert.match(combinedOutput(result), /不能用.*更丰富/u);
});

test('每张图片都必须声明 source', () => {
  const data = cloneValid();
  delete data.images[1].source;
  expectFailure(data, 'missing-source', /images\[1\]\.source/u);
});

test('原图来源必须提供真实性状态和说明', () => {
  const data = cloneValid();
  data.images[1].source = {
    type: 'source_material',
    historicalAuthenticity: 'verified',
    note: '暂时占位的原图来源说明'
  };
  delete data.images[1].source.note;
  expectFailure(data, 'source-material-missing-note', /images\[1\]\.source\.note/u);
});

test('visual illustration 必须明确不是历史证据', () => {
  const data = cloneValid();
  data.images[1].source = {
    type: 'visual_illustration',
    isHistoricalEvidence: true,
    description: '只合成物件轮廓，不代表真实场景'
  };
  expectFailure(data, 'illustration-evidence-true', /isHistoricalEvidence.*false/u);
});

test('visual illustration 必须提供 description 或 notice', () => {
  const data = cloneValid();
  data.images[1].source = {
    type: 'visual_illustration',
    isHistoricalEvidence: false
  };
  expectFailure(data, 'illustration-missing-description', /description.*notice/u);
});

test('图片 role 只允许白名单值', () => {
  const data = cloneValid();
  data.images[1].role = 'atmosphere';
  expectFailure(data, 'unknown-role', /role.*cover.*detail.*evidence.*process/u);
});

test('后续图片不得再次使用 cover role', () => {
  const data = cloneValid();
  data.images[1].role = 'cover';
  expectFailure(data, 'second-cover', /images\[1\].*不得.*cover/u);
});

test('后续图片 hasTitle 必须为 false', () => {
  const data = cloneValid();
  data.images[1].hasTitle = true;
  expectFailure(data, 'second-title', /images\[1\]\.hasTitle.*false/u);
});

test('每张图片 purpose 必须非空', () => {
  const data = cloneValid();
  data.images[1].purpose = '';
  expectFailure(data, 'empty-purpose', /images\[1\]\.purpose/u);
});

test('detail 是合法的后续图片角色', () => {
  const data = cloneValid();
  data.images[1].role = 'detail';
  const result = runValidator(writeFixture(data, 'allowed-detail'));
  assert.equal(result.status, 0, combinedOutput(result));
});

test('只有“无字”二字的提示词不算完整否定语义', () => {
  const data = cloneValid();
  data.images[1].prompt = '保留原图物件，无字底图。';
  expectFailure(data, 'vague-no-text', /中文.*标题.*标签.*箭头/u);
});

test('提示词拒绝要求模型生成中文标题的反向指令', () => {
  const data = cloneValid();
  data.images[1].prompt = '请生成中文标题，同时不生成文字、标题、标签和箭头文字。';
  expectFailure(data, 'contradictory-text-command', /反向指令/u);
});

test('保留原图真实字迹且拒绝新增文字的自然表达可通过', () => {
  const data = cloneValid();
  data.images[1].prompt = '保持原图现有字迹和光线，不生成新增中文、标题、标签和箭头说明，不添加任何文字。';
  const result = runValidator(writeFixture(data, 'natural-negative-prompt'));
  assert.equal(result.status, 0, combinedOutput(result));
});

test('拒绝无来源第一人称私生活判断', () => {
  const data = cloneValid();
  data.body = `${data.body}。我老公昨晚跪在我面前求我原谅。`;
  expectFailure(data, 'unsupported-private-life', /伪造私生活/u);
});

test('拒绝婚姻绝对化与强行复合', () => {
  const data = cloneValid();
  data.body = `${data.body} 男人都靠不住，不管发生什么都要为了孩子复合。`;
  expectFailure(data, 'unsafe-marriage-claim', /婚姻家庭安全闸门/u);
});

test('婚姻标题不应使用空泛性别群体', () => {
  const data = cloneValid();
  data.title = '男人都靠不住的婚姻答案';
  data.images[0].overlay.text = data.title;
  expectFailure(data, 'gender-generalization', /性别战争|婚姻家庭安全闸门/u);
});

test('候选标题也必须经过内容风险与 AI 腔扫描', () => {
  const data = cloneValid();
  data.titleCandidates[0] = '男人都靠不住，女人就该马上离婚';
  expectFailure(data, 'candidate-risk-scan', /婚姻家庭安全闸门/u);
});

test('没有五个候选标题时失败', () => {
  const data = cloneValid();
  data.titleCandidates = data.titleCandidates.slice(0, 3);
  expectFailure(data, 'too-few-title-candidates', /至少需要 5 个候选标题/u);
});

test('多图必须声明同一家庭场景 continuityKey', () => {
  const data = cloneValid();
  delete data.images[1].continuityKey;
  expectFailure(data, 'missing-continuity-key', /continuityKey/u);
});

test('合成图来源必须明确标注示意范围', () => {
  const data = cloneValid();
  data.images[1].source.description = '一张普通图片';
  delete data.images[1].source.notice;
  expectFailure(data, 'illustration-without-notice', /示意.*合成范围/u);
});

test('婚姻家庭赛道必须锁定42岁社区行政文员人设', () => {
  const data = cloneValid();
  data.perspective = '采用30岁旅行博主视角';
  expectFailure(data, 'marriage-persona', /42岁|社区行政文员|结婚17年/u);
});

test('拒绝性别战争和全知评判', () => {
  const data = cloneValid();
  data.body = `${data.body} 男人都靠不住，女人就该离婚。`;
  expectFailure(data, 'gender-war', /性别战争|全知|婚姻家庭/u);
});

test('拒绝没有边界的强行复合建议', () => {
  const data = cloneValid();
  data.body = `${data.body} 不管发生什么都要为了孩子马上复合。`;
  expectFailure(data, 'forced-reconcile', /强行复合|为了孩子.*复合/u);
});

test('拒绝伪造私生活与未授权身份细节', () => {
  const data = cloneValid();
  data.body = `${data.body} 我老公昨晚跪在我面前求我原谅。`;
  expectFailure(data, 'fabricated-private-life', /伪造私生活|私生活/u);
});

test('婚姻故事必须有动态生活场景', () => {
  const data = cloneValid();
  data.body = data.body.replace(/下班|餐桌|作业本|丈夫|孩子|社区窗口|回到家|手机|书包|水杯|碗|家长会|文员|沉默|家庭|婚姻/gu, '关系');
  expectFailure(data, 'missing-life-scene', /动态生活场景|具体场景/u);
});

test('两层交付字段必须存在且格式化正文首行是标题', () => {
  const data = cloneValid();
  delete data.formattedText;
  expectFailure(data, 'missing-formatted-text', /formattedText/u);
});

test('formattedText 必须同步正文与候选标题', () => {
  const data = cloneValid();
  data.formattedText = `${data.title}\n\n正文不同步\n\n标题候选\n${data.titleCandidates.join('\n')}`;
  expectFailure(data, 'unsynced-formatted-text', /formattedText.*body|formattedText.*titleCandidates/u);
});

test('breakdownAnalysis 必须包含统一六字段', () => {
  const data = cloneValid();
  data.breakdownAnalysis = { angle: '夫妻沟通' };
  expectFailure(data, 'incomplete-breakdown', /breakdownAnalysis.*keywords|breakdownAnalysis.*titleStructure|breakdownAnalysis.*imageStrategy/u);
});
