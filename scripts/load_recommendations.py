#!/usr/bin/env python3
"""
Load Recommendations System for SyferStackV2
Provides intelligent loading and processing of audit recommendations
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class Priority(Enum):
    """Priority levels for recommendations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(Enum):
    """Categories for recommendations."""
    SECURITY = "security"
    PERFORMANCE = "performance" 
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    TESTING = "testing"
    DOCUMENTATION = "documentation"


@dataclass
class Recommendation:
    """Individual recommendation from audit."""
    id: str
    title: str
    description: str
    priority: Priority
    category: Category
    file_path: str
    line_number: Optional[int] = None
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False
    estimated_effort: str = "medium"  # low, medium, high
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class RecommendationSummary:
    """Summary of all recommendations."""
    total_recommendations: int
    by_priority: Dict[str, int]
    by_category: Dict[str, int]
    auto_fixable_count: int
    estimated_total_effort: str
    most_common_issues: List[str]


class RecommendationLoader:
    """Loads and processes audit recommendations from various sources."""
    
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.recommendations: List[Recommendation] = []
        self.logger = logging.getLogger(__name__)
    
    def load_from_audit_report(self, report_path: Optional[Path] = None) -> List[Recommendation]:
        """Load recommendations from audit JSON report."""
        if report_path is None:
            report_path = self.reports_dir / "production_audit.json"
        
        if not report_path.exists():
            self.logger.warning(f"Audit report not found: {report_path}")
            return []
        
        try:
            with open(report_path) as f:
                audit_data = json.load(f)
            
            recommendations = []
            rec_id = 1
            
            # Process Ruff findings
            ruff_results = audit_data.get("ruff", [])
            if isinstance(ruff_results, list):
                for finding in ruff_results:
                    rec = self._create_recommendation_from_ruff(finding, rec_id)
                    if rec:
                        recommendations.append(rec)
                        rec_id += 1
            
            # Process Bandit findings
            bandit_results = audit_data.get("bandit", {}).get("results", [])
            for finding in bandit_results:
                rec = self._create_recommendation_from_bandit(finding, rec_id)
                if rec:
                    recommendations.append(rec)
                    rec_id += 1
            
            # Process MyPy findings
            mypy_output = audit_data.get("mypy", "")
            mypy_recs = self._parse_mypy_output(mypy_output, rec_id)
            recommendations.extend(mypy_recs)
            rec_id += len(mypy_recs)
            
            # Process LLM findings
            llm_files = audit_data.get("files", [])
            for file_analysis in llm_files:
                llm_recs = self._parse_llm_analysis(file_analysis, rec_id)
                recommendations.extend(llm_recs)
                rec_id += len(llm_recs)
            
            self.recommendations.extend(recommendations)
            self.logger.info(f"Loaded {len(recommendations)} recommendations from {report_path}")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error loading recommendations from {report_path}: {e}")
            return []
    
    def _create_recommendation_from_ruff(self, finding: Dict[str, Any], rec_id: int) -> Optional[Recommendation]:
        """Create recommendation from Ruff finding."""
        try:
            # Determine priority based on rule type
            rule_id = finding.get("code", "")
            priority = Priority.MEDIUM
            
            if rule_id.startswith(("E", "F")):  # Errors
                priority = Priority.HIGH
            elif rule_id.startswith("W"):  # Warnings
                priority = Priority.MEDIUM
            elif rule_id.startswith(("N", "D")):  # Naming, docstrings
                priority = Priority.LOW
            
            # Determine category
            category = Category.STYLE
            if rule_id.startswith(("S", "B")):  # Security
                category = Category.SECURITY
                priority = Priority.HIGH
            elif rule_id.startswith("PERF"):  # Performance
                category = Category.PERFORMANCE
            
            return Recommendation(
                id=f"ruff-{rec_id}",
                title=f"Ruff: {rule_id}",
                description=finding.get("message", "Code quality issue"),
                priority=priority,
                category=category,
                file_path=finding.get("filename", ""),
                line_number=finding.get("row"),
                auto_fixable=finding.get("fix_available", False),
                estimated_effort="low"
            )
        except Exception as e:
            self.logger.error(f"Error processing Ruff finding: {e}")
            return None
    
    def _create_recommendation_from_bandit(self, finding: Dict[str, Any], rec_id: int) -> Optional[Recommendation]:
        """Create recommendation from Bandit finding."""
        try:
            severity = finding.get("issue_severity", "MEDIUM").upper()
            priority = Priority.MEDIUM
            
            if severity == "HIGH":
                priority = Priority.CRITICAL
            elif severity == "MEDIUM":
                priority = Priority.HIGH
            elif severity == "LOW":
                priority = Priority.MEDIUM
            
            return Recommendation(
                id=f"bandit-{rec_id}",
                title=f"Security: {finding.get('test_name', 'Security Issue')}",
                description=finding.get("issue_text", "Security vulnerability detected"),
                priority=priority,
                category=Category.SECURITY,
                file_path=finding.get("filename", ""),
                line_number=finding.get("line_number"),
                auto_fixable=False,  # Security fixes usually need manual review
                estimated_effort="high" if priority == Priority.CRITICAL else "medium"
            )
        except Exception as e:
            self.logger.error(f"Error processing Bandit finding: {e}")
            return None
    
    def _parse_mypy_output(self, mypy_output: str, start_id: int) -> List[Recommendation]:
        """Parse MyPy output and create recommendations."""
        recommendations = []
        
        if not mypy_output:
            return recommendations
        
        lines = mypy_output.split('\n')
        rec_id = start_id
        
        for line in lines:
            if ':' in line and ('error:' in line or 'warning:' in line):
                try:
                    parts = line.split(':')
                    if len(parts) >= 4:
                        file_path = parts[0].strip()
                        line_num = int(parts[1].strip()) if parts[1].strip().isdigit() else None
                        error_type = parts[2].strip()
                        message = ':'.join(parts[3:]).strip()
                        
                        priority = Priority.HIGH if 'error' in error_type else Priority.MEDIUM
                        
                        rec = Recommendation(
                            id=f"mypy-{rec_id}",
                            title=f"Type Check: {error_type}",
                            description=message,
                            priority=priority,
                            category=Category.MAINTAINABILITY,
                            file_path=file_path,
                            line_number=line_num,
                            auto_fixable=False,
                            estimated_effort="medium"
                        )
                        recommendations.append(rec)
                        rec_id += 1
                        
                except (ValueError, IndexError) as e:
                    self.logger.debug(f"Could not parse MyPy line: {line}")
        
        return recommendations
    
    def _parse_llm_analysis(self, file_analysis: Dict[str, Any], start_id: int) -> List[Recommendation]:
        """Parse LLM analysis and extract actionable recommendations."""
        recommendations = []
        
        analysis = file_analysis.get("llm_analysis", "")
        file_path = file_analysis.get("path", "")
        
        if not analysis or analysis.startswith("Skipped"):
            return recommendations
        
        # Look for common recommendation patterns in LLM output
        rec_id = start_id
        
        # Security recommendations
        if "security" in analysis.lower():
            recommendations.append(Recommendation(
                id=f"llm-security-{rec_id}",
                title="LLM: Security Review Needed",
                description="LLM identified potential security concerns in this file",
                priority=Priority.MEDIUM,
                category=Category.SECURITY,
                file_path=file_path,
                auto_fixable=False,
                estimated_effort="medium"
            ))
            rec_id += 1
        
        # Performance recommendations
        if any(word in analysis.lower() for word in ["performance", "efficiency", "optimization"]):
            recommendations.append(Recommendation(
                id=f"llm-performance-{rec_id}",
                title="LLM: Performance Optimization",
                description="LLM identified potential performance improvements",
                priority=Priority.LOW,
                category=Category.PERFORMANCE,
                file_path=file_path,
                auto_fixable=False,
                estimated_effort="medium"
            ))
            rec_id += 1
        
        # Maintainability recommendations
        if any(word in analysis.lower() for word in ["maintainability", "refactor", "code smell"]):
            recommendations.append(Recommendation(
                id=f"llm-maintainability-{rec_id}",
                title="LLM: Maintainability Improvement",
                description="LLM suggested maintainability improvements",
                priority=Priority.LOW,
                category=Category.MAINTAINABILITY,
                file_path=file_path,
                auto_fixable=False,
                estimated_effort="low"
            ))
            rec_id += 1
        
        return recommendations
    
    def filter_recommendations(self, 
                             priority: Optional[Priority] = None,
                             category: Optional[Category] = None,
                             file_pattern: Optional[str] = None,
                             auto_fixable_only: bool = False) -> List[Recommendation]:
        """Filter recommendations based on criteria."""
        filtered = self.recommendations
        
        if priority:
            filtered = [r for r in filtered if r.priority == priority]
        
        if category:
            filtered = [r for r in filtered if r.category == category]
        
        if file_pattern:
            import fnmatch
            filtered = [r for r in filtered if fnmatch.fnmatch(r.file_path, file_pattern)]
        
        if auto_fixable_only:
            filtered = [r for r in filtered if r.auto_fixable]
        
        return filtered
    
    def get_summary(self) -> RecommendationSummary:
        """Get summary statistics of recommendations."""
        total = len(self.recommendations)
        
        by_priority = {}
        for priority in Priority:
            count = len([r for r in self.recommendations if r.priority == priority])
            by_priority[priority.value] = count
        
        by_category = {}
        for category in Category:
            count = len([r for r in self.recommendations if r.category == category])
            by_category[category.value] = count
        
        auto_fixable_count = len([r for r in self.recommendations if r.auto_fixable])
        
        # Estimate total effort
        effort_points = {"low": 1, "medium": 3, "high": 8}
        total_effort_points = sum(effort_points.get(r.estimated_effort, 3) for r in self.recommendations)
        
        if total_effort_points <= 10:
            estimated_total_effort = "low"
        elif total_effort_points <= 50:
            estimated_total_effort = "medium"
        else:
            estimated_total_effort = "high"
        
        # Find most common issues
        issue_types = {}
        for rec in self.recommendations:
            issue_type = f"{rec.category.value}_{rec.priority.value}"
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        most_common = sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:5]
        most_common_issues = [f"{issue.replace('_', ' ').title()} ({count})" for issue, count in most_common]
        
        return RecommendationSummary(
            total_recommendations=total,
            by_priority=by_priority,
            by_category=by_category,
            auto_fixable_count=auto_fixable_count,
            estimated_total_effort=estimated_total_effort,
            most_common_issues=most_common_issues
        )
    
    def export_to_json(self, output_path: Path) -> None:
        """Export recommendations to JSON file."""
        data = {
            "summary": asdict(self.get_summary()),
            "recommendations": [asdict(rec) for rec in self.recommendations],
            "exported_at": datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        self.logger.info(f"Exported {len(self.recommendations)} recommendations to {output_path}")
    
    def generate_action_plan(self, max_items: int = 20) -> List[Recommendation]:
        """Generate prioritized action plan."""
        # Sort by priority (critical first) and effort (low effort first within same priority)
        priority_order = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3, Priority.INFO: 4}
        effort_order = {"low": 0, "medium": 1, "high": 2}
        
        sorted_recs = sorted(
            self.recommendations,
            key=lambda r: (priority_order.get(r.priority, 5), effort_order.get(r.estimated_effort, 2))
        )
        
        return sorted_recs[:max_items]


def main():
    """CLI interface for recommendation loader."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Load and analyze audit recommendations")
    parser.add_argument('--report', type=str, help='Path to audit report JSON')
    parser.add_argument('--summary', action='store_true', help='Show summary statistics')
    parser.add_argument('--priority', choices=[p.value for p in Priority], help='Filter by priority')
    parser.add_argument('--category', choices=[c.value for c in Category], help='Filter by category')
    parser.add_argument('--auto-fixable', action='store_true', help='Show only auto-fixable items')
    parser.add_argument('--action-plan', type=int, default=10, help='Generate action plan (max items)')
    parser.add_argument('--export', type=str, help='Export to JSON file')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Load recommendations
    loader = RecommendationLoader()
    
    report_path = Path(args.report) if args.report else None
    recommendations = loader.load_from_audit_report(report_path)
    
    if not recommendations:
        print("❌ No recommendations found")
        return
    
    # Apply filters
    priority_filter = Priority(args.priority) if args.priority else None
    category_filter = Category(args.category) if args.category else None
    
    filtered_recs = loader.filter_recommendations(
        priority=priority_filter,
        category=category_filter,
        auto_fixable_only=args.auto_fixable
    )
    
    if args.summary:
        summary = loader.get_summary()
        print("📊 Recommendation Summary")
        print(f"  Total: {summary.total_recommendations}")
        print(f"  Auto-fixable: {summary.auto_fixable_count}")
        print(f"  Estimated effort: {summary.estimated_total_effort}")
        print("\n📈 By Priority:")
        for priority, count in summary.by_priority.items():
            if count > 0:
                print(f"  {priority.title()}: {count}")
        print("\n📂 By Category:")
        for category, count in summary.by_category.items():
            if count > 0:
                print(f"  {category.title()}: {count}")
        
        if summary.most_common_issues:
            print("\n🔥 Most Common Issues:")
            for issue in summary.most_common_issues:
                print(f"  • {issue}")
    
    if args.action_plan:
        action_plan = loader.generate_action_plan(args.action_plan)
        print(f"\n🎯 Action Plan (Top {len(action_plan)} items)")
        for i, rec in enumerate(action_plan, 1):
            priority_icon = {"critical": "🚨", "high": "⚠️", "medium": "📋", "low": "📝", "info": "ℹ️"}
            icon = priority_icon.get(rec.priority.value, "📋")
            print(f"{i:2d}. {icon} {rec.title}")
            print(f"     {rec.description}")
            print(f"     File: {rec.file_path}" + (f":{rec.line_number}" if rec.line_number else ""))
            print(f"     Effort: {rec.estimated_effort} | Auto-fix: {'Yes' if rec.auto_fixable else 'No'}")
            print()
    
    if args.export:
        export_path = Path(args.export)
        loader.export_to_json(export_path)
        print(f"💾 Exported to {export_path}")


if __name__ == "__main__":
    main()