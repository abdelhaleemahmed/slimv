#!/usr/bin/env bash
# queue_watch.sh — milestone watcher for an autonomous slimv queue run.
#
# WHY THIS EXISTS: earlier sessions armed many `tail -f | grep` Monitor loops; over ~11 days
# 43 of them orphaned and piled up (171 MB RAM, 4.4 CPU-hours of spinning), contributing to
# system-RAM pressure that starved the QSV encoder ("Cannot allocate memory"). Lesson: use ONE
# clean watcher, stop it when the run ends, and don't let them accumulate.
#
# THIS IMPLEMENTATION spawns NO `grep` and NO `tail`: it reads the log with the bash built-in
# `mapfile` and matches lines with a `case` glob. A single instance sleeping between 60 s polls
# uses ~5 MB RAM and ~0 CPU. It only emits NEW milestone lines (skips the pre-existing tail on
# start), so each stdout line becomes exactly one notification.
#
# USAGE (via the Monitor tool, persistent):
#   bash /path/to/AV_kit/queue_watch.sh "<absolute path to master_queue.log>"
# The log path is session-specific (it lives under the session's scratchpad), so pass it in.
#
# To stop it: TaskStop the monitor (or end the session). Do NOT leave it running across runs.

LOG="${1:?usage: queue_watch.sh <path-to-master_queue.log>}"
PAT='ENCODE DONE|VERIFY DONE|QUEUE DONE|ABORT|STOPPED_DISK|no progress|SRC_MISSING'  # doc only; matching is below

# Prime: count existing lines so we report only what happens from now on.
mapfile -t L < "$LOG" 2>/dev/null || L=()
seen=${#L[@]}

while true; do
  sleep 60
  mapfile -t L < "$LOG" 2>/dev/null || continue
  n=${#L[@]}
  (( n > seen )) || continue
  for (( i=seen; i<n; i++ )); do
    line="${L[i]}"
    case "$line" in
      *"ENCODE DONE"*|*"VERIFY DONE"*|*"QUEUE DONE"*|*"ABORT"*|*"STOPPED_DISK"*|*"no progress"*|*"SRC_MISSING"*)
        echo "$line" ;;
    esac
  done
  seen=$n
done
