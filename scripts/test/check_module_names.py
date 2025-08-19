#!/usr/bin/env python3
"""Check all module names in build_spec.yml against actual files"""

import yaml
from pathlib import Path

# Load build spec
with open('build_spec.yml', 'r') as f:
    spec = yaml.safe_load(f)

# Check each module
modules_dir = Path('builder/modules')
print('Checking all modules in build_spec.yml:')
print('=' * 60)

issues = []
for module in spec['modules']:
    name = module['name']
    
    # Try different naming conventions
    possible_files = [
        f'{name}.py',
        f'{name.lower()}.py',
        f'{name.replace("Setup", "_setup").lower()}.py',
        f'{name.replace("Config", "_config").lower()}.py',
    ]
    
    found = False
    for pf in possible_files:
        if (modules_dir / pf).exists():
            expected = f'{name}.py'
            if pf != expected:
                issues.append((name, pf[:-3]))  # Remove .py extension
            print(f'✅ {name} -> {pf}')
            found = True
            break
    
    if not found:
        print(f'❌ {name} -> NOT FOUND')
        issues.append((name, None))

if issues:
    print(f'\n⚠️ Found {len(issues)} modules that need correction:')
    for name, correct in issues:
        if correct:
            print(f'  {name} should be: {correct}')
        else:
            print(f'  {name}: file not found')
else:
    print('\n✅ All module names are correct!')