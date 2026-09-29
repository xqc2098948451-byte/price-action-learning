# Project

## Identity

- Project ID: `PRJ-PRICE-ACTION-LEARNING-1394745962`
- Name: Price Action Learning
- Repository: `xqc2098948451-byte/price-action-learning` (GitHub repository ID `1394745962`)

## Evidence-derived project profile

- Purpose: GPT-driven personal price-action learning, using TradingView screenshots and independent user analysis.
- Learning loop: screenshot -> user analysis -> constrained GPT evaluation -> learning-state update -> focused training when needed -> delayed review.
- Languages / runtimes: none selected; this repository currently contains governance and contract documentation only.
- Frameworks: GPT-Codex Framework v2.7.4 governs the project; no business runtime framework is selected.
- Repository shape: `docs/` contains project-native contracts and rules; `spec/` has five existing module directories with `.gitkeep` files. `src/`, `tests/`, and `spec/study_entry/` remain absent.
- Existing test/build/lint/typecheck mechanisms and CI/CD: none present at bootstrap.
- External systems: GitHub is the public source repository; TradingView supplies screenshots. No TradingView API, database, or trading integration is implemented.
- Privacy: private screenshots, training history, Learning State, prompts, tokens, and credentials stay outside the public repository.

## Architecture and constraints

- MVP is S1-S3. The approved domain modules are `study_entry`, `learning_map`, `training`, `evaluation`, `learning_state`, and `review`.
- Study Entry is the entry layer. Domain ownership and target paths are governed by `AGENTS.md` and `docs/DIRECTORY_POLICY.md`; absent directories are not created as placeholders.
- The user analyzes before GPT. Initial analysis is immutable after submission. Evaluation judges the reasoning process without hindsight prediction.
- The current Stage bounds knowledge. Only CORE and Stage-allowed knowledge may formally judge an error; low confidence or insufficient information permits abstention.
- The project follows a minimum closed loop and YAGNI. It does not build a complete local technical-analysis knowledge base, automatic trading, or S4-S8.
- `docs/CONTRACTS.md`, `docs/DOMAIN_CONSTITUTION.md`, and `docs/PROJECT_SCOPE.md` remain the project-native sources for their respective domain rules. The private learning plugin is not intended for public publication.

## Governance rationale

Framework governance is limited to project identity, selected Built-in snapshots, navigation, validation, and GitHub continuity. The existing project-native rules remain authoritative for product scope and domain behavior. No project-local extension is justified at bootstrap; the required Harvest capability remains dormant unless an extension is later approved.

## Source-of-truth rule

- This file explains what the project is.
- `CONTROL.json` defines which governance extensions are enabled.
- `STATE.json` defines where governed execution is now.
