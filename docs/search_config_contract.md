# Search Config Contract

Each run must have a per-run search configuration at `$PAL_SEARCH_CONFIG`.

The human creates the run manifest and `run.env`. The code assistant creates this search config before running the machine-learning workflow. Existing config files may be used as examples, but the assistant must choose the run's search space and criteria.

Required top-level keys:

- `objective`: short text describing the run goal.
- `constraints`: resource, time, token, and quality constraints.
- `search_space_rationale`: why these bounds are appropriate for this run.
- `generated_run_artifacts`: files, scripts, configs, and commands generated inside the run directory.
- `evaluation_plan`: how the run will check success/failure.
- `artifacts`: output paths that should be preserved.

For machine-learning campaigns, record model sizes, learning rates, batch sizes,
data slices, seeds, stopping criteria, validation thresholds, and the exact
commands or generated scripts used to run each trial. List-valued hyperparameters
represent the search grid. Scalar values represent fixed parameters.
