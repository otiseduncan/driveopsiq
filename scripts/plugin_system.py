#!/usr/bin/env python3
"""
Extensible Plugin Architecture for SyferStackV2 Audit System
Supports custom analyzers, audit tools, and report generators
"""

import asyncio
import importlib
import inspect
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
import yaml
import json

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    description: str
    author: str
    category: str
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass 
class AnalysisResult:
    """Standardized analysis result from plugins."""
    plugin_name: str
    file_path: str
    issues: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    execution_time: float = 0.0


class PluginInterface(ABC):
    """Base interface for all audit plugins."""
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize plugin with configuration."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup plugin resources."""
        pass


class StaticAnalyzerPlugin(PluginInterface):
    """Interface for static analysis tool plugins."""
    
    @abstractmethod
    async def analyze_file(self, file_path: Path) -> AnalysisResult:
        """Analyze a single file."""
        pass
    
    @abstractmethod
    async def analyze_project(self, project_path: Path) -> AnalysisResult:
        """Analyze entire project."""
        pass
    
    @abstractmethod
    def supports_file_type(self, file_path: Path) -> bool:
        """Check if plugin supports this file type."""
        pass


class LLMAnalyzerPlugin(PluginInterface):
    """Interface for LLM-based analysis plugins."""
    
    @abstractmethod
    async def analyze_code(self, code: str, file_path: Path, context: Dict[str, Any]) -> AnalysisResult:
        """Analyze code with LLM."""
        pass
    
    @abstractmethod
    def get_analysis_prompt(self, code: str, file_path: Path) -> str:
        """Generate analysis prompt for LLM."""
        pass


class ReportGeneratorPlugin(PluginInterface):
    """Interface for custom report generators."""
    
    @abstractmethod
    async def generate_report(self, audit_results: Dict[str, Any], output_path: Path) -> bool:
        """Generate custom report format."""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Return list of supported output formats."""
        pass


class WebhookPlugin(PluginInterface):
    """Interface for webhook/notification plugins."""
    
    @abstractmethod
    async def send_notification(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Send notification for audit events."""
        pass
    
    @abstractmethod
    def get_supported_events(self) -> List[str]:
        """Return list of supported event types."""
        pass


# Built-in Plugin Examples

class ESLintPlugin(StaticAnalyzerPlugin):
    """ESLint static analysis plugin."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="eslint",
            version="1.0.0",
            description="JavaScript/TypeScript linting with ESLint",
            author="SyferStack",
            category="static_analysis",
            dependencies=["eslint"]
        )
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        self.config = config
        self.enabled = config.get('enabled', True)
        return True
    
    async def cleanup(self) -> None:
        pass
    
    def supports_file_type(self, file_path: Path) -> bool:
        return file_path.suffix in ['.js', '.ts', '.jsx', '.tsx']
    
    async def analyze_file(self, file_path: Path) -> AnalysisResult:
        """Run ESLint on a single file."""
        import subprocess
        import time
        
        start_time = time.time()
        
        try:
            cmd = ['eslint', '--format', 'json', str(file_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            issues = []
            if result.stdout:
                eslint_output = json.loads(result.stdout)
                for file_result in eslint_output:
                    for message in file_result.get('messages', []):
                        issues.append({
                            'rule': message.get('ruleId'),
                            'severity': 'error' if message.get('severity') == 2 else 'warning',
                            'message': message.get('message'),
                            'line': message.get('line'),
                            'column': message.get('column')
                        })
            
            return AnalysisResult(
                plugin_name=self.metadata.name,
                file_path=str(file_path),
                issues=issues,
                success=True,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return AnalysisResult(
                plugin_name=self.metadata.name,
                file_path=str(file_path),
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time
            )
    
    async def analyze_project(self, project_path: Path) -> AnalysisResult:
        """Run ESLint on entire project."""
        # Implementation similar to analyze_file but for whole project
        return AnalysisResult(
            plugin_name=self.metadata.name,
            file_path=str(project_path),
            success=True
        )


class SecurityLLMPlugin(LLMAnalyzerPlugin):
    """Specialized LLM plugin for security analysis."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="security-llm",
            version="1.0.0",
            description="Advanced security analysis using LLM",
            author="SyferStack",
            category="llm_analysis",
            dependencies=["aiohttp"]
        )
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        self.config = config
        self.ollama_url = config.get('ollama_url', 'http://localhost:11434/api/generate')
        self.model = config.get('model', 'llama3:8b')
        return True
    
    async def cleanup(self) -> None:
        pass
    
    def get_analysis_prompt(self, code: str, file_path: Path) -> str:
        return f"""
        You are a senior cybersecurity expert. Analyze this code for security vulnerabilities.

        Focus on:
        - OWASP Top 10 vulnerabilities
        - Input validation issues
        - Authentication and authorization flaws
        - Cryptographic weaknesses
        - Injection vulnerabilities
        - Insecure deserialization
        - Security misconfigurations

        File: {file_path}
        
        Code:
        ```
        {code[:2000]}  # Limit for context
        ```
        
        Provide findings in this format:
        - CRITICAL: [description]
        - HIGH: [description] 
        - MEDIUM: [description]
        - LOW: [description]
        """
    
    async def analyze_code(self, code: str, file_path: Path, context: Dict[str, Any]) -> AnalysisResult:
        """Analyze code for security issues using LLM."""
        import aiohttp
        import time
        
        start_time = time.time()
        
        try:
            prompt = self.get_analysis_prompt(code, file_path)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.ollama_url,
                    json={"model": self.model, "prompt": prompt, "stream": False},
                    timeout=120
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        analysis = result.get('response', '')
                        
                        # Parse issues from LLM response
                        issues = self._parse_security_issues(analysis)
                        
                        return AnalysisResult(
                            plugin_name=self.metadata.name,
                            file_path=str(file_path),
                            issues=issues,
                            metadata={'llm_response': analysis},
                            success=True,
                            execution_time=time.time() - start_time
                        )
                    else:
                        raise Exception(f"LLM API error: {response.status}")
                        
        except Exception as e:
            return AnalysisResult(
                plugin_name=self.metadata.name,
                file_path=str(file_path),
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time
            )
    
    def _parse_security_issues(self, analysis: str) -> List[Dict[str, Any]]:
        """Parse security issues from LLM response."""
        issues = []
        severity_map = {'CRITICAL': 'critical', 'HIGH': 'high', 'MEDIUM': 'medium', 'LOW': 'low'}
        
        for line in analysis.split('\n'):
            line = line.strip()
            for severity, level in severity_map.items():
                if line.startswith(f"- {severity}:"):
                    description = line[len(f"- {severity}:"):].strip()
                    issues.append({
                        'severity': level,
                        'type': 'security',
                        'description': description,
                        'source': 'llm_analysis'
                    })
        
        return issues


class SlackNotificationPlugin(WebhookPlugin):
    """Slack webhook notification plugin."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="slack-notifications",
            version="1.0.0", 
            description="Send audit notifications to Slack",
            author="SyferStack",
            category="notifications",
            dependencies=["aiohttp"]
        )
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel', '#security')
        return self.webhook_url is not None
    
    async def cleanup(self) -> None:
        pass
    
    def get_supported_events(self) -> List[str]:
        return ['audit_complete', 'audit_failed', 'critical_issue_found']
    
    async def send_notification(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Send Slack notification."""
        if not self.webhook_url:
            return False
            
        try:
            import aiohttp
            
            if event_type == 'audit_complete':
                payload = {
                    "channel": self.channel,
                    "text": f"🛡️ Security audit completed",
                    "attachments": [{
                        "color": "good" if data.get('total_issues', 0) == 0 else "warning",
                        "fields": [
                            {"title": "Files Scanned", "value": str(data.get('total_files', 0)), "short": True},
                            {"title": "Issues Found", "value": str(data.get('total_issues', 0)), "short": True},
                            {"title": "Grade", "value": data.get('grade', 'N/A'), "short": True}
                        ]
                    }]
                }
            elif event_type == 'critical_issue_found':
                payload = {
                    "channel": self.channel,
                    "text": f"🚨 Critical security issue detected!",
                    "attachments": [{
                        "color": "danger",
                        "fields": [
                            {"title": "File", "value": data.get('file_path', 'Unknown'), "short": False},
                            {"title": "Issue", "value": data.get('description', 'Unknown'), "short": False}
                        ]
                    }]
                }
            else:
                return False
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False


class PluginManager:
    """Manages loading, initialization, and execution of plugins."""
    
    def __init__(self, plugin_dir: Path = None):
        self.plugin_dir = plugin_dir or Path("plugins")
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        
        # Built-in plugins
        self.builtin_plugins = {
            'eslint': ESLintPlugin,
            'security-llm': SecurityLLMPlugin,
            'slack-notifications': SlackNotificationPlugin
        }
    
    def load_plugin_config(self, config_path: Path = None) -> None:
        """Load plugin configuration from YAML file."""
        config_file = config_path or Path("plugin_config.yaml")
        
        if config_file.exists():
            with open(config_file) as f:
                self.plugin_configs = yaml.safe_load(f) or {}
    
    async def discover_and_load_plugins(self) -> None:
        """Discover and load all available plugins."""
        # Load built-in plugins
        for name, plugin_class in self.builtin_plugins.items():
            await self._load_plugin(name, plugin_class)
        
        # Discover external plugins
        if self.plugin_dir.exists():
            for plugin_file in self.plugin_dir.glob("*.py"):
                if plugin_file.stem.startswith("plugin_"):
                    await self._load_external_plugin(plugin_file)
    
    async def _load_plugin(self, name: str, plugin_class: Type[PluginInterface]) -> None:
        """Load and initialize a plugin."""
        try:
            plugin = plugin_class()
            config = self.plugin_configs.get(name, {})
            
            if await plugin.initialize(config):
                self.plugins[name] = plugin
                logger.info(f"Loaded plugin: {plugin.metadata.name} v{plugin.metadata.version}")
            else:
                logger.warning(f"Failed to initialize plugin: {name}")
                
        except Exception as e:
            logger.error(f"Error loading plugin {name}: {e}")
    
    async def _load_external_plugin(self, plugin_file: Path) -> None:
        """Load external plugin from file."""
        try:
            spec = importlib.util.spec_from_file_location(plugin_file.stem, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class in module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, PluginInterface) and 
                    obj != PluginInterface):
                    await self._load_plugin(plugin_file.stem, obj)
                    break
                    
        except Exception as e:
            logger.error(f"Error loading external plugin {plugin_file}: {e}")
    
    def get_plugins_by_category(self, category: str) -> List[PluginInterface]:
        """Get all plugins of a specific category."""
        return [
            plugin for plugin in self.plugins.values()
            if plugin.metadata.category == category
        ]
    
    async def run_static_analysis(self, file_path: Path) -> List[AnalysisResult]:
        """Run all applicable static analysis plugins on a file."""
        results = []
        static_plugins = self.get_plugins_by_category("static_analysis")
        
        for plugin in static_plugins:
            if isinstance(plugin, StaticAnalyzerPlugin) and plugin.supports_file_type(file_path):
                try:
                    result = await plugin.analyze_file(file_path)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Plugin {plugin.metadata.name} failed on {file_path}: {e}")
        
        return results
    
    async def run_llm_analysis(self, code: str, file_path: Path) -> List[AnalysisResult]:
        """Run all LLM analysis plugins on code."""
        results = []
        llm_plugins = self.get_plugins_by_category("llm_analysis")
        
        for plugin in llm_plugins:
            if isinstance(plugin, LLMAnalyzerPlugin):
                try:
                    result = await plugin.analyze_code(code, file_path, {})
                    results.append(result)
                except Exception as e:
                    logger.error(f"LLM plugin {plugin.metadata.name} failed on {file_path}: {e}")
        
        return results
    
    async def send_notifications(self, event_type: str, data: Dict[str, Any]) -> None:
        """Send notifications through all webhook plugins."""
        webhook_plugins = self.get_plugins_by_category("notifications")
        
        for plugin in webhook_plugins:
            if isinstance(plugin, WebhookPlugin) and event_type in plugin.get_supported_events():
                try:
                    await plugin.send_notification(event_type, data)
                except Exception as e:
                    logger.error(f"Notification plugin {plugin.metadata.name} failed: {e}")
    
    async def cleanup_all(self) -> None:
        """Cleanup all loaded plugins."""
        for plugin in self.plugins.values():
            try:
                await plugin.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up plugin {plugin.metadata.name}: {e}")
    
    def get_plugin_status(self) -> Dict[str, Any]:
        """Get status of all plugins."""
        return {
            "total_plugins": len(self.plugins),
            "plugins": {
                name: {
                    "name": plugin.metadata.name,
                    "version": plugin.metadata.version,
                    "category": plugin.metadata.category,
                    "description": plugin.metadata.description
                }
                for name, plugin in self.plugins.items()
            }
        }


# Example plugin configuration
def create_sample_plugin_config():
    """Create sample plugin configuration file."""
    config = {
        "eslint": {
            "enabled": True,
            "config_file": ".eslintrc.js"
        },
        "security-llm": {
            "enabled": True,
            "ollama_url": "http://localhost:11434/api/generate",
            "model": "llama3:8b"
        },
        "slack-notifications": {
            "enabled": True,
            "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
            "channel": "#security-alerts"
        }
    }
    
    with open("plugin_config.yaml", "w") as f:
        yaml.dump(config, f, indent=2)


# CLI for plugin management
async def main():
    """Command line interface for plugin management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Plugin management")
    parser.add_argument('--list', action='store_true', help='List all plugins')
    parser.add_argument('--test', type=str, help='Test specific plugin')
    parser.add_argument('--create-config', action='store_true', help='Create sample config')
    
    args = parser.parse_args()
    
    if args.create_config:
        create_sample_plugin_config()
        print("✅ Created sample plugin_config.yaml")
        return
    
    # Load and test plugins
    manager = PluginManager()
    manager.load_plugin_config()
    await manager.discover_and_load_plugins()
    
    if args.list:
        status = manager.get_plugin_status()
        print(f"📦 Loaded {status['total_plugins']} plugins:")
        for name, info in status['plugins'].items():
            print(f"  • {info['name']} v{info['version']} ({info['category']})")
            print(f"    {info['description']}")
    
    if args.test:
        plugin = manager.plugins.get(args.test)
        if plugin:
            print(f"🧪 Testing plugin: {plugin.metadata.name}")
            # Add test logic here
        else:
            print(f"❌ Plugin not found: {args.test}")
    
    await manager.cleanup_all()


if __name__ == "__main__":
    asyncio.run(main())