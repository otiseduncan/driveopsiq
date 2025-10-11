#!/usr/bin/env python3
"""
Comprehensive test suite for the audit system
Tests configuration, tools, LLM integration, and reporting
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import yaml
from dataclasses import asdict

# Import our modules
import sys
sys.path.append(str(Path(__file__).parent))

from config_manager import ConfigManager, AuditConfig
from improved_audit import (
    ProductionAuditor, AuditToolRunner, LLMAnalyzer, 
    AuditReporter, FileAnalysis, AuditResults
)


class TestConfigManager:
    """Test configuration management system."""
    
    def test_default_config_creation(self):
        """Test creating default configuration."""
        config = AuditConfig()
        assert config.environment == "development"
        assert config.ollama.url == "http://localhost:11434/api/generate"
        assert config.files.max_size_mb == 1
        assert config.performance.parallel_llm_requests == 5
    
    def test_config_validation_invalid_environment(self):
        """Test configuration validation with invalid environment."""
        with pytest.raises(ValueError):
            AuditConfig(environment="invalid")
    
    def test_config_validation_invalid_url(self):
        """Test Ollama URL validation."""
        with pytest.raises(ValueError):
            AuditConfig(ollama={"url": "invalid-url"})
    
    def test_yaml_config_loading(self):
        """Test loading configuration from YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = {
                'environment': 'testing',
                'ollama': {'model': 'test-model'},
                'files': {'max_size_mb': 5}
            }
            yaml.dump(yaml_content, f)
            config_path = Path(f.name)
        
        try:
            config_manager = ConfigManager(config_path)
            config = config_manager.load_config()
            
            assert config.environment == 'testing'
            assert config.ollama.model == 'test-model'
            assert config.files.max_size_mb == 5
        finally:
            config_path.unlink()
    
    @patch.dict('os.environ', {
        'AUDIT_ENVIRONMENT': 'production',
        'AUDIT_OLLAMA_MODEL': 'env-model',
        'AUDIT_PARALLEL_REQUESTS': '10',
        'AUDIT_ENABLE_CACHE': 'true'
    })
    def test_environment_variable_overrides(self):
        """Test environment variable overrides."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = {'environment': 'development'}
            yaml.dump(yaml_content, f)
            config_path = Path(f.name)
        
        try:
            config_manager = ConfigManager(config_path)
            config = config_manager.load_config()
            
            assert config.environment == 'production'  # Overridden
            assert config.ollama.model == 'env-model'  # Overridden
            assert config.performance.parallel_llm_requests == 10  # Overridden
            assert config.performance.enable_caching == True  # Overridden
        finally:
            config_path.unlink()


class TestAuditToolRunner:
    """Test static analysis tool runner."""
    
    @pytest.fixture
    def tool_runner(self):
        """Create tool runner with test configuration."""
        config = AuditConfig()
        return AuditToolRunner(config)
    
    @pytest.mark.asyncio
    async def test_run_command_safe_success(self, tool_runner):
        """Test successful command execution."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock successful process
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b'success output', b'')
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            result = await tool_runner.run_command_safe(['echo', 'test'], 'Test command')
            
            assert result == 'success output'
            mock_subprocess.assert_called_once_with(
                'echo', 'test',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
    
    @pytest.mark.asyncio
    async def test_run_command_safe_failure(self, tool_runner):
        """Test command execution with non-zero return code."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b'', b'error message')
            mock_process.returncode = 1
            mock_subprocess.return_value = mock_process
            
            result = await tool_runner.run_command_safe(['false'], 'Failing command')
            
            assert result == ''  # stdout is empty
    
    @pytest.mark.asyncio
    async def test_run_ruff_success(self, tool_runner):
        """Test successful Ruff execution."""
        mock_output = json.dumps([{"file": "test.py", "message": "test issue"}])
        
        with patch.object(tool_runner, 'run_command_safe', return_value=mock_output):
            result = await tool_runner.run_ruff()
            
            assert isinstance(result, list)
            assert result[0]["file"] == "test.py"
    
    @pytest.mark.asyncio
    async def test_run_ruff_invalid_json(self, tool_runner):
        """Test Ruff with invalid JSON output."""
        with patch.object(tool_runner, 'run_command_safe', return_value='invalid json'):
            result = await tool_runner.run_ruff()
            
            assert "error" in result
            assert result["error"] == "Invalid Ruff output"
    
    @pytest.mark.asyncio
    async def test_run_bandit_success(self, tool_runner):
        """Test successful Bandit execution."""
        mock_output = json.dumps({"results": [{"issue_text": "test security issue"}]})
        
        with patch.object(tool_runner, 'run_command_safe', return_value=mock_output):
            result = await tool_runner.run_bandit()
            
            assert "results" in result
            assert len(result["results"]) == 1


class TestLLMAnalyzer:
    """Test LLM analyzer component."""
    
    @pytest.fixture
    def analyzer_config(self):
        """Create analyzer configuration."""
        return AuditConfig()
    
    @pytest.mark.asyncio
    async def test_analyze_file_success(self, analyzer_config):
        """Test successful file analysis."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('print("Hello, world!")')
            test_file = Path(f.name)
        
        try:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"response": "Analysis complete"}
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            analyzer = LLMAnalyzer(analyzer_config)
            analyzer.session = mock_session
            
            result = await analyzer.analyze_file(test_file)
            
            assert isinstance(result, FileAnalysis)
            assert result.path == str(test_file)
            assert result.llm_analysis == "Analysis complete"
            assert result.error is None
        finally:
            test_file.unlink()
    
    @pytest.mark.asyncio
    async def test_analyze_file_too_large(self, analyzer_config):
        """Test file analysis with oversized file."""
        # Create config with very small max size
        analyzer_config.files.max_size_mb = 0  # 0 MB limit
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('x' * 1000)  # 1KB file
            test_file = Path(f.name)
        
        try:
            analyzer = LLMAnalyzer(analyzer_config)
            result = await analyzer.analyze_file(test_file)
            
            assert result.error is not None
            assert result.skipped is True
            assert "File too large" in result.error
        finally:
            test_file.unlink()
    
    @pytest.mark.asyncio
    async def test_analyze_file_api_error(self, analyzer_config):
        """Test file analysis with API error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('print("test")')
            test_file = Path(f.name)
        
        try:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text.return_value = "Internal Server Error"
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            analyzer = LLMAnalyzer(analyzer_config)
            analyzer.session = mock_session
            
            result = await analyzer.analyze_file(test_file)
            
            assert result.error is not None
            assert "LLM API error 500" in result.error
        finally:
            test_file.unlink()
    
    def test_validate_file_path_security(self, analyzer_config):
        """Test path validation security checks."""
        analyzer = LLMAnalyzer(analyzer_config)
        
        # Test non-existent file
        with pytest.raises(Exception):
            analyzer._validate_file_path(Path("/nonexistent/file.py"))


class TestAuditReporter:
    """Test audit reporting functionality."""
    
    @pytest.fixture
    def reporter_config(self):
        """Create reporter configuration."""
        return AuditConfig()
    
    @pytest.fixture
    def sample_results(self, reporter_config):
        """Create sample audit results."""
        return AuditResults(
            timestamp="2025-01-01T00:00:00",
            ruff=[{"file": "test.py", "message": "test issue"}],
            bandit={"results": [{"issue_text": "test security issue"}]},
            mypy="No issues found",
            files=[
                FileAnalysis(
                    path="test.py",
                    llm_analysis="This file looks good",
                    size_bytes=100
                )
            ],
            config=reporter_config,
            errors=[]
        )
    
    @pytest.mark.asyncio
    async def test_save_json_report(self, reporter_config, sample_results):
        """Test JSON report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter_config.output.reports_dir = tmpdir
            reporter = AuditReporter(reporter_config)
            
            report_path = await reporter.save_json_report(sample_results)
            
            assert report_path.exists()
            with open(report_path) as f:
                data = json.load(f)
            
            assert data["timestamp"] == "2025-01-01T00:00:00"
            assert len(data["files"]) == 1
    
    def test_calculate_grade(self, reporter_config):
        """Test grade calculation logic."""
        reporter = AuditReporter(reporter_config)
        
        # Perfect score
        assert reporter._calculate_grade(0, 0) == "A+"
        
        # Some issues
        assert reporter._calculate_grade(1, 5) == "B+"
        
        # Many issues
        assert reporter._calculate_grade(5, 10) == "F"
    
    @pytest.mark.asyncio
    async def test_generate_markdown_summary(self, reporter_config, sample_results):
        """Test Markdown report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter_config.output.reports_dir = tmpdir
            reporter = AuditReporter(reporter_config)
            
            summary_path = await reporter.generate_markdown_summary(sample_results)
            
            assert summary_path.exists()
            with open(summary_path) as f:
                content = f.read()
            
            assert "SyferStackV2 Production Audit Report" in content
            assert "test.py" in content
            assert "This file looks good" in content


class TestProductionAuditor:
    """Test main auditor orchestration."""
    
    @pytest.fixture
    def auditor_config(self):
        """Create auditor configuration."""
        config = AuditConfig()
        config.performance.parallel_llm_requests = 1  # Reduce for testing
        return config
    
    def test_collect_files(self):
        """Test file collection logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_py = Path(tmpdir) / "test.py"
            test_js = Path(tmpdir) / "test.js"
            test_txt = Path(tmpdir) / "test.txt"  # Should be ignored
            
            test_py.touch()
            test_js.touch() 
            test_txt.touch()
            
            auditor = ProductionAuditor(AuditConfig())
            
            # Change to temp directory
            import os
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            
            try:
                files = auditor._collect_files()
                file_names = [f.name for f in files]
                
                assert "test.py" in file_names
                assert "test.js" in file_names
                assert "test.txt" not in file_names  # Not supported extension
            finally:
                os.chdir(original_cwd)
    
    @pytest.mark.asyncio
    async def test_analyze_files_concurrently(self, auditor_config):
        """Test concurrent file analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_files = []
            for i in range(3):
                test_file = Path(tmpdir) / f"test_{i}.py"
                test_file.write_text(f'print("test {i}")')
                test_files.append(test_file)
            
            auditor = ProductionAuditor(auditor_config)
            
            # Mock the LLM analyzer
            with patch('improved_audit.LLMAnalyzer') as mock_analyzer_class:
                mock_analyzer = AsyncMock()
                mock_analyzer_class.return_value.__aenter__.return_value = mock_analyzer
                
                # Configure mock to return different results
                def mock_analyze(file_path):
                    return FileAnalysis(
                        path=str(file_path),
                        llm_analysis=f"Analysis for {file_path.name}",
                        size_bytes=file_path.stat().st_size
                    )
                
                mock_analyzer.analyze_file.side_effect = mock_analyze
                
                results = await auditor._analyze_files_concurrently(test_files)
                
                assert len(results) == 3
                assert all(isinstance(r, FileAnalysis) for r in results)
                assert mock_analyzer.analyze_file.call_count == 3


class TestIntegration:
    """Integration tests for the complete audit system."""
    
    @pytest.mark.asyncio
    async def test_full_audit_workflow(self):
        """Test complete audit workflow end-to-end."""
        config = AuditConfig()
        config.performance.parallel_llm_requests = 1
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup test environment
            config.output.reports_dir = tmpdir
            
            # Create a test Python file
            test_file = Path(tmpdir) / "test_code.py"
            test_file.write_text('''
def hello_world():
    """A simple function."""
    print("Hello, world!")
    return "success"

if __name__ == "__main__":
    hello_world()
''')
            
            # Change to test directory
            import os
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            
            try:
                auditor = ProductionAuditor(config)
                
                # Mock external dependencies
                with patch.object(auditor, '_analyze_files_concurrently') as mock_llm, \
                     patch('improved_audit.AuditToolRunner') as mock_tool_runner_class:
                    
                    # Mock LLM analysis
                    mock_llm.return_value = [
                        FileAnalysis(
                            path="test_code.py",
                            llm_analysis="Code looks good, follows best practices",
                            size_bytes=test_file.stat().st_size
                        )
                    ]
                    
                    # Mock tool runner
                    mock_tool_runner = AsyncMock()
                    mock_tool_runner.run_ruff.return_value = []
                    mock_tool_runner.run_bandit.return_value = {"results": []}
                    mock_tool_runner.run_mypy.return_value = "Success: no issues found"
                    mock_tool_runner_class.return_value = mock_tool_runner
                    
                    # Run the audit
                    results = await auditor.run_audit()
                    
                    # Verify results
                    assert isinstance(results, AuditResults)
                    assert len(results.files) == 1
                    assert results.files[0].path == "test_code.py"
                    assert "Code looks good" in results.files[0].llm_analysis
                    
                    # Verify reports were generated
                    json_report = Path(tmpdir) / "production_audit.json"
                    markdown_report = Path(tmpdir) / "summary.md"
                    
                    assert json_report.exists()
                    assert markdown_report.exists()
                    
            finally:
                os.chdir(original_cwd)


# Pytest fixtures for running tests
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])