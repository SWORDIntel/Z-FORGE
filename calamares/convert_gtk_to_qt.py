#!/usr/bin/env python3
"""
GTK to Qt Converter for Calamares Modules
Converts GTK-based GUI code to Qt for Calamares compatibility
"""

import os
import re
from pathlib import Path

def convert_gtk_to_qt(file_path):
    """Convert GTK code to Qt in a Python file"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if file uses GTK
    if 'gi.repository' not in content and 'Gtk' not in content:
        return False
    
    print(f"Converting {file_path}...")
    
    # Replace imports
    replacements = [
        # GTK imports to Qt
        (r"import gi\ngi\.require_version\('Gtk', '3\.0'\)\nfrom gi\.repository import Gtk",
         "from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QCheckBox, QLineEdit, QTextEdit, QGroupBox\nfrom PyQt5.QtCore import Qt, pyqtSignal"),
        
        # Common GTK to Qt widget replacements
        (r"Gtk\.Window", "QWidget"),
        (r"Gtk\.VBox", "QVBoxLayout"),
        (r"Gtk\.HBox", "QHBoxLayout"),
        (r"Gtk\.Label", "QLabel"),
        (r"Gtk\.Button", "QPushButton"),
        (r"Gtk\.Entry", "QLineEdit"),
        (r"Gtk\.TextView", "QTextEdit"),
        (r"Gtk\.ComboBoxText", "QComboBox"),
        (r"Gtk\.CheckButton", "QCheckBox"),
        (r"Gtk\.Box", "QGroupBox"),
        
        # Method replacements
        (r"\.pack_start\([^)]+\)", ".addWidget"),
        (r"\.show_all\(\)", ".show()"),
        (r"\.set_text\(", ".setText("),
        (r"\.get_text\(\)", ".text()"),
        (r"\.connect\('clicked',", ".clicked.connect("),
        (r"\.set_active\(", ".setChecked("),
        (r"\.get_active\(\)", ".isChecked()"),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # Backup original file
    backup_path = f"{file_path}.gtk_backup"
    os.rename(file_path, backup_path)
    
    # Write converted file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"  Converted and backed up to {backup_path}")
    return True

def main():
    """Convert all GTK modules to Qt"""
    modules_dir = Path("modules")
    converted_count = 0
    
    for module_dir in modules_dir.iterdir():
        if module_dir.is_dir():
            for py_file in module_dir.glob("*.py"):
                if convert_gtk_to_qt(py_file):
                    converted_count += 1
    
    print(f"\nConverted {converted_count} files from GTK to Qt")

if __name__ == "__main__":
    main()
