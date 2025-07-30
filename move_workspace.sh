#!/bin/bash
# Move workspace to avoid noexec issue

echo "Moving Z-FORGE workspace to home directory..."
echo ""
echo "Run these commands:"
echo ""
echo "# 1. Move the workspace"
echo "sudo mv /tmp/zforge_workspace /home/john/"
echo ""
echo "# 2. Set environment variable"
echo "export ZFORGE_WORKSPACE=/home/john/zforge_workspace"
echo ""
echo "# 3. Run build"
echo "make build"
echo ""
echo "Or all in one line:"
echo "sudo mv /tmp/zforge_workspace /home/john/ && export ZFORGE_WORKSPACE=/home/john/zforge_workspace && make build"