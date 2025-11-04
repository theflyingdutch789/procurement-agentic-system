# Change Log

## 2025-11-04

- Reorganized evaluation toolkit into a top-level `evaluation/` package and removed obsolete helper scripts.
- Split the GPT-5 MongoDB agent into modular components (schema, validator, executor, LangGraph wrapper).
- Converted the frontend to ES modules with a `main.js` bootstrapper and removed inline handlers.
- Cleaned interview/mobile audit assets and deleted unused test fixtures to keep the repo production ready.
- Added a Docker Compose `seed` profile so MongoDB retains data between restarts by default.
