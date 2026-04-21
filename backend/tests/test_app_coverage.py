"""
Test app configuration to ensure coverage of app module.
"""
from app.core.config import Settings


def test_settings_class_exists():
    """Test that Settings class can be imported."""
    assert Settings is not None

def test_settings_with_secret():
    """Test settings with required secret key."""
    test_settings = Settings(secret_key="test-secret-key-for-testing")
    
    # Test basic attributes exist
    assert hasattr(test_settings, 'app_name')
    assert hasattr(test_settings, 'debug')
    assert hasattr(test_settings, 'host')
    assert hasattr(test_settings, 'port')
    
    # Test default values
    assert test_settings.app_name == "SyferStack Backend"
    assert test_settings.host == "0.0.0.0"
    assert test_settings.port == 8000

def test_settings_properties():
    """Test settings properties work correctly."""
    test_settings = Settings(secret_key="test-key", debug=True)
    assert test_settings.is_development is True
    assert test_settings.is_production is False
    
    test_settings = Settings(secret_key="test-key", debug=False)
    assert test_settings.is_development is False
    assert test_settings.is_production is True