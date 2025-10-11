#!/bin/bash
# SyferStackV2 Full-Stack Audit Runner
# Performs comprehensive code analysis on both frontend and backend

set -e

echo "🚀 SyferStackV2 Full-Stack Audit Starting..."
echo "================================================="

# Check if Ollama is running
echo "🔍 Checking Ollama service..."
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "⚠️  Ollama not running. Starting Ollama..."
    # You may need to adjust this based on your Ollama setup
    # ollama serve &
    # sleep 5
    echo "❌ Please start Ollama manually: ollama serve"
    exit 1
fi

# Check if required model is available
echo "🤖 Checking for model: llama3:8b-instruct..."
if ! ollama list | grep -q "llama3:8b-instruct"; then
    echo "📥 Pulling required model..."
    ollama pull llama3:8b-instruct
fi

# Install Python dependencies if needed
echo "📦 Checking Python dependencies..."
if ! python3 -c "import requests" 2>/dev/null; then
    echo "Installing requests..."
    pip3 install requests
fi

# Install frontend dependencies if needed
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    echo "📦 Checking frontend dependencies..."
    cd frontend
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi
    cd ..
fi

# Run the audit
echo "🔍 Running full-stack audit..."
python3 full_stack_audit.py

echo ""
echo "✅ Audit completed successfully!"
echo "📊 Check the reports/ directory for detailed results"