# 🛡️ SyferStackV2 Enterprise Audit System

A production-grade, enterprise-ready security and code quality audit system with advanced features including LLM-powered analysis, intelligent caching, comprehensive metrics, and extensible plugin architecture.

## 🌟 Features

### Core Capabilities
- **🔍 Multi-Tool Static Analysis** - Integrates Ruff, Bandit, MyPy, ESLint, and more
- **🤖 LLM-Powered Code Analysis** - Advanced semantic analysis using Ollama
- **⚡ Intelligent Caching** - Git-hash based caching for unchanged files
- **📊 Comprehensive Metrics** - Performance tracking and quality metrics
- **🔄 Retry Logic** - Exponential backoff with circuit breaker patterns
- **🧩 Plugin Architecture** - Extensible system for custom analyzers
- **🐳 Docker Support** - Containerized deployment with orchestration
- **⚙️ CI/CD Integration** - GitHub Actions with SARIF output
- **📈 Real-time Monitoring** - Prometheus metrics and Grafana dashboards

### Enterprise Features
- **📋 Configuration Management** - YAML-based config with environment overrides
- **🎯 Quality Grading** - Intelligent scoring and grade calculation
- **📝 Multiple Report Formats** - JSON, Markdown, HTML, SARIF
- **🔔 Webhook Notifications** - Slack, Teams, custom integrations
- **🏗️ Scalable Architecture** - Async processing with concurrency control
- **🔒 Security First** - Path validation, input sanitization, resource limits

## 🚀 Quick Start

### Option 1: Docker (Recommended)
```bash
# Clone repository
git clone https://github.com/otiseduncan/SyferStackV2.git
cd SyferStackV2/scripts

# Start the complete audit stack
docker-compose up -d

# Run audit
docker-compose exec audit-runner python production_audit.py
```

### Option 2: Local Installation
```bash
# Install dependencies
pip install -r requirements.txt
pip install ruff bandit mypy safety

# Configure system
python config_manager.py

# Run audit
python production_audit.py
```

## 📁 Project Structure

```
scripts/
├── production_audit.py        # Main enterprise audit system
├── config_manager.py          # Configuration management
├── cache_system.py           # Git-based caching system
├── metrics_system.py         # Metrics collection & monitoring
├── retry_system.py           # Retry logic & circuit breakers
├── plugin_system.py          # Extensible plugin architecture
├── improved_audit.py         # Core audit components
├── test_audit_system.py      # Comprehensive test suite
├── audit_scheduler.py        # Automated scheduling
├── audit_config.yaml         # Main configuration file
├── docker-compose.yml        # Docker orchestration
├── Dockerfile               # Container definition
├── prometheus.yml           # Metrics configuration
└── requirements.txt         # Python dependencies
```

## ⚙️ Configuration

### Main Configuration (`audit_config.yaml`)
```yaml
environment: production

ollama:
  url: "http://localhost:11434/api/generate"
  model: "llama3:8b"
  timeout: 120
  max_retries: 3

files:
  max_size_mb: 1
  supported_extensions: [".py", ".js", ".ts", ".tsx"]
  exclude_patterns: ["node_modules/**", "__pycache__/**"]

performance:
  parallel_llm_requests: 5
  enable_caching: true
  cache_duration_hours: 24

tools:
  ruff:
    enabled: true
  bandit:
    enabled: true
    severity_level: "medium"
  mypy:
    enabled: true

output:
  reports_dir: "reports"
  formats: ["json", "markdown", "html", "sarif"]
```

### Environment Variable Overrides
```bash
export AUDIT_ENVIRONMENT=production
export AUDIT_OLLAMA_URL=http://ollama:11434/api/generate
export AUDIT_PARALLEL_REQUESTS=10
export AUDIT_ENABLE_CACHE=true
```

## 🔧 Advanced Usage

### Running with Custom Configuration
```bash
python production_audit.py --config custom_config.yaml --output-dir ./my_reports
```

### Plugin Management
```bash
# List available plugins
python plugin_system.py --list

# Create plugin configuration
python plugin_system.py --create-config

# Test specific plugin
python plugin_system.py --test eslint
```

### Cache Management
```bash
# View cache statistics
python cache_system.py --stats

# Clear cache
python cache_system.py --clear

# Clean expired entries
python cache_system.py --cleanup
```

### Metrics Analysis
```bash
# Current metrics
python metrics_system.py --current

# 24-hour summary
python metrics_system.py --summary 24

# Export for analysis
python metrics_system.py --export json > metrics.json
```

## 🧪 Testing

### Run Test Suite
```bash
# Full test suite
pytest test_audit_system.py -v

# Specific test categories
pytest test_audit_system.py::TestConfigManager -v
pytest test_audit_system.py::TestLLMAnalyzer -v

# With coverage
pytest test_audit_system.py --cov=. --cov-report=html
```

### Integration Testing
```bash
# Test retry system
python retry_system.py

# Test plugin system
python plugin_system.py --test security-llm

# Validate configuration
python config_manager.py
```

## 🐳 Docker Deployment

### Services Architecture
- **audit-runner** - Main audit execution service
- **ollama** - LLM service for code analysis
- **prometheus** - Metrics collection
- **grafana** - Metrics visualization
- **redis** - Optional caching layer
- **audit-scheduler** - Automated audit scheduling

### Deployment Commands
```bash
# Start all services
docker-compose up -d

# Scale audit runners
docker-compose up -d --scale audit-runner=3

# View logs
docker-compose logs -f audit-runner

# Update and rebuild
docker-compose build --no-cache
docker-compose up -d
```

## 🔄 CI/CD Integration

### GitHub Actions Workflow
The system includes a complete GitHub Actions workflow (`.github/workflows/security-audit.yml`) that:

- ✅ Runs on every push and PR
- 🔍 Executes full security audit
- 📊 Uploads SARIF results to GitHub Security tab  
- 💬 Comments audit summary on PRs
- 📦 Creates downloadable audit artifacts
- 🚨 Creates issues for critical failures

### Manual Trigger
```bash
# Trigger audit via workflow dispatch
gh workflow run security-audit.yml -f audit_type=full -f upload_results=true
```

## 📊 Monitoring & Dashboards

### Prometheus Metrics
Access metrics at `http://localhost:9090`:
- Audit success/failure rates
- File processing times  
- Cache hit/miss ratios
- LLM request latencies
- System resource usage

### Grafana Dashboards
Access dashboards at `http://localhost:3000` (admin/admin123):
- Audit Performance Overview
- Security Issues Trends
- System Health Monitoring
- Cache Effectiveness Analysis

## 🔌 Plugin Development

### Creating a Custom Plugin
```python
from plugin_system import StaticAnalyzerPlugin, PluginMetadata, AnalysisResult

class MyCustomPlugin(StaticAnalyzerPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="Custom analysis tool",
            author="Your Name",
            category="static_analysis"
        )
    
    async def initialize(self, config: dict) -> bool:
        # Initialize your plugin
        return True
    
    async def analyze_file(self, file_path: Path) -> AnalysisResult:
        # Implement your analysis logic
        return AnalysisResult(
            plugin_name=self.metadata.name,
            file_path=str(file_path),
            issues=[],  # Your detected issues
            success=True
        )
```

### Plugin Configuration
Add to `plugin_config.yaml`:
```yaml
my-plugin:
  enabled: true
  custom_setting: "value"
```

## 📈 Performance Optimization

### Caching Strategy
- **Git-hash based** - Tracks file changes via git
- **Content hashing** - Fallback for non-git files  
- **TTL expiration** - Configurable cache duration
- **Size limits** - Prevents cache bloat

### Concurrency Tuning
```yaml
performance:
  parallel_llm_requests: 5      # Concurrent LLM analyses
  parallel_static_tools: 3      # Concurrent tool executions
  max_file_size_mb: 1          # Skip large files
```

### Resource Management
- **Memory limits** - File size restrictions
- **Timeout handling** - Prevents hanging processes
- **Rate limiting** - Controls API request rates
- **Circuit breakers** - Handles service failures

## 🔒 Security Considerations

### Input Validation
- Path traversal protection
- File size limits
- Content sanitization
- Command injection prevention

### Container Security
- Non-root user execution
- Read-only filesystem mounts
- Resource constraints
- Network isolation

## 🚨 Troubleshooting

### Common Issues

**Ollama Connection Errors**
```bash
# Check Ollama service
docker-compose logs ollama

# Test connectivity
curl http://localhost:11434/api/generate
```

**Cache Permission Issues**
```bash
# Fix cache permissions
sudo chown -R $(id -u):$(id -g) .audit_cache/
```

**Plugin Loading Failures**
```bash
# Check plugin syntax
python -m py_compile plugins/my_plugin.py

# Validate plugin config
python plugin_system.py --list
```

### Debug Mode
```bash
export AUDIT_LOG_LEVEL=DEBUG
python production_audit.py
```

## 📚 API Reference

### Core Classes

#### `EnterpriseAuditSystem`
Main audit orchestrator with enterprise features.

#### `ConfigManager` 
Configuration loading with validation and environment overrides.

#### `AnalysisCache`
Git-based caching system with intelligent invalidation.

#### `MetricsCollector`
Comprehensive metrics collection and export.

#### `PluginManager`
Plugin discovery, loading, and execution management.

### Configuration Schema
See `config_manager.py` for complete Pydantic models and validation rules.

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Add** tests for new functionality  
4. **Run** the test suite: `pytest`
5. **Submit** a pull request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio

# Run pre-commit checks
python -m ruff check scripts/
python -m bandit -r scripts/
python -m mypy scripts/
```

## 📄 License

MIT License - see LICENSE file for details.

## 🔗 Links

- **Documentation**: [GitHub Wiki](https://github.com/otiseduncan/SyferStackV2/wiki)
- **Issues**: [GitHub Issues](https://github.com/otiseduncan/SyferStackV2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/otiseduncan/SyferStackV2/discussions)

## 📞 Support

- 📧 Email: support@syferstack.com
- 💬 Slack: [SyferStack Community](https://slack.syferstack.com)
- 🐛 Bug Reports: [GitHub Issues](https://github.com/otiseduncan/SyferStackV2/issues)

---

**Built with ❤️ by the SyferStack Team**

*Securing codebases, one audit at a time.*