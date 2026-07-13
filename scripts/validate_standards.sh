#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HTML_DIR="${1:-$PROJECT_ROOT/docs/_build/html}"
VALIDATOR_URL="${VNU_JAR_URL:-https://github.com/validator/validator/releases/download/latest/vnu.jar}"
VALIDATOR_SHA256="${VNU_JAR_SHA256:-cfebb530bd9f5a27691f468319113a85a76d03c8c51ea91fe278fea3a25d2966}"

if [ ! -d "$HTML_DIR" ]; then
    echo "Generated HTML directory not found: $HTML_DIR" >&2
    exit 1
fi

for command_name in curl java sha256sum; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required command not found: $command_name" >&2
        exit 1
    fi
done

validator_jar="$(mktemp "${TMPDIR:-/tmp}/sphinx-lightbox-vnu.XXXXXX.jar")"
cleanup() {
    rm -f "$validator_jar"
}
trap cleanup EXIT

curl --fail --location --silent --show-error "$VALIDATOR_URL" --output "$validator_jar"
checksum_output="$(sha256sum "$validator_jar")"
actual_sha256="${checksum_output%% *}"
if [ "$actual_sha256" != "$VALIDATOR_SHA256" ]; then
    echo "Nu validator checksum mismatch: expected $VALIDATOR_SHA256, got $actual_sha256" >&2
    exit 1
fi
java -jar "$validator_jar" --version

java -jar "$validator_jar" \
    --Werror \
    --skip-info-messages \
    --skip-non-html \
    "$HTML_DIR"

mapfile -d '' css_files < <(find "$HTML_DIR" -type f -name "*.css" -print0)
if [ "${#css_files[@]}" -eq 0 ]; then
    echo "No generated CSS files found in $HTML_DIR" >&2
    exit 1
fi
java -jar "$validator_jar" \
    --css \
    --Werror \
    --skip-info-messages \
    "${css_files[@]}"

mapfile -d '' svg_files < <(find "$HTML_DIR" -type f -name "*.svg" -print0)
if [ "${#svg_files[@]}" -gt 0 ]; then
    java -jar "$validator_jar" \
        --svg \
        --Werror \
        --skip-info-messages \
        "${svg_files[@]}"
fi

echo "Nu HTML, CSS, and SVG validation passed: $HTML_DIR"
