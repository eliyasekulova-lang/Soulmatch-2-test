import { describe, expect, it } from 'vitest';
import { buildApp } from '../../src/index.js';

describe('delete flow', () => {
  it('accepts user-initiated delete request endpoint', async () => {
    const app = await buildApp();
    const token = await app.jwt.sign({ sub: 'usr_test_1', role: 'user' });

    const res = await app.inject({
      method: 'POST',
      url: '/v1/rights/delete',
      headers: { authorization: `Bearer ${token}` },
      payload: { reason: 'privacy request' }
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.ok).toBe(true);
    expect(body.status).toBe('queued');

    await app.close();
  });
});
