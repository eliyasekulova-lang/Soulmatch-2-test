#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
EMAIL="${EMAIL:-trial$(date +%s)@example.com}"
PASSWORD="${PASSWORD:-StrongPass#2026}"
BIRTH_DATE="${BIRTH_DATE:-1997-06-20}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "BASE_URL=$BASE_URL"
echo "EMAIL=$EMAIL"

signup_payload=$(cat <<JSON
{"email":"$EMAIL","password":"$PASSWORD","birth_date":"$BIRTH_DATE"}
JSON
)

echo "== 1) Signup =="
SIGNUP=$(curl -sS -X POST "$BASE_URL/v1/auth/signup" -H "Content-Type: application/json" -d "$signup_payload")
echo "$SIGNUP"

TOKEN=$(printf "%s" "$SIGNUP" | "$PYTHON_BIN" -c 'import sys,json; d=json.load(sys.stdin); print(d.get("access_token",""))')
USER_ID=$(printf "%s" "$SIGNUP" | "$PYTHON_BIN" -c 'import sys,json; d=json.load(sys.stdin); print(d.get("user_id",""))')
if [[ -z "$TOKEN" || -z "$USER_ID" ]]; then
  echo "Signup failed; stopping."
  exit 1
fi
echo "USER_ID=$USER_ID TOKEN_LEN=${#TOKEN}"

auth_header=(-H "Authorization: Bearer $TOKEN")
json_header=(-H "Content-Type: application/json")

echo "== 2) Legal consent =="
curl -sS -X POST "$BASE_URL/v1/legal/consent" "${auth_header[@]}" "${json_header[@]}" -d '{"accept":true}'; echo

echo "== 3) Create profile =="
profile_payload=$(cat <<JSON
{"id":"$USER_ID","name":"Trial User","email":"$EMAIL","birth":{"date":"1997-06-20","time":"09:30","place":"Toronto, Canada","latitude":43.6532,"longitude":-79.3832,"timezone":"America/Toronto"},"goals":["romance","friendship"],"consent_privacy":true,"consent_sensitive_data":true,"policy_version":"v1"}
JSON
)
curl -sS -X POST "$BASE_URL/v1/users" "${auth_header[@]}" "${json_header[@]}" -d "$profile_payload"; echo

echo "== 4) Gate check before onboarding =="
PRE_GATE=$(curl -sS -o /tmp/soulmatch_phase_a_gate.json -w "%{http_code}" "$BASE_URL/v1/matches" "${auth_header[@]}")
cat /tmp/soulmatch_phase_a_gate.json; echo
if [[ "$PRE_GATE" != "409" ]]; then
  echo "Expected /v1/matches to return 409 before identity onboarding. Got: $PRE_GATE"
  exit 1
fi

echo "== 5) Identity onboarding submit =="
onboarding_payload=$(cat <<JSON
{"birth":{"birth_date":"1997-06-20","birth_time":"09:30:00","birth_place_name":"Toronto, Canada","lat":43.6532,"lon":-79.3832,"timezone_iana":"America/Toronto","birth_datetime_utc":"1997-06-20T13:30:00Z","dst_flag":true},"psycho":{"answers":{"B5_O_01":2,"B5_O_02":3,"B5_O_03":4,"B5_O_04":5,"B5_C_01":1,"B5_C_02":2,"B5_C_03":3,"B5_C_04":4,"B5_E_01":5,"B5_E_02":1,"B5_E_03":2,"B5_E_04":3,"B5_A_01":4,"B5_A_02":5,"B5_A_03":1,"B5_A_04":2,"B5_N_01":3,"B5_N_02":4,"B5_N_03":5,"B5_N_04":1,"ATT_01":2,"ATT_02":3,"ATT_03":4,"ATT_04":5,"CON_01":1,"CON_02":2,"CON_03":3,"VAL_01":4,"VAL_02":5,"AFF_01":1},"response_ms":{"B5_O_01":1400,"B5_O_02":1400,"B5_O_03":1400,"B5_O_04":1400,"B5_C_01":1400,"B5_C_02":1400,"B5_C_03":1400,"B5_C_04":1400,"B5_E_01":1400,"B5_E_02":1400,"B5_E_03":1400,"B5_E_04":1400,"B5_A_01":1400,"B5_A_02":1400,"B5_A_03":1400,"B5_A_04":1400,"B5_N_01":1400,"B5_N_02":1400,"B5_N_03":1400,"B5_N_04":1400,"ATT_01":1400,"ATT_02":1400,"ATT_03":1400,"ATT_04":1400,"CON_01":1400,"CON_02":1400,"CON_03":1400,"VAL_01":1400,"VAL_02":1400,"AFF_01":1400}}}
JSON
)
ONBOARDING=$(curl -sS -X POST "$BASE_URL/v1/onboarding/submit" "${auth_header[@]}" "${json_header[@]}" -d "$onboarding_payload")
echo "$ONBOARDING"

printf "%s" "$ONBOARDING" | "$PYTHON_BIN" -c '
import json, sys
payload = json.load(sys.stdin)
stage = payload.get("stage")
if stage != "eligible":
    raise SystemExit(f"Expected onboarding stage=eligible, got {stage!r}")
print(f"stage={stage} overall_confidence={payload.get('overall_confidence')}")
'

echo "== 6) Top-7 matches =="
MATCHES=$(curl -sS "$BASE_URL/v1/matches" "${auth_header[@]}")
echo "$MATCHES"
printf "%s" "$MATCHES" | "$PYTHON_BIN" -c '
import json, sys
payload = json.load(sys.stdin)
if not isinstance(payload, list):
    raise SystemExit("Expected list payload from /v1/matches")
if len(payload) > 7:
    raise SystemExit(f"Expected at most 7 matches, got {len(payload)}")
scores = [float(item.get("final_score", 0.0)) for item in payload]
if scores != sorted(scores, reverse=True):
    raise SystemExit(f"Expected matches sorted by final_score desc, got {scores}")
print(f"match_count={len(payload)}")
'

CANDIDATE_ID=$(printf "%s" "$MATCHES" | "$PYTHON_BIN" -c 'import sys,json; d=json.load(sys.stdin); print((d or [{}])[0].get("other_user_id","")) if isinstance(d, list) else print("")')
if [[ -n "$CANDIDATE_ID" ]]; then
  echo "== 7) Explain/prediction/timing/openers =="
  curl -sS "$BASE_URL/v1/matches/$USER_ID/explain/$CANDIDATE_ID?mode=romance&match_mode=destiny" "${auth_header[@]}"; echo
  curl -sS "$BASE_URL/v1/matches/$USER_ID/prediction/$CANDIDATE_ID?mode=romance&match_mode=attraction" "${auth_header[@]}"; echo
  curl -sS "$BASE_URL/v1/matches/$USER_ID/timing/$CANDIDATE_ID?mode=romance" "${auth_header[@]}"; echo
  curl -sS "$BASE_URL/v1/matches/$USER_ID/openers/$CANDIDATE_ID?tone=playful" "${auth_header[@]}"; echo
else
  echo "No candidate returned from /v1/matches; skipping explain/prediction/timing/openers."
fi

echo "== 8) Health + deploy verifier =="
curl -sS "$BASE_URL/health/live"; echo
curl -sS "$BASE_URL/health/ready"; echo
curl -sS "$BASE_URL/health/jobs"; echo
"$PYTHON_BIN" -m scripts.verify_deploy_target --base-url "$BASE_URL" --timeout 3

echo "== Trial complete =="
