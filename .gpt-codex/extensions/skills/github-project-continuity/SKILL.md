# GitHub Project Continuity

This optional Skill is enabled through a project’s versioned
`CONTROL.extensions.skills[]` snapshot. It reads canonical CONTROL/STATE,
validates both project context and repository ID, and labels resume facts as
`LATEST_SYNCED_REMOTE_STATE` or `LOCAL_UNSYNCED_STATE`.

Before a new mutating Work Unit, `NEW_WORK_PREFLIGHT` must be
`CLEAN_SYNCED`. A currently authorized Work Unit that already passed that
gate may continue local editing, tests, and explicitly allowed local commits
after temporary remote loss, but returns `LOCAL_COMPLETE` with
`SYNC_PENDING`, cannot start another Work Unit, and cannot return `PASS`.

Formal publication is bounded: WORK COMMIT W, PUBLICATION COMMIT P, then live
`TOOL_OBSERVED` verification that the selected remote ref head equals P. P
references W and the durable Result but never contains its own SHA. Push exit
status alone is insufficient. A failed or unavailable remote leaves a pending
or reconciliation result and never mutates remotes destructively.
