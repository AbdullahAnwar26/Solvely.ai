#!/usr/bin/env bash
# Replays the next N queued commits from `push-queue` onto `main` and pushes.
#
# Each replayed commit is created NOW with the real current date (git commit
# --reset-author), so GitHub's contribution graph shows the day you actually run
# this script. No dates are faked. Run it from the dev checkout (branch push-queue);
# it works in a separate worktree so your uncommitted work is never touched.
#
# Usage:   bash scripts/push-day.sh <count>        e.g. bash scripts/push-day.sh 4
# Preview: DRY_RUN=1 bash scripts/push-day.sh 4    (replays locally, does not push)
set -euo pipefail

count="${1:-3}"
case "$count" in ''|*[!0-9]*) echo "count must be a positive number"; exit 2;; esac

repo="$(git rev-parse --show-toplevel)"
queue_branch="${QUEUE_BRANCH:-push-queue}"
wt="${PUSH_WORKTREE:-$repo/../$(basename "$repo")-pushwt}"

git -C "$repo" rev-parse --verify -q "$queue_branch" >/dev/null || { echo "branch $queue_branch not found"; exit 2; }
[ -n "$(git -C "$repo" config user.name)" ] && [ -n "$(git -C "$repo" config user.email)" ] || { echo "git user.name/user.email not set"; exit 2; }

git -C "$repo" fetch origin main -q
if [ ! -d "$wt" ]; then
  git -C "$repo" worktree add -q "$wt" main
fi
cd "$wt"
git checkout -q main
git merge --ff-only -q origin/main

# Queued = commits on the queue branch whose patch is not already on main.
mapfile -t todo < <(git cherry main "$queue_branch" | awk '/^\+/{print $2}')
if [ "${#todo[@]}" -eq 0 ]; then
  echo "Nothing queued: main already has everything on $queue_branch."
  exit 0
fi

n=$(( count < ${#todo[@]} ? count : ${#todo[@]} ))
echo "Replaying $n of ${#todo[@]} queued commit(s) onto main:"
for sha in "${todo[@]:0:$n}"; do
  if ! git cherry-pick --no-commit "$sha" >/dev/null 2>&1; then
    git cherry-pick --abort >/dev/null 2>&1 || git reset -q --hard HEAD
    echo "Conflict replaying $sha; stopped. main was left at the last good commit."
    exit 1
  fi
  git commit -q -C "$sha" --reset-author
  echo "  + $(git log -1 --format='%h %s')"
done

if [ "${DRY_RUN:-0}" = "1" ]; then
  echo "DRY_RUN=1: not pushing. main is now $n commit(s) ahead of origin/main."
else
  git push origin main
  echo "Pushed. Remaining queued: $(( ${#todo[@]} - n ))"
fi
