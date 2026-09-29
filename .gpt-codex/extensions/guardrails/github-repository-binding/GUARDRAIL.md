# GitHub Repository Binding

For a project adopting GitHub continuity, `CONTROL.github.repository_id` is
the stable repository identity. `repository_full_name` is diagnostic metadata
and `default_branch` is a remote hint. `remote_name` is local runtime
observation or an instruction hint only and is never durable project identity.

Codex enumerates local remotes and selects a uniquely matching repository ID.
It fails closed on missing, foreign, ambiguous, stale, or conflicting
identity. It must not mutate remotes, force-push, rewrite history, or update
state before project context and repository identity both match.
