import { describe, it, expect } from 'vitest';
import { buildApp } from '../src/index.js';

describe('m1 smoke', () => {
  it('health works', async () => {
    const app = await buildApp();
    const res = await app.inject({ method: 'GET', url: '/health' });
    expect(res.statusCode).toBe(200);
    expect(res.json().milestone).toBe('M1');
    await app.close();
  });
});
