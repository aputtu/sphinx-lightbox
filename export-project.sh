#!/bin/bash
# export-project.sh - Export complete project structure and contents
# Excludes artifacts, builds, virtual environments, binary files, and images.

# Generate timestamp for filename
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
OUTPUT_FILE="../sphinx-lightbox-export_${TIMESTAMP}.txt"

echo "🔄 Exporting project to: $OUTPUT_FILE"

{
    echo "# Sphinx Filter Tabs - Complete Project Export"
    echo "# Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "# Working Directory: $(pwd)"
    echo ""
    
    echo "================================================================================"
    echo "PROJECT STRUCTURE"
    echo "================================================================================"
    echo ""
    
    # Using multiple -I flags guarantees exclusion across all versions of 'tree'
    tree -a \
        -I ".git" -I ".tox" -I "venv*" -I ".venv*" -I "env*" \
        -I "dist" -I "build" -I "_build" -I "*.egg-info" \
        -I "htmlcov" -I "__pycache__" -I ".pytest_cache" \
        -I ".mypy_cache" -I ".ruff_cache" -I ".vscode" -I ".idea" \
        -I "*.pyc" -I "*.pyo" -I "*.pdf" -I "*.png" -I "*.jpg" \
        -I "*.jpeg" -I "*.gif" -I "*.svg" -I "*.ico"
    
    echo ""
    echo ""
    echo "================================================================================"
    echo "FILE CONTENTS"
    echo "================================================================================"
    echo ""
    
    # Explicit -type d ensures we prune whole directories safely
    find . \
        -type d \( \
            -name ".git" -o \
            -name ".tox" -o \
            -name "venv*" -o \
            -name ".venv*" -o \
            -name "env*" -o \
            -name "dist" -o \
            -name "build" -o \
            -name "_build" -o \
            -name "*.egg-info" -o \
            -name "htmlcov" -o \
            -name "__pycache__" -o \
            -name ".pytest_cache" -o \
            -name ".mypy_cache" -o \
            -name ".ruff_cache" -o \
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
        -not -name 'coverage.xml' \
        -not -name '*.png' \
        -not -name '*.jpg' \
        -not -name '*.jpeg' \
        -not -name '*.gif' \
        -not -name '*.svg' \
        -not -name '*.ico' \
        -not -name 'export*.sh' \
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
