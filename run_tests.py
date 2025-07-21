#!/usr/bin/env python3
"""Z-FORGE Test Runner"""
import sys
import subprocess
import argparse
from pathlib import Path

def run_tests(test_type="all", verbose=False, coverage=False):
    """Run the test suite"""
    cmd = ["pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=calamares/modules", "--cov=builder", "--cov-report=html", "--cov-report=term"])
    
    if test_type == "all":
        cmd.append("tests/")
    elif test_type == "unit":
        cmd.append("tests/module_tests/")
    elif test_type == "integration":
        cmd.append("tests/integration_tests/")
    elif test_type == "specific":
        # Run specific test file
        return cmd
    
    # Add common pytest options
    cmd.extend(["-x", "--tb=short"])  # Stop on first failure, short traceback
    
    return cmd

def main():
    parser = argparse.ArgumentParser(description="Run Z-FORGE tests")
    parser.add_argument("--type", choices=["all", "unit", "integration"], 
                       default="all", help="Type of tests to run")
    parser.add_argument("--module", help="Specific module to test")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    
    args = parser.parse_args()
    
    if args.install_deps:
        print("Installing test dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", 
                       "pytest", "pytest-cov", "pytest-mock", "pytest-timeout"],
                      check=True)
        print("Dependencies installed!")
        return
    
    # Build test command
    cmd = run_tests(args.type, args.verbose, args.coverage)
    
    if args.module:
        # Test specific module
        test_file = Path(f"tests/module_tests/test_{args.module}.py")
        if test_file.exists():
            cmd.append(str(test_file))
        else:
            print(f"Test file not found: {test_file}")
            sys.exit(1)
    
    print(f"Running: {' '.join(cmd)}")
    
    # Run tests
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()