#!/bin/bash
# MRABILITY Finance Backend Startup Script

echo "========================================"
echo "  MRABILITY Finance — Backend Server"
echo "========================================"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/venv"

# ── Auto-create venv if missing ───────────────────────
if [ ! -d "$VENV" ]; then
  echo ""
  echo "📦 Creating virtual environment..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q flask flask-cors pyjwt bcrypt cryptography typing_extensions
  echo "✅ Virtual environment ready."
fi

echo ""
echo "🌐  Website          :  http://localhost:8080"
echo "🛡️  Admin Dashboard  :  http://localhost:8080/admin.html"
echo "👤  Default Admin    :  admin@mrability.in / Admin@1234"
echo ""

# ── Show OAuth status (credentials come from .env automatically) ──
# Load .env just to check values for this display message
if [ -f "$DIR/.env" ]; then
  source <(grep -v '^\s*#' "$DIR/.env" | grep -v '^\s*$' | sed 's/^/export /')
fi

if [ -z "$GOOGLE_CLIENT_ID" ]; then
  echo "⚪  Google Login     :  NOT configured"
  echo "   → Fill in GOOGLE_CLIENT_ID in your .env file to enable"
else
  echo "✅  Google Login     :  ENABLED  (${GOOGLE_CLIENT_ID:0:25}...)"
fi

if [ -z "$FACEBOOK_APP_ID" ]; then
  echo "⚪  Facebook Login   :  NOT configured"
  echo "   → Fill in FACEBOOK_APP_ID in your .env file to enable"
else
  echo "✅  Facebook Login   :  ENABLED  (App ID: $FACEBOOK_APP_ID)"
fi

echo ""
echo "💡  OAuth credentials are read from:  .env  (edit once, works forever)"
echo "Press Ctrl+C to stop the server."
echo "========================================"
echo ""

cd "$DIR"
"$VENV/bin/python3" server.py
