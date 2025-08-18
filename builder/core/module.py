#!/usr/bin/env python3
"""
Base Module Class for Z-FORGE Builder
Provides common functionality for build modules
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


class BaseModule:
    """Base class for all build modules"""
    
    def __init__(self, config: Dict[str, Any], chroot_path: Optional[Path] = None):
        """Initialize base module
        
        Args:
            config: Module configuration dictionary
            chroot_path: Path to chroot environment (optional)
        """
        self.config = config
        self.chroot_path = Path(chroot_path) if chroot_path else None
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def execute(self) -> bool:
        """Execute module logic - must be implemented by subclasses
        
        Returns:
            bool: True if successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement execute() method")
        
    def cleanup(self) -> bool:
        """Cleanup module resources - optional override
        
        Returns:
            bool: True if successful, False otherwise
        """
        return True
        
    def get_status(self) -> Dict[str, Any]:
        """Get module status - optional override
        
        Returns:
            dict: Module status information
        """
        return {
            'name': self.__class__.__name__,
            'config': self.config,
            'chroot_path': str(self.chroot_path) if self.chroot_path else None
        }
    
    def _validate_chroot(self) -> bool:
        """Validate chroot environment is available and accessible
        
        Returns:
            bool: True if chroot is valid, False otherwise
        """
        if not self.chroot_path:
            self.logger.error("No chroot path specified")
            return False
            
        if not self.chroot_path.exists():
            self.logger.error(f"Chroot path does not exist: {self.chroot_path}")
            return False
            
        if not self.chroot_path.is_dir():
            self.logger.error(f"Chroot path is not a directory: {self.chroot_path}")
            return False
            
        # Check if basic system directories exist
        required_dirs = ['bin', 'usr', 'etc']
        for dirname in required_dirs:
            dir_path = self.chroot_path / dirname
            if not dir_path.exists():
                self.logger.warning(f"Missing system directory in chroot: {dirname}")
                
        return True
    
    def _run_in_chroot(self, command: str) -> bool:
        """Run command in chroot environment
        
        Args:
            command: Shell command to execute
            
        Returns:
            bool: True if command succeeded (exit code 0), False otherwise
        """
        if not self._validate_chroot():
            return False
            
        try:
            self.logger.debug(f"Running in chroot: {command}")
            
            # Use shell to execute command in chroot
            full_command = ['chroot', str(self.chroot_path), 'bash', '-c', command]
            
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                if result.stdout:
                    self.logger.debug(f"Command output: {result.stdout.strip()}")
                return True
            else:
                self.logger.error(f"Command failed (exit {result.returncode}): {command}")
                if result.stderr:
                    self.logger.error(f"Error output: {result.stderr.strip()}")
                if result.stdout:
                    self.logger.debug(f"Standard output: {result.stdout.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {command}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to run command in chroot: {e}")
            return False
    
    def _run_in_chroot_output(self, command: str) -> str:
        """Run command in chroot and return output
        
        Args:
            command: Shell command to execute
            
        Returns:
            str: Command output (stdout), empty string on failure
        """
        if not self._validate_chroot():
            return ""
            
        try:
            self.logger.debug(f"Running in chroot for output: {command}")
            
            # Use shell to execute command in chroot
            full_command = ['chroot', str(self.chroot_path), 'bash', '-c', command]
            
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                self.logger.debug(f"Command output: {output}")
                return output
            else:
                self.logger.error(f"Command failed (exit {result.returncode}): {command}")
                if result.stderr:
                    self.logger.error(f"Error output: {result.stderr.strip()}")
                return ""
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {command}")
            return ""
        except Exception as e:
            self.logger.error(f"Failed to run command in chroot: {e}")
            return ""
    
    def _path_exists_in_chroot(self, path: str) -> bool:
        """Check if a path exists within the chroot environment
        
        Args:
            path: Path to check (relative to chroot root or absolute)
            
        Returns:
            bool: True if path exists in chroot, False otherwise
        """
        if not self._validate_chroot():
            return False
            
        try:
            # Convert path to Path object and handle both absolute and relative paths
            check_path = Path(path)
            
            # If path is absolute, remove leading slash to make it relative to chroot
            if check_path.is_absolute():
                check_path = Path(*check_path.parts[1:])
                
            # Build full chroot path
            full_path = self.chroot_path / check_path
            
            exists = full_path.exists()
            self.logger.debug(f"Path exists check: {path} -> {full_path} = {exists}")
            
            return exists
            
        except Exception as e:
            self.logger.error(f"Failed to check path in chroot: {e}")
            return False