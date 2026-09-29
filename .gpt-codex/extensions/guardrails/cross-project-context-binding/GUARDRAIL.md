# Cross-project Context Binding

`cross-project-context-binding` is a required safety guardrail after a project adopts Framework v2.1.0.

The sole project-level selection source is `CONTROL.extensions.guardrails[]`. A valid v2.1.0 control must contain exactly one enabled Built-in entry with this id and version `1.0.0`. Missing, disabled, or malformed adoption denies executable work.

Every GPT instruction must bind to the target project's `PROJECT_CONTEXT_ID`, and every Codex return must bind back to the source project's same identity. Mismatch or stale state is quarantined or analysis-only and cannot execute business work.

Legacy governed bootstrap compares `BOOTSTRAP_TARGET_PROJECT_ID` with local `CONTROL.project_id` before mutation. A truly unbound project uses a two-step challenge: the first request is read-only and creates no files; the exact challenge-bound second request creates and verifies identity, then hard-stops before business work. Replay, stale, or wrong challenges are denied.
