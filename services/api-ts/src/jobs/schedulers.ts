import { behaviorQueue, safetyQueue } from './queues.js';

export async function scheduleNightlyJobs() {
  await behaviorQueue.upsertJobScheduler('nightly_behavior', { pattern: '0 2 * * *' }, { name: 'aggregate' });
  await safetyQueue.upsertJobScheduler('nightly_safety', { pattern: '15 2 * * *' }, { name: 'score' });
}
