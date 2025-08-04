#!/bin/bash

echo "=== Z-FORGE Build Specifications Check ==="
echo ""
echo "Checking all build specifications for:"
echo "1. Workspace path set to /home/john/zforge_workspace"
echo "2. dracut_config module present"
echo ""

# Counter for summary
total=0
correct_workspace=0
has_dracut=0

# Check each build spec
for spec in build_specs/build_spec.yml build_specs/build_spec_stable.yml build_specs/build_spec_no_tmp.yml build_specs/build_spec_outside_packages.yml build_specs/build_spec_proxmox9.yml build_specs/build_spec_proxmox_full.yml build_specs/build_spec_trixie_clean.yml; do
    if [ -f "$spec" ]; then
        total=$((total + 1))
        echo "📄 $spec"
        
        # Check workspace path
        workspace=$(grep "workspace_path:" "$spec" | head -1 | awk '{print $2}')
        if [ "$workspace" = "/home/john/zforge_workspace" ]; then
            echo "  ✅ Workspace: /home/john/zforge_workspace"
            correct_workspace=$((correct_workspace + 1))
        else
            echo "  ❌ Workspace: $workspace (should be /home/john/zforge_workspace)"
        fi
        
        # Check dracut_config
        if grep -q "dracut_config" "$spec"; then
            echo "  ✅ Has dracut_config module"
            has_dracut=$((has_dracut + 1))
        else
            echo "  ❌ Missing dracut_config module"
        fi
        
        echo ""
    fi
done

echo "=== Summary ==="
echo "Total specs checked: $total"
echo "Correct workspace path: $correct_workspace/$total"
echo "Has dracut_config: $has_dracut/$total"

if [ "$correct_workspace" -eq "$total" ] && [ "$has_dracut" -eq "$total" ]; then
    echo ""
    echo "✅ All build specifications are correctly configured!"
    echo ""
    echo "Ready to build with:"
    echo "  sudo python3 build.py --spec build_specs/build_spec_stable.yml"
else
    echo ""
    echo "⚠️  Some specifications need updates"
fi