#!/usr/bin/env python3
"""
Mock PyQt5 package for testing outside of Calamares environment
"""

# Re-export all submodules
from . import QtWidgets
from . import QtCore
from . import QtGui

__all__ = ['QtWidgets', 'QtCore', 'QtGui']