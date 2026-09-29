# Harvest Export

Read the authoritative project-local extension, normalize semantic identity and provenance, remove unnecessary project-private details, bind source project/revision/hash, and write only to `framework/.gpt-codex/harvest/inbox/<project_id>/`. If the framework root is unavailable, report/record Harvest pending rather than mutating another location or blocking otherwise-valid work.
