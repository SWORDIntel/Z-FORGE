#!/usr/bin/env python3
"""Apply a targeted fix to the module builder"""

# Read the file
with open('implementation/multi_agent_module_builder.py', 'r') as f:
    lines = f.readlines()

# The issue is specifically at lines 2506-2507
# We need to ensure they match the pattern from working agents

# Find the issue
for i in range(len(lines)):
    if i == 2505 and 'calamares_module = PostInstallViewStep' in lines[i]:
        print(f"Found target at line {i+1}")
        print(f"Line {i+1}: {repr(lines[i])}")
        print(f"Line {i+2}: {repr(lines[i+1])}")
        print(f"Line {i+3}: {repr(lines[i+2])}")
        
        # The pattern from working agents is:
        # Line N: "calamares_module = SomeViewStep\n"
        # Line N+1: "'''\n"
        # Line N+2: "        (module_path / "main.py").write_text(main_content)\n"
        
        # Check if our lines match this pattern
        if lines[i].rstrip() == 'calamares_module = PostInstallViewStep':
            print("Line 2506 is correct")
        
        if lines[i+1].rstrip() == "'''":
            print("Line 2507 is correct")
        else:
            print(f"Line 2507 issue: expected \"'''\", got {repr(lines[i+1].rstrip())}")
            
        # Check line 2508 (index i+2)
        expected_prefix = '        (module_path / "main.py").write_text(main_content)'
        if lines[i+2].rstrip() == expected_prefix:
            print("Line 2508 is correct")
        else:
            print(f"Line 2508 issue: got {repr(lines[i+2].rstrip())}")
        
        # Apply fix - ensure exact format
        lines[i] = 'calamares_module = PostInstallViewStep\n'
        lines[i+1] = "'''\n"
        # Line i+2 should already be correct
        
        break

# Write back
with open('implementation/multi_agent_module_builder.py', 'w') as f:
    f.writelines(lines)

print("\nFix applied. Testing...")

# Test compile
try:
    with open('implementation/multi_agent_module_builder.py', 'r') as f:
        compile(f.read(), 'test', 'exec')
    print("Success! File now compiles without errors.")
except SyntaxError as e:
    print(f"Still has error at line {e.lineno}: {e.msg}")