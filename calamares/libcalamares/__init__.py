#!/usr/bin/env python3
"""
Mock libcalamares module for testing outside of Calamares environment
This allows modules to be imported and tested without the actual Calamares framework
"""

class GlobalStorage:
    """Mock GlobalStorage class"""
    def __init__(self):
        self.data = {}
        
    def insert(self, key, value):
        """Store a value in global storage"""
        self.data[key] = value
        
    def value(self, key):
        """Retrieve a value from global storage"""
        return self.data.get(key)
    
    def setValue(self, key, value):
        """Store a value (Qt-style naming)"""
        self.data[key] = value
        
    def remove(self, key):
        """Remove a value from global storage"""
        if key in self.data:
            del self.data[key]
            
    def contains(self, key):
        """Check if key exists"""
        return key in self.data

class JobQueue:
    """Mock JobQueue class"""
    def __init__(self):
        self.jobs = []
        
    def start(self):
        """Start the job queue"""
        pass
        
    def stop(self):
        """Stop the job queue"""
        pass

class Job:
    """Mock Job class"""
    def setPath(self, path):
        self.path = path
        
    def setWorkingPath(self, path):
        self.working_path = path

# Global instances
globalstorage = GlobalStorage()
job = JobQueue()

# Module functions
def gettext_path():
    """Get translation path"""
    return "/usr/share/calamares/lang"

def gettext_languages():
    """Get available languages"""
    return ["en", "es", "fr", "de", "it", "pt", "ru", "zh"]

def pretty_name():
    """Get pretty name for module"""
    return "Calamares Module"

def check_target_env_call(cmd):
    """Check command in target environment"""
    return 0

def target_env_process_output(cmd):
    """Get output from target environment command"""
    return "", ""

# Constants
ViewStepInterface = object
JobInterface = object