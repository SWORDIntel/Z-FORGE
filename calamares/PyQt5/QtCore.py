#!/usr/bin/env python3
"""
Mock QtCore module  
"""

class MockWidget:
    """Base mock widget class"""
    def __init__(self, *args, **kwargs):
        pass

class Qt:
    """Qt namespace with constants"""
    AlignLeft = 1
    AlignRight = 2
    AlignCenter = 4
    AlignTop = 32
    AlignBottom = 64
    AlignVCenter = 128
    AlignHCenter = 4
    Horizontal = 1
    Vertical = 2
    KeepAspectRatio = 0
    IgnoreAspectRatio = 1
    Checked = 2
    Unchecked = 0
    PartiallyChecked = 1

def pyqtSignal(*args):
    """Mock signal decorator"""
    return lambda self: None

QObject = MockWidget
QTimer = MockWidget
QThread = MockWidget
QMutex = MockWidget
QWaitCondition = MockWidget
QEvent = MockWidget
QSize = MockWidget
QPoint = MockWidget
QRect = MockWidget
QUrl = MockWidget
QDateTime = MockWidget
QDate = MockWidget
QTime = MockWidget

# Mock GLib for compatibility
class GLib:
    """Mock GLib module"""
    pass