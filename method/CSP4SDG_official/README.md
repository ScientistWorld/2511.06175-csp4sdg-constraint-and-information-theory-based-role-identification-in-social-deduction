# CSP4SDG: Constraint and Information-Theory Based Role Identification in Social Deduction Games with LLM-Enhanced Inference

Kaijie Xu (McGill University), Fandi Meng (Queen Mary University of London),  
Clark Verbrugge (McGill University), Simon Lucas (Queen Mary University of London)  
AAAI Conference on Artificial Intelligence, 2026 

> **Note:** The datasets themselves are **not** included here due to space constraints — we rely on publicly available data.

## Environment & prerequisites

- Python 3.10+
- Set your OpenAI API key before running any script that calls the LLM:
  ```bash
  export OPENAI_API_KEY="sk-..."
  ```
  (On Windows PowerShell: `setx OPENAI_API_KEY "sk-..."`)
- All scripts are deterministic given the same inputs; AvalonLogs preprocessing
  uses a fixed RNG seed, so re-running produces identical constraints.
- Install Python dependencies (tested with Python 3.10–3.12):
  ```bash
  pip install -r requirements.txt
  ```

## Download the public datasets

This repository depends on the following public datasets, which must be downloaded manually:

- **Avalon‑NLU** (Stepputtis et al., 2023, *Findings of ACL: EMNLP 2023*)  
- **Mafia-UCB** (Ibraheem et al., 2022, *NAACL-HLT 2022*)  
- **AvalonLogs** (WhoaWhoa, 2022, <https://github.com/WhoaWhoa/avalonlogs>)

After downloading, arrange the files into a reproducible workspace (example):

```
CSP4SDG/
├── Avalon_NLU/
│   ├── dataset_raw/{Truth,Lie}/*.json
│   ├── dataset_processed/{Truth,Lie}/*_constraints.json
│   └── dataset_llm/{Truth,Lie}/*.json        # produced by avalon_batch_llm_exp.py
├── Mafia/
│   ├── mafia_dataset_raw/...
│   ├── mafia_dataset/{Truth,Lie}/*.json      # processed dialogue
│   ├── mafia_dataset_constraints/{Truth,Lie}/*_constraints.json
│   └── mafia_dataset_llm/{Truth,Lie}/*.json
├── Avalon_Logs/
│   ├── avalon_logs_raw/*.json
│   ├── avalon_logs_constraints/*_constraints.json
│   └── avalon_logs_llm/*.json
└── ...
```


## Pre‑processing Pipeline

### Avalon‑NLU Dialogue Corpus
```bash
python Avalon_NLU/batch_avalon_llm.py <raw_avalon_nlu_dir> <processed_avalon_nlu_dir>
```

### Avalon‑Logs Event Corpus
```bash
python Avalon_Logs/batch_convert_structured.py avalon_logs_raw avalon_logs_constraints
```

### Mafia-UCB Corpus
```bash
python Mafia/build_mafia_constraints.py <raw_mafia_dir> <constraints_out_dir> Mafia/prompt_head.txt
python Mafia/build_mafia_game_data.py <raw_mafia_dir> <game_data_out_dir>
```

## Running Experiments

### Avalon‑NLU

- CSP

```bash
python Avalon_NLU/avalon_batch_csp_exp.py <processed_avalon_nlu_dir> <csp_results_dir>
```
- LLM

```bash
python Avalon_NLU/avalon_batch_llm_exp.py <raw_avalon_nlu_dir> <processed_avalon_nlu_dir> <llm_results_dir>
```
- Metrics

```bash
python Avalon_NLU/compute_csp_metrics.py  <csp_results_dir>  <output_prefix>
python Avalon_NLU/compute_llm_metrics.py  <llm_results_dir>  <output_prefix>
```

### AvalonLogs

- CSP

```bash
python Avalon_Logs/batch_solve_structured.py <avalon_logs_constraints> <csp_results_dir>
```
- LLM

```bash
python Avalon_Logs/avalon_logs_llm_exp.py <raw_avalon_logs_dir> <avalon_logs_constraints> <llm_results_dir> [view]
```
- Metrics

```bash
python Avalon_Logs/compute_avalon_logs_metrics.py <llm_results_dir> <csp_results_dir> <output_prefix>
```

### Mafia-UCB

- CSP

```bash
python Mafia/mafia_batch_csp_exp.py <mafia_constraints_dir> <csp_results_dir>
```
- LLM

```bash
python Mafia/mafia_llm_exp.py <mafia_game_data_dir> <mafia_constraints_dir> <llm_results_dir>
```
- Metrics

```bash
python Mafia/compute_mafia_csp_metrics.py <csp_results_dir> <output_prefix>
python Mafia/compute_mafia_llm_metrics.py <llm_results_dir> <output_prefix>
```

For detailed usage and additional options, please refer to the inline comments at the top of each script. 

## Citation

If you find our work useful for your research, please consider citing the paper 
```
@misc{xu2025csp4sdgconstraintinformationtheorybased,
  title        = {CSP4SDG: Constraint and Information-Theory Based Role Identification in Social Deduction Games with LLM-Enhanced Inference},
  author       = {Kaijie Xu and Fandi Meng and Clark Verbrugge and Simon Lucas},
  year         = {2025},
  eprint       = {2511.06175},
  archivePrefix= {arXiv},
  primaryClass = {cs.AI},
  url          = {https://arxiv.org/abs/2511.06175}
}
```