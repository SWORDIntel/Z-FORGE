#!/usr/bin/env python3
"""
Mock QtGui module
"""

class MockWidget:
    """Base mock widget class"""
    def __init__(self, *args, **kwargs):
        pass

QPixmap = MockWidget
QImage = MockWidget
QIcon = MockWidget
QFont = MockWidget
QColor = MockWidget
QPalette = MockWidget
QBrush = MockWidget
QPen = MockWidget
QPainter = MockWidget
QKeySequence = MockWidget
QValidator = MockWidget
QIntValidator = MockWidget
QDoubleValidator = MockWidget
QRegExpValidator = MockWidget