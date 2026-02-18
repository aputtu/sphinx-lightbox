#!/bin/bash
# export-project.sh - Export complete project structure and contents
# Excludes artifacts, builds, virtual environments, binary files, and images.

# Generate timestamp for filename
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
OUTPUT_FILE="../sphinx-lightbox-export_${TIMESTAMP}.txt"

echo "🔄 Exporting project to: $OUTPUT_FILE"

# Define exclusion pattern for 'tree'
# Matches: .git, .tox, venv, build artifacts, cache, IDE folders, AND images
TREE_IGNORE='.git|.tox|venv*|.venv*|env*|dist|build|*.egg-info|_build|__pycache__|*.pyc|*.pdf|htmlcov|.coverage|.pytest_cache|.vscode|.idea|*.png|*.jpg|*.jpeg|*.gif|*.svg|*.ico'

{
    echo "# Sphinx Filter Tabs - Complete Project Export"
    echo "# Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "# Working Directory: $(pwd)"
    echo ""
    
    echo "================================================================================"
    echo "PROJECT STRUCTURE"
    echo "================================================================================"
    echo ""
    
    # -a: All files (hidden included)
    # -I: Ignore pattern
    tree -a -I "$TREE_IGNORE"
    
    echo ""
    echo ""
    echo "================================================================================"
    echo "FILE CONTENTS"
    echo "================================================================================"
    echo ""
    
    # Find files, pruning ignored directories to prevent traversal
    find . \
        \( \
            -name ".git" -o \
            -name ".tox" -o \
            -name "venv*" -o \
            -name ".venv*" -o \
            -name "env*" -o \
            -name "dist" -o \
            -name "build" -o \
            -name "*.egg-info" -o \
            -name "htmlcov" -o \
            -name ".pytest_cache" -o \
            -name "__pycache__" -o \
            -name "_build" -o \
            -name ".vscode" -o \
            -name ".idea" \
        \) -prune -o \
        -type f \
        -not -name '*.pyc' \
        -not -name '*.pyo' \
        -not -name '*.pdf' \
        -not -name '.DS_Store' \
        -not -name 'Thumbs.db' \
        -not -name '.coverage' \
        -not -name '*.png' \
        -not -name '*.jpg' \
        -not -name 'export*.sh' \
        -not -name '*.jpeg' \
        -not -name '*.gif' \
        -not -name '*.svg' \
        -not -name '*.ico' \
        -print0 | xargs -0 -I {} sh -c '
            echo "=== {} ==="
            # Double check for binary content just in case
            if file "{}" | grep -q "text\|empty"; then
                cat "{}"
            else
                echo "[Binary file - content not displayed]"
            fi
            echo ""
        '
    
    echo ""
    echo "================================================================================"
    echo "EXPORT COMPLETE"
    echo "================================================================================"

} > "$OUTPUT_FILE"

echo "✅ Export complete!"
echo "📁 File: $OUTPUT_FILE"
echo "📊 Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
