#!/usr/bin/env bash
# Generate browsable Robot Framework keyword docs (libdoc HTML) into docs/.
# Output is gitignored; run this locally or in CI to (re)produce the docs.
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p docs

RESOURCES="common policy_api ssh_keywords traffic_keywords bbprobe_keywords failure_keywords"
TOTAL=$(( $(echo "$RESOURCES" | wc -w) + 1 ))
i=0

step() {
    i=$((i + 1))
    if [ -t 2 ]; then
        echo "[$i/$TOTAL] libdoc $1" >&2
    fi
}

step "nsxt_robot.NsxtApi"
uv run python -m robot.libdoc nsxt_robot.NsxtApi docs/NsxtApi.html

for r in $RESOURCES; do
    step "resources/$r.robot"
    uv run python -m robot.libdoc "src/nsxt_robot/resources/$r.robot" "docs/$r.html"
done

if [ -t 2 ]; then
    echo "Docs written to docs/*.html" >&2
fi
