const disallowedPatterns = [
  /why did my last relationship fail/i,
  /analy[sz]e my ex/i,
  /whose fault was/i
];

export function isBlockedAdvisorPrompt(prompt: string): boolean {
  return disallowedPatterns.some((re) => re.test(prompt));
}
