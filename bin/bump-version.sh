#!/usr/bin/env bash
# bump-version.sh — manually bump the VERSION file with semver validation.
#
# In normal release flow you do NOT need this — just `git tag v2.2.2 &&
# git push --tags` and the sync-version workflow will update VERSION
# automatically after the release is published.
#
# This script is for the rare cases where you want to bump VERSION on
# a feature branch, override the auto-sync, or set a pre-release version
# locally.
#
# Usage:
#   ./bin/bump-version.sh 2.2.2
#   ./bin/bump-version.sh 3.0.0-rc.1

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <version>" >&2
    echo "Example: $0 2.2.2" >&2
    exit 1
fi

NEW_VERSION="$1"

# Strip a leading 'v' if the user passed one (e.g. "v2.2.2")
NEW_VERSION="${NEW_VERSION#v}"

# Semver validation:
#   MAJOR.MINOR.PATCH, optionally followed by a -PRERELEASE suffix
#   (e.g. 2.2.2, 3.0.0-rc.1, 1.0.0-dev-abc1234)
SEMVER_REGEX='^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$'
if ! [[ "$NEW_VERSION" =~ $SEMVER_REGEX ]]; then
    echo "Error: '$NEW_VERSION' is not a valid semver version" >&2
    echo "Expected: MAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH-PRERELEASE" >&2
    echo "Examples: 2.2.2, 3.0.0-rc.1" >&2
    exit 1
fi

# Find the repo root by walking up from this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_FILE="$REPO_ROOT/VERSION"

if [[ ! -f "$VERSION_FILE" ]]; then
    echo "Error: VERSION file not found at $VERSION_FILE" >&2
    exit 1
fi

OLD_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"

if [[ "$OLD_VERSION" == "$NEW_VERSION" ]]; then
    echo "VERSION is already $NEW_VERSION — nothing to do"
    exit 0
fi

# Atomic write: write to temp file then rename
TMP_FILE="$(mktemp "${VERSION_FILE}.XXXXXX")"
echo "$NEW_VERSION" > "$TMP_FILE"
mv "$TMP_FILE" "$VERSION_FILE"

echo "Bumped VERSION: $OLD_VERSION → $NEW_VERSION"
echo
echo "Next steps:"
echo "  git add VERSION"
echo "  git commit -m \"chore: bump version to v$NEW_VERSION\""
echo "  git tag v$NEW_VERSION"
echo "  git push && git push --tags"
