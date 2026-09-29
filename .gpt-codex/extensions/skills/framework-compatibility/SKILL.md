# Framework Compatibility

Read-only. Compare only framework changes relevant to the project. Run this scan before adopting or migrating a Framework Source Folder and return exactly one of `NO_ACTION`, `OPTIONAL_REUSE`, `RECOMMENDED_UPGRADE`, `REQUIRED_MIGRATION`, or `CONFLICT`. Never modify the project during evaluation and never equate evaluation with adoption.

Consumer workspaces use one fixed, unversioned auxiliary Framework Source Folder such as `gpt-codex-framework` or `framework-source`. A versioned path such as `gpt-codex-framework-v2.0.2-bootstrap` is a release artifact name, not a long-lived binding. Project is authoritative; Framework is advisory. Framework Kernel and Framework Built-ins are `READ ONLY` during ordinary project development. Adopted Built-ins are copied as versioned snapshots into the project, and Framework upgrades do not automatically modify the project. v2.1.0 compatibility also verifies the authoritative `project_context_id` and the required `cross-project-context-binding` entry in `CONTROL.extensions.guardrails[]`.

For a one-time migration from a versioned binding: remove the old versioned auxiliary folder, add the fixed folder, save the Codex project configuration, then use the fixed folder for future upgrades.

v2.2 GitHub continuity is additive under Schema generation 1. A project that
adopts it binds one `PROJECT_CONTEXT_ID` to one stable
`CONTROL.github.repository_id`; local remote names remain runtime facts, and
the read-only migration scan must resolve ambiguous remotes explicitly.
