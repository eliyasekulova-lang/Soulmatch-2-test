import { describe, expect, it } from 'vitest';
import { isBlockedAdvisorPrompt } from '../../src/modules/advisor/policy.js';

describe('advisor policy', () => {
  it('blocks backward failure analysis prompt', () => {
    expect(isBlockedAdvisorPrompt('Why did my last relationship fail?')).toBe(true);
  });

  it('allows forward guidance prompt', () => {
    expect(isBlockedAdvisorPrompt('How can I set boundaries early?')).toBe(false);
  });
});
