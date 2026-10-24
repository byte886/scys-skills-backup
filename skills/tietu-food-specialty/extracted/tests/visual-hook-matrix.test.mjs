import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const skillDir = dirname(dirname(fileURLToPath(import.meta.url)));
const profile = JSON.parse(readFileSync(join(skillDir, 'assets', 'track-profile.json'), 'utf8'));

test('视觉爆点矩阵能按赛道和主题组装提示词', () => {
  const hook = profile.images?.visualHook;
  assert.ok(hook, '缺少 images.visualHook');
  assert.ok(hook.stopReason.length >= 12);
  assert.ok(hook.hookVariants.length >= 2);
  assert.ok(hook.prioritySignals.length >= 5);
  assert.ok(hook.preferredMoments.length >= 4);
  assert.ok(hook.compositionBias.length >= 3);
  assert.ok(hook.authenticityTraces.length >= 4);
  assert.ok(hook.avoidGenericScenes.length >= 4);
  assert.match(hook.topicAdaptationRule, /主题|素材/u);
  assert.deepEqual(hook.promptAssemblyOrder, [
  "topicHook",
  "subjectState",
  "singleAction",
  "evidenceDetail",
  "ordinaryEnvironment",
  "authenticityTraces",
  "compositionGoal",
  "overlayDecision",
  "factBoundary",
  "negativeConstraints"
]);
});
