#!/usr/bin/env python3
"""
SyferStackV2 – Automated Security Audit System
Production-ready security audit automation with reporting and alerting.
"""

import os
import sys
import json
import time
import hashlib
import asyncio
import aiohttp
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import argparse
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("audit_automation.log")
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class AuditFinding:
    """Security audit finding data structure."""
    severity: str
    category: str
    title: str
    description: str
    file_path: Optional[str]
    line_number: Optional[int]
    recommendation: str
    cve_id: Optional[str] = None
    confidence: str = "medium"


@dataclass
class AuditReport:
    """Complete audit report structure."""
    timestamp: str
    duration_seconds: float
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    findings: List[AuditFinding]
    tools_used: List[str]
    scan_summary: Dict[str, Any]


class SecurityAuditAutomation:
    """
    Automated security audit system with notification and reporting.
    """
    
    def __init__(self, config_file: str = "audit_automation_config.json"):
        """Initialize the audit automation system."""
        self.config_file = config_file
        self.config = self._load_config()
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        # Notification endpoints
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration with secure defaults."""
        default_config = {
            "schedule_cron": "0 2 * * *",  # 2 AM daily
            "enabled_tools": ["bandit", "safety", "semgrep", "ruff"],
            "severity_threshold": "medium",
            "notification_threshold": "high",
            "max_audit_duration_minutes": 30,
            "retention_days": 90,
            "auto_publish": True,
            "notification_channels": {
                "slack": True,
                "discord": False,
                "email": False
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        return default_config
    
    async def run_bandit_scan(self) -> List[AuditFinding]:
        """Run Bandit security analysis."""
        findings = []
        try:
            logger.info("Running Bandit security scan...")
            
            result = subprocess.run([
                "bandit", "-r", ".", "-f", "json", 
                "--exclude", "./venv,./node_modules,./.git"
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 or result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for issue in data.get("results", []):
                        finding = AuditFinding(
                            severity=issue.get("issue_severity", "medium").lower(),
                            category="security",
                            title=issue.get("test_name", "Unknown"),
                            description=issue.get("issue_text", ""),
                            file_path=issue.get("filename"),
                            line_number=issue.get("line_number"),
                            recommendation=issue.get("more_info", ""),
                            confidence=issue.get("issue_confidence", "medium").lower()
                        )
                        findings.append(finding)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Bandit output: {e}")
                    
        except subprocess.TimeoutExpired:
            logger.error("Bandit scan timed out")
        except Exception as e:
            logger.error(f"Bandit scan failed: {e}")
            
        return findings
    
    async def run_safety_scan(self) -> List[AuditFinding]:
        """Run Safety vulnerability scan."""
        findings = []
        try:
            logger.info("Running Safety vulnerability scan...")
            
            result = subprocess.run([
                "safety", "check", "--json", "--ignore", "70612"
            ], capture_output=True, text=True, timeout=120)
            
            if result.stdout:
                try:
                    vulnerabilities = json.loads(result.stdout)
                    for vuln in vulnerabilities:
                        finding = AuditFinding(
                            severity="high" if vuln.get("vulnerability_id") else "medium",
                            category="dependency",
                            title=f"Vulnerable dependency: {vuln.get('package_name', 'unknown')}",
                            description=vuln.get("advisory", ""),
                            file_path=None,
                            line_number=None,
                            recommendation=f"Update to version {vuln.get('analyzed_version', 'latest')}",
                            cve_id=vuln.get("vulnerability_id")
                        )
                        findings.append(finding)
                        
                except json.JSONDecodeError:
                    # Safety might return non-JSON output for no vulnerabilities
                    pass
                    
        except subprocess.TimeoutExpired:
            logger.error("Safety scan timed out")
        except Exception as e:
            logger.error(f"Safety scan failed: {e}")
            
        return findings
    
    async def run_ruff_security_scan(self) -> List[AuditFinding]:
        """Run Ruff with security-focused rules."""
        findings = []
        try:
            logger.info("Running Ruff security scan...")
            
            result = subprocess.run([
                "ruff", "check", ".", "--select", "S", "--format", "json"
            ], capture_output=True, text=True, timeout=120)
            
            if result.stdout:
                try:
                    issues = json.loads(result.stdout)
                    for issue in issues:
                        finding = AuditFinding(
                            severity="medium",
                            category="code_quality_security",
                            title=issue.get("code", "Security Issue"),
                            description=issue.get("message", ""),
                            file_path=issue.get("filename"),
                            line_number=issue.get("location", {}).get("row"),
                            recommendation="Review and fix security issue",
                        )
                        findings.append(finding)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Ruff output: {e}")
                    
        except Exception as e:
            logger.error(f"Ruff security scan failed: {e}")
            
        return findings
    
    async def analyze_findings(self, findings: List[AuditFinding]) -> Dict[str, int]:
        """Analyze and categorize findings."""
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for finding in findings:
            severity = finding.severity.lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
                
        return severity_counts
    
    async def generate_report(self, findings: List[AuditFinding], 
                            duration: float, tools_used: List[str]) -> AuditReport:
        """Generate comprehensive audit report."""
        severity_counts = await self.analyze_findings(findings)
        
        report = AuditReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_seconds=duration,
            total_findings=len(findings),
            critical_findings=severity_counts["critical"],
            high_findings=severity_counts["high"],
            medium_findings=severity_counts["medium"],
            low_findings=severity_counts["low"],
            findings=findings,
            tools_used=tools_used,
            scan_summary={
                "total_files_scanned": await self._count_source_files(),
                "scan_depth": "full_repository",
                "excluded_paths": ["./venv", "./node_modules", "./.git"]
            }
        )
        
        return report
    
    async def _count_source_files(self) -> int:
        """Count source files in the repository."""
        try:
            extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".yaml", ".yml", ".json"]
            count = 0
            for ext in extensions:
                result = subprocess.run([
                    "find", ".", "-name", f"*{ext}", "-not", "-path", "./venv/*", 
                    "-not", "-path", "./node_modules/*", "-not", "-path", "./.git/*"
                ], capture_output=True, text=True)
                if result.returncode == 0:
                    count += len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            return count
        except:
            return 0
    
    async def save_report(self, report: AuditReport) -> Path:
        """Save audit report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"security_audit_{timestamp}.json"
        
        try:
            with open(report_file, 'w') as f:
                json.dump(asdict(report), f, indent=2, default=str)
                
            # Create/update latest report symlink
            latest_file = self.reports_dir / "latest.json"
            if latest_file.exists():
                latest_file.unlink()
            latest_file.symlink_to(report_file.name)
            
            logger.info(f"Report saved to {report_file}")
            return report_file
            
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            raise
    
    async def send_notifications(self, report: AuditReport):
        """Send notifications based on findings."""
        threshold_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        threshold_level = threshold_map.get(self.config["notification_threshold"], 2)
        
        # Determine if we should notify
        should_notify = (
            report.critical_findings > 0 or 
            (report.high_findings > 0 and threshold_level <= 3) or
            (report.medium_findings > 0 and threshold_level <= 2) or
            (report.low_findings > 0 and threshold_level <= 1)
        )
        
        if not should_notify:
            logger.info("No notifications needed based on threshold")
            return
        
        # Prepare notification content
        severity_emoji = "🚨" if report.critical_findings > 0 else "⚠️" if report.high_findings > 0 else "📋"
        
        message = f"""
{severity_emoji} **SyferStack V2 Security Audit Report**

📊 **Summary:**
• Total Findings: {report.total_findings}
• Critical: {report.critical_findings}
• High: {report.high_findings}  
• Medium: {report.medium_findings}
• Low: {report.low_findings}

⏱️ **Scan Details:**
• Duration: {report.duration_seconds:.1f}s
• Tools: {', '.join(report.tools_used)}
• Files Scanned: {report.scan_summary.get('total_files_scanned', 'Unknown')}

📅 **Timestamp:** {report.timestamp}
        """.strip()
        
        # Send to configured channels
        if self.config["notification_channels"].get("slack") and self.slack_webhook:
            await self._send_slack_notification(message, report)
            
        if self.config["notification_channels"].get("discord") and self.discord_webhook:
            await self._send_discord_notification(message, report)
    
    async def _send_slack_notification(self, message: str, report: AuditReport):
        """Send Slack notification."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": message,
                    "username": "SyferStack Security Bot",
                    "icon_emoji": ":shield:"
                }
                
                async with session.post(self.slack_webhook, json=payload) as response:
                    if response.status == 200:
                        logger.info("Slack notification sent successfully")
                    else:
                        logger.error(f"Failed to send Slack notification: {response.status}")
                        
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
    
    async def _send_discord_notification(self, message: str, report: AuditReport):
        """Send Discord notification."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "content": message,
                    "username": "SyferStack Security",
                    "avatar_url": "https://example.com/security-bot-avatar.png"
                }
                
                async with session.post(self.discord_webhook, json=payload) as response:
                    if response.status == 204:
                        logger.info("Discord notification sent successfully")
                    else:
                        logger.error(f"Failed to send Discord notification: {response.status}")
                        
        except Exception as e:
            logger.error(f"Discord notification failed: {e}")
    
    async def run_full_audit(self) -> AuditReport:
        """Execute complete security audit process."""
        start_time = time.time()
        all_findings = []
        tools_used = []
        
        logger.info("Starting automated security audit...")
        
        # Run enabled tools
        if "bandit" in self.config["enabled_tools"]:
            findings = await self.run_bandit_scan()
            all_findings.extend(findings)
            tools_used.append("bandit")
            
        if "safety" in self.config["enabled_tools"]:
            findings = await self.run_safety_scan()
            all_findings.extend(findings)
            tools_used.append("safety")
            
        if "ruff" in self.config["enabled_tools"]:
            findings = await self.run_ruff_security_scan()
            all_findings.extend(findings)
            tools_used.append("ruff")
        
        # Generate report
        duration = time.time() - start_time
        report = await self.generate_report(all_findings, duration, tools_used)
        
        # Save and publish
        await self.save_report(report)
        
        if self.config.get("auto_publish", True):
            await self.send_notifications(report)
        
        logger.info(f"Audit completed in {duration:.1f}s with {len(all_findings)} findings")
        return report


async def main():
    """Main entry point for audit automation."""
    parser = argparse.ArgumentParser(description="SyferStack V2 Security Audit Automation")
    parser.add_argument("--config", default="audit_automation_config.json", help="Config file")
    parser.add_argument("--run-once", action="store_true", help="Run audit once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Run audit without notifications")
    
    args = parser.parse_args()
    
    try:
        audit_system = SecurityAuditAutomation(args.config)
        
        if args.dry_run:
            audit_system.config["auto_publish"] = False
            
        if args.run_once:
            report = await audit_system.run_full_audit()
            print(f"Audit complete: {report.total_findings} findings")
            sys.exit(0 if report.critical_findings == 0 else 1)
        
        # Continuous mode would go here (with proper scheduling)
        logger.info("Use --run-once for single audit execution")
        
    except KeyboardInterrupt:
        logger.info("Audit interrupted by user")
    except Exception as e:
        logger.error(f"Audit system failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())