# Directory Policy

This repository follows the minimum closed loop, YAGNI, domain ownership, and no placeholder structure principles. Only `AGENTS.md`, `README.md`, `.gitignore`, `docs/`, `spec/`, `src/`, and `tests/` are approved top-level entries. Any other top-level directory requires explicit architecture approval.

## Target structure

```text
price-action-learning/
├── AGENTS.md
├── README.md
├── .gitignore
├── docs/
├── spec/
│   ├── study_entry/
│   ├── learning_map/
│   ├── training/
│   ├── evaluation/
│   ├── learning_state/
│   └── review/
├── src/
│   └── price_action_learning/
│       ├── study_entry/
│       ├── learning_map/
│       ├── training/
│       ├── evaluation/
│       ├── learning_state/
│       └── review/
└── tests/
    ├── study_entry/
    ├── learning_map/
    ├── training/
    ├── evaluation/
    ├── learning_state/
    └── review/
```

**THIS IS A TARGET STRUCTURE, NOT A REQUIREMENT TO CREATE EMPTY DIRECTORIES.** Git does not track empty directories. Create each directory only when its first real approved file is added. `src/`, `tests/`, and `spec/study_entry/` remain absent until then. The five existing `spec/` module directories and their `.gitkeep` files remain in place; an existing `.gitkeep` may be removed when a real file enters that directory. Do not add new `.gitkeep` files or other placeholders.

When a module is materialized, use the exact same approved module name in `spec/`, `src/price_action_learning/`, and `tests/`. This is a naming rule, not a requirement to materialize all three locations at once.

## Module ownership

| Module | Owns |
| --- | --- |
| `study_entry` | Study Entry, StudyContext assembly, loading current study constraints |
| `learning_map` | Stages, skills, concepts, error mappings, knowledge boundaries, confidence rules, candidate concept proposals |
| `training` | TrainingAttempt lifecycle, initial analysis, user confidence, one revision, focused training mode |
| `evaluation` | GPT evaluation contract, diagnostic feedback, primary error, contributors, confidence, abstain |
| `learning_state` | Current stage, skill states, error states, current focus, due reviews |
| `review` | Review scheduling, hidden-answer review, review results |

One module must not absorb another module's responsibility. Code belongs to the module that owns the behavior. Introduce a shared abstraction only after real reuse in at least two modules and explicit approval.

## Forbidden directory behavior

- Creating a new top-level directory without approval or placeholder folders for hypothetical future needs.
- Using generic utility dumping grounds such as `utils`, `helpers`, `common`, `misc`, `managers`, `services`, `engine`, or `lib`.
- Duplicating domain models or scattering a module's logic across unrelated directories.
- Putting production business logic in test helpers.
- Committing generated output beside source code.
- Scattering feature documentation outside `docs/` or `spec/`.
- Creating a separate folder for each tiny class or function, or rearranging files solely for aesthetic symmetry.
- Keeping parallel implementations, version suffix files, or abandoned experimental files on `main`.

Prefer one concept → one owning module → one spec location → one implementation location → one test location. A Codex workstream must not modify another workstream's owned module without explicit authorization. S4-S8 remain out of scope, and private training data must never enter the public repository.
