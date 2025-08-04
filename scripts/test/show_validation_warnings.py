#!/usr/bin/env python3
"""Show validation warnings in detail."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from builder.modules.build_pipeline_validator import BuildPipelineValidator, ValidationLevel

def main():
    """Show validation warnings."""
    workspace = project_root / "test_workspace"
    config = {
        'name': 'Z-FORGE',
        'zfs': {'enabled': True}
    }
    
    print("Running build pipeline validation...")
    print("=" * 70)
    
    validator = BuildPipelineValidator(project_root, workspace, config)
    report = validator.validate_complete_pipeline()
    
    # Summary
    print(f"\nValidation Results: {report.overall_status}")
    print(f"Total Checks: {report.total_checks}")
    print(f"Passed: {report.passed_checks}")
    print(f"Failed: {report.failed_checks}")
    print(f"Critical: {report.critical_failures}")
    print(f"Errors: {report.error_failures}")
    print(f"Warnings: {report.warning_count}")
    
    # Show warnings
    if report.warning_count > 0:
        print("\n" + "=" * 70)
        print("⚠️  WARNINGS FOUND:")
        print("=" * 70)
        
        warning_num = 1
        for check in report.results:
            if check.level == ValidationLevel.WARNING:
                print(f"\nWarning {warning_num}: {check.component} - {check.check_name}")
                print(f"Status: {'PASSED' if check.status else 'FAILED'}")
                print(f"Message: {check.message}")
                if check.details:
                    print(f"Details: {check.details}")
                if check.fix_suggestion:
                    print(f"Fix: {check.fix_suggestion}")
                warning_num += 1
    
    # Show errors if any
    if report.error_failures > 0:
        print("\n" + "=" * 70)
        print("❌ ERRORS FOUND:")
        print("=" * 70)
        
        error_num = 1
        for check in report.results:
            if check.level == ValidationLevel.ERROR:
                print(f"\nError {error_num}: {check.component} - {check.check_name}")
                print(f"Status: {'PASSED' if check.status else 'FAILED'}")
                print(f"Message: {check.message}")
                if check.details:
                    print(f"Details: {check.details}")
                if check.fix_suggestion:
                    print(f"Fix: {check.fix_suggestion}")
                error_num += 1
    
    # Recommendations
    print("\n" + "=" * 70)
    print("📋 RECOMMENDATIONS:")
    print("=" * 70)
    
    if report.warning_count > 0:
        print("\nThe warnings are non-critical and the build can proceed.")
        print("They typically involve:")
        print("- Optional features not configured")
        print("- Non-essential tools not installed")
        print("- Recommended but not required settings")
    else:
        print("\n✅ No warnings or errors found!")
    
    print("\nTo proceed with the build:")
    print("  sudo python3 build.py --spec build_spec.yml")

if __name__ == "__main__":
    main()