import React, { useMemo, useState } from "react";
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import { LinearGradient } from "expo-linear-gradient";
import { useFonts, SpaceGrotesk_400Regular, SpaceGrotesk_600SemiBold } from "@expo-google-fonts/space-grotesk";
import tzLookup from "tz-lookup";
import { API_BASE_URL } from "./src/config";

const steps = ["welcome", "identity", "birth", "goals", "consent", "done"];

function makeUserId(name) {
  const clean = (name || "user").trim().toLowerCase().replace(/[^a-z0-9]/g, "");
  const suffix = String(Date.now()).slice(-6);
  return `${clean || "user"}-${suffix}`;
}

function validateBirthDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return "Use date format YYYY-MM-DD.";
  }
  const d = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) {
    return "Birth date is invalid.";
  }
  const [year, month, day] = value.split("-").map(Number);
  if (d.getUTCFullYear() !== year || d.getUTCMonth() + 1 !== month || d.getUTCDate() !== day) {
    return "Birth date is invalid.";
  }
  return "";
}

function validateBirthTime(value) {
  if (!/^([01]\d|2[0-3]):([0-5]\d)$/.test(value)) {
    return "Use time format HH:MM in 24h.";
  }
  return "";
}

function safeTimezone(lat, lon) {
  try {
    return tzLookup(lat, lon);
  } catch (_e) {
    return "";
  }
}

async function apiRequest(method, path, payload, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: payload ? JSON.stringify(payload) : undefined,
    });
  } catch (e) {
    const err = new Error(`network_error: ${String(e?.message || "failed_to_fetch")}`);
    err.status = 0;
    throw err;
  }

  let body = null;
  try {
    body = await res.json();
  } catch (_e) {
    body = null;
  }

  return { ok: res.ok, status: res.status, body };
}

function normalizeApiError(body, fallback = "request_failed") {
  if (!body) return fallback;
  const detail = body.detail ?? body.error ?? body.message;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const path = Array.isArray(item.loc) ? item.loc.join(".") : "payload";
          const msg = item.msg || item.type || "invalid";
          return `${path}: ${msg}`;
        }
        return String(item);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return fallback;
}

function normalizeUnknownError(err, fallback = "request_failed") {
  if (!err) return fallback;
  if (typeof err === "string") return err;
  if (err instanceof Error && typeof err.message === "string" && err.message.trim()) {
    return err.message;
  }
  if (typeof err === "object" && err.message) {
    return String(err.message);
  }
  try {
    return JSON.stringify(err);
  } catch (_e) {
    return fallback;
  }
}

const PLACE_FALLBACK_RESULTS = [
  { id: "toronto", label: "Toronto, Ontario, Canada", latitude: 43.6532, longitude: -79.3832 },
  { id: "new-york", label: "New York City, NY, USA", latitude: 40.7128, longitude: -74.006 },
  { id: "london", label: "London, England, UK", latitude: 51.5074, longitude: -0.1278 },
  { id: "los-angeles", label: "Los Angeles, CA, USA", latitude: 34.0522, longitude: -118.2437 },
  { id: "paris", label: "Paris, France", latitude: 48.8566, longitude: 2.3522 },
  { id: "sydney", label: "Sydney, NSW, Australia", latitude: -33.8688, longitude: 151.2093 },
  { id: "dubai", label: "Dubai, UAE", latitude: 25.2048, longitude: 55.2708 },
  { id: "singapore", label: "Singapore", latitude: 1.3521, longitude: 103.8198 },
  { id: "tokyo", label: "Tokyo, Japan", latitude: 35.6762, longitude: 139.6503 },
  { id: "berlin", label: "Berlin, Germany", latitude: 52.52, longitude: 13.405 },
  { id: "amsterdam", label: "Amsterdam, Netherlands", latitude: 52.3676, longitude: 4.9041 },
  { id: "chicago", label: "Chicago, IL, USA", latitude: 41.8781, longitude: -87.6298 },
  { id: "mumbai", label: "Mumbai, India", latitude: 19.076, longitude: 72.8777 },
  { id: "mexico-city", label: "Mexico City, Mexico", latitude: 19.4326, longitude: -99.1332 },
  { id: "sao-paulo", label: "São Paulo, Brazil", latitude: -23.5505, longitude: -46.6333 },
  { id: "vancouver", label: "Vancouver, BC, Canada", latitude: 49.2827, longitude: -123.1207 },
  { id: "seoul", label: "Seoul, South Korea", latitude: 37.5665, longitude: 126.978 },
  { id: "cairo", label: "Cairo, Egypt", latitude: 30.0444, longitude: 31.2357 },
  { id: "istanbul", label: "Istanbul, Turkey", latitude: 41.0082, longitude: 28.9784 },
  { id: "barcelona", label: "Barcelona, Spain", latitude: 41.3851, longitude: 2.1734 },
];

function buildPlaceFallback(query, limit = 6) {
  const q = (query || "").trim().toLowerCase();
  const ranked = PLACE_FALLBACK_RESULTS.filter((item) => {
    if (!q) return true;
    return item.label.toLowerCase().includes(q) || q.split(/\s+/).some((part) => item.label.toLowerCase().includes(part));
  });
  const list = (ranked.length ? ranked : PLACE_FALLBACK_RESULTS).slice(0, limit);
  return list.map((item) => ({
    ...item,
    timezone: safeTimezone(item.latitude, item.longitude),
  }));
}

function parseIsoDateMs(value) {
  if (!value) return 0;
  const t = Date.parse(value);
  return Number.isNaN(t) ? 0 : t;
}

export default function App() {
  const [fontsLoaded] = useFonts({
    SpaceGrotesk_400Regular,
    SpaceGrotesk_600SemiBold,
  });

  const [stepIndex, setStepIndex] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [birthValidationError, setBirthValidationError] = useState("");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authSession, setAuthSession] = useState({
    userId: "",
    accessToken: "",
    accessTokenExpiresAt: "",
    refreshToken: "",
    refreshTokenExpiresAt: "",
  });
  const [birthDate, setBirthDate] = useState("");
  const [birthTime, setBirthTime] = useState("");
  const [placeQuery, setPlaceQuery] = useState("");
  const [placeResults, setPlaceResults] = useState([]);
  const [placeLoading, setPlaceLoading] = useState(false);
  const [selectedPlace, setSelectedPlace] = useState(null);
  const [romanceGoal, setRomanceGoal] = useState(true);
  const [friendshipGoal, setFriendshipGoal] = useState(true);
  const [matchingPreference, setMatchingPreference] = useState("psych_behavior_astro");
  const [consentPrivacy, setConsentPrivacy] = useState(false);
  const [consentSensitive, setConsentSensitive] = useState(false);
  const [privacySummary, setPrivacySummary] = useState("");
  const [termsSummary, setTermsSummary] = useState("");
  const [onboardingSummary, setOnboardingSummary] = useState(null);
  const [mode, setMode] = useState("romance");
  const [matches, setMatches] = useState([]);

  const currentStep = steps[stepIndex];

  const goals = useMemo(() => {
    const g = [];
    if (romanceGoal) g.push("romance");
    if (friendshipGoal) g.push("friendship");
    return g;
  }, [romanceGoal, friendshipGoal]);

  const visibleMatches = useMemo(() => {
    const mapped = matches.map((m) => ({ ...m, score: Number(m.score || 0) }));
    return mapped.sort((a, b) => b.score - a.score);
  }, [matches]);

  if (!fontsLoaded) {
    return null;
  }

  function isAccessTokenExpired() {
    const expiresAtMs = parseIsoDateMs(authSession.accessTokenExpiresAt);
    if (!expiresAtMs) return true;
    return Date.now() >= expiresAtMs - 15000;
  }

  function isRefreshTokenExpired() {
    const expiresAtMs = parseIsoDateMs(authSession.refreshTokenExpiresAt);
    if (!expiresAtMs) return true;
    return Date.now() >= expiresAtMs;
  }

  async function refreshAccessToken() {
    if (!authSession.refreshToken || isRefreshTokenExpired()) {
      throw new Error("refresh_token_unavailable");
    }
    const response = await apiRequest("POST", "/auth/refresh", { refresh_token: authSession.refreshToken }, null);
    if (!response.ok) {
      throw new Error(normalizeApiError(response.body, "refresh_failed"));
    }
    const next = {
      userId: response.body.user_id,
      accessToken: response.body.access_token,
      accessTokenExpiresAt: response.body.access_token_expires_at,
      refreshToken: response.body.refresh_token,
      refreshTokenExpiresAt: response.body.refresh_token_expires_at,
    };
    setAuthSession(next);
    return next.accessToken;
  }

  async function authorizedPost(path, payload, providedToken = "") {
    let token = providedToken || authSession.accessToken;
    const usingSessionToken = !providedToken;
    if (usingSessionToken && token && isAccessTokenExpired()) {
      token = await refreshAccessToken();
    }
    let response = await apiRequest("POST", path, payload, token || null);
    if (response.status === 401 && authSession.refreshToken) {
      token = await refreshAccessToken();
      response = await apiRequest("POST", path, payload, token);
    }
    if (!response.ok) {
      const err = new Error(normalizeApiError(response.body, "request_failed"));
      err.status = response.status;
      throw err;
    }
    return response.body;
  }

  async function authorizedGet(path, providedToken = "") {
    let token = providedToken || authSession.accessToken;
    const usingSessionToken = !providedToken;
    if (usingSessionToken && token && isAccessTokenExpired()) {
      token = await refreshAccessToken();
    }
    let response = await apiRequest("GET", path, null, token || null);
    if (response.status === 401 && authSession.refreshToken) {
      token = await refreshAccessToken();
      response = await apiRequest("GET", path, null, token);
    }
    if (!response.ok) {
      const err = new Error(normalizeApiError(response.body, "request_failed"));
      err.status = response.status;
      throw err;
    }
    return response.body;
  }

  async function trackEvent(eventName, payload) {
    try {
      await authorizedPost("/events", {
        event_name: eventName,
        event_payload: payload || {},
      });
    } catch (_e) {
      // non-blocking analytics
    }
  }

  async function searchPlace() {
    if (!placeQuery.trim()) return;
    setPlaceLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/places/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: placeQuery.trim(), limit: 6 }),
      });
      if (!res.ok) {
        throw new Error("place_search_failed");
      }
      const data = await res.json();
      const mapped = (Array.isArray(data?.results) ? data.results : []).map((item) => {
        const lat = Number(item.latitude);
        const lon = Number(item.longitude);
        return {
          id: item.id,
          label: item.label,
          latitude: lat,
          longitude: lon,
          timezone: safeTimezone(lat, lon),
        };
      });
      if (mapped.length > 0) {
        setPlaceResults(mapped);
      } else {
        setPlaceResults(buildPlaceFallback(placeQuery.trim(), 6));
      }
      trackEvent("place_search_success", { query: placeQuery.trim(), count: mapped.length });
    } catch (_e) {
      const fallback = buildPlaceFallback(placeQuery.trim(), 6);
      setPlaceResults(fallback);
      setError("Live place lookup is unavailable. Showing fallback city results.");
      trackEvent("place_search_fallback", { query: placeQuery.trim(), count: fallback.length });
    } finally {
      setPlaceLoading(false);
    }
  }

  function selectPlace(item) {
    setSelectedPlace(item);
  }

  function validateBirthFields() {
    const dateErr = validateBirthDate(birthDate.trim());
    if (dateErr) return dateErr;
    const timeErr = validateBirthTime(birthTime.trim());
    if (timeErr) return timeErr;
    return "";
  }

  function canContinue() {
    if (currentStep === "identity") return Boolean(name.trim() && email.trim() && password.trim().length >= 8);
    if (currentStep === "birth") {
      return Boolean(birthDate.trim() && birthTime.trim() && selectedPlace);
    }
    if (currentStep === "goals") return goals.length > 0;
    if (currentStep === "consent") return consentPrivacy && consentSensitive;
    return true;
  }

  async function fetchRankedMatches(userId, matchMode, providedToken = "") {
    const response = await authorizedPost("/matches", {
      user_id: userId,
      mode: matchMode,
    }, providedToken);

    const ranked = (response.results || []).map((r) => {
      return {
        id: r.candidate_id,
        name: r.candidate_name || r.candidate_id,
        city: r.candidate_city || "Unknown",
        score: r.score,
        highlights: r.highlights || [],
      };
    });

    setMatches(ranked);
  }

  async function submitOnboarding() {
    setBusy(true);
    setError("");
    setBirthValidationError("");

    const validationErr = validateBirthFields();
    if (validationErr) {
      setBirthValidationError(validationErr);
      setBusy(false);
      return;
    }

    const payload = {
      id: makeUserId(name),
      name: name.trim(),
      email: email.trim() || undefined,
      birth: {
        date: birthDate.trim(),
        time: birthTime.trim(),
        place: selectedPlace.label,
        latitude: selectedPlace.latitude,
        longitude: selectedPlace.longitude,
        timezone: selectedPlace.timezone,
      },
      goals,
      matching_preference: matchingPreference,
      consent_privacy: consentPrivacy,
      consent_sensitive_data: consentSensitive,
      policy_version: "v1",
    };

    try {
      const initialMode = goals.includes("romance") ? "romance" : "friendship";
      setMode(initialMode);

      let auth;
      try {
        const signupResponse = await apiRequest(
          "POST",
          "/auth/signup",
          {
            email: email.trim(),
            password: password.trim(),
            birth_date: birthDate.trim(),
          },
          null
        );
        if (!signupResponse.ok) {
          const err = new Error(normalizeApiError(signupResponse.body, "signup_failed"));
          err.status = signupResponse.status;
          throw err;
        }
        auth = signupResponse.body;
      } catch (signupErr) {
        if (signupErr.status === 409) {
          const loginResponse = await apiRequest("POST", "/auth/login", { email: email.trim(), password: password.trim() }, null);
          if (!loginResponse.ok) {
            throw new Error(normalizeApiError(loginResponse.body, "login_failed"));
          }
          auth = loginResponse.body;
        } else {
          throw signupErr;
        }
      }

      const resolvedUserId = auth.user_id;
      setAuthSession({
        userId: resolvedUserId,
        accessToken: auth.access_token,
        accessTokenExpiresAt: auth.access_token_expires_at,
        refreshToken: auth.refresh_token,
        refreshTokenExpiresAt: auth.refresh_token_expires_at,
      });

      const consentResponse = await apiRequest("POST", "/legal/consent", { accept: true }, auth.access_token);
      if (!consentResponse.ok) {
        throw new Error(normalizeApiError(consentResponse.body, "legal_consent_failed"));
      }

      await authorizedPost("/users", { ...payload, id: resolvedUserId }, auth.access_token);
      if (matchingPreference === "psych_behavior_astro") {
        await authorizedPost("/vectors/generate", { user_id: resolvedUserId }, auth.access_token);
      }

      await fetchRankedMatches(resolvedUserId, initialMode, auth.access_token);
      trackEvent("onboarding_completed", { mode: initialMode });

      setOnboardingSummary({
        userId: resolvedUserId,
        place: selectedPlace.label,
        latitude: selectedPlace.latitude,
        longitude: selectedPlace.longitude,
        timezone: selectedPlace.timezone || "Unknown",
      });
      setStepIndex(5);
    } catch (_e) {
      const detail = normalizeUnknownError(_e, "unknown_error");
      setError(`Could not submit onboarding or fetch matches (${detail}). API: ${API_BASE_URL}`);
      trackEvent("onboarding_error", { message: detail });
    } finally {
      setBusy(false);
    }
  }

  async function refreshModeMatches(nextMode) {
    setMode(nextMode);
    if (!onboardingSummary) return;
    try {
      setBusy(true);
      await fetchRankedMatches(onboardingSummary.userId, nextMode);
      trackEvent("match_mode_changed", { mode: nextMode });
    } catch (_e) {
      setError("Could not refresh matches for selected mode.");
    } finally {
      setBusy(false);
    }
  }

  function nextStep() {
    if (currentStep === "birth") {
      const validationErr = validateBirthFields();
      setBirthValidationError(validationErr);
      if (validationErr) return;
    }

    if (currentStep === "consent") {
      submitOnboarding();
      return;
    }

    setStepIndex((v) => Math.min(v + 1, 5));
  }

  function prevStep() {
    setError("");
    setBirthValidationError("");
    setStepIndex((v) => Math.max(v - 1, 0));
  }

  function renderTopBar() {
    const progress = Math.round((stepIndex / (steps.length - 1)) * 100);
    return (
      <View style={styles.topBar}>
        <Text style={styles.brand}>SoulMatch</Text>
        <Text style={styles.progressText}>{progress}%</Text>
      </View>
    );
  }

  function renderWelcome() {
    return (
      <View style={styles.panel}>
        <Text style={styles.title}>Personalized matching from real birth-chart data.</Text>
        <Text style={styles.body}>
          Pilot city is Toronto. The onboarding supports worldwide location search and timezone-aware chart calculation.
        </Text>
      </View>
    );
  }

  function renderIdentity() {
    return (
      <View style={styles.panel}>
        <Text style={styles.sectionTitle}>Profile Basics</Text>
        <TextInput
          style={styles.input}
          placeholder="Name"
          placeholderTextColor="#9AA5BA"
          value={name}
          onChangeText={setName}
        />
        <TextInput
          style={styles.input}
          placeholder="Email"
          placeholderTextColor="#9AA5BA"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
        />
        <TextInput
          style={styles.input}
          placeholder="Password (min 8 chars)"
          placeholderTextColor="#9AA5BA"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoCapitalize="none"
        />
      </View>
    );
  }

  function renderBirth() {
    return (
      <View style={styles.panel}>
        <Text style={styles.sectionTitle}>Birth Data</Text>
        <TextInput
          style={styles.input}
          placeholder="Birth date (YYYY-MM-DD)"
          placeholderTextColor="#9AA5BA"
          value={birthDate}
          onChangeText={(v) => {
            setBirthDate(v);
            if (birthValidationError) setBirthValidationError("");
          }}
        />
        <TextInput
          style={styles.input}
          placeholder="Birth time (HH:MM, 24h)"
          placeholderTextColor="#9AA5BA"
          value={birthTime}
          onChangeText={(v) => {
            setBirthTime(v);
            if (birthValidationError) setBirthValidationError("");
          }}
        />

        <View style={styles.row}>
          <TextInput
            style={[styles.input, styles.flex]}
            placeholder="Birth place (city, country)"
            placeholderTextColor="#9AA5BA"
            value={placeQuery}
            onChangeText={setPlaceQuery}
          />
          <TouchableOpacity style={styles.searchBtn} onPress={searchPlace} disabled={placeLoading}>
            <Text style={styles.searchText}>{placeLoading ? "..." : "Search"}</Text>
          </TouchableOpacity>
        </View>

        {placeLoading ? <ActivityIndicator color="#7FE7C4" /> : null}

        {placeResults.map((item) => {
          const isSelected = selectedPlace && selectedPlace.id === item.id;
          return (
            <TouchableOpacity
              key={String(item.id)}
              style={[styles.placeCard, isSelected ? styles.placeCardSelected : null]}
              onPress={() => selectPlace(item)}
            >
              <Text style={styles.placeTitle}>{item.label}</Text>
              <Text style={styles.placeMeta}>
                {item.latitude.toFixed(4)}, {item.longitude.toFixed(4)} | {item.timezone || "timezone unavailable"}
              </Text>
            </TouchableOpacity>
          );
        })}

        <Text style={styles.placeMeta}>Map picker is available in native builds. Web uses place search results.</Text>

        {selectedPlace ? (
          <View style={styles.summaryCard}>
            <Text style={styles.summaryText}>Selected: {selectedPlace.label}</Text>
            <Text style={styles.summaryText}>
              Lat/Lon: {selectedPlace.latitude.toFixed(4)}, {selectedPlace.longitude.toFixed(4)}
            </Text>
            <Text style={styles.summaryText}>Timezone: {selectedPlace.timezone || "Unknown"}</Text>
          </View>
        ) : null}

        {birthValidationError ? <Text style={styles.error}>{birthValidationError}</Text> : null}
      </View>
    );
  }

  function renderGoals() {
    return (
      <View style={styles.panel}>
        <Text style={styles.sectionTitle}>Matching Goals</Text>
        <View style={styles.toggleRow}>
          <Text style={styles.body}>Romance</Text>
          <Switch value={romanceGoal} onValueChange={setRomanceGoal} trackColor={{ true: "#7FE7C4" }} />
        </View>
        <View style={styles.toggleRow}>
          <Text style={styles.body}>Friendship</Text>
          <Switch value={friendshipGoal} onValueChange={setFriendshipGoal} trackColor={{ true: "#7FE7C4" }} />
        </View>

        <Text style={styles.body}>Matching Method</Text>
        <TouchableOpacity
          style={[styles.preferenceCard, matchingPreference === "psych_behavior" ? styles.preferenceCardSelected : null]}
          onPress={() => setMatchingPreference("psych_behavior")}
        >
          <Text style={styles.preferenceTitle}>Psych + Behavior</Text>
          <Text style={styles.placeMeta}>Use psychological and behavior profiles only.</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.preferenceCard, matchingPreference === "psych_behavior_astro" ? styles.preferenceCardSelected : null]}
          onPress={() => setMatchingPreference("psych_behavior_astro")}
        >
          <Text style={styles.preferenceTitle}>Psych + Behavior + Astro</Text>
          <Text style={styles.placeMeta}>Blend psychological, behavior, and astrology signals together.</Text>
        </TouchableOpacity>
      </View>
    );
  }

  function renderConsent() {
    return (
      <View style={styles.panel}>
        <Text style={styles.sectionTitle}>Consent</Text>
        <TouchableOpacity
          style={styles.secondaryAction}
          onPress={async () => {
            try {
              const [privacy, terms] = await Promise.all([authorizedGet("/legal/privacy"), authorizedGet("/legal/terms")]);
              setPrivacySummary(privacy.summary || "");
              setTermsSummary(terms.summary || "");
              trackEvent("legal_summaries_loaded", {});
            } catch (_e) {
              setError("Could not load legal summaries.");
            }
          }}
        >
          <Text style={styles.secondaryActionText}>Load Privacy and Terms Summary</Text>
        </TouchableOpacity>
        {privacySummary ? <Text style={styles.placeMeta}>Privacy: {privacySummary}</Text> : null}
        {termsSummary ? <Text style={styles.placeMeta}>Terms: {termsSummary}</Text> : null}
        <View style={styles.toggleRow}>
          <Text style={styles.body}>I agree to the privacy policy and secure storage terms.</Text>
          <Switch value={consentPrivacy} onValueChange={setConsentPrivacy} trackColor={{ true: "#7FE7C4" }} />
        </View>
        <View style={styles.toggleRow}>
          <Text style={styles.body}>
            {matchingPreference === "psych_behavior_astro"
              ? "I consent to processing sensitive birth data for astrology-enhanced matching."
              : "I understand my birth details stay on file and can be used later if I turn on astrology matching."}
          </Text>
          <Switch value={consentSensitive} onValueChange={setConsentSensitive} trackColor={{ true: "#7FE7C4" }} />
        </View>
      </View>
    );
  }

  function renderDone() {
    return (
      <View style={styles.panel}>
        <Text style={styles.sectionTitle}>Your Matches</Text>
        <Text style={styles.disclaimerText}>
          Match insights are guidance only, not medical advice, and not deterministic guarantees.
        </Text>
        <Text style={styles.body}>Mode</Text>
        <View style={styles.modeRow}>
          <TouchableOpacity
            style={[styles.modeBtn, mode === "romance" ? styles.modeBtnActive : null]}
            onPress={() => refreshModeMatches("romance")}
            disabled={busy}
          >
            <Text style={styles.modeText}>Romance</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.modeBtn, mode === "friendship" ? styles.modeBtnActive : null]}
            onPress={() => refreshModeMatches("friendship")}
            disabled={busy}
          >
            <Text style={styles.modeText}>Friendship</Text>
          </TouchableOpacity>
        </View>

        {onboardingSummary ? (
          <View style={styles.summaryCard}>
            <Text style={styles.summaryText}>User: {onboardingSummary.userId}</Text>
            <Text style={styles.summaryText}>Place: {onboardingSummary.place}</Text>
            <Text style={styles.summaryText}>
              Lat/Lon: {onboardingSummary.latitude.toFixed(4)}, {onboardingSummary.longitude.toFixed(4)}
            </Text>
            <Text style={styles.summaryText}>Timezone: {onboardingSummary.timezone}</Text>
          </View>
        ) : null}

        {busy ? <ActivityIndicator color="#7FE7C4" /> : null}

        {visibleMatches.map((m) => (
          <View key={m.id} style={styles.matchCard}>
            <View style={styles.matchHeader}>
              <Text style={styles.matchName}>{m.name}</Text>
              <Text style={styles.matchScore}>{m.score.toFixed(2)}%</Text>
            </View>
            <Text style={styles.placeMeta}>{m.city}</Text>
            {(m.highlights || []).map((h) => (
              <Text key={`${m.id}-${h}`} style={styles.highlight}>
                {h}
              </Text>
            ))}
            <TouchableOpacity style={styles.chatBtn}>
              <Text style={styles.chatText}>Open Chat</Text>
            </TouchableOpacity>
          </View>
        ))}
      </View>
    );
  }

  function renderStep() {
    if (currentStep === "welcome") return renderWelcome();
    if (currentStep === "identity") return renderIdentity();
    if (currentStep === "birth") return renderBirth();
    if (currentStep === "goals") return renderGoals();
    if (currentStep === "consent") return renderConsent();
    return renderDone();
  }

  return (
    <LinearGradient colors={["#0A0F1A", "#121D30", "#1B2A3E"]} style={styles.bg}>
      <StatusBar style="light" />
      <SafeAreaView style={styles.safe}>
        <ScrollView contentContainerStyle={styles.container}>
          {renderTopBar()}
          {renderStep()}

          {error ? <Text style={styles.error}>{error}</Text> : null}

          {currentStep !== "done" ? (
            <View style={styles.actionRow}>
              <TouchableOpacity
                style={[styles.secondaryAction, stepIndex === 0 ? styles.disabled : null]}
                onPress={prevStep}
                disabled={stepIndex === 0 || busy}
              >
                <Text style={styles.secondaryActionText}>Back</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.primaryAction, !canContinue() || busy ? styles.disabled : null]}
                onPress={nextStep}
                disabled={!canContinue() || busy}
              >
                <Text style={styles.primaryActionText}>
                  {busy ? "Submitting..." : currentStep === "consent" ? "Finish" : "Continue"}
                </Text>
              </TouchableOpacity>
            </View>
          ) : null}
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  bg: { flex: 1 },
  safe: { flex: 1 },
  container: {
    padding: 18,
    paddingTop: 20,
    gap: 14,
  },
  topBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  brand: {
    color: "#7FE7C4",
    fontSize: 14,
    letterSpacing: 1.5,
    textTransform: "uppercase",
    fontFamily: "SpaceGrotesk_600SemiBold",
  },
  progressText: {
    color: "#C6D0E3",
    fontSize: 13,
    fontFamily: "SpaceGrotesk_400Regular",
  },
  panel: {
    backgroundColor: "#111B2A",
    borderColor: "#24344D",
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    gap: 12,
  },
  title: {
    color: "#F5F7FB",
    fontSize: 30,
    lineHeight: 34,
    fontFamily: "SpaceGrotesk_600SemiBold",
  },
  sectionTitle: {
    color: "#F5F7FB",
    fontSize: 22,
    lineHeight: 26,
    fontFamily: "SpaceGrotesk_600SemiBold",
  },
  body: {
    color: "#C7D2E7",
    fontSize: 15,
    lineHeight: 22,
    fontFamily: "SpaceGrotesk_400Regular",
  },
  input: {
    borderColor: "#30425E",
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: "#F5F7FB",
    fontSize: 15,
    fontFamily: "SpaceGrotesk_400Regular",
    backgroundColor: "#0C1320",
  },
  row: {
    flexDirection: "row",
    gap: 8,
    alignItems: "center",
  },
  flex: { flex: 1 },
  searchBtn: {
    backgroundColor: "#7FE7C4",
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 10,
  },
  searchText: {
    color: "#0A0F1A",
    fontSize: 13,
    fontFamily: "SpaceGrotesk_600SemiBold",
  },
  placeCard: {
    backgroundColor: "#0D1726",
    borderColor: "#30425E",
    borderWidth: 1,
    borderRadius: 12,
    padding: 10,
    gap: 4,
  },
  preferenceCard: {
    backgroundColor: "#0D1726",
    borderColor: "#30425E",
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    gap: 4,
  },
  preferenceCardSelected: {
    borderColor: "#7FE7C4",
    backgroundColor: "#132336",
  },
  preferenceTitle: {
    color: "#E7ECF5",
    fontSize: 15,
    fontFamily: "SpaceGrotesk_600SemiBold",
  },
  placeCardSelected: {
    borderColor: "#7FE7C4",
  },
  placeTitle: {
    color: "#E7ECF5",
    fontSize: 14,
    fontFamily: "SpaceGrotesk_600SemiBold",
  },
  placeMeta: {
    color: "#9FB0CB",
    fontSize: 12,
    lineHeight: 18,
    fontFamily: "SpaceGrotesk_400Regular",
  },
  mapWrap: {
    gap: 8,
  },
  map: {
    height: 190,
    borderRadius: 12,
  },
  toggleRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
  },
  primaryAction: {
    flex: 1,
    backgroundColor: "#7FE7C4",
    paddingVertical: 12,
    borderRadius: 12,
  },
  primaryActionText: {
    textAlign: "center",
    color: "#0A0F1A",
    fontSize: 15,
    fontFamily: "SpaceGrotesk_600SemiBold",
  },
  secondaryAction: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#334867",
    paddingVertical: 12,
    borderRadius: 12,
  },
  secondaryActionText: {
    textAlign: "center",
    color: "#E7ECF5",
    fontSize: 15,
    fontFamily: "SpaceGrotesk_600SemiBold",
  },
  disabled: {
    opacity: 0.5,
  },
  error: {
    color: "#FF8E96",
    fontFamily: "SpaceGrotesk_400Regular",
    fontSize: 13,
  },
  modeRow: {
    flexDirection: "row",
    gap: 10,
  },
  modeBtn: {
    flex: 1,
    backgroundColor: "#0C1320",
    borderColor: "#30425E",
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 10,
  },
  modeBtnActive: {
    borderColor: "#7FE7C4",
  },
  modeText: {
    color: "#E7ECF5",
    textAlign: "center",
    fontFamily: "SpaceGrotesk_600SemiBold",
    fontSize: 14,
  },
  summaryCard: {
    backgroundColor: "#0D1726",
    borderColor: "#314462",
    borderWidth: 1,
    borderRadius: 12,
    padding: 10,
    gap: 4,
  },
  summaryText: {
    color: "#C6D0E3",
    fontSize: 12,
    fontFamily: "SpaceGrotesk_400Regular",
  },
  matchCard: {
    backgroundColor: "#0D1726",
    borderColor: "#30425E",
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    gap: 7,
  },
  matchHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  matchName: {
    color: "#EAF0FA",
    fontSize: 17,
    fontFamily: "SpaceGrotesk_600SemiBold",
  },
  matchScore: {
    color: "#7FE7C4",
    fontSize: 17,
    fontFamily: "SpaceGrotesk_600SemiBold",
  },
  highlight: {
    color: "#C7D2E7",
    fontSize: 13,
    fontFamily: "SpaceGrotesk_400Regular",
  },
  chatBtn: {
    marginTop: 4,
    backgroundColor: "#1A2B42",
    borderColor: "#325279",
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 8,
  },
  chatText: {
    color: "#E7ECF5",
    textAlign: "center",
    fontSize: 13,
    fontFamily: "SpaceGrotesk_600SemiBold",
  },
  disclaimerText: {
    color: "#9FB0CB",
    fontSize: 12,
    lineHeight: 18,
    fontFamily: "SpaceGrotesk_400Regular",
  },
});
