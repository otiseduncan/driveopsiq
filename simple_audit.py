#!/usr/bin/env python3
import argparse, subprocess, json, os

def run_llama(prompt: str) -> str:
    """Send prompt to CodeLlama via Ollama."""
    process = subprocess.Popen(
        ["ollama", "run", "codellama:latest"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True
    )
    output, _ = process.communicate(prompt)
    return output

def main():
    parser = argparse.ArgumentParser(description="SyferStack AI Audit")
    parser.add_argument("--input-file", required=True, help="File to audit")
    parser.add_argument("--output-file", required=True, help="Output file")
    args = parser.parse_args()

    with open(args.input_file, "r", encoding="utf-8") as f:
        input_text = f.read()

    prompt = f"""
You are a senior software engineer and security auditor.
Perform a detailed analysis and correction of this file for production readiness.
Check for:
- Security vulnerabilities (OWASP Top 10, unsafe imports, missing auth, unvalidated input)
- Performance and monitoring gaps
- Misconfigured CORS or headers
- Logging, error handling, and observability issues
- Code smells or anti-patterns

Then output a corrected, production-safe version of the file.

=== FILE CONTENT START ===
{input_text}
=== FILE CONTENT END ===
"""
    print(f"🧠 Auditing {args.input_file} with CodeLlama...")
    result = run_llama(prompt)

    with open(args.output_file, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"✅ Audit complete → {args.output_file}")

if __name__ == "__main__":
    main()