# Local Protocol

This package runs a small local version of the Flowcept LLM tutorial campaign.

## Setup

```bash
conda env create -f environment.yml
conda activate flowcept-llm-local
```

Start or confirm MongoDB on `localhost:27017`. The configured DB is `flowcept_codex_dpl_test_7`, matching the existing Flowcept settings file.

## Step 1: Search Workflow only

```bash
scripts/run_step1.sh
scripts/verify_mongo.py --step step1
```

Expected provenance: one `SearchWorkflow` record plus Dask task records for `model_train`.

## Step 2: Data Prep plus Search Workflow

```bash
scripts/run_step2.sh
scripts/verify_mongo.py --step step2
```

Expected provenance: `DataPrepWorkflow`, `SearchWorkflow`, and Dask task records. Torch instrumentation stays off.

## Notes

The first run may download WikiText-2 through Hugging Face `datasets`. Later runs reuse cached/generated tensors under `data/llm_tutorial/input_data`.
