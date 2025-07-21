#!/usr/bin/env python3
"""Fix the PostInstallAgent to match the pattern of other agents"""

with open('implementation/multi_agent_module_builder.py', 'r') as f:
    content = f.read()

# The issue is that the main_content in PostInstallAgent contains nested triple quotes
# which confuses the parser. We need to escape them or restructure.

# Let's check if this is indeed the issue
lines = content.split('\n')

# Find where main_content is defined in PostInstallAgent
main_content_line = None
for i in range(len(lines)):
    if 'class PostInstallAgent' in lines[i]:
        # Look for main_content in this class
        for j in range(i, min(i + 100, len(lines))):
            if 'main_content = ' in lines[j] and "'''" in lines[j]:
                main_content_line = j
                print(f"Found main_content at line {j+1}")
                break
        break

if main_content_line:
    # Find the end of this string
    end_line = None
    quote_count = 1  # We started with opening '''
    
    for i in range(main_content_line + 1, len(lines)):
        if "'''" in lines[i]:
            # Check if this is inside the string (part of the content) or closing it
            # If the line starts without indentation and is just ''', it's likely closing
            if lines[i].strip() == "'''" and len(lines[i]) - len(lines[i].lstrip()) == 0:
                # Check what comes after
                if i + 1 < len(lines) and 'module_path' in lines[i + 1]:
                    end_line = i
                    print(f"Found end of main_content at line {i+1}")
                    break

# The fix: Look at the pattern from NetworkConfigAgent
# In that agent, the main_content doesn't contain nested ''' strings
# But in PostInstallAgent, it does (the script_content variable)

# We need to escape the inner triple quotes
print("\nApplying fix...")

# Replace the inner triple quotes with escaped version
# Find the script_content definition inside main_content
fixed_lines = []
inside_main_content = False
main_content_start_line = 0

for i, line in enumerate(lines):
    if i == main_content_line:
        inside_main_content = True
        main_content_start_line = i
        fixed_lines.append(line)
    elif inside_main_content and i == end_line:
        inside_main_content = False
        fixed_lines.append(line)
    elif inside_main_content:
        # Check if this line has script_content = '''
        if "script_content = '''" in line:
            # Replace ''' with \"\"\"
            fixed_line = line.replace("'''", '"""')
            fixed_lines.append(fixed_line)
            print(f"Fixed line {i+1}: replaced ''' with \"\"\"")
        elif line.strip() == "'''" and "script_content" in ''.join(lines[max(0,i-20):i]):
            # This is the closing ''' for script_content
            fixed_line = line.replace("'''", '"""')
            fixed_lines.append(fixed_line)
            print(f"Fixed line {i+1}: replaced closing ''' with \"\"\"")
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

# Write the fixed content
fixed_content = '\n'.join(fixed_lines)
with open('implementation/multi_agent_module_builder.py', 'w') as f:
    f.write(fixed_content)

print("\nTesting fix...")
try:
    compile(fixed_content, 'test', 'exec')
    print("Success! File now compiles without errors.")
except SyntaxError as e:
    print(f"Still has error at line {e.lineno}: {e.msg}")
    print(f"Error text: {e.text}")