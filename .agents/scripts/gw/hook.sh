#!/bin/sh
# Mechanism: questions
# Every core hook runs here, launched by a Git alias:
#
#     git -c "alias.gw-hook=!sh .agents/scripts/gw/hook.sh" gw-hook <host>
#
# Git is on the path of every shell the hosts were seen to use — Git Bash, Windows PowerShell,
# cmd — and runs an alias under its own sh from the repository's top level, so one command serves
# every host and platform, from whatever folder the host's shell stands in. The interpreter is the
# one the link step recorded in this clone's Git directory: a bare `python` may be the Windows
# Store stub, and `uv` is one machine's habit.

host="$1"
record=$(git rev-parse --git-path gw-interpreter 2>/dev/null)
python=""
if [ -n "$record" ] && [ -f "$record" ]; then
    python=$(head -n 1 "$record" | tr -d '\r')
fi
if [ -n "$python" ] && [ -f "$python" ]; then
    exec "$python" .agents/scripts/gw/questions.py --hook "$host"
fi

# No interpreter: say which step makes the record, in the form the host reads, and exit 0 — a
# failing prompt hook can hold back the person's message.
notice="This clone has no interpreter recorded for its hooks; run \`python .agents/scripts/gw/harness.py . --links\` once."
case "$host" in
    cursor) printf '{"additional_context": "%s"}\n' "$notice" ;;
    *) printf '%s\n' "$notice" ;;
esac
exit 0
