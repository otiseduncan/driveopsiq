#!/usr/bin/env python3
import os, subprocess, json, requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3:8b-instruct"

def analyze_file(path: str):
    with open(path, "r", errors="ignore") as f:
        code = f.read()
    prompt = f"""
You are a senior software engineer performing a production audit.
Review the following code for:
1. Logic or syntax errors
2. Security or performance issues
3. Improvements to make it production ready
Respond in JSON: {{"file": "{path}", "issues": [], "recommendations": []}}

CODE:
{code[:5000]}
"""
    r = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False})
    return json.loads(r.text)["response"]

def run_static_tools():
    """Run static analysis tools for both backend and frontend"""
    tools = {
        # Backend Python tools
        "ruff": ["ruff", "check", "--output-format", "json", "backend/"],
        "mypy": ["mypy", "--json-report", "reports/mypy", "backend/"],
        "bandit": ["bandit", "-r", "backend/", "-f", "json"],
        
        # Frontend TypeScript/JavaScript tools
        "eslint": ["npx", "eslint", "frontend/src", "--format", "json", "--output-file", "reports/eslint.json"],
        "typescript": ["npx", "tsc", "--noEmit", "--project", "frontend/tsconfig.json"],
        "audit-npm": ["npm", "audit", "--json", "--prefix", "frontend/"]
    }
    
    os.makedirs("reports", exist_ok=True)
    
    for name, cmd in tools.items():
        try:
            print(f"Running {name}...")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            # Save output for JSON-formatted tools
            if name in ["ruff", "bandit", "eslint", "audit-npm"]:
                output_file = f"reports/{name}.json"
                with open(output_file, "w") as f:
                    f.write(result.stdout if result.stdout else "[]")
                    
            print(f"✅ {name} completed")
        except Exception as e:
            print(f"❌ {name} failed: {e}")

def main():
    """Main audit function for full-stack analysis"""
    print("🔍 Starting SyferStackV2 Full-Stack Audit...")
    
    # Run static analysis tools
    run_static_tools()
    
    # Analyze individual files with LLM
    print("🤖 Running LLM-based code analysis...")
    results = []
    
    # Define directories to scan
    scan_dirs = ["backend/app", "frontend/src"]
    
    for scan_dir in scan_dirs:
        if os.path.exists(scan_dir):
            print(f"Scanning {scan_dir}...")
            for root, _, files in os.walk(scan_dir):
                for file in files:
                    if file.endswith((".py", ".tsx", ".ts", ".js", ".vue")):
                        file_path = os.path.join(root, file)
                        try:
                            print(f"  Analyzing {file_path}")
                            result = analyze_file(file_path)
                            results.append(result)
                        except Exception as e:
                            print(f"  ⚠️  Failed to analyze {file_path}: {e}")
        else:
            print(f"⚠️  Directory {scan_dir} not found, skipping...")
    
    # Save LLM analysis results
    with open("reports/llm_audit.json", "w") as out:
        json.dump(results, out, indent=2)
    
    print("\n✅ Full-stack audit complete!")
    print("📊 Reports generated:")
    print("  - reports/llm_audit.json (LLM analysis)")
    print("  - reports/ruff.json (Python linting)")
    print("  - reports/bandit.json (Security analysis)")
    print("  - reports/eslint.json (Frontend linting)")
    print("  - reports/mypy/ (Type checking)")

if __name__ == "__main__":
    main()