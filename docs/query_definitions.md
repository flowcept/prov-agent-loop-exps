# Query Definitions

## Q1. Reproduce selected trained model end to end

Evidence: objective, plan, code/data inputs, hyperparameters, checkpoints or model artifacts, metrics, Dask/Slurm evidence when available.

## Q2. Explain plan evolution and execution divergence

Evidence: execution plan, plan versions, plan-step executions, loop iterations, observations, decisions.

## Q3. Verify constraints and stop/continue decisions

Evidence: mandates, evaluation criteria, evaluation results, decisions, token usage, resource usage.

## Q4. Diagnose failed or degraded training trial

Evidence: tool invocations, generated data, observations, beliefs, Dask failures, telemetry.

## Q5. Find effort-quality Pareto frontier

Evidence: model metrics, hyperparameters, runtime, resource use, assistant token cost.

## Q6. Locate resource bottlenecks and assess optimization

Evidence: plan-step executions, telemetry, Dask tasks, runtime, ML quality.

## Q7. Audit human authorization, delegation, attribution

Evidence: human and AI agents, mandates, approvals, attribution/delegation fields, external actions.

## Q8. Measure reuse of provenance-backed knowledge across sessions

Evidence: observations, beliefs, memories, lessons learned, plans, decisions, outcomes.

Baseline is expected to miss agent-loop evidence. OPL is expected to answer structural questions partially. DPL is expected to provide the richest evidence when the assistant emitted the required annotations.
