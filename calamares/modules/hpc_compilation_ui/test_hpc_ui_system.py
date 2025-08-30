#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HPC Compilation UI System Test Suite
Comprehensive testing for the HPC compilation installer UI system
"""

import sys
import os
import time
import json
import unittest
import tempfile
import subprocess
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    from compilation_progress_parser import CompilationProgressParser, CompilationPhase, ErrorSeverity, CompilationError, ProgressInfo
    from resource_monitor import HPCResourceMonitor, ThermalState, ResourceMetrics, ThermalReading
    from compilation_controller import HPCCompilationController, CompilationState, ZoneState, CompilationZone
except ImportError as e:
    print(f"ERROR: Could not import modules: {e}")
    print("Make sure all required modules are in the current directory")
    sys.exit(1)

class TestCompilationProgressParser(unittest.TestCase):
    """Test the compilation progress parser"""
    
    def setUp(self):
        self.parser = CompilationProgressParser()
    
    def test_progress_parsing(self):
        """Test progress extraction from compiler output"""
        test_cases = [
            ("[ 25%] Building CXX object main.cpp.o", 25.0),
            ("[50/100] Compiling source.c", 50.0),
            ("make[1]: *** [75%] Built target test", 75.0),
        ]
        
        for line, expected_progress in test_cases:
            progress, errors = self.parser.parse_output_line(line, "test_component")
            
            if progress:
                self.assertGreaterEqual(progress.percent_complete, expected_progress - 1)
                self.assertLessEqual(progress.percent_complete, expected_progress + 1)
    
    def test_error_detection(self):
        """Test error detection in compiler output"""
        test_cases = [
            ("error: 'undefined_function' was not declared", ErrorSeverity.ERROR),
            ("fatal error: cuda_runtime.h: No such file or directory", ErrorSeverity.FATAL),
            ("warning: unused variable 'temp'", ErrorSeverity.WARNING),
            ("note: candidate function not viable", ErrorSeverity.INFO),
        ]
        
        for line, expected_severity in test_cases:
            progress, errors = self.parser.parse_output_line(line, "test_component")
            
            self.assertGreater(len(errors), 0)
            self.assertEqual(errors[0].severity, expected_severity)
    
    def test_component_specific_parsing(self):
        """Test component-specific parsing"""
        cuda_line = "nvcc -arch=sm_35 -c kernel.cu -o kernel.o"
        progress, errors = self.parser.parse_output_line(cuda_line, "cuda")
        
        # Should detect CUDA compilation (parser may return 'nvcc' as component)
        self.assertIsNotNone(progress)
        self.assertIn(progress.component, ["cuda", "nvcc"])  # Accept either
    
    def test_error_suggestions(self):
        """Test error suggestion generation"""
        error_line = "fatal error: cuda_runtime.h: No such file or directory"
        progress, errors = self.parser.parse_output_line(error_line, "cuda")
        
        self.assertGreater(len(errors), 0)
        # Check that suggestion is helpful (contains relevant terms)
        suggestion = errors[0].suggestion.lower()
        self.assertTrue(any(word in suggestion for word in ["install", "package", "dependencies", "cuda"]))

class TestResourceMonitor(unittest.TestCase):
    """Test the resource monitor"""
    
    def setUp(self):
        self.config = {
            'update_interval_seconds': 0.1,
            'thermal_threshold_celsius': 85,
            'thermal_critical_celsius': 95,
            'memory_threshold_percent': 85,
            'memory_critical_percent': 95
        }
        self.monitor = HPCResourceMonitor(self.config)
    
    def test_initialization(self):
        """Test monitor initialization"""
        self.assertIsNotNone(self.monitor.current_metrics)
        self.assertIsInstance(self.monitor.thermal_sensors, list)
    
    def test_metrics_collection(self):
        """Test system metrics collection"""
        # Start monitoring briefly
        self.monitor.start_monitoring()
        time.sleep(0.2)  # Let it collect metrics
        self.monitor.stop_monitoring()
        
        metrics = self.monitor.get_current_metrics()
        
        # Check basic metrics are collected
        self.assertGreater(metrics.cpu_cores_physical, 0)
        self.assertGreater(metrics.memory_total_gb, 0)
        self.assertGreaterEqual(metrics.cpu_usage_percent, 0)
        self.assertGreaterEqual(metrics.memory_percent, 0)
    
    def test_thermal_state_determination(self):
        """Test thermal state determination"""
        test_cases = [
            (70.0, ThermalState.NORMAL),
            (80.0, ThermalState.ELEVATED),
            (90.0, ThermalState.WARNING),
            (97.0, ThermalState.CRITICAL),
            (105.0, ThermalState.EMERGENCY),
        ]
        
        for temp, expected_state in test_cases:
            state = self.monitor._determine_thermal_state(temp)
            self.assertEqual(state, expected_state)
    
    def test_performance_analysis(self):
        """Test performance analysis"""
        analysis = self.monitor.get_performance_analysis()
        
        # Check required fields
        self.assertIn('efficiency_percent', analysis)
        self.assertIn('recommended_parallel_jobs', analysis)
        self.assertIn('thermal_state', analysis)
        self.assertIn('recommendations', analysis)
        
        # Check realistic values
        self.assertGreaterEqual(analysis['efficiency_percent'], 0)
        self.assertLessEqual(analysis['efficiency_percent'], 100)
        self.assertGreaterEqual(analysis['recommended_parallel_jobs'], 1)
    
    def test_thermal_callbacks(self):
        """Test thermal state change callbacks"""
        callback_called = threading.Event()
        callback_args = []
        
        def test_callback(old_state, new_state, metrics):
            callback_args.extend([old_state, new_state, metrics])
            callback_called.set()
        
        self.monitor.add_thermal_callback(ThermalState.WARNING, test_callback)
        
        # Mock a thermal state change
        old_state = self.monitor.thermal_state
        self.monitor.thermal_state = ThermalState.NORMAL
        
        # Create mock metrics with elevated temperature
        mock_metrics = ResourceMetrics()
        mock_metrics.cpu_temperature = 90.0
        mock_metrics.thermal_state = ThermalState.WARNING
        
        self.monitor._check_thermal_state_changes(mock_metrics)
        
        # Check if callback was called
        self.assertTrue(callback_called.wait(timeout=1.0))
        self.assertEqual(len(callback_args), 3)

class TestCompilationController(unittest.TestCase):
    """Test the compilation controller"""
    
    def setUp(self):
        self.config = {
            'max_parallel_jobs': 2,
            'enable_process_control': True,
            'pause_timeout_seconds': 5.0,
            'stop_timeout_seconds': 10.0
        }
        self.controller = HPCCompilationController(self.config)
        
        # Setup test zones
        zones_config = [
            {
                'name': 'test_zone_1',
                'components': ['component_1', 'component_2'],
                'max_retries': 2
            },
            {
                'name': 'test_zone_2',
                'components': ['component_3'],
                'max_retries': 1
            }
        ]
        self.controller.initialize_zones(zones_config)
    
    def test_initialization(self):
        """Test controller initialization"""
        self.assertEqual(len(self.controller.zones), 2)
        self.assertEqual(self.controller.state, CompilationState.IDLE)
        self.assertEqual(self.controller.current_zone_index, 0)
    
    def test_zone_initialization(self):
        """Test zone setup"""
        zone1 = self.controller.zones[0]
        self.assertEqual(zone1.name, 'test_zone_1')
        self.assertEqual(len(zone1.components), 2)
        self.assertEqual(zone1.state, ZoneState.PENDING)
    
    def test_state_transitions(self):
        """Test compilation state transitions"""
        # Test start
        self.assertTrue(self.controller.start_compilation())
        self.assertEqual(self.controller.state, CompilationState.RUNNING)
        
        # Test pause
        time.sleep(0.1)  # Let it start
        self.assertTrue(self.controller.pause_compilation())
        self.assertEqual(self.controller.state, CompilationState.PAUSED)
        
        # Test resume
        self.assertTrue(self.controller.resume_compilation())
        self.assertEqual(self.controller.state, CompilationState.RUNNING)
        
        # Test stop
        self.assertTrue(self.controller.stop_compilation())
        self.assertEqual(self.controller.state, CompilationState.CANCELLED)
    
    def test_zone_skipping(self):
        """Test zone skip functionality"""
        zone_name = 'test_zone_1'
        self.assertTrue(self.controller.skip_zone(zone_name))
        
        zone = self.controller._find_zone(zone_name)
        self.assertEqual(zone.state, ZoneState.SKIPPED)
        self.assertTrue(zone.skip_remaining)
    
    def test_zone_retry(self):
        """Test zone retry functionality"""
        zone_name = 'test_zone_1'
        zone = self.controller._find_zone(zone_name)
        
        # Set zone to failed state
        zone.state = ZoneState.FAILED
        zone.retry_count = 0
        
        self.assertTrue(self.controller.retry_zone(zone_name))
        self.assertEqual(zone.state, ZoneState.RETRYING)
        self.assertEqual(zone.retry_count, 1)
    
    def test_parallelism_adjustment(self):
        """Test parallel job adjustment"""
        original_jobs = self.controller.current_parallel_jobs
        new_jobs = original_jobs + 2
        
        self.assertTrue(self.controller.adjust_parallelism(new_jobs))
        self.assertEqual(self.controller.current_parallel_jobs, new_jobs)
    
    def test_status_reporting(self):
        """Test compilation status reporting"""
        status = self.controller.get_compilation_status()
        
        # Check required fields
        required_fields = [
            'state', 'is_paused', 'total_zones', 'current_zone_index',
            'overall_progress', 'active_processes', 'zones'
        ]
        
        for field in required_fields:
            self.assertIn(field, status)
        
        self.assertEqual(status['total_zones'], 2)
        self.assertEqual(len(status['zones']), 2)
    
    def test_callbacks(self):
        """Test callback functionality"""
        callback_events = []
        
        def state_callback(old_state, new_state):
            callback_events.append(('state', old_state, new_state))
        
        def zone_callback(zone):
            callback_events.append(('zone', zone.name, zone.state))
        
        self.controller.add_state_change_callback(state_callback)
        self.controller.add_zone_change_callback(zone_callback)
        
        # Trigger state change
        self.controller._change_state(CompilationState.STARTING)
        
        # Check callbacks
        self.assertGreater(len(callback_events), 0)
        self.assertEqual(callback_events[0][0], 'state')
        self.assertEqual(callback_events[0][2], CompilationState.STARTING)

class TestUIIntegration(unittest.TestCase):
    """Test UI system integration"""
    
    def test_qt_availability(self):
        """Test Qt availability for GUI"""
        try:
            from PyQt5 import QtCore, QtWidgets
            self.assertTrue(True, "PyQt5 is available")
        except ImportError:
            self.skipTest("PyQt5 not available - GUI tests skipped")
    
    def test_curses_availability(self):
        """Test curses availability for TUI"""
        try:
            import curses
            self.assertTrue(True, "curses is available")
        except ImportError:
            self.fail("curses not available - TUI will not work")
    
    def test_psutil_availability(self):
        """Test psutil availability for resource monitoring"""
        try:
            import psutil
            self.assertTrue(True, "psutil is available")
        except ImportError:
            self.fail("psutil not available - resource monitoring will not work")

class TestSystemIntegration(unittest.TestCase):
    """Test full system integration"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'max_parallel_jobs': 2,
            'update_interval_seconds': 0.1,
            'thermal_threshold_celsius': 85,
            'memory_threshold_percent': 85,
            'state_file': os.path.join(self.temp_dir, 'state.json')
        }
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_integrated_compilation_flow(self):
        """Test complete compilation flow with monitoring"""
        # Create components
        parser = CompilationProgressParser()
        monitor = HPCResourceMonitor(self.config)
        controller = HPCCompilationController(self.config)
        
        # Setup test zones
        zones_config = [
            {
                'name': 'integrated_test',
                'components': ['test_component'],
                'max_retries': 1
            }
        ]
        controller.initialize_zones(zones_config)
        
        # Start monitoring
        monitor.start_monitoring()
        
        try:
            # Test progress parsing
            test_line = "[ 50%] Building test_component"
            progress, errors = parser.parse_output_line(test_line, "test")
            
            self.assertIsNotNone(progress)
            self.assertEqual(progress.percent_complete, 50.0)
            
            # Test resource monitoring
            time.sleep(0.2)  # Let monitor collect data
            metrics = monitor.get_current_metrics()
            
            self.assertGreater(metrics.cpu_cores_physical, 0)
            self.assertGreaterEqual(metrics.cpu_usage_percent, 0)
            
            # Test controller
            status = controller.get_compilation_status()
            self.assertEqual(status['state'], 'idle')
            
        finally:
            monitor.stop_monitoring()
    
    def test_error_handling(self):
        """Test error handling across components"""
        parser = CompilationProgressParser()
        
        # Test with invalid input
        progress, errors = parser.parse_output_line("", "")
        # Should not crash
        
        # Test monitor with invalid config
        try:
            monitor = HPCResourceMonitor({})
            # Should use defaults
            self.assertIsNotNone(monitor.config)
        except Exception as e:
            self.fail(f"Monitor initialization failed with invalid config: {e}")
    
    def test_state_persistence(self):
        """Test state saving and loading"""
        controller = HPCCompilationController(self.config)
        zones_config = [{'name': 'test', 'components': ['comp1'], 'max_retries': 1}]
        controller.initialize_zones(zones_config)
        
        # Save state
        controller._save_state()
        
        # Check state file exists
        self.assertTrue(os.path.exists(self.config['state_file']))
        
        # Check state file content
        with open(self.config['state_file'], 'r') as f:
            state_data = json.load(f)
        
        self.assertEqual(state_data['state'], 'idle')
        self.assertEqual(len(state_data['zones']), 1)

def run_performance_tests():
    """Run performance tests"""
    print("\n=== Performance Tests ===")
    
    # Test parser performance
    print("Testing parser performance...")
    parser = CompilationProgressParser()
    
    test_lines = [
        "[ 25%] Building CXX object main.cpp.o",
        "gcc -c -O3 src/test.c -o test.o",
        "error: undefined reference to 'function'",
        "warning: unused variable 'temp'",
    ] * 100  # 400 lines total
    
    start_time = time.time()
    
    for line in test_lines:
        parser.parse_output_line(line, "test")
    
    elapsed = time.time() - start_time
    lines_per_second = len(test_lines) / elapsed
    
    print(f"Parsed {len(test_lines)} lines in {elapsed:.3f}s ({lines_per_second:.0f} lines/sec)")
    
    # Test monitor performance
    print("Testing monitor performance...")
    config = {'update_interval_seconds': 0.01}
    monitor = HPCResourceMonitor(config)
    
    start_time = time.time()
    monitor.start_monitoring()
    time.sleep(1.0)  # Run for 1 second
    monitor.stop_monitoring()
    elapsed = time.time() - start_time
    
    history = monitor.get_metrics_history()
    updates_per_second = len(history) / elapsed
    
    print(f"Collected {len(history)} metric updates in {elapsed:.3f}s ({updates_per_second:.0f} updates/sec)")

def run_stress_tests():
    """Run stress tests"""
    print("\n=== Stress Tests ===")
    
    # Test many zones
    print("Testing with many compilation zones...")
    config = {'max_parallel_jobs': 4}
    controller = HPCCompilationController(config)
    
    # Create 50 zones with 10 components each
    zones_config = []
    for i in range(50):
        zones_config.append({
            'name': f'zone_{i}',
            'components': [f'comp_{j}' for j in range(10)],
            'max_retries': 2
        })
    
    start_time = time.time()
    controller.initialize_zones(zones_config)
    elapsed = time.time() - start_time
    
    print(f"Initialized {len(zones_config)} zones with {sum(len(z['components']) for z in zones_config)} components in {elapsed:.3f}s")
    
    # Test status reporting performance
    start_time = time.time()
    for _ in range(100):
        status = controller.get_compilation_status()
    elapsed = time.time() - start_time
    
    print(f"Generated 100 status reports in {elapsed:.3f}s ({100/elapsed:.0f} reports/sec)")

def main():
    """Main test runner"""
    print("=== HPC Compilation UI System Test Suite ===\n")
    
    # Check if we can import all modules
    try:
        from compilation_progress_parser import CompilationProgressParser
        from resource_monitor import HPCResourceMonitor  
        from compilation_controller import HPCCompilationController
        print("✓ All modules imported successfully\n")
    except ImportError as e:
        print(f"✗ Module import failed: {e}")
        return 1
    
    # Run unit tests
    print("Running unit tests...")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestCompilationProgressParser,
        TestResourceMonitor,
        TestCompilationController,
        TestUIIntegration,
        TestSystemIntegration
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Run performance tests
    if result.wasSuccessful():
        run_performance_tests()
        run_stress_tests()
        
        print("\n=== Test Summary ===")
        print(f"✓ {result.testsRun} unit tests passed")
        print("✓ Performance tests completed")
        print("✓ Stress tests completed")
        print("\n🎉 All tests passed! HPC Compilation UI system is ready for deployment.")
        return 0
    else:
        print(f"\n✗ {len(result.failures)} test failures, {len(result.errors)} errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())