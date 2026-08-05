# HPC Scaling Notes

For a larger campaign, keep the same package layout and change only `project.yaml` plus cluster launch mechanics.

Recommended scaling path:

- Move `data/llm_tutorial` to shared project storage visible to all workers.
- Use a unique `campaign_id` per submitted job or allocation.
- Increase `subset_size`, then expand `max_runs`, then add larger `emsize`, `nhid`, `nlayers`, and more epochs.
- Replace the local Dask cluster with an HPC scheduler-backed Dask cluster and pass the scheduler/client details through a small wrapper script.
- Point Flowcept settings to a reachable MongoDB service, preferably with a DB name per campaign family.
- Keep Step 1/2 validation queries unchanged so local and HPC results are comparable.

Do not enable per-epoch loops, parent forwards, child forwards, or telemetry until Step 2 provenance is stable at the target scale.
