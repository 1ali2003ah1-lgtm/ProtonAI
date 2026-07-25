# ProtonAI

Clinical AI Platform for Proton Therapy Accuracy

## Overview
ProtonAI is a production-grade AI platform designed to improve the accuracy and outcomes of proton therapy using real hospital data and state-of-the-art machine learning.

## Project Structure
```
protonai/
├── src/protonai/        # Core source code
│   ├── contracts.py      # Data contracts & validation rules
│   ├── validators.py     # Cross-field clinical validators
│   └── ingestion.py      # Data ingestion pipeline
├── tests/               # Automated tests
├── data/                # Data directory (not tracked by git)
└── reports/             # Generated reports
```

## Quick Start
```bash
pip install -r requirements.txt
pytest tests/           # Run tests
```

## Data Fields
- **Patient**: patient_id, age, sex
- **Tumor**: tumor_site, tumor_volume_ml, tumor_stage, histology
- **Dose**: dose_gy, fraction_count, dose_per_fraction
- **Imaging**: ct_timestamp, voxel_size_mm
- **Outcomes**: local_control, toxicity_grade, survival_months
- **Proton**: beam_energy_mev, rbe

## Author
Ali Hussein — Medical Devices Engineering, National University of Science and Technology
