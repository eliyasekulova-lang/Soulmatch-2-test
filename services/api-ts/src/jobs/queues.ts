import { Queue, Worker } from 'bullmq';
import IORedis from 'ioredis';
import { env } from '../config/env.js';

const connection = new IORedis(env.REDIS_URL, { maxRetriesPerRequest: null });

export const behaviorQueue = new Queue('behavior-aggregation', { connection });
export const safetyQueue = new Queue('safety-scoring', { connection });
export const deletionQueue = new Queue('deletion-jobs', { connection });
export const exportQueue = new Queue('export-jobs', { connection });

export function startWorkers() {
  new Worker('behavior-aggregation', async () => ({ ok: true }), { connection });
  new Worker('safety-scoring', async () => ({ ok: true }), { connection });
  new Worker('deletion-jobs', async () => ({ ok: true }), { connection });
  new Worker('export-jobs', async () => ({ ok: true }), { connection });
}
