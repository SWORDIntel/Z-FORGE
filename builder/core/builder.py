#!/usr/bin/env python3
# z-forge/builder/core/builder.py

"""
Core Builder Framework
Orchestrates the Z-Forge build process
"""

import sys
import logging
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .config import BuildConfig
from .lockfile import BuildLockfile


class ZForgeBuilder:
    """
    Main orchestration engine for Z-Forge ISO builder
    Implements modular build pipeline based on build_spec.yml
    """

    def __init__(self, config_path: str = "build_spec.yml"):
        """Initialize builder with configuration"""
        self.config = BuildConfig(config_path)
        builder_config = self.config.get('builder_config', {})
        workspace_path = builder_config.get('workspace_path',
                                           '/tmp/zforge_workspace')
        self.workspace = Path(workspace_path)
        self._setup_logging()
        self.modules_path = Path(__file__).parent.parent / "modules"

    def _setup_logging(self):
        """Configure comprehensive logging"""

        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"zforge_build_{timestamp}.log"

        # Configure logging
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('ZForge')
        self.log_path = log_file

    def execute_pipeline(
        self,
        modules: Optional[List[str]] = None,
        resume: bool = False,
        lockfile: Optional[BuildLockfile] = None
    ) -> Dict:
        """
        Execute the complete build pipeline or specific modules

        Args:
            modules: Optional list of modules to run (default: all enabled in config)
            resume: Whether to resume from a previously failed build
            lockfile: Optional lockfile instance for version tracking

        Returns:
            Dict with build status and results
        """

        self.logger.info("Starting Z-Forge build pipeline")

        # Get modules to execute
        if not modules:
            modules_config = self.config.get('modules', [])
            modules = [
                m['name'] for m in modules_config if m.get('enabled', True)
            ]

        self.logger.info(
            f"Executing modules: {', '.join(modules)}"
        )

        # Initialize or load lockfile
        if not lockfile:
            lockfile_path = Path("build_spec.lock")
            lockfile = BuildLockfile(lockfile_path)

        # Track progress
        results = {}
        resume_data = {}

        try:
            # Execute each module in sequence
            for module_name in modules:
                # Check if we should skip based on resume
                if resume and module_name in results:
                    self.logger.info(f"Skipping already completed module: {module_name}")
                    continue

                # Get resume data for this module if available
                module_resume = resume_data.get(module_name)

                # Execute the module
                self.logger.info(f"Executing module: {module_name}")

                try:
                    result = self._execute_module(module_name, module_resume, lockfile)
                    results[module_name] = result

                    # Check if the module was successful
                    if result.get('status') != 'success':
                        error_details = result.get('error')
                        self.logger.error(
                            f"Module {module_name} failed: {error_details}"
                        )
                        return {
                            'status': 'error',
                            'error': error_details,
                            'module': module_name,
                            'results': results,
                            'log_path': str(self.log_path),
                        }

                    # Save progress after each module
                    self._save_progress(results, lockfile)

                except Exception as e:
                    error_msg = f"Exception in module {module_name}: {str(e)}"
                    self.logger.error(error_msg)
                    self.logger.error(traceback.format_exc())
                    return {
                        'status': 'error',
                        'error': error_msg,
                        'module': module_name,
                        'results': results,
                        'log_path': str(self.log_path),
                    }

            # All modules completed successfully
            iso_path = None
            if 'ISOGeneration' in results:
                iso_path = results['ISOGeneration'].get('iso_path')

            return {
                'status': 'success',
                'results': results,
                'iso_path': iso_path,
                'log_path': str(self.log_path),
                'lockfile_path': str(lockfile.lockfile_path),
            }

        except Exception as e:
            error_msg = f"Build pipeline failed: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'error': error_msg,
                'results': results,
                'log_path': str(self.log_path),
            }

    def execute_module(self, module_name: str, resume_data: Optional[Dict] = None) -> Dict:
        """
        Execute a single module with optional resume data

        Args:
            module_name: Name of the module to execute
            resume_data: Optional data for resuming partial execution

        Returns:
            Dict with module execution results
        """

        return self._execute_module(module_name, resume_data)

    def _execute_module(self, module_name: str, resume_data: Optional[Dict] = None,
                       lockfile: Optional[BuildLockfile] = None) -> Dict:
        """Internal implementation of module execution"""

        # Import the module
        try:
            module_path = f"modules.{module_name.lower()}"
            module = importlib.import_module(module_path, package="builder")

            # Create instance
            class_name = module_name
            if not hasattr(module, class_name):
                class_name = ''.join(
                    word.title() for word in module_name.split('_')
                )

            if hasattr(module, class_name):
                module_instance = getattr(module, class_name)(
                    self.workspace,
                    self.config.data
                )

                # Execute module
                result = module_instance.execute(resume_data)

                # Record to lockfile if provided
                if lockfile and result.get('status') == 'success':
                    lockfile.record_module_execution(module_name, result)

                return result
            else:
                error_msg = (
                    f"Class {class_name} not found in module {module_name}"
                )
                return {
                    'status': 'error',
                    'error': error_msg
                }

        except ImportError as e:
            return {
                'status': 'error',
                'error': f"Failed to import module {module_name}: {str(e)}"
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Error in module {module_name}: {str(e)}"
            }

    def _save_progress(self, results: Dict, lockfile: BuildLockfile):
        """Save current build progress to enable resuming"""

        # Save results to progress file
        # progress_file = self.workspace / "build_progress.json" # TODO: Implement saving results

        # Save lockfile
        lockfile.save()

        # In a more complete implementation, we'd save the results here
        # to persist them between runs
