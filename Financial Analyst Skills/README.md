# Financial Analyst Skills

This repository contains a multi-analyst stock research workflow and the analyst specification files it depends on.

## Current Layout

- `api_workflow/`: reusable Python workflow package
- `workflow_specs/`: runtime analyst specifications and global workflow documents
- `outputs/`: generated JSON / markdown reports
- project-level config files such as `.env.example`, `requirements.txt`, and `.gitignore`

## Recommended Packaging Boundary

If you want to embed this workflow into another backend project, the main reusable unit is:

- `api_workflow/`

It also depends on:

- `workflow_specs/analysts/`
- `workflow_specs/global/`

## Safe to Exclude from Integration

These are not required at runtime:

- historical files under `outputs/`
- `__pycache__/`
- local-only debug artifacts

`GPT_Builder_Package/` and `分析师形象库/` are not required for runtime execution of `api_workflow`, but you may keep them if you still use them as authoring or reference material.

## First Place to Read

See [api_workflow/README.md](api_workflow/README.md) for:

- stable Python entry points
- CLI usage
- inputs and outputs
- environment variables
- integration guidance
- smoke-test commands
