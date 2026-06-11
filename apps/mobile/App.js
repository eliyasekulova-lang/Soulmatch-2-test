import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Animated,
  Dimensions,
  FlatList,
  KeyboardAvoidingView,
  Platform,
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
import {
  useFonts,
  SpaceGrotesk_400Regular,
  SpaceGrotesk_600SemiBold,
} from "@expo-google-fonts/space-grotesk";
import tzLookup from "tz-lookup";
import { API_BASE_URL } from "./src/config";

const { width: W, height: H } = Dimensions.get("window");

// ── COLORS ────────────────────────────────────────────────────────────────────
const C = {
  bg:     "#0B0E14",
  bg2:    "#10141E",
  bg3:    "#161B27",
  bg4:    "#1C2233",
  purple: "#7B2FBE",
  violet: "#9D4EDD",
  pink:   "#E040FB",
  teal:   "#00C9C8",
  gold:   "#FFD700",
  green:  "#40FB82",
  text:   "#F0F0F8",
  muted:  "#8A8FA8",
  error:  "#FF6B7A",
  border: "rgba(255,255,255,0.08)",
};

// ── PSYCHOLOGY ASSESSMENT ─────────────────────────────────────────────────────
const QUESTIONS = [
  {
    dimension: "Attachment Style",
    emoji: "🔗",
    question: "When you haven't heard from someone you care about in a while, what's your first reaction?",
    options: [
      "I worry — did I say something wrong?",
      "I give them space and trust they'll reach out",
      "I feel fine, I appreciate my independence",
      "I get briefly irritated, then let it go",
    ],
  },
  {
    dimension: "Emotional Regulation",
    emoji: "🌊",
    question: "When you're really upset, you usually...",
    options: [
      "Need to talk it out with someone immediately",
      "Process quietly on my own, then talk",
      "Distract myself until it passes",
      "Channel it — exercise, writing, creating",
    ],
  },
  {
    dimension: "Core Values",
    emoji: "⚡",
    question: "What matters most in a partner?",
    options: [
      "Ambition and a real growth mindset",
      "Emotional warmth and being present",
      "Independence and stability",
      "Playfulness and adventure",
    ],
  },
  {
    dimension: "Communication Style",
    emoji: "💬",
    question: "When something bothers you, you tend to...",
    options: [
      "Say it in the moment, even if it's uncomfortable",
      "Reflect first, then bring it up calmly",
      "Let small things go, only address big ones",
      "Find it really hard to bring up at all",
    ],
  },
  {
    dimension: "Conflict Approach",
    emoji: "🛡",
    question: "During conflict, your instinct is to...",
    options: [
      "Resolve it immediately, even if tense",
      "Need a breather, then come back to talk",
      "Find common ground as quickly as possible",
      "Withdraw until things settle on their own",
    ],
  },
  {
    dimension: "Independence Needs",
    emoji: "🌙",
    question: "Your ideal weekend with a partner looks like...",
    options: [
      "Together all weekend — wherever, whatever",
      "Morning together, afternoon apart",
      "Separate days, come together in the evening",
      "Completely flexible — it depends on the week",
    ],
  },
  {
    dimension: "Vulnerability Comfort",
    emoji: "🫀",
    question: "Sharing something emotionally vulnerable with someone new feels...",
    options: [
      "Natural — I connect through openness",
      "Okay, once I feel safe enough",
      "Hard — I share slowly over time",
      "Very uncomfortable — I keep things private",
    ],
  },
  {
    dimension: "Reassurance Needs",
    emoji: "🤝",
    question: "After a disagreement, what do you need most?",
    options: [
      "Explicit confirmation that we're still okay",
      "Normal interaction — it signals we're fine",
      "Time alone to fully reset",
      "Physical closeness to feel reconnected",
    ],
  },
  {
    dimension: "Love Language",
    emoji: "💝",
    question: "You feel most loved when...",
    options: [
      "Someone tells me directly and sincerely",
      "Someone gives me their full, undivided attention",
      "Someone does something thoughtful for me",
      "Physical presence, touch, or proximity",
    ],
  },
  {
    dimension: "Growth Mindset",
    emoji: "🌱",
    question: "When you're wrong about something, you...",
    options: [
      "Find it uncomfortable but own it quickly",
      "Need some time, but always get there",
      "Defend my view until fully convinced otherwise",
      "Over-apologise — I take it really hard",
    ],
  },
  {
    dimension: "Openness",
    emoji: "🧭",
    question: "Your attitude toward new experiences is...",
    options: [
      "Always excited — novelty energises me",
      "Open, but with some structure around it",
      "Prefer familiar, open to occasional change",
      "Routines ground me — change is stressful",
    ],
  },
  {
    dimension: "Relationship Goals",
    emoji: "🎯",
    question: "In 5 years, your ideal relationship looks like...",
    options: [
      "Deep partnership — building something together",
      "Strong individuals who choose each other daily",
      "Secure home base while pursuing separate ambitions",
      "Still figuring it out — the journey is the goal",
    ],
  },
];

const DEMO_MATCHES = [
  { id: "1", name: "Zara M.", city: "Toronto, ON", score: 91, avatar: "Z", highlights: ["Secure attachment", "Shared growth mindset", "Both value independence"] },
  { id: "2", name: "Jordan K.", city: "Toronto, ON", score: 84, avatar: "J", highlights: ["Similar conflict approach", "Complementary love languages", "Aligned relationship goals"] },
  { id: "3", name: "Sofia T.", city: "Toronto, ON", score: 78, avatar: "S", highlights: ["High emotional regulation match", "Shared core values", "Compatible communication styles"] },
  { id: "4", name: "Alex R.", city: "Toronto, ON", score: 73, avatar: "A", highlights: ["Strong vulnerability alignment", "Matching openness score", "Similar reassurance needs"] },
];

const DIMENSIONS_DEMO = [
  { label: "Attachment Style",     score: 88, color: "#7B2FBE" },
  { label: "Emotional Regulation", score: 74, color: "#9D4EDD" },
  { label: "Core Values",          score: 92, color: "#E040FB" },
  { label: "Communication",        score: 65, color: "#00C9C8" },
  { label: "Conflict Approach",    score: 81, color: "#40FB82" },
  { label: "Independence Needs",   score: 70, color: "#7B2FBE" },
  { label: "Vulnerability",        score: 58, color: "#9D4EDD" },
  { label: "Reassurance Needs",    score: 44, color: "#E040FB" },
  { label: "Love Language",        score: 95, color: "#00C9C8" },
  { label: "Growth Mindset",       score: 87, color: "#40FB82" },
  { label: "Openness",             score: 76, color: "#7B2FBE" },
  { label: "Relationship Goals",   score: 90, color: "#9D4EDD" },
];

// ── PLACE FALLBACK ────────────────────────────────────────────────────────────
const PLACE_FALLBACK = [
  { id: "toronto", label: "Toronto, Ontario, Canada", latitude: 43.6532, longitude: -79.3832 },
  { id: "vancouver", label: "Vancouver, BC, Canada", latitude: 49.2827, longitude: -123.1207 },
  { id: "new-york", label: "New York City, NY, USA", latitude: 40.7128, longitude: -74.006 },
  { id: "london", label: "London, England, UK", latitude: 51.5074, longitude: -0.1278 },
  { id: "los-angeles", label: "Los Angeles, CA, USA", latitude: 34.0522, longitude: -118.2437 },
  { id: "paris", label: "Paris, France", latitude: 48.8566, longitude: 2.3522 },
  { id: "sydney", label: "Sydney, NSW, Australia", latitude: -33.8688, longitude: 151.2093 },
  { id: "berlin", label: "Berlin, Germany", latitude: 52.52, longitude: 13.405 },
  { id: "singapore", label: "Singapore", latitude: 1.3521, longitude: 103.8198 },
  { id: "tokyo", label: "Tokyo, Japan", latitude: 35.6762, longitude: 139.6503 },
];

function safeTimezone(lat, lon) {
  try { return tzLookup(lat, lon); } catch (_) { return ""; }
}

function buildPlaceFallback(query, limit = 6) {
  const q = (query || "").toLowerCase();
  const results = PLACE_FALLBACK.filter(p =>
    !q || p.label.toLowerCase().includes(q)
  ).slice(0, limit);
  return (results.length ? results : PLACE_FALLBACK.slice(0, limit)).map(p => ({
    ...p, timezone: safeTimezone(p.latitude, p.longitude),
  }));
}

// ── API HELPERS ───────────────────────────────────────────────────────────────
async function apiRequest(method, path, payload, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: payload ? JSON.stringify(payload) : undefined,
    });
    let body = null;
    try { body = await res.json(); } catch (_) {}
    return { ok: res.ok, status: res.status, body };
  } catch (e) {
    const err = new Error(`network_error: ${e?.message || "failed_to_fetch"}`);
    err.status = 0;
    throw err;
  }
}

function normalizeError(bodyOrErr, fallback = "request_failed") {
  if (!bodyOrErr) return fallback;
  if (bodyOrErr instanceof Error) return bodyOrErr.message || fallback;
  const d = bodyOrErr.detail ?? bodyOrErr.error ?? bodyOrErr.message;
  if (typeof d === "string" && d.trim()) return d;
  if (Array.isArray(d)) return d.map(i => (typeof i === "string" ? i : i?.msg || "invalid")).join("; ");
  return fallback;
}

function makeUserId(name) {
  const clean = (name || "user").trim().toLowerCase().replace(/[^a-z0-9]/g, "");
  return `${clean || "user"}-${String(Date.now()).slice(-6)}`;
}

function validateDate(v) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return "Use YYYY-MM-DD format";
  const d = new Date(`${v}T00:00:00Z`);
  if (isNaN(d.getTime())) return "Invalid date";
  const [yr, mo, dy] = v.split("-").map(Number);
  if (d.getUTCFullYear() !== yr || d.getUTCMonth() + 1 !== mo || d.getUTCDate() !== dy) return "Invalid date";
  return "";
}
function validateTime(v) {
  if (!/^([01]\d|2[0-3]):([0-5]\d)$/.test(v)) return "Use HH:MM format (24h)";
  return "";
}

// ── SHARED UI COMPONENTS ──────────────────────────────────────────────────────
function GradBtn({ label, onPress, disabled, style }) {
  return (
    <TouchableOpacity onPress={onPress} disabled={disabled} style={[{ opacity: disabled ? 0.45 : 1 }, style]}>
      <LinearGradient colors={["#7B2FBE", "#E040FB"]} start={[0, 0]} end={[1, 0]} style={s.gradBtn}>
        <Text style={s.gradBtnText}>{label}</Text>
      </LinearGradient>
    </TouchableOpacity>
  );
}

function GhostBtn({ label, onPress, disabled, style }) {
  return (
    <TouchableOpacity onPress={onPress} disabled={disabled} style={[s.ghostBtn, disabled && { opacity: 0.45 }, style]}>
      <Text style={s.ghostBtnText}>{label}</Text>
    </TouchableOpacity>
  );
}

function Badge({ label, color = C.teal }) {
  return (
    <View style={[s.badge, { borderColor: color + "44", backgroundColor: color + "18" }]}>
      <Text style={[s.badgeText, { color }]}>{label}</Text>
    </View>
  );
}

function DimBar({ label, score, color }) {
  const pct = Math.min(100, Math.max(0, score));
  return (
    <View style={s.dimRow}>
      <Text style={s.dimLabel} numberOfLines={1}>{label}</Text>
      <View style={s.dimBarBg}>
        <View style={[s.dimBarFill, { width: `${pct}%`, backgroundColor: color }]} />
      </View>
      <Text style={s.dimScore}>{pct}%</Text>
    </View>
  );
}

function Hdr({ title, subtitle, onBack }) {
  return (
    <View style={s.screenHdr}>
      {onBack && (
        <TouchableOpacity onPress={onBack} style={s.backBtn}>
          <Text style={s.backIcon}>←</Text>
        </TouchableOpacity>
      )}
      <View style={{ flex: 1 }}>
        <Text style={s.screenTitle}>{title}</Text>
        {subtitle ? <Text style={s.screenSub}>{subtitle}</Text> : null}
      </View>
    </View>
  );
}

// ── 1. SPLASH SCREEN ──────────────────────────────────────────────────────────
function SplashScreen({ onDone }) {
  const fade = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(0.85)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fade,  { toValue: 1, duration: 800, useNativeDriver: true }),
      Animated.spring(scale, { toValue: 1, tension: 60, friction: 8, useNativeDriver: true }),
    ]).start();
    const t = setTimeout(onDone, 2200);
    return () => clearTimeout(t);
  }, []);

  return (
    <LinearGradient colors={["#0B0E14", "#0F1525", "#161B30"]} style={s.fill}>
      <StatusBar style="light" />
      <Animated.View style={[s.splashCenter, { opacity: fade, transform: [{ scale }] }]}>
        <View style={s.splashLogo}>
          <LinearGradient colors={["#7B2FBE", "#E040FB"]} style={s.splashLogoGrad}>
            <Text style={s.splashLogoIcon}>✦</Text>
          </LinearGradient>
        </View>
        <Text style={s.splashWordmark}>SoulMatch</Text>
        <Text style={s.splashTagline}>Know yourself.{"\n"}Find your match.</Text>
      </Animated.View>
      <View style={s.splashFooter}>
        <View style={s.dot} />
        <View style={[s.dot, { backgroundColor: C.violet }]} />
        <View style={[s.dot, { backgroundColor: C.pink }]} />
      </View>
    </LinearGradient>
  );
}

// ── 2. LOGIN SCREEN ───────────────────────────────────────────────────────────
function LoginScreen({ onLogin, onGoRegister, error, busy }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <LinearGradient colors={["#0B0E14", "#10141E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={s.fill}>
          <ScrollView contentContainerStyle={s.authContainer} keyboardShouldPersistTaps="handled">
            <View style={s.authTop}>
              <Text style={s.wordmark}>✦ SoulMatch</Text>
              <Badge label="Beta · Toronto" color={C.teal} />
            </View>
            <Text style={s.authTitle}>Welcome back</Text>
            <Text style={s.authSub}>Sign in to your account</Text>

            <View style={s.formCard}>
              <View style={s.inputWrap}>
                <Text style={s.inputLabel}>Email</Text>
                <TextInput
                  style={s.input}
                  placeholder="your@email.com"
                  placeholderTextColor={C.muted}
                  value={email}
                  onChangeText={setEmail}
                  keyboardType="email-address"
                  autoCapitalize="none"
                />
              </View>
              <View style={s.inputWrap}>
                <Text style={s.inputLabel}>Password</Text>
                <TextInput
                  style={s.input}
                  placeholder="Your password"
                  placeholderTextColor={C.muted}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                  autoCapitalize="none"
                />
              </View>
              <TouchableOpacity><Text style={s.forgotLink}>Forgot password?</Text></TouchableOpacity>
            </View>

            {error ? <Text style={s.errorMsg}>{error}</Text> : null}

            <GradBtn
              label={busy ? "Signing in…" : "Sign in"}
              onPress={() => onLogin(email, password)}
              disabled={!email || !password || busy}
              style={{ marginTop: 8 }}
            />
            <TouchableOpacity onPress={onGoRegister} style={s.switchLink}>
              <Text style={s.switchLinkText}>New here? <Text style={{ color: C.violet }}>Create account →</Text></Text>
            </TouchableOpacity>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 3. REGISTRATION SCREEN (multi-step) ───────────────────────────────────────
function RegisterScreen({ onComplete, onGoLogin, error, busy }) {
  const [step, setStep] = useState(0);
  const [name, setName]         = useState("");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [birthDate, setBD]      = useState("");
  const [birthTime, setBT]      = useState("");
  const [placeQuery, setPQ]     = useState("");
  const [placeResults, setPR]   = useState([]);
  const [placeLoading, setPL]   = useState(false);
  const [selectedPlace, setSP]  = useState(null);
  const [romance, setRomance]   = useState(true);
  const [friendship, setFriend] = useState(true);
  const [preference, setPref]   = useState("psych_behavior_astro");
  const [consentP, setCP]       = useState(false);
  const [consentS, setCS]       = useState(false);
  const [fieldErr, setFE]       = useState("");

  const STEPS = ["Basics", "Birth data", "Goals", "Consent"];

  async function searchPlace() {
    if (!placeQuery.trim()) return;
    setPL(true); setFE("");
    try {
      const res = await fetch(`${API_BASE_URL}/places/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: placeQuery.trim(), limit: 6 }),
      });
      if (res.ok) {
        const data = await res.json();
        const mapped = (data.results || []).map(p => ({
          ...p, timezone: safeTimezone(+p.latitude, +p.longitude),
        }));
        setPR(mapped.length ? mapped : buildPlaceFallback(placeQuery));
      } else { setPR(buildPlaceFallback(placeQuery)); }
    } catch (_) { setPR(buildPlaceFallback(placeQuery)); }
    finally { setPL(false); }
  }

  function canAdvance() {
    if (step === 0) return name.trim() && email.trim() && password.trim().length >= 8;
    if (step === 1) return birthDate.trim() && birthTime.trim() && selectedPlace;
    if (step === 2) return romance || friendship;
    if (step === 3) return consentP && consentS;
    return true;
  }

  function advance() {
    if (step === 1) {
      const de = validateDate(birthDate.trim());
      const te = validateTime(birthTime.trim());
      if (de || te) { setFE(de || te); return; }
    }
    if (step < 3) { setStep(s => s + 1); setFE(""); return; }
    const goals = [romance && "romance", friendship && "friendship"].filter(Boolean);
    onComplete({ name, email, password, birthDate, birthTime, selectedPlace, goals, preference, consentP, consentS });
  }

  return (
    <LinearGradient colors={["#0B0E14", "#10141E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={s.fill}>
          <ScrollView contentContainerStyle={s.authContainer} keyboardShouldPersistTaps="handled">
            <View style={s.authTop}>
              <Text style={s.wordmark}>✦ SoulMatch</Text>
            </View>

            {/* Step dots */}
            <View style={s.stepDots}>
              {STEPS.map((label, i) => (
                <View key={i} style={s.stepDotWrap}>
                  <View style={[s.stepDot, i <= step && s.stepDotActive, i === step && s.stepDotCurrent]}>
                    <Text style={[s.stepDotNum, i <= step && { color: "#fff" }]}>{i + 1}</Text>
                  </View>
                  {i < STEPS.length - 1 && <View style={[s.stepLine, i < step && s.stepLineActive]} />}
                </View>
              ))}
            </View>
            <Text style={s.stepLabel}>{STEPS[step]}</Text>

            {/* Step 0: Basics */}
            {step === 0 && (
              <View style={s.formCard}>
                <View style={s.inputWrap}>
                  <Text style={s.inputLabel}>Your name</Text>
                  <TextInput style={s.input} placeholder="First name" placeholderTextColor={C.muted} value={name} onChangeText={setName} />
                </View>
                <View style={s.inputWrap}>
                  <Text style={s.inputLabel}>Email</Text>
                  <TextInput style={s.input} placeholder="your@email.com" placeholderTextColor={C.muted} value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" />
                </View>
                <View style={s.inputWrap}>
                  <Text style={s.inputLabel}>Password</Text>
                  <TextInput style={s.input} placeholder="Min 8 characters" placeholderTextColor={C.muted} value={password} onChangeText={setPassword} secureTextEntry autoCapitalize="none" />
                </View>
              </View>
            )}

            {/* Step 1: Birth data */}
            {step === 1 && (
              <View style={s.formCard}>
                <Text style={s.formNote}>Birth data is used for astrology matching (optional feature). Psychology matching doesn't require it.</Text>
                <View style={s.inputWrap}>
                  <Text style={s.inputLabel}>Birth date</Text>
                  <TextInput style={s.input} placeholder="YYYY-MM-DD" placeholderTextColor={C.muted} value={birthDate} onChangeText={v => { setBD(v); setFE(""); }} />
                </View>
                <View style={s.inputWrap}>
                  <Text style={s.inputLabel}>Birth time (24h)</Text>
                  <TextInput style={s.input} placeholder="HH:MM" placeholderTextColor={C.muted} value={birthTime} onChangeText={v => { setBT(v); setFE(""); }} />
                </View>
                <View style={s.inputWrap}>
                  <Text style={s.inputLabel}>Birth city</Text>
                  <View style={s.searchRow}>
                    <TextInput style={[s.input, { flex: 1 }]} placeholder="City, Country" placeholderTextColor={C.muted} value={placeQuery} onChangeText={setPQ} />
                    <TouchableOpacity style={s.searchBtn} onPress={searchPlace} disabled={placeLoading}>
                      <Text style={s.searchBtnText}>{placeLoading ? "…" : "Search"}</Text>
                    </TouchableOpacity>
                  </View>
                </View>
                {placeResults.map(p => (
                  <TouchableOpacity key={p.id} style={[s.placeCard, selectedPlace?.id === p.id && s.placeCardSel]} onPress={() => setSP(p)}>
                    <Text style={s.placeLabel}>{p.label}</Text>
                    <Text style={s.placeMeta}>{p.timezone || "—"}</Text>
                  </TouchableOpacity>
                ))}
                {selectedPlace && (
                  <View style={s.selectedPlaceBox}>
                    <Text style={s.selectedPlaceText}>✓ {selectedPlace.label}</Text>
                  </View>
                )}
                {fieldErr ? <Text style={s.errorMsg}>{fieldErr}</Text> : null}
              </View>
            )}

            {/* Step 2: Goals */}
            {step === 2 && (
              <View style={s.formCard}>
                <Text style={s.inputLabel}>I'm looking for</Text>
                <View style={s.toggleRow}>
                  <View style={s.toggleLabel}><Text style={s.body}>💕 Romance</Text><Text style={s.muted}>Romantic partnership</Text></View>
                  <Switch value={romance} onValueChange={setRomance} trackColor={{ true: C.violet }} thumbColor="#fff" />
                </View>
                <View style={s.toggleRow}>
                  <View style={s.toggleLabel}><Text style={s.body}>🤝 Friendship</Text><Text style={s.muted}>Meaningful connections</Text></View>
                  <Switch value={friendship} onValueChange={setFriend} trackColor={{ true: C.teal }} thumbColor="#fff" />
                </View>
                <Text style={[s.inputLabel, { marginTop: 16 }]}>Matching method</Text>
                {[
                  { val: "psych_behavior", title: "Psychology + Behaviour", sub: "Core compatibility. No astrology." },
                  { val: "psych_behavior_astro", title: "Psychology + Behaviour + Astrology", sub: "Full picture including your birth chart." },
                ].map(opt => (
                  <TouchableOpacity key={opt.val} style={[s.prefCard, preference === opt.val && s.prefCardSel]} onPress={() => setPref(opt.val)}>
                    <View style={[s.prefDot, preference === opt.val && s.prefDotSel]} />
                    <View style={{ flex: 1 }}>
                      <Text style={s.prefTitle}>{opt.title}</Text>
                      <Text style={s.prefSub}>{opt.sub}</Text>
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            )}

            {/* Step 3: Consent */}
            {step === 3 && (
              <View style={s.formCard}>
                <Text style={s.formNote}>Before we create your profile, we need your consent for how we handle your data.</Text>
                <View style={s.toggleRow}>
                  <Text style={[s.body, { flex: 1 }]}>I agree to the Privacy Policy and secure data storage</Text>
                  <Switch value={consentP} onValueChange={setCP} trackColor={{ true: C.violet }} thumbColor="#fff" />
                </View>
                <View style={s.toggleRow}>
                  <Text style={[s.body, { flex: 1 }]}>I consent to processing my data for psychological matching</Text>
                  <Switch value={consentS} onValueChange={setCS} trackColor={{ true: C.violet }} thumbColor="#fff" />
                </View>
              </View>
            )}

            {error ? <Text style={s.errorMsg}>{error}</Text> : null}

            <View style={s.btnRow}>
              {step > 0 ? (
                <GhostBtn label="Back" onPress={() => setStep(s => s - 1)} style={{ flex: 1 }} />
              ) : (
                <GhostBtn label="Sign in instead" onPress={onGoLogin} style={{ flex: 1 }} />
              )}
              <GradBtn
                label={step === 3 ? (busy ? "Creating…" : "Create account") : "Continue →"}
                onPress={advance}
                disabled={!canAdvance() || busy}
                style={{ flex: 2 }}
              />
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 4. ASSESSMENT SCREEN ──────────────────────────────────────────────────────
function AssessmentScreen({ onComplete, onSkip }) {
  const [qIdx, setQIdx]     = useState(0);
  const [answers, setAns]   = useState({});
  const [selected, setSel]  = useState(null);
  const fade = useRef(new Animated.Value(1)).current;
  const q = QUESTIONS[qIdx];
  const progress = (qIdx / QUESTIONS.length) * 100;

  function pickOption(i) { setSel(i); }

  function advance() {
    if (selected === null) return;
    const next = { ...answers, [qIdx]: selected };
    setAns(next);
    if (qIdx === QUESTIONS.length - 1) { onComplete(next); return; }
    Animated.sequence([
      Animated.timing(fade, { toValue: 0, duration: 150, useNativeDriver: true }),
    ]).start(() => {
      setQIdx(i => i + 1);
      setSel(null);
      Animated.timing(fade, { toValue: 1, duration: 250, useNativeDriver: true }).start();
    });
  }

  return (
    <LinearGradient colors={["#0B0E14", "#0F1420"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <View style={s.assessHdr}>
          <TouchableOpacity onPress={onSkip}><Text style={s.skipText}>Skip for now</Text></TouchableOpacity>
          <Text style={s.assessCount}>{qIdx + 1} / {QUESTIONS.length}</Text>
        </View>

        {/* Progress bar */}
        <View style={s.progressBg}>
          <View style={[s.progressFill, { width: `${progress}%` }]} />
        </View>

        <ScrollView contentContainerStyle={s.assessBody} keyboardShouldPersistTaps="handled">
          <Animated.View style={{ opacity: fade }}>
            <View style={s.dimBadge}>
              <Text style={s.dimBadgeEmoji}>{q.emoji}</Text>
              <Text style={s.dimBadgeLabel}>{q.dimension}</Text>
            </View>

            <Text style={s.assessQuestion}>{q.question}</Text>

            <View style={s.options}>
              {q.options.map((opt, i) => (
                <TouchableOpacity
                  key={i}
                  style={[s.optionCard, selected === i && s.optionCardSel]}
                  onPress={() => pickOption(i)}
                  activeOpacity={0.75}
                >
                  <View style={[s.optionDot, selected === i && s.optionDotSel]}>
                    {selected === i && <Text style={s.optionCheck}>✓</Text>}
                  </View>
                  <Text style={[s.optionText, selected === i && s.optionTextSel]}>{opt}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </Animated.View>
        </ScrollView>

        <View style={s.assessFooter}>
          {qIdx > 0 && (
            <GhostBtn label="← Back" onPress={() => { setQIdx(i => i - 1); setSel(answers[qIdx - 1] ?? null); }} style={{ flex: 1 }} />
          )}
          <GradBtn
            label={qIdx === QUESTIONS.length - 1 ? "Complete →" : "Next →"}
            onPress={advance}
            disabled={selected === null}
            style={{ flex: 2 }}
          />
        </View>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 5. PROFILE SCREEN ─────────────────────────────────────────────────────────
function ProfileScreen({ user, dims, onTakeAssessment, onViewReports, onViewMatches, onOpenSettings }) {
  const initials = (user?.name || "U").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  const assessed = dims && dims.length > 0;
  const avgScore = assessed ? Math.round(dims.reduce((a, d) => a + d.score, 0) / dims.length) : null;

  return (
    <LinearGradient colors={["#0B0E14", "#10141E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <ScrollView contentContainerStyle={s.profileContainer}>
          <View style={s.profileHdr}>
            <Text style={s.wordmark}>✦ SoulMatch</Text>
            <TouchableOpacity onPress={onOpenSettings}><Text style={s.settingsIcon}>⚙️</Text></TouchableOpacity>
          </View>

          {/* Avatar */}
          <View style={s.avatarWrap}>
            <LinearGradient colors={["#7B2FBE", "#E040FB"]} style={s.avatar}>
              <Text style={s.avatarText}>{initials}</Text>
            </LinearGradient>
            {assessed && (
              <View style={s.avatarBadge}>
                <Text style={s.avatarBadgeText}>{avgScore}%</Text>
              </View>
            )}
          </View>

          <Text style={s.profileName}>{user?.name || "Your name"}</Text>
          <Text style={s.profileEmail}>{user?.email || ""}</Text>

          {assessed ? (
            <Badge label="Assessment complete" color={C.green} />
          ) : (
            <Badge label="Assessment pending" color={C.gold} />
          )}

          {/* Quick actions */}
          <View style={s.profileActions}>
            <TouchableOpacity style={s.profileAction} onPress={onViewMatches}>
              <Text style={s.profileActionIcon}>💕</Text>
              <Text style={s.profileActionLabel}>Matches</Text>
            </TouchableOpacity>
            <TouchableOpacity style={s.profileAction} onPress={onViewReports}>
              <Text style={s.profileActionIcon}>📊</Text>
              <Text style={s.profileActionLabel}>My report</Text>
            </TouchableOpacity>
            <TouchableOpacity style={s.profileAction} onPress={onTakeAssessment}>
              <Text style={s.profileActionIcon}>🧠</Text>
              <Text style={s.profileActionLabel}>{assessed ? "Retake" : "Assess"}</Text>
            </TouchableOpacity>
          </View>

          {/* Dimensions */}
          {assessed ? (
            <View style={s.card}>
              <Text style={s.cardTitle}>Your psychological profile</Text>
              {dims.map((d, i) => (
                <DimBar key={i} label={d.label} score={d.score} color={d.color} />
              ))}
            </View>
          ) : (
            <View style={s.emptyAssess}>
              <Text style={s.emptyAssessEmoji}>🧠</Text>
              <Text style={s.emptyAssessTitle}>Take the assessment</Text>
              <Text style={s.emptyAssessSub}>Answer 12 quick questions to see your psychological profile and unlock your matches.</Text>
              <GradBtn label="Start assessment →" onPress={onTakeAssessment} style={{ marginTop: 16 }} />
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 6. MATCH DISCOVERY SCREEN ─────────────────────────────────────────────────
function DiscoveryScreen({ matches, mode, onModeChange, onViewMatch, onOpenProfile, busy }) {
  const list = matches.length ? matches : DEMO_MATCHES;
  const isDemo = !matches.length;

  return (
    <LinearGradient colors={["#0B0E14", "#10141E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <View style={s.discHdr}>
          <TouchableOpacity onPress={onOpenProfile}><Text style={s.discAvatar}>👤</Text></TouchableOpacity>
          <Text style={s.wordmark}>✦ SoulMatch</Text>
          <View style={{ width: 36 }} />
        </View>

        {/* Mode toggle */}
        <View style={s.modeRow}>
          {["romance", "friendship"].map(m => (
            <TouchableOpacity key={m} style={[s.modeBtn, mode === m && s.modeBtnActive]} onPress={() => onModeChange(m)}>
              <Text style={[s.modeBtnText, mode === m && s.modeBtnTextActive]}>
                {m === "romance" ? "💕 Romance" : "🤝 Friendship"}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {isDemo && (
          <View style={s.demoNote}>
            <Text style={s.demoNoteText}>✦ Demo mode — complete your assessment to see real matches</Text>
          </View>
        )}

        {busy ? (
          <View style={s.centerFill}><Text style={s.loadingText}>Finding your matches…</Text></View>
        ) : (
          <FlatList
            data={list}
            keyExtractor={m => m.id}
            contentContainerStyle={s.matchList}
            showsVerticalScrollIndicator={false}
            renderItem={({ item: m }) => (
              <View style={s.matchCard}>
                <View style={s.matchCardTop}>
                  <LinearGradient colors={["#7B2FBE", "#E040FB"]} style={s.matchAvatar}>
                    <Text style={s.matchAvatarText}>{m.avatar || m.name[0]}</Text>
                  </LinearGradient>
                  <View style={s.matchInfo}>
                    <Text style={s.matchName}>{m.name}</Text>
                    <Text style={s.matchCity}>📍 {m.city}</Text>
                  </View>
                  <View style={s.matchScoreBadge}>
                    <Text style={s.matchScoreNum}>{Math.round(m.score)}%</Text>
                    <Text style={s.matchScoreLabel}>match</Text>
                  </View>
                </View>
                <View style={s.matchHighlights}>
                  {(m.highlights || []).map((h, i) => (
                    <View key={i} style={s.highlightPill}>
                      <Text style={s.highlightText}>✓ {h}</Text>
                    </View>
                  ))}
                </View>
                <View style={s.matchActions}>
                  <GhostBtn label="View profile" onPress={() => onViewMatch(m)} style={{ flex: 1 }} />
                  <GradBtn label="Message →" onPress={() => onViewMatch(m)} style={{ flex: 1 }} />
                </View>
              </View>
            )}
          />
        )}
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 7. MATCH DETAIL SCREEN ────────────────────────────────────────────────────
function MatchDetailScreen({ match: m, userDims, onBack, onChat }) {
  if (!m) return null;
  const dims = userDims || DIMENSIONS_DEMO;

  return (
    <LinearGradient colors={["#0B0E14", "#10141E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <Hdr title={m.name} subtitle={`📍 ${m.city}`} onBack={onBack} />
        <ScrollView contentContainerStyle={s.detailContainer}>
          {/* Hero */}
          <View style={s.detailHero}>
            <LinearGradient colors={["#7B2FBE", "#E040FB"]} style={s.detailAvatar}>
              <Text style={s.detailAvatarText}>{m.avatar || m.name[0]}</Text>
            </LinearGradient>
            <View style={s.detailScoreRing}>
              <Text style={s.detailScoreNum}>{Math.round(m.score)}%</Text>
              <Text style={s.detailScoreLabel}>compatible</Text>
            </View>
          </View>

          {/* Highlights */}
          <View style={s.card}>
            <Text style={s.cardTitle}>Why you match</Text>
            {(m.highlights || []).map((h, i) => (
              <View key={i} style={s.detailHighlight}>
                <Text style={s.detailHighlightDot}>✦</Text>
                <Text style={s.detailHighlightText}>{h}</Text>
              </View>
            ))}
          </View>

          {/* Dimension breakdown */}
          <View style={s.card}>
            <Text style={s.cardTitle}>Compatibility breakdown</Text>
            <Text style={s.cardSub}>Based on your combined psychological profiles</Text>
            {dims.map((d, i) => {
              const shimmed = Math.min(100, Math.round(d.score * (0.8 + Math.sin(i * 1.7) * 0.15)));
              return <DimBar key={i} label={d.label} score={shimmed} color={d.color} />;
            })}
          </View>

          <GradBtn label="Start conversation →" onPress={() => onChat(m)} style={{ marginBottom: 12 }} />
          <GhostBtn label="Not interested" onPress={onBack} />
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 8. CHAT SCREEN ────────────────────────────────────────────────────────────
function ChatScreen({ match: m, messages, onSend, onBack }) {
  const [text, setText] = useState("");
  const listRef = useRef(null);
  const msgs = messages || [
    { id: "0", text: "Hey! I saw we matched. Your compatibility breakdown was really interesting 🙂", from: "them", ts: "10:24" },
    { id: "1", text: "The shared core values dimension especially — I don't often find that.", from: "them", ts: "10:25" },
  ];

  function send() {
    if (!text.trim()) return;
    onSend(m.id, text.trim());
    setText("");
  }

  return (
    <LinearGradient colors={["#0B0E14", "#10141E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <Hdr title={m?.name || "Chat"} subtitle={`${Math.round(m?.score || 0)}% compatible`} onBack={onBack} />
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={s.fill}>
          <FlatList
            ref={listRef}
            data={msgs}
            keyExtractor={msg => msg.id}
            contentContainerStyle={s.chatList}
            onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
            renderItem={({ item: msg }) => {
              const mine = msg.from === "me";
              return (
                <View style={[s.msgWrap, mine ? s.msgWrapMine : s.msgWrapThem]}>
                  {mine ? (
                    <LinearGradient colors={["#7B2FBE", "#E040FB"]} style={s.msgBubble}>
                      <Text style={s.msgTextMine}>{msg.text}</Text>
                    </LinearGradient>
                  ) : (
                    <View style={[s.msgBubble, s.msgBubbleThem]}>
                      <Text style={s.msgTextThem}>{msg.text}</Text>
                    </View>
                  )}
                  <Text style={s.msgTime}>{msg.ts}</Text>
                </View>
              );
            }}
          />
          <View style={s.chatInput}>
            <TextInput
              style={s.chatTextInput}
              placeholder="Type a message…"
              placeholderTextColor={C.muted}
              value={text}
              onChangeText={setText}
              multiline
              returnKeyType="send"
              onSubmitEditing={send}
            />
            <TouchableOpacity onPress={send} disabled={!text.trim()}>
              <LinearGradient colors={["#7B2FBE", "#E040FB"]} style={[s.sendBtn, !text.trim() && { opacity: 0.45 }]}>
                <Text style={s.sendIcon}>↑</Text>
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 9. REPORTS SCREEN ─────────────────────────────────────────────────────────
const DIM_DESCRIPTIONS = [
  "Describes how you seek connection and respond to perceived distance or rejection.",
  "How well you manage your emotional responses under stress or conflict.",
  "The fundamental beliefs and priorities that guide your choices and life decisions.",
  "Your preferred style for expressing thoughts, needs, and feelings in relationships.",
  "How you typically approach disagreements — avoidant, confrontational, or collaborative.",
  "Your need for personal space, autonomy, and time apart within a relationship.",
  "Your comfort with emotional openness and sharing personal struggles with others.",
  "How much you need explicit confirmation that things are okay between you and a partner.",
  "The primary ways you express and prefer to receive love and care.",
  "Your belief that you and others can change, learn, and improve over time.",
  "Your appetite for novel experiences, ideas, and diverse perspectives.",
  "What you're ultimately hoping to build in a relationship — short-term or long-term.",
];

function ReportsScreen({ user, dims, assessed, onBack, onTakeAssessment }) {
  const d = (dims && dims.length > 0) ? dims : DIMENSIONS_DEMO;
  const avg = Math.round(d.reduce((a, x) => a + x.score, 0) / d.length);

  return (
    <LinearGradient colors={["#0B0E14", "#10141E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <Hdr title="My Report" subtitle="Psychological profile" onBack={onBack} />
        <ScrollView contentContainerStyle={s.reportContainer}>
          {!assessed && (
            <View style={s.reportDemoNote}>
              <Text style={s.reportDemoText}>This is a sample report. Complete your assessment to see real scores.</Text>
              <GradBtn label="Take assessment →" onPress={onTakeAssessment} style={{ marginTop: 12 }} />
            </View>
          )}

          {/* Score summary */}
          <LinearGradient colors={["#7B2FBE22", "#E040FB11"]} style={s.reportSummaryCard}>
            <Text style={s.reportSummaryLabel}>Average compatibility score</Text>
            <Text style={s.reportSummaryScore}>{avg}%</Text>
            <Text style={s.reportSummaryName}>{user?.name || "Your"} profile</Text>
          </LinearGradient>

          {/* Each dimension */}
          {d.map((dim, i) => (
            <View key={i} style={s.reportDimCard}>
              <View style={s.reportDimHdr}>
                <Text style={s.reportDimName}>{dim.label}</Text>
                <Text style={[s.reportDimScore, { color: dim.color }]}>{dim.score}%</Text>
              </View>
              <View style={s.dimBarBg}>
                <View style={[s.dimBarFill, { width: `${dim.score}%`, backgroundColor: dim.color }]} />
              </View>
              <Text style={s.reportDimDesc}>{DIM_DESCRIPTIONS[i]}</Text>
            </View>
          ))}

          <View style={s.reportDisclaimer}>
            <Text style={s.reportDisclaimerText}>This report is for self-discovery and compatibility matching purposes only. It is not a medical or psychological diagnosis.</Text>
          </View>
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 10. SETTINGS SCREEN ───────────────────────────────────────────────────────
function SettingsScreen({ user, onBack, onSignOut, onDeleteAccount }) {
  const [notifs, setNotifs] = useState(true);

  function Row({ label, value, onPress, danger }) {
    return (
      <TouchableOpacity style={s.settingsRow} onPress={onPress}>
        <Text style={[s.settingsRowLabel, danger && { color: C.error }]}>{label}</Text>
        {value ? <Text style={s.settingsRowValue}>{value}</Text> : <Text style={s.settingsRowArrow}>›</Text>}
      </TouchableOpacity>
    );
  }

  return (
    <LinearGradient colors={["#0B0E14", "#10141E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <Hdr title="Settings" onBack={onBack} />
        <ScrollView contentContainerStyle={s.settingsContainer}>

          {/* Account */}
          <Text style={s.settingsSection}>Account</Text>
          <View style={s.card}>
            <Row label="Name" value={user?.name || "—"} />
            <View style={s.divider} />
            <Row label="Email" value={user?.email || "—"} />
            <View style={s.divider} />
            <Row label="Edit profile" />
          </View>

          {/* Notifications */}
          <Text style={s.settingsSection}>Notifications</Text>
          <View style={s.card}>
            <View style={s.settingsRow}>
              <Text style={s.settingsRowLabel}>Match alerts</Text>
              <Switch value={notifs} onValueChange={setNotifs} trackColor={{ true: C.violet }} thumbColor="#fff" />
            </View>
          </View>

          {/* Subscription */}
          <Text style={s.settingsSection}>Subscription</Text>
          <LinearGradient colors={["#7B2FBE", "#E040FB"]} style={s.subCard}>
            <Text style={s.subCardTitle}>SoulMatch Premium</Text>
            <Text style={s.subCardSub}>Unlimited matches · Full compatibility reports · Priority listing</Text>
            <View style={s.subCardPrice}>
              <Text style={s.subCardPriceNum}>$14.99</Text>
              <Text style={s.subCardPricePer}>/month</Text>
            </View>
            <TouchableOpacity style={s.subCardBtn}>
              <Text style={s.subCardBtnText}>Upgrade to Premium</Text>
            </TouchableOpacity>
          </LinearGradient>
          <View style={s.card}>
            <Row label="Current plan" value="Beta (Free)" />
          </View>

          {/* Legal */}
          <Text style={s.settingsSection}>Legal & privacy</Text>
          <View style={s.card}>
            <Row label="Privacy Policy" />
            <View style={s.divider} />
            <Row label="Terms of Service" />
            <View style={s.divider} />
            <Row label="Delete my data" />
          </View>

          {/* Sign out */}
          <View style={s.card}>
            <Row label="Sign out" danger onPress={onSignOut} />
          </View>

          <TouchableOpacity style={s.deleteBtn} onPress={onDeleteAccount}>
            <Text style={s.deleteBtnText}>Delete account permanently</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── ROOT APP ──────────────────────────────────────────────────────────────────
export default function App() {
  const [fontsLoaded] = useFonts({ SpaceGrotesk_400Regular, SpaceGrotesk_600SemiBold });

  // Navigation
  const [screen, setScreen] = useState("splash");
  const [navParam, setNavParam] = useState(null);
  function navigate(s, param = null) { setNavParam(param); setScreen(s); }

  // Auth & user state
  const [user, setUser] = useState(null); // { id, name, email }
  const [authToken, setAuthToken] = useState("");
  const [refreshToken, setRefreshToken] = useState("");

  // App state
  const [busy, setBusy] = useState(false);
  const [authError, setAuthError] = useState("");
  const [mode, setMode] = useState("romance");
  const [matches, setMatches] = useState([]);
  const [messages, setMessages] = useState({});
  const [assessed, setAssessed] = useState(false);
  const [userDims, setUserDims] = useState(null);

  if (!fontsLoaded) return null;

  // ── API HELPERS ──────────────────────────────────────────────────────────
  async function withAuth(fn) {
    let token = authToken;
    return fn(token);
  }

  async function login(email, password) {
    setBusy(true); setAuthError("");
    try {
      const res = await apiRequest("POST", "/auth/login", { email, password }, null);
      if (!res.ok) { setAuthError(normalizeError(res.body, "Login failed")); return; }
      const body = res.body;
      setAuthToken(body.access_token);
      setRefreshToken(body.refresh_token);
      setUser({ id: body.user_id, name: body.name || email.split("@")[0], email });
      navigate("profile");
    } catch (e) {
      setAuthError(normalizeError(e, "Network error. Check your connection."));
    } finally { setBusy(false); }
  }

  async function register(data) {
    setBusy(true); setAuthError("");
    const { name, email, password, birthDate, birthTime, selectedPlace, goals, preference, consentP, consentS } = data;
    try {
      let auth;
      const signupRes = await apiRequest("POST", "/auth/signup", { email, password, birth_date: birthDate }, null);
      if (signupRes.ok) {
        auth = signupRes.body;
      } else if (signupRes.status === 409) {
        const loginRes = await apiRequest("POST", "/auth/login", { email, password }, null);
        if (!loginRes.ok) { setAuthError(normalizeError(loginRes.body, "Login failed")); return; }
        auth = loginRes.body;
      } else {
        setAuthError(normalizeError(signupRes.body, "Registration failed")); return;
      }

      setAuthToken(auth.access_token);
      setRefreshToken(auth.refresh_token);
      const uid = auth.user_id;

      await apiRequest("POST", "/legal/consent", { accept: true }, auth.access_token);

      const profilePayload = {
        id: uid, name, email,
        birth: {
          date: birthDate, time: birthTime,
          place: selectedPlace?.label || "",
          latitude: selectedPlace?.latitude || 0,
          longitude: selectedPlace?.longitude || 0,
          timezone: selectedPlace?.timezone || "",
        },
        goals, matching_preference: preference,
        consent_privacy: consentP, consent_sensitive_data: consentS,
        policy_version: "v1",
      };
      await apiRequest("POST", "/users", profilePayload, auth.access_token);
      if (preference === "psych_behavior_astro") {
        await apiRequest("POST", "/vectors/generate", { user_id: uid }, auth.access_token);
      }

      setUser({ id: uid, name, email });
      navigate("assessment");
    } catch (e) {
      setAuthError(normalizeError(e, "Registration failed. Check your connection."));
    } finally { setBusy(false); }
  }

  async function loadMatches(m = mode) {
    if (!user?.id || !authToken) { setMatches([]); return; }
    setBusy(true);
    try {
      const res = await apiRequest("POST", "/matches", { user_id: user.id, mode: m }, authToken);
      if (res.ok) {
        const ranked = (res.body?.results || []).map(r => ({
          id: r.candidate_id,
          name: r.candidate_name || r.candidate_id,
          city: r.candidate_city || "Toronto, ON",
          score: r.score,
          avatar: (r.candidate_name || "?")[0].toUpperCase(),
          highlights: r.highlights || [],
        }));
        setMatches(ranked);
      } else { setMatches([]); }
    } catch (_) { setMatches([]); }
    finally { setBusy(false); }
  }

  function sendMessage(matchId, text) {
    const now = new Date();
    const ts = `${now.getHours()}:${String(now.getMinutes()).padStart(2, "0")}`;
    const msg = { id: String(Date.now()), text, from: "me", ts };
    setMessages(prev => ({
      ...prev,
      [matchId]: [...(prev[matchId] || []), msg],
    }));
  }

  function signOut() {
    setUser(null); setAuthToken(""); setRefreshToken(""); setMatches([]);
    setAssessed(false); setUserDims(null); navigate("login");
  }

  function handleAssessmentComplete(answers) {
    setAssessed(true);
    setUserDims(DIMENSIONS_DEMO); // In production: compute from answers + POST to /psychology/session
    navigate("discovery");
    loadMatches();
  }

  // ── SCREEN RENDERING ─────────────────────────────────────────────────────
  if (screen === "splash") return <SplashScreen onDone={() => navigate("login")} />;

  if (screen === "login") return (
    <LoginScreen
      onLogin={login}
      onGoRegister={() => { setAuthError(""); navigate("register"); }}
      error={authError}
      busy={busy}
    />
  );

  if (screen === "register") return (
    <RegisterScreen
      onComplete={register}
      onGoLogin={() => { setAuthError(""); navigate("login"); }}
      error={authError}
      busy={busy}
    />
  );

  if (screen === "assessment") return (
    <AssessmentScreen
      onComplete={handleAssessmentComplete}
      onSkip={() => { setAssessed(false); navigate("profile"); }}
    />
  );

  if (screen === "profile") return (
    <ProfileScreen
      user={user}
      dims={userDims || DIMENSIONS_DEMO}
      onTakeAssessment={() => navigate("assessment")}
      onViewReports={() => navigate("reports")}
      onViewMatches={() => { navigate("discovery"); loadMatches(); }}
      onOpenSettings={() => navigate("settings")}
    />
  );

  if (screen === "discovery") return (
    <DiscoveryScreen
      matches={matches}
      mode={mode}
      onModeChange={m => { setMode(m); loadMatches(m); }}
      onViewMatch={m => navigate("match_detail", m)}
      onOpenProfile={() => navigate("profile")}
      busy={busy}
    />
  );

  if (screen === "match_detail") return (
    <MatchDetailScreen
      match={navParam}
      userDims={userDims || DIMENSIONS_DEMO}
      onBack={() => navigate("discovery")}
      onChat={m => navigate("chat", m)}
    />
  );

  if (screen === "chat") return (
    <ChatScreen
      match={navParam}
      messages={messages[navParam?.id]}
      onSend={sendMessage}
      onBack={() => navigate("match_detail", navParam)}
    />
  );

  if (screen === "reports") return (
    <ReportsScreen
      user={user}
      dims={userDims}
      assessed={assessed}
      onBack={() => navigate("profile")}
      onTakeAssessment={() => navigate("assessment")}
    />
  );

  if (screen === "settings") return (
    <SettingsScreen
      user={user}
      onBack={() => navigate("profile")}
      onSignOut={signOut}
      onDeleteAccount={() => {}}
    />
  );

  return null;
}

// ── STYLES ────────────────────────────────────────────────────────────────────
const s = StyleSheet.create({
  fill: { flex: 1 },
  centerFill: { flex: 1, alignItems: "center", justifyContent: "center" },

  // ── Splash
  splashCenter: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 40 },
  splashLogo: { marginBottom: 24 },
  splashLogoGrad: { width: 80, height: 80, borderRadius: 24, alignItems: "center", justifyContent: "center" },
  splashLogoIcon: { color: "#fff", fontSize: 40, fontWeight: "700" },
  splashWordmark: { color: C.text, fontSize: 36, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -1, marginBottom: 16 },
  splashTagline: { color: C.muted, fontSize: 18, textAlign: "center", lineHeight: 28, fontFamily: "SpaceGrotesk_400Regular" },
  splashFooter: { flexDirection: "row", gap: 8, justifyContent: "center", paddingBottom: 60 },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: C.purple },

  // ── Auth
  authContainer: { padding: 24, paddingTop: 20, gap: 16 },
  authTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 8 },
  authTitle: { color: C.text, fontSize: 30, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -0.5 },
  authSub: { color: C.muted, fontSize: 16, fontFamily: "SpaceGrotesk_400Regular", marginBottom: 4 },
  formCard: { backgroundColor: C.bg3, borderRadius: 20, borderWidth: 1, borderColor: C.border, padding: 20, gap: 14 },
  formNote: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 20 },
  inputWrap: { gap: 6 },
  inputLabel: { color: C.muted, fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: 0.8, textTransform: "uppercase" },
  input: { backgroundColor: C.bg2, borderWidth: 1, borderColor: C.border, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular" },
  forgotLink: { color: C.violet, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", textAlign: "right" },
  switchLink: { alignItems: "center", paddingVertical: 8 },
  switchLinkText: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular" },
  searchRow: { flexDirection: "row", gap: 8, alignItems: "center" },
  searchBtn: { backgroundColor: C.teal, paddingHorizontal: 14, paddingVertical: 12, borderRadius: 12 },
  searchBtnText: { color: C.bg, fontSize: 14, fontFamily: "SpaceGrotesk_600SemiBold" },
  placeCard: { backgroundColor: C.bg2, borderWidth: 1, borderColor: C.border, borderRadius: 12, padding: 12, gap: 4 },
  placeCardSel: { borderColor: C.violet },
  placeLabel: { color: C.text, fontSize: 14, fontFamily: "SpaceGrotesk_600SemiBold" },
  placeMeta: { color: C.muted, fontSize: 12, fontFamily: "SpaceGrotesk_400Regular" },
  selectedPlaceBox: { backgroundColor: "rgba(157,78,221,0.12)", borderRadius: 10, padding: 10, borderWidth: 1, borderColor: "rgba(157,78,221,0.3)" },
  selectedPlaceText: { color: C.violet, fontSize: 13, fontFamily: "SpaceGrotesk_600SemiBold" },
  toggleRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
  toggleLabel: { flex: 1, gap: 2 },
  prefCard: { backgroundColor: C.bg2, borderWidth: 1, borderColor: C.border, borderRadius: 14, padding: 14, flexDirection: "row", alignItems: "flex-start", gap: 12 },
  prefCardSel: { borderColor: C.violet, backgroundColor: "rgba(157,78,221,0.08)" },
  prefDot: { width: 18, height: 18, borderRadius: 9, borderWidth: 2, borderColor: C.border, marginTop: 2 },
  prefDotSel: { borderColor: C.violet, backgroundColor: C.violet },
  prefTitle: { color: C.text, fontSize: 14, fontFamily: "SpaceGrotesk_600SemiBold" },
  prefSub: { color: C.muted, fontSize: 12, fontFamily: "SpaceGrotesk_400Regular", marginTop: 2 },
  btnRow: { flexDirection: "row", gap: 10 },

  // ── Step dots
  stepDots: { flexDirection: "row", alignItems: "center", justifyContent: "center", marginBottom: 8 },
  stepDotWrap: { flexDirection: "row", alignItems: "center" },
  stepDot: { width: 28, height: 28, borderRadius: 14, borderWidth: 2, borderColor: C.border, alignItems: "center", justifyContent: "center", backgroundColor: C.bg3 },
  stepDotActive: { borderColor: C.violet, backgroundColor: C.violet },
  stepDotCurrent: { borderColor: C.pink, backgroundColor: C.purple },
  stepDotNum: { color: C.muted, fontSize: 11, fontFamily: "SpaceGrotesk_600SemiBold" },
  stepLine: { width: 28, height: 2, backgroundColor: C.border },
  stepLineActive: { backgroundColor: C.violet },
  stepLabel: { color: C.text, fontSize: 22, fontFamily: "SpaceGrotesk_600SemiBold", textAlign: "center", letterSpacing: -0.3, marginBottom: 4 },

  // ── Assessment
  assessHdr: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, paddingTop: 12, paddingBottom: 8 },
  skipText: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular" },
  assessCount: { color: C.text, fontSize: 14, fontFamily: "SpaceGrotesk_600SemiBold" },
  progressBg: { height: 4, backgroundColor: C.bg3, marginHorizontal: 20, borderRadius: 4 },
  progressFill: { height: 4, borderRadius: 4, backgroundColor: C.violet },
  assessBody: { padding: 24, paddingTop: 28, gap: 20 },
  dimBadge: { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: "rgba(157,78,221,0.12)", borderRadius: 50, paddingHorizontal: 14, paddingVertical: 8, alignSelf: "flex-start", borderWidth: 1, borderColor: "rgba(157,78,221,0.3)" },
  dimBadgeEmoji: { fontSize: 16 },
  dimBadgeLabel: { color: C.violet, fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: 0.5 },
  assessQuestion: { color: C.text, fontSize: 22, fontFamily: "SpaceGrotesk_600SemiBold", lineHeight: 30, letterSpacing: -0.3 },
  options: { gap: 12 },
  optionCard: { backgroundColor: C.bg3, borderWidth: 1, borderColor: C.border, borderRadius: 16, padding: 16, flexDirection: "row", alignItems: "center", gap: 14 },
  optionCardSel: { borderColor: C.violet, backgroundColor: "rgba(157,78,221,0.1)" },
  optionDot: { width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: C.border, alignItems: "center", justifyContent: "center", flexShrink: 0 },
  optionDotSel: { borderColor: C.violet, backgroundColor: C.violet },
  optionCheck: { color: "#fff", fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold" },
  optionText: { color: C.muted, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", flex: 1, lineHeight: 22 },
  optionTextSel: { color: C.text },
  assessFooter: { flexDirection: "row", gap: 10, padding: 20, paddingBottom: 32 },

  // ── Profile
  profileContainer: { padding: 20, gap: 20 },
  profileHdr: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  settingsIcon: { fontSize: 20 },
  avatarWrap: { alignItems: "center", marginTop: 8 },
  avatar: { width: 96, height: 96, borderRadius: 48, alignItems: "center", justifyContent: "center" },
  avatarText: { color: "#fff", fontSize: 34, fontFamily: "SpaceGrotesk_600SemiBold" },
  avatarBadge: { position: "absolute", bottom: 0, right: W / 2 - 76, backgroundColor: C.bg, borderRadius: 12, paddingHorizontal: 8, paddingVertical: 4, borderWidth: 2, borderColor: C.green },
  avatarBadgeText: { color: C.green, fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold" },
  profileName: { color: C.text, fontSize: 24, fontFamily: "SpaceGrotesk_600SemiBold", textAlign: "center", letterSpacing: -0.3 },
  profileEmail: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular", textAlign: "center" },
  profileActions: { flexDirection: "row", gap: 12, justifyContent: "center" },
  profileAction: { backgroundColor: C.bg3, borderWidth: 1, borderColor: C.border, borderRadius: 16, padding: 16, alignItems: "center", minWidth: 90 },
  profileActionIcon: { fontSize: 24, marginBottom: 6 },
  profileActionLabel: { color: C.muted, fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold" },
  emptyAssess: { backgroundColor: C.bg3, borderRadius: 20, borderWidth: 1, borderColor: C.border, padding: 28, alignItems: "center" },
  emptyAssessEmoji: { fontSize: 48, marginBottom: 16 },
  emptyAssessTitle: { color: C.text, fontSize: 20, fontFamily: "SpaceGrotesk_600SemiBold", marginBottom: 8 },
  emptyAssessSub: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular", textAlign: "center", lineHeight: 22 },

  // ── Shared card
  card: { backgroundColor: C.bg3, borderRadius: 20, borderWidth: 1, borderColor: C.border, padding: 20, gap: 14 },
  cardTitle: { color: C.text, fontSize: 16, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -0.2 },
  cardSub: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", marginTop: -6 },
  divider: { height: 1, backgroundColor: C.border },

  // ── Dim bar
  dimRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  dimLabel: { width: 160, color: C.muted, fontSize: 12, fontFamily: "SpaceGrotesk_400Regular" },
  dimBarBg: { flex: 1, height: 6, backgroundColor: "rgba(255,255,255,0.06)", borderRadius: 6, overflow: "hidden" },
  dimBarFill: { height: 6, borderRadius: 6 },
  dimScore: { color: C.muted, fontSize: 11, fontFamily: "SpaceGrotesk_600SemiBold", width: 32, textAlign: "right" },

  // ── Discovery
  discHdr: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, paddingTop: 12, paddingBottom: 8 },
  discAvatar: { fontSize: 24 },
  modeRow: { flexDirection: "row", margin: 16, marginTop: 8, backgroundColor: C.bg3, borderRadius: 50, padding: 4, borderWidth: 1, borderColor: C.border },
  modeBtn: { flex: 1, paddingVertical: 10, borderRadius: 50, alignItems: "center" },
  modeBtnActive: { backgroundColor: C.purple },
  modeBtnText: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_600SemiBold" },
  modeBtnTextActive: { color: "#fff" },
  demoNote: { marginHorizontal: 16, backgroundColor: "rgba(157,78,221,0.08)", borderRadius: 12, padding: 10, borderWidth: 1, borderColor: "rgba(157,78,221,0.2)", marginBottom: 8 },
  demoNoteText: { color: C.violet, fontSize: 12, fontFamily: "SpaceGrotesk_400Regular", textAlign: "center" },
  matchList: { padding: 16, gap: 14 },
  matchCard: { backgroundColor: C.bg3, borderRadius: 20, borderWidth: 1, borderColor: C.border, padding: 18, gap: 14 },
  matchCardTop: { flexDirection: "row", alignItems: "center", gap: 14 },
  matchAvatar: { width: 52, height: 52, borderRadius: 26, alignItems: "center", justifyContent: "center" },
  matchAvatarText: { color: "#fff", fontSize: 20, fontFamily: "SpaceGrotesk_600SemiBold" },
  matchInfo: { flex: 1 },
  matchName: { color: C.text, fontSize: 18, fontFamily: "SpaceGrotesk_600SemiBold" },
  matchCity: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular" },
  matchScoreBadge: { alignItems: "center", backgroundColor: "rgba(157,78,221,0.12)", borderRadius: 12, padding: 10, borderWidth: 1, borderColor: "rgba(157,78,221,0.25)" },
  matchScoreNum: { color: C.violet, fontSize: 18, fontFamily: "SpaceGrotesk_600SemiBold" },
  matchScoreLabel: { color: C.muted, fontSize: 10, fontFamily: "SpaceGrotesk_400Regular" },
  matchHighlights: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  highlightPill: { backgroundColor: "rgba(0,201,200,0.08)", borderRadius: 50, paddingHorizontal: 10, paddingVertical: 5, borderWidth: 1, borderColor: "rgba(0,201,200,0.2)" },
  highlightText: { color: C.teal, fontSize: 12, fontFamily: "SpaceGrotesk_400Regular" },
  matchActions: { flexDirection: "row", gap: 10 },
  loadingText: { color: C.muted, fontFamily: "SpaceGrotesk_400Regular", fontSize: 16 },

  // ── Match Detail
  detailContainer: { padding: 20, gap: 20 },
  detailHero: { alignItems: "center", gap: 16, paddingVertical: 8 },
  detailAvatar: { width: 100, height: 100, borderRadius: 50, alignItems: "center", justifyContent: "center" },
  detailAvatarText: { color: "#fff", fontSize: 36, fontFamily: "SpaceGrotesk_600SemiBold" },
  detailScoreRing: { alignItems: "center", backgroundColor: "rgba(157,78,221,0.12)", borderRadius: 20, paddingHorizontal: 24, paddingVertical: 12, borderWidth: 1, borderColor: "rgba(157,78,221,0.3)" },
  detailScoreNum: { color: C.violet, fontSize: 36, fontFamily: "SpaceGrotesk_600SemiBold" },
  detailScoreLabel: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular" },
  detailHighlight: { flexDirection: "row", gap: 12, alignItems: "flex-start" },
  detailHighlightDot: { color: C.violet, fontSize: 14, marginTop: 2 },
  detailHighlightText: { color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", flex: 1, lineHeight: 22 },

  // ── Chat
  chatList: { padding: 16, gap: 8 },
  msgWrap: { maxWidth: "80%", gap: 4 },
  msgWrapMine: { alignSelf: "flex-end", alignItems: "flex-end" },
  msgWrapThem: { alignSelf: "flex-start", alignItems: "flex-start" },
  msgBubble: { borderRadius: 18, padding: 14 },
  msgBubbleThem: { backgroundColor: C.bg3, borderWidth: 1, borderColor: C.border },
  msgTextMine: { color: "#fff", fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 22 },
  msgTextThem: { color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 22 },
  msgTime: { color: C.muted, fontSize: 11, fontFamily: "SpaceGrotesk_400Regular", paddingHorizontal: 4 },
  chatInput: { flexDirection: "row", alignItems: "flex-end", gap: 10, padding: 16, borderTopWidth: 1, borderTopColor: C.border, backgroundColor: C.bg2 },
  chatTextInput: { flex: 1, backgroundColor: C.bg3, borderRadius: 22, borderWidth: 1, borderColor: C.border, paddingHorizontal: 16, paddingVertical: 12, color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", maxHeight: 100 },
  sendBtn: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center" },
  sendIcon: { color: "#fff", fontSize: 18, fontFamily: "SpaceGrotesk_600SemiBold" },

  // ── Reports
  reportContainer: { padding: 20, gap: 16 },
  reportDemoNote: { backgroundColor: "rgba(255,215,0,0.06)", borderRadius: 16, padding: 16, borderWidth: 1, borderColor: "rgba(255,215,0,0.2)" },
  reportDemoText: { color: C.gold, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 22 },
  reportSummaryCard: { borderRadius: 20, padding: 24, alignItems: "center", gap: 6, borderWidth: 1, borderColor: "rgba(224,64,251,0.2)" },
  reportSummaryLabel: { color: C.muted, fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: 0.8, textTransform: "uppercase" },
  reportSummaryScore: { color: C.text, fontSize: 52, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -2 },
  reportSummaryName: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular" },
  reportDimCard: { backgroundColor: C.bg3, borderRadius: 16, borderWidth: 1, borderColor: C.border, padding: 16, gap: 10 },
  reportDimHdr: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  reportDimName: { color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_600SemiBold" },
  reportDimScore: { fontSize: 15, fontFamily: "SpaceGrotesk_600SemiBold" },
  reportDimDesc: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 20 },
  reportDisclaimer: { backgroundColor: C.bg3, borderRadius: 12, padding: 14, borderWidth: 1, borderColor: C.border },
  reportDisclaimerText: { color: C.muted, fontSize: 12, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 18, textAlign: "center" },

  // ── Settings
  settingsContainer: { padding: 20, gap: 8 },
  settingsSection: { color: C.muted, fontSize: 11, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: 1, textTransform: "uppercase", marginTop: 12, marginBottom: 4, paddingLeft: 4 },
  settingsRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 14 },
  settingsRowLabel: { color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular" },
  settingsRowValue: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular" },
  settingsRowArrow: { color: C.muted, fontSize: 20 },
  subCard: { borderRadius: 20, padding: 24, gap: 10 },
  subCardTitle: { color: "#fff", fontSize: 20, fontFamily: "SpaceGrotesk_600SemiBold" },
  subCardSub: { color: "rgba(255,255,255,0.7)", fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 20 },
  subCardPrice: { flexDirection: "row", alignItems: "flex-end", gap: 4 },
  subCardPriceNum: { color: "#fff", fontSize: 32, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -1 },
  subCardPricePer: { color: "rgba(255,255,255,0.6)", fontSize: 14, fontFamily: "SpaceGrotesk_400Regular", paddingBottom: 6 },
  subCardBtn: { backgroundColor: "rgba(255,255,255,0.15)", borderRadius: 50, paddingVertical: 12, alignItems: "center", marginTop: 4 },
  subCardBtnText: { color: "#fff", fontSize: 15, fontFamily: "SpaceGrotesk_600SemiBold" },
  deleteBtn: { alignItems: "center", paddingVertical: 16 },
  deleteBtnText: { color: C.error, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular" },

  // ── Screen header
  screenHdr: { flexDirection: "row", alignItems: "center", gap: 14, paddingHorizontal: 20, paddingTop: 12, paddingBottom: 16 },
  backBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: C.bg3, borderWidth: 1, borderColor: C.border, alignItems: "center", justifyContent: "center" },
  backIcon: { color: C.text, fontSize: 18, marginLeft: -2 },
  screenTitle: { color: C.text, fontSize: 20, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -0.3 },
  screenSub: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular" },

  // ── Common
  wordmark: { color: C.text, fontSize: 18, fontFamily: "SpaceGrotesk_600SemiBold" },
  badge: { alignSelf: "flex-start", borderRadius: 50, paddingHorizontal: 12, paddingVertical: 5, borderWidth: 1 },
  badgeText: { fontSize: 11, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: 0.6, textTransform: "uppercase" },
  body: { color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 22 },
  muted: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular" },
  errorMsg: { color: C.error, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", textAlign: "center" },

  // ── Buttons
  gradBtn: { borderRadius: 50, paddingVertical: 14, paddingHorizontal: 24, alignItems: "center" },
  gradBtnText: { color: "#fff", fontSize: 15, fontFamily: "SpaceGrotesk_600SemiBold" },
  ghostBtn: { borderRadius: 50, paddingVertical: 14, paddingHorizontal: 24, alignItems: "center", borderWidth: 1, borderColor: C.border, backgroundColor: "transparent" },
  ghostBtnText: { color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_600SemiBold" },
});
