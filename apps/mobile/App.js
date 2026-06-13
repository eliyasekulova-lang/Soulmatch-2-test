import React, { useState, useEffect, useRef } from "react";
import {
  Alert,
  Animated,
  Dimensions,
  FlatList,
  KeyboardAvoidingView,
  Linking,
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
import { identify as phIdentify, track, reset as phReset } from "./src/analytics";
import { initSentry, captureException, setUser as setSentryUser } from "./src/sentry";

initSentry();

const { width: W } = Dimensions.get("window");

// ── COLORS ─────────────────────────────────────────────────────────────────────
const C = {
  bg: "#0D1409", bg2: "#121C0E", bg3: "#192614", bg4: "#1F2D1A",
  purple: "#4E8B5F", violet: "#6AAE78", pink: "#C8A045",
  teal: "#8BAA8D", gold: "#C8A045", green: "#7DB87D",
  text: "#E6DDD0", muted: "#7A8A7D", error: "#D97070",
  border: "rgba(255,255,255,0.07)",
};

// ── PSYCHOLOGY: 12 MAIN QUESTIONS ─────────────────────────────────────────────
const QUESTIONS = [
  {
    dimension: "Attachment Style", emoji: "🔗",
    question: "When you haven't heard from someone you care about in a while, what's your first reaction?",
    options: [
      "I worry — did I say something wrong?",
      "I give them space and trust they'll reach out",
      "I feel fine, I value my independence",
      "I get briefly irritated, then let it go",
    ],
  },
  {
    dimension: "Emotional Regulation", emoji: "🌊",
    question: "When you're really upset, you usually...",
    options: [
      "Need to talk it out with someone immediately",
      "Process quietly on my own, then talk",
      "Distract myself until it passes",
      "Channel it into exercise, writing, or creating",
    ],
  },
  {
    dimension: "Core Values", emoji: "⚡",
    question: "What matters most in a close relationship?",
    options: [
      "Shared ambition and growth mindset",
      "Emotional warmth and being genuinely present",
      "Mutual independence and stability",
      "Playfulness, spontaneity, and adventure",
    ],
  },
  {
    dimension: "Communication Style", emoji: "💬",
    question: "When something bothers you in a relationship, you tend to...",
    options: [
      "Say it in the moment, even if uncomfortable",
      "Reflect first, then bring it up calmly later",
      "Let smaller things go, only address big ones",
      "Find it really hard to bring up at all",
    ],
  },
  {
    dimension: "Conflict Approach", emoji: "🛡",
    question: "During conflict, your instinct is to...",
    options: [
      "Resolve it immediately, even if it gets tense",
      "Take a breather, then come back to talk",
      "Find common ground as quickly as possible",
      "Withdraw until things settle on their own",
    ],
  },
  {
    dimension: "Independence Needs", emoji: "🌙",
    question: "Your ideal weekend with someone close looks like...",
    options: [
      "Together the whole time — wherever, whatever",
      "Mornings together, afternoons apart",
      "Mostly separate days, reunite in the evening",
      "Completely flexible depending on the week",
    ],
  },
  {
    dimension: "Vulnerability Comfort", emoji: "🫀",
    question: "Sharing something emotionally vulnerable with someone new feels...",
    options: [
      "Natural — I connect through openness",
      "Okay, once I feel safe enough",
      "Hard — I share slowly over time",
      "Very uncomfortable — I keep things private",
    ],
  },
  {
    dimension: "Reassurance Needs", emoji: "🤝",
    question: "After a disagreement, what do you need most?",
    options: [
      "Explicit confirmation that we're still okay",
      "Normal interaction — that signals things are fine",
      "Time alone to fully reset first",
      "Physical closeness to feel reconnected",
    ],
  },
  {
    dimension: "Love Language", emoji: "💝",
    question: "You feel most loved when...",
    options: [
      "Someone tells me directly and sincerely",
      "Someone gives me their full, undivided attention",
      "Someone does something thoughtful without being asked",
      "Physical presence, touch, or proximity",
    ],
  },
  {
    dimension: "Growth Mindset", emoji: "🌱",
    question: "When you're wrong about something, you...",
    options: [
      "Find it uncomfortable but own it quickly",
      "Need a little time, but always get there",
      "Defend my view until fully convinced otherwise",
      "Over-apologise — I take it really hard on myself",
    ],
  },
  {
    dimension: "Openness", emoji: "🧭",
    question: "Your attitude toward new experiences is...",
    options: [
      "Always excited — novelty energises me",
      "Open, but I like some structure around it",
      "I prefer the familiar, open to occasional change",
      "My routines ground me — change is stressful",
    ],
  },
  {
    dimension: "Relationship Goals", emoji: "🎯",
    question: "In 5 years, your ideal relationship looks like...",
    options: [
      "Deep partnership — building something together",
      "Strong individuals who actively choose each other daily",
      "A secure home base while pursuing separate ambitions",
      "Still figuring it out — the journey is the goal",
    ],
  },
];

// ── ADAPTIVE FOLLOW-UP QUESTIONS (one per attachment answer) ──────────────────
const ADAPTIVE_QUESTIONS = [
  // [0] Anxious
  {
    dimension: "Attachment Style (Depth)", emoji: "😟",
    question: "When a partner becomes less responsive or pulls back emotionally, you usually...",
    options: [
      "Wait and try hard not to read into it",
      "Send a gentle check-in to see if things are okay",
      "Increase contact — more texts, calls, showing up",
      "Feel panicked and unsure what to do with myself",
    ],
  },
  // [1] Secure
  {
    dimension: "Attachment Style (Depth)", emoji: "🌿",
    question: "When someone important to you is struggling emotionally, your instinct is to...",
    options: [
      "Listen without trying to fix anything — just be present",
      "Help them think through it practically",
      "Give them space to process, then check in",
      "Gently encourage them to open up",
    ],
  },
  // [2] Avoidant
  {
    dimension: "Attachment Style (Depth)", emoji: "🏃",
    question: "When a relationship starts feeling emotionally intense or 'too much', you...",
    options: [
      "Get very busy — work, hobbies, anything to create distance",
      "Have an honest conversation about needing more space",
      "Slowly pull back without fully explaining why",
      "Stay physically present but emotionally disconnect",
    ],
  },
  // [3] Disorganized
  {
    dimension: "Attachment Style (Depth)", emoji: "🌀",
    question: "In a close relationship, when you feel both drawn to AND scared of closeness, you...",
    options: [
      "Swing between wanting closeness and pushing the person away",
      "Try to sit with the discomfort and stay present",
      "Distract yourself until the feeling passes",
      "Create distance to feel safe, even if you don't want to",
    ],
  },
];

// ── SCORING MATRIX [question][option] → dimension score (0–100) ───────────────
const DIMENSION_SCORES = [
  [30, 90, 48, 22],  // Q0 Attachment: anxious/secure/avoidant/disorganized
  [62, 90, 40, 75],  // Q1 Emotional regulation
  [72, 82, 62, 68],  // Q2 Core values (all reasonable, type-tagged separately)
  [80, 90, 70, 28],  // Q3 Communication: direct/reflective/selective/avoidant
  [72, 88, 82, 24],  // Q4 Conflict
  [52, 88, 72, 82],  // Q5 Independence
  [90, 82, 62, 24],  // Q6 Vulnerability
  [42, 88, 72, 76],  // Q7 Reassurance
  [80, 88, 76, 72],  // Q8 Love language
  [80, 72, 40, 56],  // Q9 Growth mindset
  [90, 82, 52, 34],  // Q10 Openness
  [88, 88, 82, 52],  // Q11 Relationship goals
];

// Attachment adaptive refiners [attachment_answer][adaptive_answer] → score delta
const ADAPTIVE_DELTA = [
  [+14, +6, -6, -18],   // Anxious follow-ups
  [+5, 0, -4, -4],      // Secure follow-ups
  [-8, +14, -4, -10],   // Avoidant follow-ups
  [0, +20, +4, -4],     // Disorganized follow-ups
];

const ATTACHMENT_TYPES  = { 0: "anxious", 1: "secure", 2: "avoidant", 3: "disorganized" };
const VALUE_TYPES       = { 0: "growth", 1: "warmth", 2: "independence", 3: "adventure" };
const GOAL_TYPES        = { 0: "partnership", 1: "independence", 2: "secure_base", 3: "exploring" };
const COMM_TYPES        = { 0: "direct", 1: "reflective", 2: "selective", 3: "avoidant" };

const ATTACHMENT_LABELS = {
  secure: "🌿 Secure", anxious: "😟 Anxious-preoccupied",
  avoidant: "🏃 Dismissive-avoidant", disorganized: "🌀 Fearful-avoidant",
};
const ATTACHMENT_INSIGHTS = {
  secure: "You bring emotional stability and genuine availability to relationships. You're comfortable with both closeness and independence — one of the most compatible profiles for long-term partnership.",
  anxious: "You form deep bonds and care intensely. You do best with a secure partner who can provide consistency. Awareness of your patterns is already the biggest step toward more ease in relationships.",
  avoidant: "You value independence and need breathing room to feel safe. Self-aware avoidants who understand their patterns often build deeply fulfilling, lasting connections — especially with secure partners.",
  disorganized: "You experience relationships as both deeply desired and sometimes overwhelming. With the right partner and growing self-awareness, you can build the secure connection you're looking for.",
};

// ── COMPATIBILITY MATRICES ────────────────────────────────────────────────────
const ATTACH_ROMANCE = {
  secure:       { secure: 95, anxious: 78, avoidant: 72, disorganized: 58 },
  anxious:      { secure: 78, anxious: 44, avoidant: 18, disorganized: 30 },
  avoidant:     { secure: 72, anxious: 18, avoidant: 54, disorganized: 36 },
  disorganized: { secure: 58, anxious: 30, avoidant: 36, disorganized: 42 },
};
const ATTACH_FRIENDSHIP = {
  secure:       { secure: 92, anxious: 82, avoidant: 78, disorganized: 68 },
  anxious:      { secure: 82, anxious: 68, avoidant: 62, disorganized: 58 },
  avoidant:     { secure: 78, anxious: 62, avoidant: 72, disorganized: 64 },
  disorganized: { secure: 68, anxious: 58, avoidant: 64, disorganized: 60 },
};

// Weights per dimension for romance vs friendship (must sum to 1.0)
const W_ROMANCE    = [0.18, 0.10, 0.12, 0.08, 0.10, 0.07, 0.08, 0.07, 0.08, 0.04, 0.04, 0.04];
const W_FRIENDSHIP = [0.05, 0.08, 0.20, 0.14, 0.10, 0.08, 0.06, 0.03, 0.03, 0.11, 0.08, 0.04];

const DIM_COLORS = [
  "#7B2FBE","#9D4EDD","#E040FB","#00C9C8","#40FB82",
  "#7B2FBE","#9D4EDD","#E040FB","#00C9C8","#40FB82","#7B2FBE","#9D4EDD",
];
const DIM_LABELS = [
  "Attachment Style","Emotional Regulation","Core Values","Communication",
  "Conflict Approach","Independence Needs","Vulnerability","Reassurance Needs",
  "Love Language","Growth Mindset","Openness","Relationship Goals",
];

// ── PROFILE COMPUTATION ───────────────────────────────────────────────────────
function computeProfile(answers, adaptiveAnswer, intensities, adaptiveIntensity) {
  function applyIntensity(rawScore, level) {
    const mid = 50, mult = [0.4, 1.0, 1.35][level ?? 1];
    return Math.max(5, Math.min(98, Math.round(mid + mult * (rawScore - mid))));
  }
  const dims = DIM_LABELS.map((label, i) => {
    const ans = answers[i] ?? null;
    const raw = ans !== null ? DIMENSION_SCORES[i][ans] : 60;
    const score = ans !== null ? applyIntensity(raw, intensities?.[i]) : 60;
    return { label, score, color: DIM_COLORS[i] };
  });

  const a0 = answers[0] ?? 1;
  if (adaptiveAnswer !== null && ADAPTIVE_DELTA[a0]) {
    const baseDelta = ADAPTIVE_DELTA[a0][adaptiveAnswer] ?? 0;
    const scaledDelta = Math.round(baseDelta * [0.4, 1.0, 1.35][adaptiveIntensity ?? 1]);
    dims[0].score = Math.max(5, Math.min(98, dims[0].score + scaledDelta));
  }

  return {
    dimensions: dims,
    attachmentType: ATTACHMENT_TYPES[a0] || "secure",
    valueType:  VALUE_TYPES[answers[2] ?? 1] || "warmth",
    goalType:   GOAL_TYPES[answers[11] ?? 0] || "partnership",
    commType:   COMM_TYPES[answers[3] ?? 1] || "reflective",
    overall:    Math.round(dims.reduce((a, d) => a + d.score, 0) / dims.length),
  };
}

function computeCompatibility(pA, pB, mode) {
  const matrix = mode === "romance" ? ATTACH_ROMANCE : ATTACH_FRIENDSHIP;
  const weights = mode === "romance" ? W_ROMANCE : W_FRIENDSHIP;
  const atA = pA.attachmentType || "secure";
  const atB = pB.attachmentType || "secure";
  const attachScore = matrix[atA]?.[atB] ?? 65;

  let total = weights[0] * attachScore;
  for (let i = 1; i < 12; i++) {
    const sA = pA.dimensions[i]?.score ?? 65;
    const sB = pB.dimensions[i]?.score ?? 65;
    total += weights[i] * (100 - Math.abs(sA - sB));
  }
  return Math.round(Math.min(99, Math.max(10, total)));
}

function getMatchHighlights(pA, pB, mode) {
  const out = [];
  const atA = pA.attachmentType, atB = pB.attachmentType;

  if (mode === "romance") {
    if (atA === "secure" || atB === "secure") out.push("Complementary attachment styles");
    else if (atA === atB) out.push("Similar attachment patterns");
    const valDiff = Math.abs((pA.dimensions[2]?.score ?? 65) - (pB.dimensions[2]?.score ?? 65));
    if (valDiff < 15) out.push("Deep values alignment");
    const goalDiff = Math.abs((pA.dimensions[11]?.score ?? 70) - (pB.dimensions[11]?.score ?? 70));
    if (goalDiff < 15) out.push("Aligned relationship goals");
    const confDiff = Math.abs((pA.dimensions[4]?.score ?? 70) - (pB.dimensions[4]?.score ?? 70));
    if (confDiff < 15) out.push("Compatible conflict approach");
    const vulnAvg = ((pA.dimensions[6]?.score ?? 65) + (pB.dimensions[6]?.score ?? 65)) / 2;
    if (vulnAvg > 70) out.push("Both open to emotional depth");
  } else {
    const valDiff = Math.abs((pA.dimensions[2]?.score ?? 65) - (pB.dimensions[2]?.score ?? 65));
    if (valDiff < 15) out.push("Shared core values");
    const commDiff = Math.abs((pA.dimensions[3]?.score ?? 70) - (pB.dimensions[3]?.score ?? 70));
    if (commDiff < 15) out.push("Natural communication rhythm");
    const growthAvg = ((pA.dimensions[9]?.score ?? 65) + (pB.dimensions[9]?.score ?? 65)) / 2;
    if (growthAvg > 72) out.push("Great accountability partners");
    const openDiff = Math.abs((pA.dimensions[10]?.score ?? 65) - (pB.dimensions[10]?.score ?? 65));
    if (openDiff < 15) out.push("Matched openness to experience");
    const indDiff = Math.abs((pA.dimensions[5]?.score ?? 70) - (pB.dimensions[5]?.score ?? 70));
    if (indDiff < 15) out.push("Compatible independence needs");
  }

  if (out.length < 3) out.push("Strong overall psychological fit");
  return out.slice(0, 3);
}

// ── DEMO PROFILES (for demo mode when no real matches) ────────────────────────
const DEMO_PROFILES = [
  { id: "1", name: "Zara M.", city: "Toronto, ON", avatar: "Z",
    attachmentType: "secure", valueType: "warmth", goalType: "partnership", commType: "reflective",
    dimensions: DIM_LABELS.map((label, i) => ({ label, color: DIM_COLORS[i], score: [88,82,90,78,85,76,80,84,88,85,80,90][i] })) },
  { id: "2", name: "Jordan K.", city: "Toronto, ON", avatar: "J",
    attachmentType: "secure", valueType: "growth", goalType: "independence", commType: "direct",
    dimensions: DIM_LABELS.map((label, i) => ({ label, color: DIM_COLORS[i], score: [85,76,82,88,80,85,70,76,72,90,88,82][i] })) },
  { id: "3", name: "Sofia T.", city: "Toronto, ON", avatar: "S",
    attachmentType: "anxious", valueType: "warmth", goalType: "partnership", commType: "reflective",
    dimensions: DIM_LABELS.map((label, i) => ({ label, color: DIM_COLORS[i], score: [44,68,85,72,68,58,85,42,88,70,72,88][i] })) },
  { id: "4", name: "Alex R.", city: "Toronto, ON", avatar: "A",
    attachmentType: "avoidant", valueType: "independence", goalType: "secure_base", commType: "selective",
    dimensions: DIM_LABELS.map((label, i) => ({ label, color: DIM_COLORS[i], score: [52,78,68,72,76,88,55,72,68,80,90,80][i] })) },
  { id: "5", name: "Maya P.", city: "Toronto, ON", avatar: "M",
    attachmentType: "secure", valueType: "adventure", goalType: "exploring", commType: "direct",
    dimensions: DIM_LABELS.map((label, i) => ({ label, color: DIM_COLORS[i], score: [90,80,68,85,72,80,82,78,76,85,92,52][i] })) },
  { id: "6", name: "Riley C.", city: "Toronto, ON", avatar: "R",
    attachmentType: "secure", valueType: "growth", goalType: "partnership", commType: "reflective",
    dimensions: DIM_LABELS.map((label, i) => ({ label, color: DIM_COLORS[i], score: [88,88,90,82,85,72,78,80,80,92,80,88][i] })) },
];

function getDemoMatches(userProfile, mode) {
  return DEMO_PROFILES.map(p => ({
    ...p,
    score: computeCompatibility(userProfile, p, mode),
    highlights: getMatchHighlights(userProfile, p, mode),
  })).sort((a, b) => b.score - a.score);
}

// ── PLACE FALLBACK ─────────────────────────────────────────────────────────────
const PLACE_FALLBACK = [
  { id: "toronto",   label: "Toronto, Ontario, Canada",      latitude: 43.6532,  longitude: -79.3832  },
  { id: "vancouver", label: "Vancouver, BC, Canada",         latitude: 49.2827,  longitude: -123.1207 },
  { id: "montreal",  label: "Montreal, QC, Canada",          latitude: 45.5017,  longitude: -73.5673  },
  { id: "new-york",  label: "New York City, NY, USA",        latitude: 40.7128,  longitude: -74.006   },
  { id: "london",    label: "London, England, UK",           latitude: 51.5074,  longitude: -0.1278   },
  { id: "sydney",    label: "Sydney, NSW, Australia",        latitude: -33.8688, longitude: 151.2093  },
  { id: "berlin",    label: "Berlin, Germany",               latitude: 52.52,    longitude: 13.405    },
  { id: "paris",     label: "Paris, France",                 latitude: 48.8566,  longitude: 2.3522    },
  { id: "singapore", label: "Singapore",                     latitude: 1.3521,   longitude: 103.8198  },
  { id: "tokyo",     label: "Tokyo, Japan",                  latitude: 35.6762,  longitude: 139.6503  },
];
function safeTimezone(lat, lon) { try { return tzLookup(lat, lon); } catch (_) { return ""; } }
function buildPlaceFallback(query, limit = 6) {
  const q = (query || "").toLowerCase();
  const r = PLACE_FALLBACK.filter(p => !q || p.label.toLowerCase().includes(q)).slice(0, limit);
  return (r.length ? r : PLACE_FALLBACK.slice(0, limit)).map(p => ({
    ...p, timezone: safeTimezone(p.latitude, p.longitude),
  }));
}

// ── API HELPERS ────────────────────────────────────────────────────────────────
async function apiRequest(method, path, payload, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      method, headers, body: payload ? JSON.stringify(payload) : undefined,
    });
    let body = null;
    try { body = await res.json(); } catch (_) {}
    return { ok: res.ok, status: res.status, body };
  } catch (e) {
    const err = new Error(`network_error: ${e?.message || "failed"}`);
    err.status = 0; throw err;
  }
}
function normalizeError(x, fallback = "Something went wrong") {
  if (!x) return fallback;
  if (x instanceof Error) return x.message || fallback;
  const d = x.detail ?? x.error ?? x.message;
  if (typeof d === "string" && d.trim()) return d;
  if (Array.isArray(d)) return d.map(i => (typeof i === "string" ? i : i?.msg || "invalid")).join("; ");
  return fallback;
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
  return /^([01]\d|2[0-3]):([0-5]\d)$/.test(v) ? "" : "Use HH:MM format (24h)";
}

// ── SHARED UI ──────────────────────────────────────────────────────────────────
function GradBtn({ label, onPress, disabled, style }) {
  return (
    <TouchableOpacity onPress={onPress} disabled={disabled} style={[{ opacity: disabled ? 0.4 : 1 }, style]}>
      <LinearGradient colors={["#4E8B5F", "#7DB87D"]} start={[0, 0]} end={[1, 0]} style={s.gradBtn}>
        <Text style={s.gradBtnTxt}>{label}</Text>
      </LinearGradient>
    </TouchableOpacity>
  );
}
function GhostBtn({ label, onPress, disabled, style, danger }) {
  return (
    <TouchableOpacity onPress={onPress} disabled={disabled}
      style={[s.ghostBtn, disabled && { opacity: 0.4 }, danger && { borderColor: C.error }, style]}>
      <Text style={[s.ghostBtnTxt, danger && { color: C.error }]}>{label}</Text>
    </TouchableOpacity>
  );
}
function Badge({ label, color = C.teal }) {
  return (
    <View style={[s.badge, { borderColor: color + "44", backgroundColor: color + "18" }]}>
      <Text style={[s.badgeTxt, { color }]}>{label}</Text>
    </View>
  );
}
function DimBar({ label, score, color }) {
  return (
    <View style={s.dimRow}>
      <Text style={s.dimLabel} numberOfLines={1}>{label}</Text>
      <View style={s.dimBg}><View style={[s.dimFill, { width: `${Math.min(100, score)}%`, backgroundColor: color }]} /></View>
      <Text style={s.dimPct}>{score}%</Text>
    </View>
  );
}
function Hdr({ title, subtitle, onBack, rightLabel, onRight }) {
  return (
    <View style={s.hdr}>
      {onBack && (
        <TouchableOpacity onPress={onBack} style={s.backBtn}>
          <Text style={s.backIcon}>←</Text>
        </TouchableOpacity>
      )}
      <View style={{ flex: 1 }}>
        <Text style={s.hdrTitle}>{title}</Text>
        {subtitle ? <Text style={s.hdrSub}>{subtitle}</Text> : null}
      </View>
      {onRight && (
        <TouchableOpacity onPress={onRight} style={s.hdrRight}>
          <Text style={s.hdrRightTxt}>{rightLabel || "⋯"}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

// ── 1. SPLASH ──────────────────────────────────────────────────────────────────
function SplashScreen({ onDone }) {
  const fade  = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(0.82)).current;
  useEffect(() => {
    Animated.parallel([
      Animated.timing(fade,  { toValue: 1, duration: 800, useNativeDriver: true }),
      Animated.spring(scale, { toValue: 1, tension: 60, friction: 8, useNativeDriver: true }),
    ]).start();
    const t = setTimeout(onDone, 2200);
    return () => clearTimeout(t);
  }, []);
  return (
    <LinearGradient colors={["#0D1409", "#101C0C", "#142010"]} style={s.fill}>
      <StatusBar style="light" />
      <Animated.View style={[s.splashCenter, { opacity: fade, transform: [{ scale }] }]}>
        <LinearGradient colors={["#4E8B5F", "#7DB87D"]} style={s.splashLogoBox}>
          <Text style={s.splashLogoIcon}>✦</Text>
        </LinearGradient>
        <Text style={s.splashWordmark}>SoulMatch</Text>
        <Text style={s.splashTagline}>Know yourself.{"\n"}Find your match.</Text>
      </Animated.View>
      <View style={s.splashDots}>
        {[C.purple, C.violet, C.pink].map((c, i) => (
          <View key={i} style={[s.dot, { backgroundColor: c }]} />
        ))}
      </View>
    </LinearGradient>
  );
}

// ── 2. LOGIN ───────────────────────────────────────────────────────────────────
function LoginScreen({ onLogin, onGoRegister, error, busy }) {
  const [email, setEmail]     = useState("");
  const [password, setPass]   = useState("");
  return (
    <LinearGradient colors={["#0D1409", "#121C0E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={s.fill}>
          <ScrollView contentContainerStyle={s.authScroll} keyboardShouldPersistTaps="handled">
            <View style={s.authTop}>
              <Text style={s.wordmark}>✦ SoulMatch</Text>
              <Badge label="Beta · Toronto" color={C.teal} />
            </View>
            <Text style={s.authTitle}>Welcome back</Text>
            <Text style={s.authSub}>Sign in to continue</Text>
            <View style={s.formCard}>
              <Text style={s.inputLabel}>Email</Text>
              <TextInput style={s.input} placeholder="your@email.com" placeholderTextColor={C.muted} value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" />
              <Text style={s.inputLabel}>Password</Text>
              <TextInput style={s.input} placeholder="Your password" placeholderTextColor={C.muted} value={password} onChangeText={setPass} secureTextEntry autoCapitalize="none" />
              <TouchableOpacity><Text style={s.forgotLink}>Forgot password?</Text></TouchableOpacity>
            </View>
            {error ? <Text style={s.errMsg}>{error}</Text> : null}
            <GradBtn label={busy ? "Signing in…" : "Sign in →"} onPress={() => onLogin(email, password)} disabled={!email || !password || busy} style={{ marginTop: 8 }} />
            <TouchableOpacity onPress={onGoRegister} style={s.switchLink}>
              <Text style={s.switchLinkTxt}>New here? <Text style={{ color: C.violet }}>Create account →</Text></Text>
            </TouchableOpacity>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 3. REGISTRATION (4-step) ───────────────────────────────────────────────────
function RegisterScreen({ onComplete, onGoLogin, error, busy }) {
  const [step, setStep]         = useState(0);
  const [name, setName]         = useState("");
  const [email, setEmail]       = useState("");
  const [password, setPass]     = useState("");
  const [birthDate, setBD]      = useState("");
  const [birthTime, setBT]      = useState("");
  const [placeQuery, setPQ]     = useState("");
  const [placeResults, setPR]   = useState([]);
  const [placeLoading, setPL]   = useState(false);
  const [selectedPlace, setSP]  = useState(null);
  const [romance, setRomance]   = useState(true);
  const [friendship, setFriend] = useState(true);
  const [pref, setPref]         = useState("psych_behavior_astro");
  const [consentP, setCP]       = useState(false);
  const [consentS, setCS]       = useState(false);
  const [fieldErr, setFE]       = useState("");
  const STEPS = ["Basics", "Birth data", "Goals", "Consent"];

  async function searchPlace() {
    if (!placeQuery.trim()) return;
    setPL(true); setFE("");
    try {
      const res = await fetch(`${API_BASE_URL}/places/search`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: placeQuery.trim(), limit: 6 }),
      });
      const data = res.ok ? await res.json() : null;
      const mapped = (data?.results || []).map(p => ({ ...p, timezone: safeTimezone(+p.latitude, +p.longitude) }));
      setPR(mapped.length ? mapped : buildPlaceFallback(placeQuery));
    } catch (_) { setPR(buildPlaceFallback(placeQuery)); }
    finally { setPL(false); }
  }

  function canAdvance() {
    if (step === 0) return name.trim() && email.trim() && password.trim().length >= 8;
    if (step === 1) return birthDate.trim() && birthTime.trim() && selectedPlace;
    if (step === 2) return romance || friendship;
    return consentP && consentS;
  }
  function advance() {
    if (step === 1) {
      const de = validateDate(birthDate.trim()), te = validateTime(birthTime.trim());
      if (de || te) { setFE(de || te); return; }
    }
    if (step < 3) { setStep(s => s + 1); setFE(""); return; }
    const goals = [romance && "romance", friendship && "friendship"].filter(Boolean);
    onComplete({ name, email, password, birthDate, birthTime, selectedPlace, goals, pref, consentP, consentS });
  }

  return (
    <LinearGradient colors={["#0D1409", "#121C0E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={s.fill}>
          <ScrollView contentContainerStyle={s.authScroll} keyboardShouldPersistTaps="handled">
            <View style={s.authTop}><Text style={s.wordmark}>✦ SoulMatch</Text></View>
            {/* Step dots */}
            <View style={s.stepDots}>
              {STEPS.map((_, i) => (
                <View key={i} style={s.stepDotWrap}>
                  <View style={[s.stepDot, i <= step && s.stepDotActive, i === step && s.stepDotCur]}>
                    <Text style={[s.stepDotNum, i <= step && { color: "#fff" }]}>{i + 1}</Text>
                  </View>
                  {i < STEPS.length - 1 && <View style={[s.stepLine, i < step && s.stepLineActive]} />}
                </View>
              ))}
            </View>
            <Text style={s.stepLabel}>{STEPS[step]}</Text>

            {step === 0 && (
              <View style={s.formCard}>
                <Text style={s.inputLabel}>Your name</Text>
                <TextInput style={s.input} placeholder="First name" placeholderTextColor={C.muted} value={name} onChangeText={setName} />
                <Text style={s.inputLabel}>Email</Text>
                <TextInput style={s.input} placeholder="your@email.com" placeholderTextColor={C.muted} value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" />
                <Text style={s.inputLabel}>Password</Text>
                <TextInput style={s.input} placeholder="Min 8 characters" placeholderTextColor={C.muted} value={password} onChangeText={setPass} secureTextEntry autoCapitalize="none" />
              </View>
            )}

            {step === 1 && (
              <View style={s.formCard}>
                <Text style={s.formNote}>Used for the optional astrology layer. Psychology matching works without it.</Text>
                <Text style={s.inputLabel}>Birth date</Text>
                <TextInput style={s.input} placeholder="YYYY-MM-DD" placeholderTextColor={C.muted} value={birthDate} onChangeText={v => { setBD(v); setFE(""); }} />
                <Text style={s.inputLabel}>Birth time (24h)</Text>
                <TextInput style={s.input} placeholder="HH:MM" placeholderTextColor={C.muted} value={birthTime} onChangeText={v => { setBT(v); setFE(""); }} />
                <Text style={s.inputLabel}>Birth city</Text>
                <View style={s.searchRow}>
                  <TextInput style={[s.input, { flex: 1 }]} placeholder="City, Country" placeholderTextColor={C.muted} value={placeQuery} onChangeText={setPQ} />
                  <TouchableOpacity style={s.searchBtn} onPress={searchPlace} disabled={placeLoading}>
                    <Text style={s.searchBtnTxt}>{placeLoading ? "…" : "Search"}</Text>
                  </TouchableOpacity>
                </View>
                {placeResults.map(p => (
                  <TouchableOpacity key={p.id} style={[s.placeCard, selectedPlace?.id === p.id && s.placeCardSel]} onPress={() => setSP(p)}>
                    <Text style={s.placeLabel}>{p.label}</Text>
                    <Text style={s.placeMeta}>{p.timezone || "—"}</Text>
                  </TouchableOpacity>
                ))}
                {selectedPlace && <View style={s.selPlaceBox}><Text style={s.selPlaceTxt}>✓ {selectedPlace.label}</Text></View>}
                {fieldErr ? <Text style={s.errMsg}>{fieldErr}</Text> : null}
              </View>
            )}

            {step === 2 && (
              <View style={s.formCard}>
                <Text style={s.inputLabel}>I'm looking for</Text>
                <View style={s.toggleRow}>
                  <View style={{ flex: 1 }}><Text style={s.body}>💕 Romance</Text><Text style={s.muted}>Romantic partnership</Text></View>
                  <Switch value={romance} onValueChange={setRomance} trackColor={{ true: C.violet }} thumbColor="#fff" />
                </View>
                <View style={s.toggleRow}>
                  <View style={{ flex: 1 }}><Text style={s.body}>🤝 Friendship</Text><Text style={s.muted}>Meaningful connections</Text></View>
                  <Switch value={friendship} onValueChange={setFriend} trackColor={{ true: C.teal }} thumbColor="#fff" />
                </View>
                <Text style={[s.inputLabel, { marginTop: 16 }]}>Matching method</Text>
                {[
                  { val: "psych_behavior", title: "Psychology + Behaviour", sub: "Core compatibility. No astrology." },
                  { val: "psych_behavior_astro", title: "Psychology + Behaviour + Astrology", sub: "Full picture including your birth chart." },
                ].map(opt => (
                  <TouchableOpacity key={opt.val} style={[s.prefCard, pref === opt.val && s.prefCardSel]} onPress={() => setPref(opt.val)}>
                    <View style={[s.prefDot, pref === opt.val && s.prefDotSel]} />
                    <View style={{ flex: 1 }}>
                      <Text style={s.prefTitle}>{opt.title}</Text>
                      <Text style={s.prefSub}>{opt.sub}</Text>
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            )}

            {step === 3 && (
              <View style={s.formCard}>
                <Text style={s.formNote}>Before we create your profile, we need your consent for how we store your data.</Text>
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

            {error ? <Text style={s.errMsg}>{error}</Text> : null}
            <View style={s.btnRow}>
              {step > 0 ? <GhostBtn label="Back" onPress={() => setStep(s => s - 1)} style={{ flex: 1 }} />
                        : <GhostBtn label="Sign in instead" onPress={onGoLogin} style={{ flex: 1 }} />}
              <GradBtn label={step === 3 ? (busy ? "Creating…" : "Create account") : "Continue →"} onPress={advance} disabled={!canAdvance() || busy} style={{ flex: 2 }} />
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 4. ASSESSMENT (adaptive flow) ─────────────────────────────────────────────
function AssessmentScreen({ onComplete, onSkip }) {
  const [phase, setPhase]                = useState("main"); // "main" | "adaptive"
  const [qIdx, setQIdx]                  = useState(0);
  const [answers, setAnswers]            = useState({});
  const [adaptiveAns, setAdaptive]       = useState(null);
  const [selected, setSel]               = useState(null);
  const [selIntensity, setSelInt]        = useState(null);
  const [intensities, setIntensities]    = useState({});
  const [adaptiveIntensity, setAdaptInt] = useState(null);
  const fade = useRef(new Animated.Value(1)).current;

  const isAdaptive = phase === "adaptive";
  const q = isAdaptive ? ADAPTIVE_QUESTIONS[answers[0] ?? 0] : QUESTIONS[qIdx];

  // Step numbering: Q0=0, adaptive=1, Q1=2, Q2=3, … Q11=12  → 13 total steps
  let stepNum = 0;
  if (isAdaptive) stepNum = 1;
  else if (qIdx > 0) stepNum = qIdx + 1;
  const progress = (stepNum / 12) * 100;
  const totalLabel = `${stepNum + 1} / 13`;

  function animNext(fn) {
    Animated.timing(fade, { toValue: 0, duration: 140, useNativeDriver: true }).start(() => {
      fn();
      Animated.timing(fade, { toValue: 1, duration: 220, useNativeDriver: true }).start();
    });
  }

  function advanceWithLevel(level) {
    if (selected === null) return;
    if (!isAdaptive && qIdx === 0) {
      setAnswers(prev => ({ ...prev, 0: selected }));
      setIntensities(prev => ({ ...prev, 0: level }));
      animNext(() => { setPhase("adaptive"); setSel(null); setSelInt(null); });
      return;
    }
    if (isAdaptive) {
      setAdaptive(selected);
      setAdaptInt(level);
      animNext(() => { setPhase("main"); setQIdx(1); setSel(null); setSelInt(null); });
      return;
    }
    const next = { ...answers, [qIdx]: selected };
    const nextInt = { ...intensities, [qIdx]: level };
    setAnswers(next);
    setIntensities(nextInt);
    if (qIdx === QUESTIONS.length - 1) {
      onComplete(next, adaptiveAns, nextInt, level);
      return;
    }
    animNext(() => { setQIdx(i => i + 1); setSel(null); setSelInt(null); });
  }

  function advance() {
    if (selIntensity !== null) advanceWithLevel(selIntensity);
  }

  function goBack() {
    if (isAdaptive) {
      animNext(() => { setPhase("main"); setQIdx(0); setSel(answers[0] ?? null); setSelInt(intensities[0] ?? null); });
      return;
    }
    if (qIdx === 1) {
      animNext(() => { setPhase("adaptive"); setSel(adaptiveAns); setSelInt(adaptiveIntensity); });
      return;
    }
    if (qIdx > 0) {
      animNext(() => { setQIdx(i => i - 1); setSel(answers[qIdx - 1] ?? null); setSelInt(intensities[qIdx - 1] ?? null); });
    }
  }

  const canGoBack = isAdaptive || qIdx > 0;

  return (
    <LinearGradient colors={["#0D1409", "#101C0C"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <View style={s.assessHdr}>
          <TouchableOpacity onPress={onSkip}><Text style={s.skipTxt}>Skip</Text></TouchableOpacity>
          <Text style={s.assessCount}>{totalLabel}</Text>
        </View>
        <View style={s.progressBg}><View style={[s.progressFill, { width: `${progress}%` }]} /></View>

        <ScrollView contentContainerStyle={s.assessBody} keyboardShouldPersistTaps="handled">
          <Animated.View style={{ opacity: fade }}>
            {isAdaptive && (
              <View style={s.adaptiveBanner}>
                <Text style={s.adaptiveBannerTxt}>✦ Follow-up based on your previous answer</Text>
              </View>
            )}
            <View style={s.dimBadge}>
              <Text style={s.dimBadgeEmoji}>{q.emoji}</Text>
              <Text style={s.dimBadgeLbl}>{q.dimension}</Text>
            </View>
            <Text style={s.assessQ}>{q.question}</Text>
            <View style={s.options}>
              {q.options.map((opt, i) => (
                <TouchableOpacity
                  key={i}
                  style={[s.optCard, selected === i && s.optCardSel, selected !== null && selected !== i && s.optCardDim]}
                  onPress={() => { setSel(i); if (i !== selected) setSelInt(null); }}
                  activeOpacity={0.75}
                >
                  <View style={[s.optDot, selected === i && s.optDotSel]}>
                    {selected === i && <Text style={s.optCheck}>✓</Text>}
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={[s.optTxt, selected === i && s.optTxtSel]}>{opt}</Text>
                    {selected === i && (
                      <View style={s.intRow}>
                        <Text style={s.intRowLabel}>How much does this fit?</Text>
                        <View style={s.intBtns}>
                          {['A little', 'Mostly', 'Exactly me'].map((lbl, level) => (
                            <TouchableOpacity
                              key={level}
                              style={[s.intBtn, selIntensity === level && s.intBtnActive]}
                              onPress={() => { setSelInt(level); setTimeout(() => advanceWithLevel(level), 200); }}
                              activeOpacity={0.75}
                            >
                              <Text style={[s.intBtnTxt, selIntensity === level && s.intBtnTxtActive]}>{lbl}</Text>
                            </TouchableOpacity>
                          ))}
                        </View>
                      </View>
                    )}
                  </View>
                </TouchableOpacity>
              ))}
            </View>
          </Animated.View>
        </ScrollView>

        <View style={s.assessFooter}>
          {canGoBack && <GhostBtn label="← Back" onPress={goBack} style={{ flex: 1 }} />}
          <GradBtn
            label={!isAdaptive && qIdx === QUESTIONS.length - 1 ? "Complete →" : "Next →"}
            onPress={advance}
            disabled={selected === null || selIntensity === null}
            style={{ flex: canGoBack ? 2 : 1 }}
          />
        </View>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 5. PROFILE ─────────────────────────────────────────────────────────────────
function ProfileScreen({ user, profile, assessed, onAssess, onReports, onMatches, onSettings }) {
  const initials = (user?.name || "U").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  const dims = profile?.dimensions || [];

  return (
    <LinearGradient colors={["#0D1409", "#121C0E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <ScrollView contentContainerStyle={s.profileScroll}>
          <View style={s.profileHdr}>
            <Text style={s.wordmark}>✦ SoulMatch</Text>
            <TouchableOpacity onPress={onSettings}><Text style={{ fontSize: 22 }}>⚙️</Text></TouchableOpacity>
          </View>
          <View style={s.avatarWrap}>
            <LinearGradient colors={["#4E8B5F", "#7DB87D"]} style={s.avatar}>
              <Text style={s.avatarTxt}>{initials}</Text>
            </LinearGradient>
            {assessed && profile && (
              <View style={s.avatarBadge}>
                <Text style={s.avatarBadgeTxt}>{profile.overall}%</Text>
              </View>
            )}
          </View>
          <Text style={s.profileName}>{user?.name || "Your profile"}</Text>
          <Text style={s.profileEmail}>{user?.email || ""}</Text>
          {assessed && profile ? (
            <Badge label={ATTACHMENT_LABELS[profile.attachmentType] || "Assessed"} color={C.violet} />
          ) : (
            <Badge label="Assessment pending" color={C.gold} />
          )}

          <View style={s.profileActions}>
            {[
              { icon: "💕", label: "Matches",   fn: onMatches },
              { icon: "📊", label: "My report", fn: onReports },
              { icon: "🧠", label: assessed ? "Retake" : "Assess", fn: onAssess },
            ].map(a => (
              <TouchableOpacity key={a.label} style={s.profileAction} onPress={a.fn}>
                <Text style={{ fontSize: 26 }}>{a.icon}</Text>
                <Text style={s.profileActionLbl}>{a.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {assessed && dims.length > 0 ? (
            <View style={s.card}>
              <Text style={s.cardTitle}>Your psychological profile</Text>
              {dims.map((d, i) => <DimBar key={i} label={d.label} score={d.score} color={d.color} />)}
            </View>
          ) : (
            <View style={s.emptyCard}>
              <Text style={{ fontSize: 44 }}>🧠</Text>
              <Text style={s.emptyTitle}>Take the assessment</Text>
              <Text style={s.emptySub}>12 questions + 1 adaptive follow-up. Takes about 4 minutes. Unlocks your matches and full psychological report.</Text>
              <GradBtn label="Start assessment →" onPress={onAssess} style={{ marginTop: 16 }} />
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 6. DISCOVERY ───────────────────────────────────────────────────────────────
function DiscoveryScreen({ matches, mode, onModeChange, onViewMatch, onProfile, busy, userProfile }) {
  const list = matches.length ? matches
    : (userProfile ? getDemoMatches(userProfile, mode) : []);
  const isDemo = !matches.length;

  const modeDesc = {
    romance:    "Scored on attachment, vulnerability, love language & values",
    friendship: "Scored on values, communication, growth mindset & openness",
  };

  return (
    <LinearGradient colors={["#0D1409", "#121C0E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <View style={s.discHdr}>
          <TouchableOpacity onPress={onProfile} style={s.discAvatarBtn}>
            <Text style={{ fontSize: 20 }}>👤</Text>
          </TouchableOpacity>
          <Text style={s.wordmark}>✦ SoulMatch</Text>
          <View style={{ width: 40 }} />
        </View>

        {/* Mode toggle */}
        <View style={s.modePill}>
          {[
            { key: "romance",    label: "💕  Romance" },
            { key: "friendship", label: "🤝  Friendship" },
          ].map(m => (
            <TouchableOpacity key={m.key} style={[s.modeBtn, mode === m.key && s.modeBtnActive]} onPress={() => onModeChange(m.key)}>
              <Text style={[s.modeBtnTxt, mode === m.key && s.modeBtnTxtActive]}>{m.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <Text style={s.modeSubtitle}>{modeDesc[mode]}</Text>

        {isDemo && (
          <View style={s.demoBanner}>
            <Text style={s.demoBannerTxt}>✦ Demo matches — your actual matches unlock after completing the assessment</Text>
          </View>
        )}

        {busy ? (
          <View style={s.centerFill}><Text style={s.muted}>Finding your matches…</Text></View>
        ) : (
          <FlatList
            data={list}
            keyExtractor={m => m.id}
            contentContainerStyle={s.matchList}
            showsVerticalScrollIndicator={false}
            renderItem={({ item: m }) => (
              <View style={s.matchCard}>
                <View style={s.matchCardTop}>
                  <LinearGradient colors={["#4E8B5F", "#7DB87D"]} style={s.matchAvatar}>
                    <Text style={s.matchAvatarTxt}>{m.avatar || m.name[0]}</Text>
                  </LinearGradient>
                  <View style={{ flex: 1 }}>
                    <Text style={s.matchName}>{m.name}</Text>
                    <Text style={s.matchCity}>📍 {m.city}</Text>
                  </View>
                  <View style={s.scoreBadge}>
                    <Text style={s.scoreNum}>{Math.round(m.score)}%</Text>
                    <Text style={s.scoreLbl}>{mode === "romance" ? "romantic" : "friendship"}</Text>
                  </View>
                </View>
                <View style={s.highlights}>
                  {(m.highlights || []).map((h, i) => (
                    <View key={i} style={s.highlightPill}>
                      <Text style={s.highlightTxt}>✓ {h}</Text>
                    </View>
                  ))}
                </View>
                <View style={s.matchActions}>
                  <GhostBtn label="View profile" onPress={() => onViewMatch(m, mode)} style={{ flex: 1 }} />
                  <GradBtn  label="Message →"    onPress={() => onViewMatch(m, mode)} style={{ flex: 1 }} />
                </View>
              </View>
            )}
          />
        )}
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 7. MATCH DETAIL ────────────────────────────────────────────────────────────
function MatchDetailScreen({ match: m, userProfile, mode, onBack, onChat, onBlock, onReport }) {
  if (!m) return null;
  const dims = userProfile?.dimensions || m.dimensions;

  const modeColor = mode === "romance" ? C.pink : C.teal;
  const modeLabel = mode === "romance" ? "Romantic compatibility" : "Friendship compatibility";

  return (
    <LinearGradient colors={["#0D1409", "#121C0E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <Hdr title={m.name} subtitle={`📍 ${m.city}`} onBack={onBack} />
        <ScrollView contentContainerStyle={s.detailScroll}>
          <View style={s.detailHero}>
            <LinearGradient colors={["#4E8B5F", "#7DB87D"]} style={s.detailAvatar}>
              <Text style={s.detailAvatarTxt}>{m.avatar || m.name[0]}</Text>
            </LinearGradient>
            <View style={[s.detailScoreBox, { borderColor: modeColor + "44", backgroundColor: modeColor + "12" }]}>
              <Text style={[s.detailScoreNum, { color: modeColor }]}>{Math.round(m.score)}%</Text>
              <Text style={[s.detailScoreLbl, { color: modeColor }]}>{modeLabel}</Text>
            </View>
          </View>

          {/* Attachment type badge for match */}
          {m.attachmentType && (
            <View style={{ alignItems: "center", marginBottom: 8 }}>
              <Badge label={`Their style: ${ATTACHMENT_LABELS[m.attachmentType] || m.attachmentType}`} color={C.violet} />
            </View>
          )}

          <View style={s.card}>
            <Text style={s.cardTitle}>Why you {mode === "romance" ? "connect romantically" : "make great friends"}</Text>
            {(m.highlights || []).map((h, i) => (
              <View key={i} style={s.detailHighlight}>
                <Text style={{ color: C.violet, fontSize: 14 }}>✦</Text>
                <Text style={s.detailHighlightTxt}>{h}</Text>
              </View>
            ))}
          </View>

          <View style={s.card}>
            <Text style={s.cardTitle}>Compatibility breakdown</Text>
            <Text style={s.cardSub}>Your combined psychological profiles</Text>
            {dims.map((d, i) => {
              const matchScore = m.dimensions?.[i]?.score ?? 70;
              const compat = Math.round(100 - Math.abs(d.score - matchScore) * 0.8);
              return <DimBar key={i} label={d.label} score={compat} color={d.color} />;
            })}
          </View>

          <GradBtn label="Start conversation →" onPress={() => onChat(m)} style={{ marginBottom: 12 }} />
          <GhostBtn label="Not interested" onPress={onBack} />
          <View style={s.safetyRow}>
            <TouchableOpacity onPress={() => onBlock?.(m)} style={s.safetyBtn}>
              <Text style={s.safetyTxt}>🚫 Block</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => onReport?.(m)} style={s.safetyBtn}>
              <Text style={s.safetyTxt}>⚑ Report</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 8. CHAT ────────────────────────────────────────────────────────────────────
function ChatScreen({ match: m, messages, onSend, onBack, onBlock, onReport }) {
  const [text, setText] = useState("");
  const listRef = useRef(null);
  const msgs = messages?.length ? messages : [
    { id: "0", text: "Hey! I saw we matched. Your profile was really interesting to read through 🙂", from: "them", ts: "10:24" },
    { id: "1", text: "The shared values dimension especially — I don't often find that so clearly.", from: "them", ts: "10:25" },
  ];

  function send() {
    if (!text.trim()) return;
    onSend(m.id, text.trim());
    setText("");
  }

  return (
    <LinearGradient colors={["#0D1409", "#121C0E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <Hdr
          title={m?.name || "Chat"}
          subtitle={`${Math.round(m?.score || 0)}% compatible`}
          onBack={onBack}
          rightLabel="⋯"
          onRight={() => Alert.alert(
            m?.name || "User",
            "What would you like to do?",
            [
              { text: "Block this person", style: "destructive", onPress: () => onBlock?.(m) },
              { text: "Report this person", style: "destructive", onPress: () => onReport?.(m) },
              { text: "Cancel", style: "cancel" },
            ]
          )}
        />
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
                    <LinearGradient colors={["#4E8B5F", "#7DB87D"]} style={s.msgBubble}>
                      <Text style={s.msgTxtMine}>{msg.text}</Text>
                    </LinearGradient>
                  ) : (
                    <View style={[s.msgBubble, s.msgBubbleThem]}>
                      <Text style={s.msgTxtThem}>{msg.text}</Text>
                    </View>
                  )}
                  <Text style={s.msgTime}>{msg.ts}</Text>
                </View>
              );
            }}
          />
          <View style={s.chatBar}>
            <TextInput
              style={s.chatInput}
              placeholder="Type a message…"
              placeholderTextColor={C.muted}
              value={text}
              onChangeText={setText}
              multiline
              returnKeyType="send"
              onSubmitEditing={send}
            />
            <TouchableOpacity onPress={send} disabled={!text.trim()}>
              <LinearGradient colors={["#4E8B5F", "#7DB87D"]} style={[s.sendBtn, !text.trim() && { opacity: 0.4 }]}>
                <Text style={s.sendIcon}>↑</Text>
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 9. REPORTS ─────────────────────────────────────────────────────────────────
const DIM_DESCRIPTIONS = [
  "How you seek and maintain emotional bonds — your comfort with closeness, distance, and perceived rejection.",
  "How effectively you process and recover from emotional distress without damaging your relationships.",
  "The fundamental beliefs and priorities that guide your choices in relationships and life.",
  "Whether you tend to say things directly, reflect first, pick your battles, or stay quiet when bothered.",
  "Your approach to disagreements — do you push through, cool down first, compromise fast, or withdraw?",
  "Your need for personal space, autonomy, and time apart from people you're close to.",
  "How naturally you can share emotional struggles, fears, and personal truths with others.",
  "How much you need explicit reassurance that things are okay between you and someone you care about.",
  "The primary way you express love and prefer to receive it from others.",
  "Your belief in the capacity for people — including yourself — to change, grow, and improve.",
  "Your appetite for new ideas, experiences, perspectives, and ways of doing things.",
  "What you're ultimately hoping to build in a relationship, and on what timeline.",
];

function ReportsScreen({ user, profile, assessed, onBack, onAssess, isPremium, onUpgrade }) {
  const dims = profile?.dimensions || DIM_LABELS.map((label, i) => ({ label, score: 65, color: DIM_COLORS[i] }));
  const avg  = Math.round(dims.reduce((a, d) => a + d.score, 0) / dims.length);
  const at   = profile?.attachmentType || "secure";
  const FREE_DIMS = 3;

  return (
    <LinearGradient colors={["#0D1409", "#121C0E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <Hdr title="My Report" subtitle="Psychological profile" onBack={onBack} />
        <ScrollView contentContainerStyle={s.reportScroll}>
          {!assessed && (
            <View style={s.reportDemoCard}>
              <Text style={{ color: C.gold, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 22 }}>
                This is a sample report. Complete the assessment to see your real psychological profile.
              </Text>
              <GradBtn label="Take assessment →" onPress={onAssess} style={{ marginTop: 12 }} />
            </View>
          )}

          {/* Score hero */}
          <LinearGradient colors={["#4E8B5F22", "#C8A04511"]} style={s.reportHero}>
            <Text style={s.reportHeroScore}>{avg}%</Text>
            <Text style={s.reportHeroLabel}>Average self-alignment score</Text>
            <Text style={s.reportHeroName}>{user?.name || "Your"} profile</Text>
          </LinearGradient>

          {/* Attachment type insight */}
          <View style={s.card}>
            <Text style={s.cardTitle}>Your attachment style</Text>
            <Badge label={ATTACHMENT_LABELS[at]} color={C.violet} />
            <Text style={[s.body, { marginTop: 8 }]}>{ATTACHMENT_INSIGHTS[at]}</Text>
          </View>

          {/* Dimensions — first 3 free, rest premium */}
          {dims.slice(0, isPremium ? 12 : FREE_DIMS).map((d, i) => (
            <View key={i} style={s.reportDimCard}>
              <View style={s.reportDimHdr}>
                <Text style={s.reportDimName}>{d.label}</Text>
                <Text style={[s.reportDimScore, { color: d.color }]}>{d.score}%</Text>
              </View>
              <View style={s.dimBg}><View style={[s.dimFill, { width: `${d.score}%`, backgroundColor: d.color }]} /></View>
              <Text style={s.reportDimDesc}>{DIM_DESCRIPTIONS[i]}</Text>
            </View>
          ))}

          {/* Paywall gate for remaining 9 dimensions */}
          {!isPremium && (
            <View style={s.reportPaywallCard}>
              <Text style={{ fontSize: 32, textAlign: "center" }}>🔒</Text>
              <Text style={s.reportPaywallTitle}>9 more dimensions locked</Text>
              <Text style={s.reportPaywallSub}>
                See your full breakdown — Conflict Approach, Vulnerability Comfort, Love Language, and 6 more — plus how each dimension shapes your compatibility.
              </Text>
              <GradBtn label="Unlock full report →" onPress={onUpgrade} style={{ marginTop: 4 }} />
            </View>
          )}

          <View style={[s.card, { marginTop: 8 }]}>
            <Text style={[s.muted, { textAlign: "center", fontSize: 12, lineHeight: 18 }]}>
              This report is for self-discovery and compatibility matching purposes only — not a clinical or psychological diagnosis.
            </Text>
          </View>
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 10. SETTINGS ───────────────────────────────────────────────────────────────
function SettingsScreen({ user, onBack, onSignOut, onDeleteAccount, isPremium, onUpgrade, onManageSub }) {
  const [notifs, setNotifs] = useState(true);
  const SettingsRow = ({ label, value, onPress, danger }) => (
    <TouchableOpacity style={s.settRow} onPress={onPress}>
      <Text style={[s.settRowLbl, danger && { color: C.error }]}>{label}</Text>
      {value ? <Text style={s.settRowVal}>{value}</Text> : <Text style={s.settRowArr}>›</Text>}
    </TouchableOpacity>
  );
  return (
    <LinearGradient colors={["#0D1409", "#121C0E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <Hdr title="Settings" onBack={onBack} />
        <ScrollView contentContainerStyle={s.settScroll}>
          <Text style={s.settSection}>Account</Text>
          <View style={s.card}>
            <SettingsRow label="Name"  value={user?.name  || "—"} />
            <View style={s.divider} />
            <SettingsRow label="Email" value={user?.email || "—"} />
            <View style={s.divider} />
            <SettingsRow label="Edit profile" />
          </View>

          <Text style={s.settSection}>Notifications</Text>
          <View style={s.card}>
            <View style={s.settRow}>
              <Text style={s.settRowLbl}>Match alerts</Text>
              <Switch value={notifs} onValueChange={setNotifs} trackColor={{ true: C.violet }} thumbColor="#fff" />
            </View>
          </View>

          <Text style={s.settSection}>Subscription</Text>
          {isPremium ? (
            <View style={s.card}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
                <LinearGradient colors={["#8A6A1E", "#C8A045"]} style={{ width: 36, height: 36, borderRadius: 10, alignItems: "center", justifyContent: "center" }}>
                  <Text style={{ fontSize: 18 }}>✦</Text>
                </LinearGradient>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_600SemiBold" }}>SoulMatch Premium</Text>
                  <Text style={{ color: C.teal, fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold" }}>Active ✓</Text>
                </View>
              </View>
              <View style={s.divider} />
              <SettingsRow label="Manage subscription" onPress={onManageSub} />
            </View>
          ) : (
            <>
              <LinearGradient colors={["#8A6A1E", "#C8A045"]} style={s.subCard}>
                <Text style={s.subTitle}>SoulMatch Premium</Text>
                <Text style={s.subSub}>Full compatibility reports · Unlimited matches · Priority listing</Text>
                <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 4, marginTop: 8 }}>
                  <Text style={s.subPrice}>$14.99</Text>
                  <Text style={s.subPer}>/month</Text>
                </View>
                <TouchableOpacity style={s.subBtn} onPress={onUpgrade}>
                  <Text style={s.subBtnTxt}>Upgrade to Premium</Text>
                </TouchableOpacity>
              </LinearGradient>
              <View style={s.card}><SettingsRow label="Current plan" value="Beta (Free)" /></View>
            </>
          )}

          <Text style={s.settSection}>Legal & privacy</Text>
          <View style={s.card}>
            <SettingsRow label="Privacy Policy" />
            <View style={s.divider} />
            <SettingsRow label="Terms of Service" />
            <View style={s.divider} />
            <SettingsRow label="Delete my data" danger onPress={onDeleteAccount} />
          </View>
          <View style={s.card}>
            <SettingsRow label="Sign out" danger onPress={onSignOut} />
          </View>
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── 11. PAYWALL ────────────────────────────────────────────────────────────────
const PAYWALL_FEATURES = [
  { icon: "📊", title: "Full psychological breakdown", sub: "All 12 dimensions explained — see exactly what drives your compatibility." },
  { icon: "💕", title: "Unlimited matches", sub: "See every compatible person, ranked by your psychological profile." },
  { icon: "⚡", title: "Priority listing", sub: "Appear higher in your matches' discovery feed." },
];

const PAYWALL_HEADLINES = {
  reports:  "Unlock your full psychological report",
  matches:  "See your complete match list",
  general:  "Unlock everything",
};

function PaywallScreen({ context = "general", onBack, onCheckout, busy, error }) {
  const headline = PAYWALL_HEADLINES[context] || PAYWALL_HEADLINES.general;
  return (
    <LinearGradient colors={["#0D1409", "#121C0E"]} style={s.fill}>
      <StatusBar style="light" />
      <SafeAreaView style={s.fill}>
        <View style={{ flexDirection: "row", justifyContent: "flex-end", paddingHorizontal: 20, paddingTop: 12, paddingBottom: 4 }}>
          <TouchableOpacity onPress={onBack} style={{ padding: 8 }}>
            <Text style={{ color: C.muted, fontSize: 20, lineHeight: 22 }}>✕</Text>
          </TouchableOpacity>
        </View>
        <ScrollView contentContainerStyle={s.paywallScroll} showsVerticalScrollIndicator={false}>
          {/* Logo */}
          <LinearGradient colors={["#8A6A1E", "#C8A045"]} style={s.paywallLogoBox}>
            <Text style={{ fontSize: 38, color: "#fff" }}>✦</Text>
          </LinearGradient>

          {/* Headline */}
          <View style={{ alignItems: "center", gap: 6 }}>
            <Text style={{ color: C.muted, fontSize: 11, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: 1.2, textTransform: "uppercase" }}>
              SoulMatch Premium
            </Text>
            <Text style={s.paywallHeadline}>{headline}</Text>
          </View>

          {/* Feature cards */}
          <View style={{ width: "100%", gap: 10 }}>
            {PAYWALL_FEATURES.map((f, i) => (
              <View key={i} style={s.paywallFeatureCard}>
                <Text style={{ fontSize: 26, flexShrink: 0 }}>{f.icon}</Text>
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={{ color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_600SemiBold" }}>{f.title}</Text>
                  <Text style={{ color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 18 }}>{f.sub}</Text>
                </View>
              </View>
            ))}
          </View>

          {/* Price */}
          <View style={{ alignItems: "center", gap: 4 }}>
            <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 4 }}>
              <Text style={s.paywallPrice}>$14.99</Text>
              <Text style={{ color: C.muted, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", paddingBottom: 6 }}>/month</Text>
            </View>
            <Text style={{ color: C.muted, fontSize: 12, fontFamily: "SpaceGrotesk_400Regular" }}>Cancel any time · No commitment</Text>
          </View>

          {/* CTA */}
          {error ? <Text style={[s.errMsg, { textAlign: "center" }]}>{error}</Text> : null}
          <GradBtn
            label={busy ? "Opening checkout…" : "Start Premium →"}
            onPress={onCheckout}
            disabled={busy}
            style={{ width: "100%", marginTop: 4 }}
          />
          <TouchableOpacity onPress={onBack} style={{ alignSelf: "center", padding: 12 }}>
            <Text style={{ color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular" }}>Maybe later</Text>
          </TouchableOpacity>

          <Text style={{ color: "rgba(255,255,255,0.18)", fontSize: 11, fontFamily: "SpaceGrotesk_400Regular", textAlign: "center", lineHeight: 18 }}>
            Payment processed securely by Stripe.{"\n"}Your subscription starts immediately after checkout.
          </Text>
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

// ── ROOT APP ───────────────────────────────────────────────────────────────────
export default function App() {
  const [fontsLoaded] = useFonts({ SpaceGrotesk_400Regular, SpaceGrotesk_600SemiBold });
  const [screen, setScreen]         = useState("splash");
  const [navParam, setNavParam]     = useState(null);
  const [user, setUser]             = useState(null);
  const [authToken, setToken]       = useState("");
  const [busy, setBusy]             = useState(false);
  const [authError, setAuthErr]     = useState("");
  const [mode, setMode]             = useState("romance");
  const [matches, setMatches]       = useState([]);
  const [messages, setMessages]     = useState({});
  const [profile, setProfile]       = useState(null);
  const [assessed, setAssessed]     = useState(false);
  // Beta: all users get premium access for free during the beta period.
  // Set to false when monetization goes live (Phase 5 production).
  const [isPremium, setIsPremium]   = useState(true);
  const [checkoutBusy, setCkBusy]   = useState(false);
  const [checkoutError, setCkErr]   = useState("");

  if (!fontsLoaded) return null;

  function nav(s, p = null) { setNavParam(p); setScreen(s); }

  async function checkSubscription(token) {
    if (!token) return;
    try {
      const res = await apiRequest("GET", "/billing/subscription", null, token);
      if (res.ok && res.body?.active_subscription?.status === "active") setIsPremium(true);
    } catch (_) {}
  }

  async function openCheckout() {
    if (!authToken) { nav("login"); return; }
    setCkBusy(true); setCkErr("");
    try {
      const res = await apiRequest("POST", "/billing/checkout-session", {
        product_code: "premium_monthly",
        success_url: "soulmatch://billing/success",
        cancel_url: "soulmatch://billing/cancel",
      }, authToken);
      if (res.ok && res.body?.checkout_url) {
        await Linking.openURL(res.body.checkout_url);
      } else {
        setCkErr(normalizeError(res.body, "Checkout failed — try again"));
      }
    } catch (e) {
      setCkErr(normalizeError(e, "Could not open checkout"));
    } finally {
      setCkBusy(false);
    }
  }

  async function openPortal() {
    if (!authToken) return;
    try {
      const res = await apiRequest("POST", "/billing/portal", null, authToken);
      if (res.ok && res.body?.portal_url) await Linking.openURL(res.body.portal_url);
    } catch (_) {}
  }

  function goPaywall(context = "general") {
    nav("paywall", { context, from: screen });
  }

  // Handle Stripe deep link return (soulmatch://billing/success)
  useEffect(() => {
    const sub = Linking.addEventListener("url", ({ url }) => {
      if (url?.includes("billing/success")) {
        checkSubscription(authToken);
        nav("profile");
      }
    });
    return () => sub.remove();
  }, [authToken]);

  async function login(email, password) {
    setBusy(true); setAuthErr("");
    try {
      const res = await apiRequest("POST", "/auth/login", { email, password }, null);
      if (!res.ok) { setAuthErr(normalizeError(res.body, "Login failed")); return; }
      setToken(res.body.access_token);
      const u = { id: res.body.user_id, name: res.body.name || email.split("@")[0], email };
      setUser(u);
      phIdentify(u.id, { email });
      setSentryUser(u.id);
      track("login");
      checkSubscription(res.body.access_token);
      nav("profile");
    } catch (e) { setAuthErr(normalizeError(e, "Network error")); }
    finally { setBusy(false); }
  }

  async function register(data) {
    setBusy(true); setAuthErr("");
    const { name, email, password, birthDate, birthTime, selectedPlace, goals, pref, consentP, consentS } = data;
    try {
      let auth;
      const r = await apiRequest("POST", "/auth/signup", { email, password, birth_date: birthDate }, null);
      if (r.ok) { auth = r.body; }
      else if (r.status === 409) {
        const l = await apiRequest("POST", "/auth/login", { email, password }, null);
        if (!l.ok) { setAuthErr(normalizeError(l.body, "Login failed")); return; }
        auth = l.body;
      } else { setAuthErr(normalizeError(r.body, "Registration failed")); return; }

      setToken(auth.access_token);
      checkSubscription(auth.access_token);
      await apiRequest("POST", "/legal/consent", { accept: true }, auth.access_token);
      await apiRequest("POST", "/users", {
        id: auth.user_id, name, email,
        birth: { date: birthDate, time: birthTime, place: selectedPlace?.label || "", latitude: selectedPlace?.latitude || 0, longitude: selectedPlace?.longitude || 0, timezone: selectedPlace?.timezone || "" },
        goals, matching_preference: pref, consent_privacy: consentP, consent_sensitive_data: consentS, policy_version: "v1",
      }, auth.access_token);
      if (pref === "psych_behavior_astro") {
        apiRequest("POST", "/vectors/generate", { user_id: auth.user_id }, auth.access_token).catch(() => {});
      }
      const u = { id: auth.user_id, name, email };
      setUser(u);
      phIdentify(u.id, { email, matching_preference: pref });
      setSentryUser(u.id);
      track("sign_up", { matching_preference: pref });
      nav("assessment");
    } catch (e) { setAuthErr(normalizeError(e, "Registration failed")); }
    finally { setBusy(false); }
  }

  async function handleAssessmentDone(answers, adaptiveAns, intensities, adaptiveIntensity) {
    const computed = computeProfile(answers, adaptiveAns, intensities, adaptiveIntensity);
    setProfile(computed);
    setAssessed(true);
    track("assessment_completed", { attachment_type: computed.attachmentType });
    if (authToken && user?.id) {
      apiRequest("POST", "/psychology/mobile-submit", {
        attachment_type: computed.attachmentType,
        answers: Object.values(answers),
        adaptive_answer: adaptiveAns,
        dimension_scores: computed.dimensions.map(d => ({ label: d.label, score: d.score })),
      }, authToken).catch(() => {});
    }
    nav("discovery");
  }

  async function loadMatches(m = mode) {
    if (!user?.id || !authToken) { setMatches([]); return; }
    setBusy(true);
    try {
      const res = await apiRequest("POST", "/matches", { user_id: user.id, mode: m }, authToken);
      if (res.ok) {
        setMatches((res.body?.results || []).map(r => ({
          id: r.candidate_id, name: r.candidate_name || r.candidate_id,
          city: r.candidate_city || "Toronto, ON", score: r.score,
          avatar: (r.candidate_name || "?")[0].toUpperCase(), highlights: r.highlights || [],
        })));
      } else { setMatches([]); }
    } catch (_) { setMatches([]); }
    finally { setBusy(false); }
  }

  function sendMessage(matchId, text) {
    const ts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setMessages(prev => ({ ...prev, [matchId]: [...(prev[matchId] || []), { id: String(Date.now()), text, from: "me", ts }] }));
  }

  function blockUser(match) {
    if (!authToken || !match?.id) return;
    Alert.alert("Block " + match.name + "?", "They won't be able to see your profile or message you.", [
      {
        text: "Block", style: "destructive", onPress: () => {
          apiRequest("POST", "/compliance/block", { blocked_user_id: match.id, reason: "user_block" }, authToken).catch(() => {});
          setMatches(prev => prev.filter(m => m.id !== match.id));
          nav("discovery");
        },
      },
      { text: "Cancel", style: "cancel" },
    ]);
  }

  function reportUser(match) {
    if (!authToken || !match?.id) return;
    Alert.alert("Report " + match.name, "Select a reason:", [
      { text: "Inappropriate content", onPress: () => _submitReport(match.id, "inappropriate_content") },
      { text: "Harassment or abuse", onPress: () => _submitReport(match.id, "harassment") },
      { text: "Fake profile / spam", onPress: () => _submitReport(match.id, "fake_profile") },
      { text: "Cancel", style: "cancel" },
    ]);
  }

  function _submitReport(targetId, reason) {
    apiRequest("POST", "/compliance/report", { target_user_id: targetId, reason }, authToken).catch(() => {});
    Alert.alert("Report submitted", "Thank you — our team will review this.");
  }

  function signOut() {
    track("sign_out");
    phReset();
    setSentryUser(null);
    setUser(null); setToken(""); setMatches([]); setProfile(null); setAssessed(false);
    nav("login");
  }

  function deleteAccount() {
    Alert.alert(
      "Delete your account?",
      "All your data will be permanently removed. This cannot be undone.",
      [
        {
          text: "Delete permanently",
          style: "destructive",
          onPress: () => {
            if (authToken) {
              apiRequest("POST", "/compliance/user/delete", { reason: "user_requested" }, authToken).catch(() => {});
            }
            signOut();
          },
        },
        { text: "Cancel", style: "cancel" },
      ]
    );
  }

  if (screen === "splash")      return <SplashScreen onDone={() => nav("login")} />;
  if (screen === "login")       return <LoginScreen onLogin={login} onGoRegister={() => { setAuthErr(""); nav("register"); }} error={authError} busy={busy} />;
  if (screen === "register")    return <RegisterScreen onComplete={register} onGoLogin={() => { setAuthErr(""); nav("login"); }} error={authError} busy={busy} />;
  if (screen === "assessment")  return <AssessmentScreen onComplete={handleAssessmentDone} onSkip={() => nav("profile")} />;
  if (screen === "profile")     return <ProfileScreen user={user} profile={profile} assessed={assessed} onAssess={() => nav("assessment")} onReports={() => nav("reports")} onMatches={() => { nav("discovery"); loadMatches(); }} onSettings={() => nav("settings")} />;
  if (screen === "discovery")   return <DiscoveryScreen matches={matches} mode={mode} onModeChange={m => { setMode(m); loadMatches(m); }} onViewMatch={(m, md) => nav("match_detail", { match: m, mode: md || mode })} onProfile={() => nav("profile")} busy={busy} userProfile={profile} isPremium={isPremium} onUpgrade={() => goPaywall("matches")} />;
  if (screen === "match_detail") return <MatchDetailScreen match={navParam?.match} userProfile={profile} mode={navParam?.mode || mode} onBack={() => nav("discovery")} onChat={m => nav("chat", m)} onBlock={blockUser} onReport={reportUser} />;
  if (screen === "chat")        return <ChatScreen match={navParam} messages={messages[navParam?.id]} onSend={sendMessage} onBack={() => nav("match_detail", { match: navParam, mode })} onBlock={blockUser} onReport={reportUser} />;
  if (screen === "reports")     return <ReportsScreen user={user} profile={profile} assessed={assessed} onBack={() => nav("profile")} onAssess={() => nav("assessment")} isPremium={isPremium} onUpgrade={() => goPaywall("reports")} />;
  if (screen === "settings")    return <SettingsScreen user={user} onBack={() => nav("profile")} onSignOut={signOut} onDeleteAccount={deleteAccount} isPremium={isPremium} onUpgrade={() => goPaywall("general")} onManageSub={openPortal} />;
  if (screen === "paywall")     return <PaywallScreen context={navParam?.context || "general"} onBack={() => nav(navParam?.from || "profile")} onCheckout={openCheckout} busy={checkoutBusy} error={checkoutError} />;
  return null;
}

// ── STYLES ─────────────────────────────────────────────────────────────────────
const s = StyleSheet.create({
  fill: { flex: 1 },
  centerFill: { flex: 1, alignItems: "center", justifyContent: "center" },

  // Splash
  splashCenter: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 40 },
  splashLogoBox: { width: 80, height: 80, borderRadius: 24, alignItems: "center", justifyContent: "center", marginBottom: 24 },
  splashLogoIcon: { color: "#fff", fontSize: 40, fontFamily: "SpaceGrotesk_600SemiBold" },
  splashWordmark: { color: C.text, fontSize: 36, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -1, marginBottom: 14 },
  splashTagline: { color: C.muted, fontSize: 18, textAlign: "center", lineHeight: 28, fontFamily: "SpaceGrotesk_400Regular" },
  splashDots: { flexDirection: "row", gap: 8, justifyContent: "center", paddingBottom: 60 },
  dot: { width: 6, height: 6, borderRadius: 3 },

  // Auth
  authScroll: { padding: 24, paddingTop: 20, gap: 16 },
  authTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 8 },
  authTitle: { color: C.text, fontSize: 30, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -0.5 },
  authSub: { color: C.muted, fontSize: 16, fontFamily: "SpaceGrotesk_400Regular", marginBottom: 4 },
  forgotLink: { color: C.violet, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", textAlign: "right" },
  switchLink: { alignItems: "center", paddingVertical: 10 },
  switchLinkTxt: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular" },
  btnRow: { flexDirection: "row", gap: 10 },

  // Form
  formCard: { backgroundColor: C.bg3, borderRadius: 20, borderWidth: 1, borderColor: C.border, padding: 20, gap: 12 },
  formNote: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 20 },
  inputLabel: { color: C.muted, fontSize: 11, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: 0.8, textTransform: "uppercase" },
  input: { backgroundColor: C.bg2, borderWidth: 1, borderColor: C.border, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular" },
  searchRow: { flexDirection: "row", gap: 8, alignItems: "center" },
  searchBtn: { backgroundColor: C.teal, paddingHorizontal: 14, paddingVertical: 12, borderRadius: 12 },
  searchBtnTxt: { color: C.bg, fontSize: 14, fontFamily: "SpaceGrotesk_600SemiBold" },
  placeCard: { backgroundColor: C.bg2, borderWidth: 1, borderColor: C.border, borderRadius: 12, padding: 12, gap: 3 },
  placeCardSel: { borderColor: C.violet },
  placeLabel: { color: C.text, fontSize: 14, fontFamily: "SpaceGrotesk_600SemiBold" },
  placeMeta: { color: C.muted, fontSize: 11, fontFamily: "SpaceGrotesk_400Regular" },
  selPlaceBox: { backgroundColor: "rgba(106,174,120,0.12)", borderRadius: 10, padding: 10, borderWidth: 1, borderColor: "rgba(106,174,120,0.32)" },
  selPlaceTxt: { color: C.violet, fontSize: 13, fontFamily: "SpaceGrotesk_600SemiBold" },
  toggleRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
  prefCard: { backgroundColor: C.bg2, borderWidth: 1, borderColor: C.border, borderRadius: 14, padding: 14, flexDirection: "row", alignItems: "flex-start", gap: 12 },
  prefCardSel: { borderColor: C.violet, backgroundColor: "rgba(106,174,120,0.09)" },
  prefDot: { width: 18, height: 18, borderRadius: 9, borderWidth: 2, borderColor: C.border, marginTop: 2 },
  prefDotSel: { borderColor: C.violet, backgroundColor: C.violet },
  prefTitle: { color: C.text, fontSize: 14, fontFamily: "SpaceGrotesk_600SemiBold" },
  prefSub: { color: C.muted, fontSize: 12, fontFamily: "SpaceGrotesk_400Regular", marginTop: 2 },

  // Step dots
  stepDots: { flexDirection: "row", alignItems: "center", justifyContent: "center", marginBottom: 10 },
  stepDotWrap: { flexDirection: "row", alignItems: "center" },
  stepDot: { width: 28, height: 28, borderRadius: 14, borderWidth: 2, borderColor: C.border, alignItems: "center", justifyContent: "center", backgroundColor: C.bg3 },
  stepDotActive: { borderColor: C.violet, backgroundColor: C.violet },
  stepDotCur: { borderColor: C.pink, backgroundColor: C.purple },
  stepDotNum: { color: C.muted, fontSize: 11, fontFamily: "SpaceGrotesk_600SemiBold" },
  stepLine: { width: 24, height: 2, backgroundColor: C.border },
  stepLineActive: { backgroundColor: C.violet },
  stepLabel: { color: C.text, fontSize: 22, fontFamily: "SpaceGrotesk_600SemiBold", textAlign: "center", letterSpacing: -0.3, marginBottom: 4 },

  // Assessment
  assessHdr: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, paddingTop: 12, paddingBottom: 8 },
  skipTxt: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular" },
  assessCount: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_600SemiBold" },
  progressBg: { height: 4, backgroundColor: C.bg3, marginHorizontal: 20, borderRadius: 4 },
  progressFill: { height: 4, borderRadius: 4, backgroundColor: C.violet },
  assessBody: { padding: 24, paddingTop: 24, gap: 20 },
  adaptiveBanner: { backgroundColor: "rgba(139,170,141,0.1)", borderRadius: 10, padding: 10, borderWidth: 1, borderColor: "rgba(139,170,141,0.22)", marginBottom: 4 },
  adaptiveBannerTxt: { color: C.teal, fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold" },
  dimBadge: { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: "rgba(106,174,120,0.12)", borderRadius: 50, paddingHorizontal: 14, paddingVertical: 8, alignSelf: "flex-start", borderWidth: 1, borderColor: "rgba(106,174,120,0.32)" },
  dimBadgeEmoji: { fontSize: 16 },
  dimBadgeLbl: { color: C.violet, fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold" },
  assessQ: { color: C.text, fontSize: 22, fontFamily: "SpaceGrotesk_600SemiBold", lineHeight: 30, letterSpacing: -0.3 },
  options: { gap: 12 },
  optCard: { backgroundColor: C.bg3, borderWidth: 1, borderColor: C.border, borderRadius: 16, padding: 16, flexDirection: "row", alignItems: "flex-start", gap: 14 },
  optCardSel: { borderColor: C.violet, backgroundColor: "rgba(106,174,120,0.12)" },
  optCardDim: { opacity: 0.38 },
  optDot: { width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: C.border, alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 },
  optDotSel: { borderColor: C.violet, backgroundColor: C.violet },
  optCheck: { color: "#fff", fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold" },
  optTxt: { color: C.muted, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 22 },
  optTxtSel: { color: C.text },
  intRow: { marginTop: 14, paddingTop: 14, borderTopWidth: 1, borderTopColor: "rgba(255,255,255,0.08)" },
  intRowLabel: { fontSize: 10, color: C.muted, fontFamily: "SpaceGrotesk_400Regular", textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 10 },
  intBtns: { flexDirection: "row", gap: 8 },
  intBtn: { flex: 1, paddingVertical: 10, paddingHorizontal: 4, backgroundColor: C.bg4, borderRadius: 10, borderWidth: 1, borderColor: C.border, alignItems: "center" },
  intBtnActive: { borderColor: C.violet, backgroundColor: "rgba(106,174,120,0.18)" },
  intBtnTxt: { fontSize: 11, color: C.muted, fontFamily: "SpaceGrotesk_400Regular" },
  intBtnTxtActive: { color: C.text, fontFamily: "SpaceGrotesk_600SemiBold" },
  assessFooter: { flexDirection: "row", gap: 10, padding: 20, paddingBottom: 32 },

  // Profile
  profileScroll: { padding: 20, gap: 20 },
  profileHdr: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  avatarWrap: { alignItems: "center", marginTop: 8 },
  avatar: { width: 96, height: 96, borderRadius: 48, alignItems: "center", justifyContent: "center" },
  avatarTxt: { color: "#fff", fontSize: 34, fontFamily: "SpaceGrotesk_600SemiBold" },
  avatarBadge: { position: "absolute", bottom: 0, right: W / 2 - 76, backgroundColor: C.bg, borderRadius: 12, paddingHorizontal: 8, paddingVertical: 4, borderWidth: 2, borderColor: C.green },
  avatarBadgeTxt: { color: C.green, fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold" },
  profileName: { color: C.text, fontSize: 24, fontFamily: "SpaceGrotesk_600SemiBold", textAlign: "center", letterSpacing: -0.3 },
  profileEmail: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular", textAlign: "center" },
  profileActions: { flexDirection: "row", gap: 12, justifyContent: "center" },
  profileAction: { backgroundColor: C.bg3, borderWidth: 1, borderColor: C.border, borderRadius: 16, padding: 16, alignItems: "center", minWidth: 90 },
  profileActionLbl: { color: C.muted, fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold", marginTop: 6 },
  emptyCard: { backgroundColor: C.bg3, borderRadius: 20, borderWidth: 1, borderColor: C.border, padding: 28, alignItems: "center", gap: 10 },
  emptyTitle: { color: C.text, fontSize: 20, fontFamily: "SpaceGrotesk_600SemiBold" },
  emptySub: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular", textAlign: "center", lineHeight: 22 },

  // Discovery
  discHdr: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, paddingTop: 12, paddingBottom: 6 },
  discAvatarBtn: { width: 38, height: 38, alignItems: "center", justifyContent: "center" },
  modePill: { flexDirection: "row", margin: 16, marginTop: 8, marginBottom: 4, backgroundColor: C.bg3, borderRadius: 50, padding: 4, borderWidth: 1, borderColor: C.border },
  modeBtn: { flex: 1, paddingVertical: 10, borderRadius: 50, alignItems: "center" },
  modeBtnActive: { backgroundColor: C.purple },
  modeBtnTxt: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_600SemiBold" },
  modeBtnTxtActive: { color: "#fff" },
  modeSubtitle: { color: C.muted, fontSize: 11, fontFamily: "SpaceGrotesk_400Regular", textAlign: "center", marginHorizontal: 20, marginBottom: 8 },
  demoBanner: { marginHorizontal: 16, backgroundColor: "rgba(106,174,120,0.09)", borderRadius: 10, padding: 10, borderWidth: 1, borderColor: "rgba(106,174,120,0.22)", marginBottom: 6 },
  demoBannerTxt: { color: C.violet, fontSize: 11, fontFamily: "SpaceGrotesk_400Regular", textAlign: "center" },
  matchList: { padding: 16, gap: 14 },
  matchCard: { backgroundColor: C.bg3, borderRadius: 20, borderWidth: 1, borderColor: C.border, padding: 18, gap: 14 },
  matchCardTop: { flexDirection: "row", alignItems: "center", gap: 14 },
  matchAvatar: { width: 52, height: 52, borderRadius: 26, alignItems: "center", justifyContent: "center" },
  matchAvatarTxt: { color: "#fff", fontSize: 20, fontFamily: "SpaceGrotesk_600SemiBold" },
  matchName: { color: C.text, fontSize: 18, fontFamily: "SpaceGrotesk_600SemiBold" },
  matchCity: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular" },
  matchActions: { flexDirection: "row", gap: 10 },
  scoreBadge: { alignItems: "center", backgroundColor: "rgba(106,174,120,0.14)", borderRadius: 12, paddingHorizontal: 10, paddingVertical: 10, borderWidth: 1, borderColor: "rgba(106,174,120,0.28)" },
  scoreNum: { color: C.violet, fontSize: 18, fontFamily: "SpaceGrotesk_600SemiBold" },
  scoreLbl: { color: C.muted, fontSize: 9, fontFamily: "SpaceGrotesk_400Regular", textTransform: "uppercase", letterSpacing: 0.5 },
  highlights: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  highlightPill: { backgroundColor: "rgba(139,170,141,0.1)", borderRadius: 50, paddingHorizontal: 10, paddingVertical: 5, borderWidth: 1, borderColor: "rgba(139,170,141,0.22)" },
  highlightTxt: { color: C.teal, fontSize: 12, fontFamily: "SpaceGrotesk_400Regular" },

  // Match detail
  detailScroll: { padding: 20, gap: 20 },
  detailHero: { alignItems: "center", gap: 16, paddingVertical: 8 },
  detailAvatar: { width: 100, height: 100, borderRadius: 50, alignItems: "center", justifyContent: "center" },
  detailAvatarTxt: { color: "#fff", fontSize: 36, fontFamily: "SpaceGrotesk_600SemiBold" },
  detailScoreBox: { borderRadius: 20, paddingHorizontal: 28, paddingVertical: 14, borderWidth: 1, alignItems: "center" },
  detailScoreNum: { fontSize: 38, fontFamily: "SpaceGrotesk_600SemiBold" },
  detailScoreLbl: { fontSize: 13, fontFamily: "SpaceGrotesk_400Regular" },
  detailHighlight: { flexDirection: "row", gap: 12, alignItems: "flex-start" },
  detailHighlightTxt: { color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", flex: 1, lineHeight: 22 },

  // Chat
  chatList: { padding: 16, gap: 8, paddingBottom: 24 },
  msgWrap: { maxWidth: "80%", gap: 4 },
  msgWrapMine: { alignSelf: "flex-end", alignItems: "flex-end" },
  msgWrapThem: { alignSelf: "flex-start", alignItems: "flex-start" },
  msgBubble: { borderRadius: 18, padding: 14 },
  msgBubbleThem: { backgroundColor: C.bg3, borderWidth: 1, borderColor: C.border },
  msgTxtMine: { color: "#fff", fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 22 },
  msgTxtThem: { color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 22 },
  msgTime: { color: C.muted, fontSize: 11, fontFamily: "SpaceGrotesk_400Regular", paddingHorizontal: 4 },
  chatBar: { flexDirection: "row", alignItems: "flex-end", gap: 10, padding: 14, borderTopWidth: 1, borderTopColor: C.border, backgroundColor: C.bg2 },
  chatInput: { flex: 1, backgroundColor: C.bg3, borderRadius: 22, borderWidth: 1, borderColor: C.border, paddingHorizontal: 16, paddingVertical: 12, color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", maxHeight: 100 },
  sendBtn: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center" },
  sendIcon: { color: "#fff", fontSize: 18, fontFamily: "SpaceGrotesk_600SemiBold" },

  // Reports
  reportScroll: { padding: 20, gap: 16 },
  reportDemoCard: { backgroundColor: "rgba(200,160,69,0.08)", borderRadius: 16, padding: 16, borderWidth: 1, borderColor: "rgba(200,160,69,0.22)" },
  reportHero: { borderRadius: 20, padding: 28, alignItems: "center", gap: 6, borderWidth: 1, borderColor: "rgba(200,160,69,0.2)" },
  reportHeroScore: { color: C.text, fontSize: 54, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -2 },
  reportHeroLabel: { color: C.muted, fontSize: 12, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: 0.5, textTransform: "uppercase" },
  reportHeroName: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular" },
  reportDimCard: { backgroundColor: C.bg3, borderRadius: 16, borderWidth: 1, borderColor: C.border, padding: 16, gap: 10 },
  reportDimHdr: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  reportDimName: { color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_600SemiBold" },
  reportDimScore: { fontSize: 15, fontFamily: "SpaceGrotesk_600SemiBold" },
  reportDimDesc: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 20 },

  // Settings
  settScroll: { padding: 20, gap: 8 },
  settSection: { color: C.muted, fontSize: 10, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: 1.2, textTransform: "uppercase", marginTop: 12, marginBottom: 4, paddingLeft: 4 },
  settRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 14 },
  settRowLbl: { color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular" },
  settRowVal: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular" },
  settRowArr: { color: C.muted, fontSize: 20 },
  subCard: { borderRadius: 20, padding: 24, gap: 6 },
  subTitle: { color: "#fff", fontSize: 20, fontFamily: "SpaceGrotesk_600SemiBold" },
  subSub: { color: "rgba(255,255,255,0.7)", fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 20 },
  subPrice: { color: "#fff", fontSize: 32, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -1 },
  subPer: { color: "rgba(255,255,255,0.6)", fontSize: 14, fontFamily: "SpaceGrotesk_400Regular", paddingBottom: 5 },
  subBtn: { backgroundColor: "rgba(255,255,255,0.15)", borderRadius: 50, paddingVertical: 12, alignItems: "center", marginTop: 6 },
  subBtnTxt: { color: "#fff", fontSize: 15, fontFamily: "SpaceGrotesk_600SemiBold" },

  // Shared
  wordmark: { color: C.text, fontSize: 18, fontFamily: "SpaceGrotesk_600SemiBold" },
  badge: { alignSelf: "flex-start", borderRadius: 50, paddingHorizontal: 12, paddingVertical: 5, borderWidth: 1 },
  badgeTxt: { fontSize: 11, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: 0.6, textTransform: "uppercase" },
  card: { backgroundColor: C.bg3, borderRadius: 20, borderWidth: 1, borderColor: C.border, padding: 20, gap: 14 },
  cardTitle: { color: C.text, fontSize: 16, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -0.2 },
  cardSub: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", marginTop: -6 },
  divider: { height: 1, backgroundColor: C.border },
  dimRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  dimLabel: { width: 150, color: C.muted, fontSize: 12, fontFamily: "SpaceGrotesk_400Regular" },
  dimBg: { flex: 1, height: 6, backgroundColor: "rgba(255,255,255,0.06)", borderRadius: 6, overflow: "hidden" },
  dimFill: { height: 6, borderRadius: 6 },
  dimPct: { color: C.muted, fontSize: 11, fontFamily: "SpaceGrotesk_600SemiBold", width: 30, textAlign: "right" },
  hdr: { flexDirection: "row", alignItems: "center", gap: 14, paddingHorizontal: 20, paddingTop: 12, paddingBottom: 14 },
  backBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: C.bg3, borderWidth: 1, borderColor: C.border, alignItems: "center", justifyContent: "center" },
  backIcon: { color: C.text, fontSize: 18, marginLeft: -2 },
  hdrTitle: { color: C.text, fontSize: 20, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -0.3 },
  hdrSub: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular" },
  hdrRight: { width: 36, height: 36, borderRadius: 18, backgroundColor: C.bg3, borderWidth: 1, borderColor: C.border, alignItems: "center", justifyContent: "center" },
  hdrRightTxt: { color: C.muted, fontSize: 18, lineHeight: 22 },
  safetyRow: { flexDirection: "row", justifyContent: "center", gap: 32, marginTop: 8, marginBottom: 20 },
  safetyBtn: { paddingVertical: 8, paddingHorizontal: 12 },
  safetyTxt: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular" },
  body: { color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_400Regular", lineHeight: 22 },
  muted: { color: C.muted, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular" },
  errMsg: { color: C.error, fontSize: 13, fontFamily: "SpaceGrotesk_400Regular", textAlign: "center" },
  gradBtn: { borderRadius: 50, paddingVertical: 14, paddingHorizontal: 24, alignItems: "center" },
  gradBtnTxt: { color: "#fff", fontSize: 15, fontFamily: "SpaceGrotesk_600SemiBold" },
  ghostBtn: { borderRadius: 50, paddingVertical: 14, paddingHorizontal: 24, alignItems: "center", borderWidth: 1, borderColor: C.border },
  ghostBtnTxt: { color: C.text, fontSize: 15, fontFamily: "SpaceGrotesk_600SemiBold" },

  // Reports premium gate
  reportPaywallCard: { backgroundColor: C.bg3, borderRadius: 20, borderWidth: 1, borderColor: "rgba(106,174,120,0.32)", padding: 24, alignItems: "center", gap: 10 },
  reportPaywallTitle: { color: C.text, fontSize: 18, fontFamily: "SpaceGrotesk_600SemiBold", textAlign: "center", letterSpacing: -0.2 },
  reportPaywallSub: { color: C.muted, fontSize: 14, fontFamily: "SpaceGrotesk_400Regular", textAlign: "center", lineHeight: 22 },

  // Paywall screen
  paywallScroll: { padding: 24, alignItems: "center", gap: 24 },
  paywallLogoBox: { width: 80, height: 80, borderRadius: 24, alignItems: "center", justifyContent: "center" },
  paywallHeadline: { color: C.text, fontSize: 26, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -0.5, textAlign: "center", lineHeight: 34 },
  paywallFeatureCard: { backgroundColor: C.bg3, borderRadius: 16, borderWidth: 1, borderColor: C.border, padding: 16, flexDirection: "row", alignItems: "flex-start", gap: 14, width: "100%" },
  paywallPrice: { color: C.text, fontSize: 42, fontFamily: "SpaceGrotesk_600SemiBold", letterSpacing: -2 },
});
