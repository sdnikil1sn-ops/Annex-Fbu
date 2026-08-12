#!/usr/bin/env bash
# =====================================================================
# ANNEX — release script (Phase 11)
#
# Cuts a release from the current branch:
#   1. Validates the semver argument.
#   2. Verifies the working tree is clean and the tag does not exist.
#   3. Moves the CHANGELOG.md [Unreleased] section into a dated
#      [<version>] section and prepends a fresh [Unreleased].
#   4. Commits the changelog bump and creates the annotated tag
#      v<version> pointing at that commit.
#
# Usage:
#   scripts/release.sh 0.2.0            # bump + commit + tag v0.2.0
#   scripts/release.sh 0.2.0 --dry-run  # preview only, changes nothing
#   scripts/release.sh 0.2.0 --no-tag   # changelog bump only (no commit/tag)
#
# Pushing (git push origin main && git push origin v0.2.0) is left to
# the developer; the tag push triggers .github/workflows/release.yml.
# =====================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

VERSION=""
DRY_RUN=0
DO_TAG=1

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --no-tag)  DO_TAG=0 ;;
    -h|--help)
      sed -n 's/^# \{0,1\}//p' "$0" | sed -n '2,/^$/p'
      exit 0
      ;;
    *)
      if [[ -n "$VERSION" ]]; then
        echo "error: unexpected argument '$arg'" >&2
        exit 2
      fi
      VERSION="$arg"
      ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "error: version required (e.g. scripts/release.sh 0.2.0)" >&2
  exit 2
fi

# Strict semver: major.minor.patch with optional pre-release/build metadata.
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$ ]]; then
  echo "error: invalid version '$VERSION' (expected semver, e.g. 0.2.0)" >&2
  exit 2
fi

TAG="v${VERSION}"
TODAY="$(date +%Y-%m-%d)"
CHANGELOG="CHANGELOG.md"

# A release must point at a reproducible tree and a unique tag.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "error: working tree is not clean; commit or stash first" >&2
  exit 1
fi
if git rev-parse --verify --quiet "$TAG" >/dev/null; then
  echo "error: tag '$TAG' already exists" >&2
  exit 1
fi
if [[ ! -f "$CHANGELOG" ]] || ! grep -q '^## \[Unreleased\]' "$CHANGELOG"; then
  echo "error: $CHANGELOG missing a [Unreleased] section" >&2
  exit 1
fi

echo "ANNEX release $VERSION ($TODAY)"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] would rewrite $CHANGELOG: [Unreleased] -> [$VERSION] - $TODAY (+ new [Unreleased])"
  if [[ "$DO_TAG" -eq 1 ]]; then
    echo "[dry-run] would commit the bump and create annotated tag $TAG"
  fi
  exit 0
fi

# Move [Unreleased] -> [<version>] - <date> and prepend a fresh section.
awk -v version="$VERSION" -v date="$TODAY" '
  /^## \[Unreleased\]/ && !done {
    print "## [Unreleased]"
    print ""
    print "## [" version "] - " date
    done = 1
    next
  }
  { print }
  END { if (!done) exit 1 }
' "$CHANGELOG" > "$CHANGELOG.tmp" && mv "$CHANGELOG.tmp" "$CHANGELOG"

echo "[ok] $CHANGELOG updated"

if [[ "$DO_TAG" -eq 1 ]]; then
  git add "$CHANGELOG"
  git commit -m "chore(repo): release $TAG"
  git tag -a "$TAG" -m "ANNEX release $TAG"
  echo "[ok] committed bump and created tag $TAG"
fi

cat <<'NEXT'

Next steps (the release pipeline runs on the tag push):
  git push origin main
  git push origin v<VERSION>
NEXT
