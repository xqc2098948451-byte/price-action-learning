# Repository Governance

1. Follow the minimum closed loop and YAGNI principles. Build only what the current approved work requires.
2. Do not create a new top-level directory without explicit architecture approval. The approved top-level entries are `AGENTS.md`, `README.md`, `.gitignore`, `docs/`, `spec/`, `src/`, and `tests/`. `src/` and `tests/` may remain absent until implementation begins.
3. The approved domain module names are `study_entry`, `learning_map`, `training`, `evaluation`, `learning_state`, and `review`.
4. When materialized, `spec/`, `src/price_action_learning/`, and `tests/` must use these exact domain module names.
5. Do not create generic dumping-ground directories or modules such as `utils`, `helpers`, `common`, `misc`, `managers`, `services`, `engine`, or `lib`.
6. Introduce a shared abstraction only after real reuse exists in at least two modules and explicit approval is given.
7. Code belongs to the domain module that owns its behavior. A Codex workstream must not modify another workstream's owned module without explicit authorization.
8. Do not create placeholder directories or files merely to reserve future structure. Create a directory when its first real approved file is added.
9. Do not relocate files for aesthetic refactoring alone.
10. S4-S8 remain out of scope.
11. The public repository must never contain private screenshots, real training history, private Learning State, credentials, tokens, private prompts, or personal user data.
12. Do not create parallel implementations, `*_v2`, `final2`, `temp`, experimental, or abandoned production files on `main`.
13. Prefer one concept → one owning module → one spec location → one implementation location → one test location.

The target layout and module ownership are defined in `docs/DIRECTORY_POLICY.md`.
