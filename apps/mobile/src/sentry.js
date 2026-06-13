// Sentry initialization for React Native / Expo.
// Captures JS errors and React component crashes in production builds.
// Native crash reporting activates after running: npx expo install @sentry/react-native
// and adding the EAS build plugin (see app.json plugins).

let Sentry = null;

export function initSentry() {
  const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN;
  if (!dsn) return;
  try {
    Sentry = require("@sentry/react-native");
    Sentry.init({
      dsn,
      environment: process.env.EXPO_PUBLIC_ENV || "development",
      tracesSampleRate: 0.15,
      enabled: (process.env.EXPO_PUBLIC_ENV || "development") !== "development",
    });
  } catch {
    // Package not installed yet — silently skip.
  }
}

export function captureException(err, context = {}) {
  if (!Sentry) return;
  Sentry.captureException(err, { extra: context });
}

export function setUser(userId) {
  if (!Sentry) return;
  Sentry.setUser(userId ? { id: userId } : null);
}
