"""Pytest configuration and shared fixtures"""
import pytest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)

@pytest.fixture
def mock_chroot(temp_dir):
    """Create a mock chroot environment"""
    chroot_path = temp_dir / "chroot"
    chroot_path.mkdir()
    
    # Create basic directory structure
    for dir_name in ["etc", "usr/bin", "var/lib", "proc", "sys", "dev"]:
        (chroot_path / dir_name).mkdir(parents=True)
    
    # Create mock files
    (chroot_path / "etc/debian_version").write_text("12\n")
    (chroot_path / "etc/hostname").write_text("z-forge-test\n")
    
    return chroot_path

@pytest.fixture
def mock_globalstorage():
    """Mock Calamares GlobalStorage"""
    class MockGlobalStorage:
        def __init__(self):
            self.data = {
                "rootMountPoint": "/tmp/test_root",
                "bootLoader": "systemd-boot"
            }
        
        def value(self, key):
            return self.data.get(key)
        
        def insert(self, key, value):
            self.data[key] = value
            
        def contains(self, key):
            return key in self.data
    
    return MockGlobalStorage()

@pytest.fixture
def mock_libcalamares(mock_globalstorage):
    """Mock libcalamares module"""
    class MockLibCalamares:
        globalstorage = mock_globalstorage
        
        @staticmethod
        def utils():
            class Utils:
                @staticmethod
                def debug(msg):
                    print(f"DEBUG: {msg}")
                    
                @staticmethod
                def warning(msg):
                    print(f"WARNING: {msg}")
                    
            return Utils
        
        @staticmethod
        def job():
            class Job:
                @staticmethod
                def setprogress(progress):
                    print(f"Progress: {progress}")
                    
            return Job
    
    # Mock the libcalamares module
    sys.modules['libcalamares'] = MockLibCalamares
    
    return MockLibCalamares

@pytest.fixture
def test_config():
    """Standard test configuration"""
    return {
        "test_timeout": 30,
        "test_retries": 3,
        "verbose": True,
        "parallel_tests": True
    }