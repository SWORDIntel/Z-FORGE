#!/usr/bin/env python3
import sys
import os

# Add calamares to path
sys.path.insert(0, 'calamares')

modules = [
    'gpupassthrough', 'hardwarehealth', 'networkconfig', 
    'postinstall', 'storagelayout', 'zfsenhancedconfig',
    'zfsrichconfig', 'zfsrootselect'
]

results = []
for module in modules:
    sys.path.insert(0, f'calamares/modules/{module}')
    try:
        exec(f"import calamares.modules.{module}.main")
        results.append(f"✅ {module}: OK")
    except Exception as e:
        results.append(f"❌ {module}: {str(e)[:50]}")
    # Remove from path for clean test
    sys.path.pop(0)

for result in results:
    print(result)

passed = sum(1 for r in results if r.startswith("✅"))
total = len(results)
print(f"\nImport test results: {passed}/{total} ({100*passed//total}%)")