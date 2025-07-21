#!/usr/bin/env python3
"""Fix the multi_agent_module_builder.py file"""

import re

with open('implementation/multi_agent_module_builder.py', 'r') as f:
    content = f.read()

# The issue is that we have a multi-line string that contains Python code
# with its own indentation, and when the string ends, Python gets confused
# about the indentation context.

# Let's find the PostInstallAgent class and fix it
# We need to ensure the implement_module method is properly structured

# Split into lines for easier processing
lines = content.split('\n')

# Find the problematic section
fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Check if this is the problematic section
    if (i == 2505 and line.strip() == "calamares_module = PostInstallViewStep" and 
        i+1 < len(lines) and lines[i+1].strip() == "'''" and
        i+2 < len(lines) and "write_text(main_content)" in lines[i+2]):
        
        # Add the current line
        fixed_lines.append(line)
        # Add the closing '''
        fixed_lines.append(lines[i+1])
        # Now we need to ensure proper indentation for the rest
        # The write_text line should be indented as part of the method
        fixed_lines.append(lines[i+2])  # This line already has correct indentation
        i += 3
    else:
        fixed_lines.append(line)
        i += 1

# Write the fixed content
fixed_content = '\n'.join(fixed_lines)

# Let's try a different approach - compile and see exactly where the error is
try:
    compile(fixed_content, 'test', 'exec')
    print("File compiles successfully!")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
    print(f"Text around error: {e.text}")
    
    # The issue might be that we need to ensure the main_content string
    # is properly closed before the write_text line
    
    # Let's check the specific pattern
    if e.lineno == 2507:
        print("\nThe issue is at line 2507. Let's examine the context...")
        
        # The problem is that after the ''' on line 2506, Python expects
        # either no indentation (module level) or consistent indentation
        # within a function/class. But line 2507 has 8 spaces, suggesting
        # it's inside a method, but the previous lines don't establish that context.
        
        # Let's trace back to find the method context
        method_indent = None
        for j in range(e.lineno - 1, max(0, e.lineno - 100), -1):
            if 'def implement_module' in lines[j]:
                method_indent = len(lines[j]) - len(lines[j].lstrip())
                print(f"Found implement_module at line {j+1} with indent {method_indent}")
                break
        
        if method_indent is not None:
            # The content inside the method should be indented by 4 more spaces
            expected_indent = method_indent + 4
            actual_indent = len(lines[e.lineno-1]) - len(lines[e.lineno-1].lstrip())
            print(f"Expected indent: {expected_indent}, Actual indent: {actual_indent}")
            
            # The issue is that the ''' string contains unindented Python code
            # which resets Python's understanding of the indentation level
            print("\nThe issue is that the multi-line string contains unindented code")
            print("which confuses Python's indentation tracking.")
            
# Write the original content back for now
with open('implementation/multi_agent_module_builder.py', 'w') as f:
    f.write(content)

print("\nTo fix this, we need to restructure how the main_content string is handled.")
print("The string should not contain unindented Python code at the module level.")