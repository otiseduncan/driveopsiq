#!/bin/bash
# SyferStackV2 AI revision harness (Ollama + CodeLlama)
set -e

MODEL="codellama:latest"
OUT_DIR=".ai_patches"
PROMPT_FILE=".ai_prompt.txt"

mkdir -p "$OUT_DIR"

cat > "$PROMPT_FILE" <<'EOF'
You are a senior software engineer reviewing SyferStackV2.
Implement the remaining production-readiness improvements:

1. Add/verify observability:
   - Prometheus /metrics
   - /health uptime logic
2. Harden Nginx (TLS, security headers, gzip, cache)
3. Update Docker Compose with Prometheus + Grafana services
4. Add Bandit + Trivy scans to .github/workflows
5. Review rate-limiting + CORS + TrustedHostMiddleware
6. Output *only* valid unified git-style diffs for each file.

Do not output explanations or commentary—diffs only.
EOF

FILES="
backend/app/main.py
backend/nginx/nginx.conf
backend/docker-compose.yml
.github/workflows/backend.yml
"

for f in $FILES; do
  echo "🧠  Sending $f to CodeLlama..."
  ollama run "$MODEL" --system "You are a senior engineer; output only diffs." \
    --prompt "$(cat "$PROMPT_FILE"; echo; echo 'FILE:' $f; echo; cat "$f")" \
    > "$OUT_DIR/$(basename "$f").diff"
done

echo "✅  Diffs written to $OUT_DIR/"
echo "👉  Review them, then apply with:"
echo "    for p in $OUT_DIR/*.diff; do git apply \$p || echo Failed \$p; done"