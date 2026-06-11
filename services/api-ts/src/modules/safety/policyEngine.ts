export type RiskBand = 'low' | 'medium' | 'high' | 'critical';

export function riskBand(score: number): RiskBand {
  if (score >= 75) return 'critical';
  if (score >= 50) return 'high';
  if (score >= 25) return 'medium';
  return 'low';
}

export function actionsForBand(band: RiskBand): string[] {
  if (band === 'medium') return ['rate_limit_mild', 'recipient_tips_contextual'];
  if (band === 'high') return ['rate_limit_strong', 'visibility_reduce', 'auto_hide_coercive'];
  if (band === 'critical') return ['rate_limit_severe', 'force_verification', 'shadow_throttle', 'admin_review'];
  return [];
}
