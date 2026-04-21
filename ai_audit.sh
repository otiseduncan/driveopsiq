#!/bin/bash
# SyferStackV2 AI Audit Harness (Ollama + CodeLlama)
# Purpose: audit + auto-correct code for production readiness

set -e
MODEL="codellama:latest"
OUT_DIR=".ai_patches"
DOCS_DIR="docs"
PROMPT_FILE=".ai_prompt.txt"

mkdir -p "$OUT_DIR"

# 🧩 Gather latest reference documents
DOCS=$(ls -t $DOCS_DIR/*.md $DOCS_DIR/*.txt 2>/dev/null | head -n 3)

echo "📚 Including context from:"
echo "$DOCS"
echo

# Merge docs into a single prompt base
cat > "$PROMPT_FILE" <<EOF
You are a senior software engineer conducting a full production-readiness audit of the SyferStackV2 project.
Audit focus:
- Security hardening (OWASP Top 10, JWT/OAuth, CORS, rate limiting)
- Observability (health checks, Prometheus metrics, logging)
- Infrastructure (Docker, Nginx, Compose, Grafana, Prometheus)
- CI/CD (GitHub Actions, tests, security scans)
- Performance (image sizes, caching, resource efficiency)
- Documentation consistency

Analyze each file and output only unified git-style diffs that correct any discovered issues or missing features.
Use clean, production-grade code and follow best practices.
EOF

# Append your guidance docs
for f in $DOCS; do
  echo -e "\n\n# Reference: $f\n" >> "$PROMPT_FILE"
  cat "$f" >> "$PROMPT_FILE"
done

FILES=$(find backend frontend .github -type f \( -name "*.py" -o -name "*.ts" -o -name "*.yml" -o -name "Dockerfile*" -o -name "*.conf" \) 2>/dev/null)

for f in $FILES; do
  echo "🧠 Auditing and fixing $f..."
  ollama run "$MODEL" \
    --system "You are a senior engineer; output only unified git diffs." \
    --prompt "$(cat "$PROMPT_FILE"; echo; echo 'FILE:' $f; echo; cat "$f")" \
    > "$OUT_DIR/$(basename "$f").diff" || echo "⚠️ Failed $f"
done

echo
echo "✅ Audit complete. Review patches in $OUT_DIR/"
echo "👉 Apply them with:"
echo "   for p in $OUT_DIR/*.diff; do git apply \$p || echo Failed \$p; done"