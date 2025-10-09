#!/bin/bash
set -e
echo "🧠 Running SyferStackV2 FastAPI Backend Audit..."
cd "$(dirname "$0")/backend"

# 1️⃣ Framework check
if grep -q "FastAPI" app/main.py; then
  echo "✅ Framework: FastAPI detected"
else
  echo "⚠️ Warning: FastAPI not found"
fi

# 2️⃣ Python environment check
echo "🐍 Checking Python environment..."
if command -v poetry &> /dev/null; then
  echo "Poetry detected — running 'poetry check'"
  poetry check || echo "⚠️ Poetry check failed"
elif command -v pip &> /dev/null; then
  echo "Using pip — verifying dependencies..."
  pip check || echo "⚠️ Some dependencies may have issues"
fi

# 3️⃣ Syntax / lint
echo "🔍 Checking syntax..."
find app -type f -name "*.py" -print0 | xargs -0 -n1 python3 -m py_compile 2>/tmp/syfer_syntax.log || true
if [ -s /tmp/syfer_syntax.log ]; then
  echo "⚠️ Syntax issues found:"
  cat /tmp/syfer_syntax.log
else
  echo "✅ No syntax errors detected."
fi

# 4️⃣ Docker / Compose check
echo "🐳 Checking Docker configuration..."
docker compose config -q && echo "✅ Docker Compose is valid." || echo "⚠️ Docker Compose validation failed."

# 5️⃣ LLM-assisted code review
echo "🤖 Running CodeLlama audit..."
find . -type f \( -name "*.py" -o -name "*.toml" -o -name "*.yml" \) \
 -exec echo "=== {} ===" \; -exec cat {} \; > /tmp/syfer_backend_code.txt
ollama run codellama "Perform a security and dependency analysis for this FastAPI backend codebase:" < /tmp/syfer_backend_code.txt
