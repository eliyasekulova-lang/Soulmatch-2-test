const ENV = process.env.EXPO_PUBLIC_ENV || "development";

const defaults = {
  development: "http://127.0.0.1:8000",
  staging: "https://soulmatching-staging.onrender.com",
  production: "https://api.soulmatch.app",
};

export const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL || defaults[ENV] || defaults.development;
export const APP_ENV = ENV;
