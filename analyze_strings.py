#!/usr/bin/env python3
"""Analyze the string literals in the file"""

with open('implementation/multi_agent_module_builder.py', 'r') as f:
    content = f.read()

# Count triple quotes before line 2507
lines = content.split('\n')
triple_count = 0
inside_docstring = False

for i in range(min(2510, len(lines))):
    line = lines[i]
    
    # Count ''' in this line
    count = line.count("'''")
    
    if count > 0:
        # Check if we're in the PostInstallAgent area
        if 1950 <= i <= 2510:
            triple_count += count
            print(f"Line {i+1}: Found {count} triple quotes. Total so far: {triple_count}")
            
            # Check if it's inside a larger string
            if i >= 2500:
                print(f"  Content: {repr(line[:60])}")

print(f"\nTotal triple quotes before line 2510: {triple_count}")
print(f"Is this even? {triple_count % 2 == 0}")

# Let's specifically check the main_content assignment
print("\n\nLooking for main_content assignment in PostInstallAgent...")
in_postinstall = False
for i in range(len(lines)):
    if 'class PostInstallAgent' in lines[i]:
        in_postinstall = True
        print(f"Found PostInstallAgent at line {i+1}")
    
    if in_postinstall and 'class ' in lines[i] and 'PostInstallAgent' not in lines[i]:
        in_postinstall = False
        print(f"Left PostInstallAgent at line {i+1}")
        break
        
    if in_postinstall and 'main_content = ' in lines[i] and "'''" in lines[i]:
        print(f"Line {i+1}: main_content assignment starts")
        
        # Find where this string ends
        j = i + 1
        while j < len(lines):
            if "'''" in lines[j]:
                print(f"Line {j+1}: Found closing ''' - {repr(lines[j][:60])}")
                break
            j += 1