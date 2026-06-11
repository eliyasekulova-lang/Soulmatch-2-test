export type ReasonCode =
  | 'SPAM_SCRIPTING'
  | 'COERCIVE_LANGUAGE'
  | 'MONEY_CUE'
  | 'ISOLATION_CUE'
  | 'BOUNDARY_VIOLATION'
  | 'LOVE_BOMBING_VELOCITY';

export function detectReasonCodes(text: string): ReasonCode[] {
  const t = text.toLowerCase();
  const out: ReasonCode[] = [];
  if (/send money|loan|wire|crypto|investment/.test(t)) out.push('MONEY_CUE');
  if (/don't tell your friends|only trust me/.test(t)) out.push('ISOLATION_CUE');
  if (/soulmate|destiny|meant for each other/.test(t)) out.push('LOVE_BOMBING_VELOCITY');
  if (/why not|you owe me|after all i did/.test(t)) out.push('BOUNDARY_VIOLATION');
  return out;
}
