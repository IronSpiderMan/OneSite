#!/usr/bin/env bash
# ============================================================================
# Permission Demo — API Test Suite
# ============================================================================
# Tests every permission boundary with each role (user/admin/developer).
# Requires the backend server to be running:
#
#     cd examples/permission_demo
#     python seed.py            # ← seed the database first
#     site run backend          # ← start the API server
#     bash samples/test_api.sh  # ← run this test suite
# ============================================================================
set -euo pipefail

BASE_URL="${API_URL:-http://localhost:8000/api/v1}"
PASS=0
FAIL=0

# ── Helpers ───────────────────────────────────────────────────────────────

login() {
  local role="$1"
  case "$role" in
    user)      curl -s -X POST "$BASE_URL/login/access-token" \
                   -H "Content-Type: application/x-www-form-urlencoded" \
                   -d "username=alice@example.com&password=password123" \
                 | sed 's/.*"access_token":"\([^"]*\)".*/\1/' ;;
    admin)     curl -s -X POST "$BASE_URL/login/access-token" \
                   -H "Content-Type: application/x-www-form-urlencoded" \
                   -d "username=bob@example.com&password=password123" \
                 | sed 's/.*"access_token":"\([^"]*\)".*/\1/' ;;
    developer) curl -s -X POST "$BASE_URL/login/access-token" \
                   -H "Content-Type: application/x-www-form-urlencoded" \
                   -d "username=carol@example.com&password=password123" \
                 | sed 's/.*"access_token":"\([^"]*\)".*/\1/' ;;
  esac
}

auth_header() {
  local token="$1"
  echo "Authorization: Bearer $token"
}

test_get() {
  local token="$1" url="$2" expected="$3" label="$4"
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" -H "$(auth_header "$token")" "$url")
  if [ "$status" = "$expected" ]; then
    echo "  ✅ GET $label → $status (expected $expected)"
    ((PASS++))
  else
    echo "  ❌ GET $label → $status (expected $expected)"
    ((FAIL++))
  fi
}

test_post() {
  local token="$1" url="$2" data="$3" expected="$4" label="$5"
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "$(auth_header "$token")" \
    -H "Content-Type: application/json" \
    -d "$data" "$url")
  if [ "$status" = "$expected" ]; then
    echo "  ✅ POST $label → $status (expected $expected)"
    ((PASS++))
  else
    echo "  ❌ POST $label → $status (expected $expected)"
    ((FAIL++))
  fi
}

test_put() {
  local token="$1" url="$2" data="$3" expected="$4" label="$5"
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
    -H "$(auth_header "$token")" \
    -H "Content-Type: application/json" \
    -d "$data" "$url")
  if [ "$status" = "$expected" ]; then
    echo "  ✅ PUT $label → $status (expected $expected)"
    ((PASS++))
  else
    echo "  ❌ PUT $label → $status (expected $expected)"
    ((FAIL++))
  fi
}

test_delete() {
  local token="$1" url="$2" expected="$3" label="$4"
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
    -H "$(auth_header "$token")" "$url")
  if [ "$status" = "$expected" ]; then
    echo "  ✅ DELETE $label → $status (expected $expected)"
    ((PASS++))
  else
    echo "  ❌ DELETE $label → $status (expected $expected)"
    ((FAIL++))
  fi
}

# ── Setup: Login as each role ─────────────────────────────────────────────

echo "═══════════════════════════════════════════════════════════════"
echo "  Permission Demo — API Test Suite"
echo "═══════════════════════════════════════════════════════════════"
echo ""

echo "🔑 Logging in..."
TOKEN_USER=$(login "user")
TOKEN_ADMIN=$(login "admin")
TOKEN_DEV=$(login "developer")

if [ -z "$TOKEN_USER" ] || [ -z "$TOKEN_ADMIN" ] || [ -z "$TOKEN_DEV" ]; then
  echo "❌ Failed to obtain tokens. Is the server running?"
  exit 1
fi
echo "  user token:      ${TOKEN_USER:0:20}..."
echo "  admin token:     ${TOKEN_ADMIN:0:20}..."
echo "  developer token: ${TOKEN_DEV:0:20}..."
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PublicArticle — all roles crud
# ═══════════════════════════════════════════════════════════════════════════
echo "📄 PublicArticle (all roles: crud)"
test_get    "$TOKEN_USER"    "$BASE_URL/public_articles"         200 "list (user)"
test_get    "$TOKEN_ADMIN"   "$BASE_URL/public_articles"         200 "list (admin)"
test_get    "$TOKEN_DEV"     "$BASE_URL/public_articles"         200 "list (developer)"
test_get    "$TOKEN_USER"    "$BASE_URL/public_articles/1"       200 "detail (user)"
test_post   "$TOKEN_USER"    "$BASE_URL/public_articles" \
  '{"title":"Test","content":"test","is_published":true}'        200 "create (user)"
test_put    "$TOKEN_USER"    "$BASE_URL/public_articles/1" \
  '{"title":"Updated"}'                                          200 "update (user)"
test_delete "$TOKEN_USER"    "$BASE_URL/public_articles/4"       200 "delete (user, draft)"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# MemberOnlyPost — user=r | admin=cru | developer=crud
# ═══════════════════════════════════════════════════════════════════════════
echo "🔒 MemberOnlyPost (user=r | admin=cru | developer=crud)"
test_get    "$TOKEN_USER"    "$BASE_URL/member_only_posts"         200 "list (user)"
test_get    "$TOKEN_ADMIN"   "$BASE_URL/member_only_posts"         200 "list (admin)"
test_get    "$TOKEN_DEV"     "$BASE_URL/member_only_posts"         200 "list (developer)"
test_get    "$TOKEN_USER"    "$BASE_URL/member_only_posts/1"       200 "detail (user)"
test_post   "$TOKEN_USER"    "$BASE_URL/member_only_posts" \
  '{"title":"Hack","content":"should fail","member_level":"gold"}' 403 "create (user → 403)"
test_post   "$TOKEN_ADMIN"   "$BASE_URL/member_only_posts" \
  '{"title":"Admin Post","content":"admin created","member_level":"gold"}' 200 "create (admin)"
test_put    "$TOKEN_USER"    "$BASE_URL/member_only_posts/1" \
  '{"title":"Hacked"}'                                             403 "update (user → 403)"
test_put    "$TOKEN_ADMIN"   "$BASE_URL/member_only_posts/1" \
  '{"title":"Admin Updated"}'                                      200 "update (admin)"
test_delete "$TOKEN_USER"    "$BASE_URL/member_only_posts/4"       403 "delete (user → 403)"
test_delete "$TOKEN_ADMIN"   "$BASE_URL/member_only_posts/4"       403 "delete (admin → 403)"
test_delete "$TOKEN_DEV"     "$BASE_URL/member_only_posts/4"       200 "delete (developer)"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PremiumContent — admin+ only
# ═══════════════════════════════════════════════════════════════════════════
echo "⭐ PremiumContent (admin+ only)"
test_get    "$TOKEN_USER"    "$BASE_URL/premium_contents"          403 "list (user → 403)"
test_get    "$TOKEN_ADMIN"   "$BASE_URL/premium_contents"          200 "list (admin)"
test_get    "$TOKEN_DEV"     "$BASE_URL/premium_contents"          200 "list (developer)"
test_post   "$TOKEN_USER"    "$BASE_URL/premium_contents" \
  '{"title":"Hack","body":"nope","price":0}'                       403 "create (user → 403)"
test_post   "$TOKEN_ADMIN"   "$BASE_URL/premium_contents" \
  '{"title":"Admin Item","body":"admin body","price":10}'          200 "create (admin)"
test_delete "$TOKEN_ADMIN"   "$BASE_URL/premium_contents/3"        200 "delete (admin)"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# AdminConfig (singleton) — admin+ only
# ═══════════════════════════════════════════════════════════════════════════
echo "⚙️  AdminConfig (singleton, admin+ only)"
test_get    "$TOKEN_USER"    "$BASE_URL/admin_config"              403 "get (user → 403)"
test_get    "$TOKEN_ADMIN"   "$BASE_URL/admin_config"              200 "get (admin)"
test_get    "$TOKEN_DEV"     "$BASE_URL/admin_config"              200 "get (developer)"
test_put    "$TOKEN_USER"    "$BASE_URL/admin_config" \
  '{"site_name":"Hacked"}'                                         403 "update (user → 403)"
test_put    "$TOKEN_ADMIN"   "$BASE_URL/admin_config" \
  '{"site_name":"Admin Updated"}'                                  200 "update (admin)"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# SecretConfig (singleton) — developer only
# ═══════════════════════════════════════════════════════════════════════════
echo "🔐 SecretConfig (singleton, developer only)"
test_get    "$TOKEN_USER"    "$BASE_URL/secret_config"             403 "get (user → 403)"
test_get    "$TOKEN_ADMIN"   "$BASE_URL/secret_config"             403 "get (admin → 403)"
test_get    "$TOKEN_DEV"     "$BASE_URL/secret_config"             200 "get (developer)"
test_put    "$TOKEN_USER"    "$BASE_URL/secret_config" \
  '{"api_key":"leaked"}'                                           403 "update (user → 403)"
test_put    "$TOKEN_ADMIN"   "$BASE_URL/secret_config" \
  '{"api_key":"leaked"}'                                           403 "update (admin → 403)"
test_put    "$TOKEN_DEV"     "$BASE_URL/secret_config" \
  '{"api_key":"sk-updated"}'                                       200 "update (developer)"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# UserProfile — user=cru | admin=cru | developer=crud
# ═══════════════════════════════════════════════════════════════════════════
echo "👤 UserProfile (user=cru | admin=cru | developer=crud)"
test_get    "$TOKEN_USER"    "$BASE_URL/user_profiles"             200 "list (user)"
test_get    "$TOKEN_ADMIN"   "$BASE_URL/user_profiles"             200 "list (admin)"
test_get    "$TOKEN_DEV"     "$BASE_URL/user_profiles"             200 "list (developer)"
test_delete "$TOKEN_USER"    "$BASE_URL/user_profiles/1"           403 "delete (user → 403)"
test_delete "$TOKEN_ADMIN"   "$BASE_URL/user_profiles/1"           403 "delete (admin → 403)"
test_delete "$TOKEN_DEV"     "$BASE_URL/user_profiles/1"           200 "delete (developer)"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════════"
echo "  Results:  $PASS passed,  $FAIL failed"
echo "═══════════════════════════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
