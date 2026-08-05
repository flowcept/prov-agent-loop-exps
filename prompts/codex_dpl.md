# Local Machine Learning Workflow Prompt

You are helping run the local smoke version of the paper's machine-learning use case.

The goal is to prepare and execute Flowcept's LLM tutorial workflow locally, including a small hyperparameter search, only through the first two tutorial stages:

- Step 1: run the search workflow only.
- Step 2: run data preparation plus the search workflow.

Use the experiment repository as the control directory and the Flowcept LLM tutorial as the application code. Read the local configuration before acting, especially `project.yaml`, `configs/profiles/local_smoke.yaml`, and any existing scripts or README instructions.

Before executing, create a concise implementation plan that makes the steps explicit. The plan should identify:

- what repository files or scripts need to be inspected or created;
- how the local Python environment will be used;
- which tutorial commands or scripts will run Step 1 and Step 2;
- which hyperparameters will be searched and which bounds from `project.yaml` will be respected;
- how success or failure will be verified;
- where logs, outputs, and manifests should be preserved.

Respect these local-smoke constraints:

- keep the hyperparameter search small;
- use the configured random seed and search bounds;
- do not run beyond Step 2;
- do not add multi-node or GPU-specific execution;
- do not add per-epoch, parent-forward, or child-layer instrumentation;
- do not change the scientific objective unless a blocker requires it.

Execute the plan carefully. Prefer reusing existing tutorial code and experiment harness scripts over creating duplicate machinery. If something is missing, add the smallest reusable script or configuration needed for this local smoke run.

Stop after Step 2 succeeds, or after writing a clear failure note that includes the command that failed, the error, and the next recommended fix.
