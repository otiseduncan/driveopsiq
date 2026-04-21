#!/usr/bin/env python3
"""
SyferStackV2 Python Audit System
Advanced AI-powered code auditing with structured analysis and reporting
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import argparse

class SyferStackAuditor:
    def __init__(self, model: str = "codellama:latest"):
        self.model = model
        self.project_root = Path.cwd()
        self.output_dir = self.project_root / ".ai_patches"
        self.docs_dir = self.project_root / "docs"
        self.report_file = self.output_dir / f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    def setup_directories(self):
        """Ensure required directories exist"""
        self.output_dir.mkdir(exist_ok=True)
        self.docs_dir.mkdir(exist_ok=True)
        
    def gather_context_docs(self) -> List[Path]:
        """Gather reference documents for AI context"""
        doc_patterns = ["*.md", "*.txt"]
        docs = []
        
        for pattern in doc_patterns:
            docs.extend(self.docs_dir.glob(pattern))
            
        # Sort by modification time, newest first
        return sorted(docs, key=lambda p: p.stat().st_mtime, reverse=True)[:3]
    
    def find_target_files(self) -> List[Path]:
        """Find all files that should be audited"""
        target_patterns = [
            "backend/**/*.py",
            "backend/**/Dockerfile*",
            "backend/**/*.yml",
            "backend/**/*.yaml", 
            "backend/**/*.conf",
            "frontend/**/*.ts",
            "frontend/**/*.js",
            "frontend/**/*.tsx",
            "frontend/**/*.jsx",
            ".github/**/*.yml",
            ".github/**/*.yaml"
        ]
        
        files = []
        for pattern in target_patterns:
            files.extend(self.project_root.glob(pattern))
            
        return [f for f in files if f.is_file()]
    
    def build_audit_prompt(self, docs: List[Path]) -> str:
        """Build comprehensive audit prompt with documentation context"""
        prompt = """You are a senior software engineer conducting a comprehensive production-readiness audit of SyferStackV2.

AUDIT CATEGORIES:
1. SECURITY: OWASP Top 10, authentication, authorization, input validation, CORS, rate limiting
2. OBSERVABILITY: Health checks, metrics, logging, tracing, monitoring
3. INFRASTRUCTURE: Docker optimization, Nginx hardening, container security
4. CI/CD: GitHub Actions, testing, security scans, deployment
5. PERFORMANCE: Caching, resource efficiency, image sizes, query optimization
6. CODE QUALITY: Type safety, error handling, documentation, maintainability

REQUIREMENTS:
- Output ONLY unified git-style diffs
- Focus on production-grade solutions
- Follow security best practices
- Implement comprehensive error handling
- Add proper logging and monitoring
- Optimize for performance and scalability

"""
        
        # Add documentation context
        for doc in docs:
            try:
                content = doc.read_text(encoding='utf-8')
                prompt += f"\n\n# Reference Documentation: {doc.name}\n{content}\n"
            except Exception as e:
                print(f"⚠️  Failed to read {doc}: {e}")
                
        return prompt
    
    def audit_file(self, file_path: Path, prompt: str) -> Dict:
        """Audit a single file using Ollama"""
        print(f"🧠 Auditing {file_path}...")
        
        try:
            file_content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            return {"error": f"Failed to read file: {e}", "file": str(file_path)}
            
        full_prompt = f"{prompt}\n\nFILE: {file_path}\n\n{file_content}"
        
        try:
            result = subprocess.run([
                "ollama", "run", self.model,
                "--system", "You are a senior engineer; output only unified git diffs.",
                "--prompt", full_prompt
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                diff_output = result.stdout.strip()
                output_file = self.output_dir / f"{file_path.name}.diff"
                
                if diff_output and len(diff_output) > 10:  # Only save non-trivial diffs
                    output_file.write_text(diff_output)
                    return {
                        "file": str(file_path),
                        "status": "success",
                        "diff_file": str(output_file),
                        "has_changes": True
                    }
                else:
                    return {
                        "file": str(file_path), 
                        "status": "no_changes",
                        "has_changes": False
                    }
            else:
                return {
                    "file": str(file_path),
                    "status": "error", 
                    "error": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {"file": str(file_path), "status": "timeout"}
        except Exception as e:
            return {"file": str(file_path), "status": "error", "error": str(e)}
    
    def generate_report(self, results: List[Dict]):
        """Generate comprehensive audit report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "model": self.model,
            "total_files": len(results),
            "files_with_changes": len([r for r in results if r.get("has_changes")]),
            "errors": len([r for r in results if r.get("status") == "error"]),
            "results": results,
            "summary": {
                "success_rate": len([r for r in results if r.get("status") == "success"]) / len(results) * 100,
                "change_rate": len([r for r in results if r.get("has_changes")]) / len(results) * 100
            }
        }
        
        self.report_file.write_text(json.dumps(report, indent=2))
        return report
    
    def run_audit(self, target_files: Optional[List[str]] = None) -> Dict:
        """Run comprehensive audit"""
        print("🚀 Starting SyferStackV2 Production Audit")
        print("=" * 50)
        
        self.setup_directories()
        
        # Gather context
        docs = self.gather_context_docs()
        print(f"📚 Using {len(docs)} reference documents:")
        for doc in docs:
            print(f"   - {doc.name}")
        print()
        
        # Build audit prompt
        prompt = self.build_audit_prompt(docs)
        
        # Find files to audit
        if target_files:
            files = [Path(f) for f in target_files if Path(f).exists()]
        else:
            files = self.find_target_files()
            
        print(f"🎯 Auditing {len(files)} files...")
        print()
        
        # Audit each file
        results = []
        for file_path in files:
            result = self.audit_file(file_path, prompt)
            results.append(result)
            
            # Progress indicator
            status = result.get("status", "unknown")
            if status == "success" and result.get("has_changes"):
                print(f"   ✅ {file_path.name} - improvements generated")
            elif status == "no_changes":
                print(f"   ✨ {file_path.name} - no changes needed")
            elif status == "error":
                print(f"   ❌ {file_path.name} - error occurred")
            else:
                print(f"   ⏸️  {file_path.name} - {status}")
        
        # Generate report
        report = self.generate_report(results)
        
        print()
        print("=" * 50)
        print("📊 AUDIT COMPLETE")
        print(f"Files audited: {report['total_files']}")
        print(f"Files with improvements: {report['files_with_changes']}")
        print(f"Success rate: {report['summary']['success_rate']:.1f}%")
        print(f"Change rate: {report['summary']['change_rate']:.1f}%")
        print()
        print(f"📁 Patches saved to: {self.output_dir}")
        print(f"📋 Report saved to: {self.report_file}")
        print()
        print("👉 Apply patches with:")
        print(f"   for p in {self.output_dir}/*.diff; do git apply $p || echo Failed $p; done")
        
        return report

def main():
    parser = argparse.ArgumentParser(description="SyferStackV2 AI Audit System")
    parser.add_argument("--model", default="codellama:latest", help="Ollama model to use")
    parser.add_argument("--files", nargs="*", help="Specific files to audit")
    parser.add_argument("--report-only", action="store_true", help="Generate report from existing patches")
    
    args = parser.parse_args()
    
    auditor = SyferStackAuditor(model=args.model)
    
    if args.report_only:
        # TODO: Implement report-only mode
        print("Report-only mode not yet implemented")
        return
        
    try:
        auditor.run_audit(target_files=args.files)
    except KeyboardInterrupt:
        print("\n🛑 Audit interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Audit failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()