# MacAma

A semi-automated toolkit for systematic reviews and meta-analysis, covering the full workflow from literature retrieval and screening to statistical analysis, figure generation, and AI-assisted manuscript writing.

## Workflow Overview

The standard workflow in this project is:

1. **Retrieval**: Batch retrieval of candidate studies based on search queries.
2. **Initial Screening**: Inclusion/exclusion decisions based on title/abstract.
3. **Secondary Screening**: Full-text based second-round screening and structured extraction.
4. **Meta Analysis (MetaflowAnalyser)**: Compute SMD for continuous outcomes and generate statistics/figures.
5. **Manuscript Generation (MetaWriter)**: Generate and iteratively refine manuscript drafts with structured inputs and a knowledge base.

The `workflow/` directory provides 3 workflow resource packs:

- `workflow/retrieval.zip`
- `workflow/initial_screening.zip`
- `workflow/secondary_screening.zip`

These can be used as templates or example resources for retrieval/screening workflows.

## Core Modules

### 1) literature_screening.py

Main script for literature retrieval and screening. Core capabilities include:

- Batch retrieval of literature records based on query criteria (e.g., PubMed URL/PMID).
- Calling LLM workflows for initial screening, secondary screening, information extraction, and statistical assistance.
- Batch processing with multi-format outputs (`xlsx` + `json` + `md`).

Major configurable items in the script include:

- API settings: `API_KEY`, multiple `APP_ID_*`.
- Path settings: `screening_result_dir`, `pmids_dir`, `articles_dir`, etc.
- Output files: e.g., `included.xlsx`, `included_data.xlsx`, and step-wise result directories.

Run with:

```bash
python literature_screening.py
```

Note: This script depends on locally available workflow app IDs and API keys. You should update retrieval parameters and output paths for your own topic before running.

### 2) MetaflowAnalyser/

A Streamlit-based visual app for meta-analysis.

Key features:

- Load and validate Excel input data.
- Compute effect sizes (SMD) and confidence intervals for continuous variables.
- Support fixed-effect and random-effects models.
- Generate forest plots, funnel plots, and subgroup analysis plots.
- Export figures and results as ZIP packages.
- Optional AI text interpretation (requires `DASHSCOPE_API_KEY`).

Launch with:

```bash
cd MetaflowAnalyser
streamlit run app.py
```

Recommended input columns:

- `Article_ID`
- `CTRL_Sample`, `CTRL`, `Ctrl_Error_Bar_Max`
- `IR_Sample`, `IR`, `IR_Error_Bar_Max`
- Subgroup variables such as `Strain`, `Gender`, `Age`, `Cancer`, `Dosage`

### 3) MetaWriter/

AI-assisted academic writing module for generating meta-analysis manuscript drafts.

Main mechanism:

- Read section-wise writing inputs from `user_manuscript_input.json`.
- Perform BM25 + HyDE retrieval from a local knowledge base (`knowledge_base.json`).
- Run section-level loops of "generate -> expert review -> judgment -> revision".
- Output final manuscript files (e.g., `final_manuscript_qwenmax.md`) by default.

Core files:

- `MetaWriter/workflow.py`: main pipeline script.
- `MetaWriter/prompts.py`: prompt templates by section.
- `MetaWriter/user_manuscript_input.json`: sample user input.
- `MetaWriter/academic_workflow.ipynb`: notebook-based workflow.

Required before running:

- Environment variable `DASHSCOPE_API_KEY`

## Case Study

`case_study/` provides a complete case package for "radiotherapy and anti-tumor immunity," split by workflow stage:

- `01_input_queries/`: retrieval input examples.
- `02_retrieval_records/`: retrieval outputs and input records.
- `03_initial_screening/`: initial screening output examples.
- `04_full_text_screening/`: full-text secondary screening inputs/outputs and batch results.
- `05_meta_analysis_data/`: MetaFlow analysis inputs and output archives for different indicators.
- `06_manuscript_generation/`: AI-generated drafts and human-revised manuscripts.
- `07_benchmark_evaluation/`: benchmark datasets for screening tasks (initial + secondary screening).


## Environment Setup

We recommend using an isolated virtual environment:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Quick Start

1. Configure your API key and workflow app IDs.
2. Run `literature_screening.py` for retrieval and screening.
3. Import structured data into `MetaflowAnalyser` for analysis and plotting.
4. Use `MetaWriter` to generate manuscript drafts and revise manually.
5. Refer to `case_study/` to check input/output formats at each stage.

## License

This project is licensed under the [MIT License](LICENSE).

## Disclaimer

AI outputs from this project are for research assistance only and do not constitute medical or academic conclusions. All results must be manually verified by researchers.
