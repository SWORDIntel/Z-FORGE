# Make libcalamares available to all modules
import sys
import os

# Add parent directory to path for libcalamares mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))