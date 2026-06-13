// Lightweight PostHog analytics client — uses the PostHog capture REST API
// directly so no npm package is required. Set EXPO_PUBLIC_POSTHOG_API_KEY in
// your EAS build environment.

const POSTHOG_API_KEY = process.env.EXPO_PUBLIC_POSTHOG_API_KEY || "";
const POSTHOG_HOST = "https://app.posthog.com";

// Session-scoped distinct ID — replaced by user ID once the user logs in.
const _sessionId = `anon-${Math.random().toString(36).slice(2)}`;
let _distinctId = _sessionId;
let _userId = null;

function _send(payload) {
  if (!POSTHOG_API_KEY) return;
  fetch(`${POSTHOG_HOST}/capture/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: POSTHOG_API_KEY, ...payload }),
  }).catch(() => {});
}

export function identify(userId, traits = {}) {
  if (!userId) return;
  _userId = userId;
  _distinctId = userId;
  _send({
    event: "$identify",
    distinct_id: _distinctId,
    $set: traits,
  });
}

export function track(event, properties = {}) {
  _send({
    event,
    distinct_id: _distinctId,
    properties: {
      ...properties,
      $lib: "soulmatch-mobile",
      user_id: _userId,
    },
  });
}

export function reset() {
  _userId = null;
  _distinctId = _sessionId;
}
