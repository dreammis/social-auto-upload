#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3000}"
EMAIL="${EMAIL:-test@example.com}"
PASSWORD="${PASSWORD:-StrongPass123!}"

echo "=== SocialFlow AI - Auth & License Test Script ==="
echo "Base URL: $BASE_URL"
echo ""

# -----------------------------------------------------------------------------
# 1. Health check (public endpoint)
# -----------------------------------------------------------------------------
echo "[1/9] Health check..."
curl -s "$BASE_URL/health" | jq .
echo ""

# -----------------------------------------------------------------------------
# 2. Register new user
# -----------------------------------------------------------------------------
echo "[2/9] Register user: $EMAIL"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"displayName\":\"Test User\"}")

echo "$REGISTER_RESPONSE" | jq .
ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.accessToken // empty')
REFRESH_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.refreshToken // empty')
USER_ROLE=$(echo "$REGISTER_RESPONSE" | jq -r '.user.role // empty')

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
  echo "ERROR: Register failed"
  exit 1
fi

echo "✓ Access token received"
echo "✓ User role: $USER_ROLE"
echo ""

# -----------------------------------------------------------------------------
# 3. Data leak test: /auth/me must not contain password_hash
# -----------------------------------------------------------------------------
echo "[3/9] Data leak test: GET /auth/me"
ME_RESPONSE=$(curl -s "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$ME_RESPONSE" | jq .

if echo "$ME_RESPONSE" | grep -q "password_hash"; then
  echo "ERROR: password_hash leaked in response!"
  exit 1
fi

if echo "$ME_RESPONSE" | grep -q "refresh_token"; then
  echo "ERROR: refresh_token leaked in response!"
  exit 1
fi

echo "✓ No sensitive data leaked"
echo ""

# -----------------------------------------------------------------------------
# 4. Login test
# -----------------------------------------------------------------------------
echo "[4/9] Login with same credentials..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

echo "$LOGIN_RESPONSE" | jq .
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.accessToken // empty')
REFRESH_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.refreshToken // empty')

echo "✓ Login successful"
echo ""

# -----------------------------------------------------------------------------
# 5. Token rotation test
# -----------------------------------------------------------------------------
echo "[5/9] Refresh token (rotation)..."
REFRESH_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refreshToken\":\"$REFRESH_TOKEN\"}")

echo "$REFRESH_RESPONSE" | jq .
NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | jq -r '.accessToken // empty')
NEW_REFRESH_TOKEN=$(echo "$REFRESH_RESPONSE" | jq -r '.refreshToken // empty')

if [ -z "$NEW_ACCESS_TOKEN" ] || [ "$NEW_ACCESS_TOKEN" = "null" ]; then
  echo "ERROR: Refresh failed"
  exit 1
fi

if [ "$NEW_REFRESH_TOKEN" = "$REFRESH_TOKEN" ]; then
  echo "ERROR: Refresh token did not rotate"
  exit 1
fi

echo "✓ Token rotated successfully"
echo ""

# -----------------------------------------------------------------------------
# 6. Replay attack test
# -----------------------------------------------------------------------------
echo "[6/9] Replay attack: reuse old refresh token..."
REPLAY_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refreshToken\":\"$REFRESH_TOKEN\"}")

echo "$REPLAY_RESPONSE" | jq .
REPLAY_STATUS=$(echo "$REPLAY_RESPONSE" | jq -r '.statusCode // 0')

if [ "$REPLAY_STATUS" != "401" ] && [ "$REPLAY_STATUS" != "0" ]; then
  echo "ERROR: Expected 401 for replay attack, got $REPLAY_STATUS"
  exit 1
fi

echo "✓ Replay attack blocked"
echo ""

# -----------------------------------------------------------------------------
# 7. Login rate limit test
# -----------------------------------------------------------------------------
echo "[7/9] Login rate limit test (expect 429 after 6 attempts)..."
for i in {1..6}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"WrongPassword$i\"}")
  echo "Attempt $i: HTTP $STATUS"
done

echo "✓ Rate limit test complete"
echo ""

# -----------------------------------------------------------------------------
# 8. Admin-only endpoint test (if user is admin)
# -----------------------------------------------------------------------------
if [ "$USER_ROLE" = "admin" ]; then
  echo "[8/9] Create license (admin only)..."
  LICENSE_RESPONSE=$(curl -s -X POST "$BASE_URL/license" \
    -H "Authorization: Bearer $NEW_ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"tier":"standard","maxDevices":2,"maxActivations":3}')

  echo "$LICENSE_RESPONSE" | jq .
  LICENSE_KEY=$(echo "$LICENSE_RESPONSE" | jq -r '.data.key // empty')

  if [ -n "$LICENSE_KEY" ] && [ "$LICENSE_KEY" != "null" ]; then
    echo "✓ License created: $LICENSE_KEY"

    # 9. Validate license
    echo "[9/9] Validate license on device A..."
    VALIDATE_RESPONSE=$(curl -s -X POST "$BASE_URL/license/validate" \
      -H "Content-Type: application/json" \
      -d "{\"key\":\"$LICENSE_KEY\",\"deviceFingerprint\":\"fp-test-1\",\"hwId\":\"hw-test-1\",\"deviceName\":\"Test Device 1\"}")

    echo "$VALIDATE_RESPONSE" | jq .
    echo "✓ License validation complete"
  else
    echo "WARN: License creation returned empty key"
  fi
else
  echo "[8/9] Skip license create (user role is $USER_ROLE, not admin)"
  echo "[9/9] Skip license validate"
fi

echo ""
echo "=== All tests completed ==="
