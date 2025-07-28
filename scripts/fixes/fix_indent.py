#!/usr/bin/env python3
"""Fix the indentation issue in multi_agent_module_builder.py"""

with open('implementation/multi_agent_module_builder.py', 'r') as f:
    content = f.read()

# The issue is around line 2506-2507
# We need to ensure the closing ''' maintains proper context
# Look for the problematic section
lines = content.split('\n')

# Find the PostInstallAgent section
for i in range(len(lines)):
    if i == 2505 and lines[i].strip() == "calamares_module = PostInstallViewStep":
        # Check if next line is just '''
        if i+1 < len(lines) and lines[i+1].strip() == "'''":
            # Check if the line after that starts with spaces
            if i+2 < len(lines) and lines[i+2].startswith('        '):
                # This is our problematic section
                # The ''' should be on the same indentation level as the write_text line
                # But the content inside the string should not be indented
                print(f"Found issue at line {i+1}")
                print(f"Line {i+1}: {repr(lines[i])}")
                print(f"Line {i+2}: {repr(lines[i+1])}")
                print(f"Line {i+3}: {repr(lines[i+2])}")
                
                # The pattern should match other agents - the ''' stays at column 0
                # This is correct, the issue might be elsewhere
                break

# Check if we have unmatched quotes
in_string = False
string_delim = None
for i, line in enumerate(lines):
    # Simple quote tracking (doesn't handle all cases but good enough)
    if "'''" in line:
        count = line.count("'''")
        if count % 2 == 1:  # Odd number toggles state
            in_string = not in_string
    
    # At line 2506, we should NOT be in a string
    if i == 2505:
        print(f"\nAt line {i+1} (calamares_module line): in_string = {in_string}")
    if i == 2506:
        print(f"At line {i+1} (''' line): in_string = {in_string}")
    if i == 2507:
        print(f"At line {i+1} (write_text line): in_string = {in_string}")
        if in_string:
            print("ERROR: We're still inside a string at the write_text line!")

print("\nChecking indentation levels...")
for i in range(2504, 2510):
    if i < len(lines):
        indent = len(lines[i]) - len(lines[i].lstrip())
        print(f"Line {i+1}: indent={indent}, content={repr(lines[i][:40])}")