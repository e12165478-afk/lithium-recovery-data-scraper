# Lithium Recovery Data Scraper

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> Automated GitHub scraper for lithium recovery, desalination, and brine treatment datasets.
> Aggregates research data from public repositories into a structured, machine-learning-ready CSV.

## 📊 What This Does

This tool:
- 🔍 Searches GitHub for 10+ keywords related to lithium recovery and desalination
- 📥 Downloads CSV, Excel, JSON files from relevant repositories
- 🔄 Normalizes column names and units (ppm, %, °C, bar, m³/hr, etc.)
- 📋 Creates a **master CSV** with 50+ standardized columns
- ✅ Includes data quality metadata (source repo, file type, provenance)

## 📋 Output Schema

The generated CSV includes:

### Feed Chemistry (Mandatory)
```
li_ppm, na_ppm, k_ppm, mg_ppm, ca_ppm, cl_ppm, so4_ppm, b_ppm, sr_ppm, ba_ppm, sio2_ppm,
tds_ppm, ph_raw, ph_adjusted, temperature_c, density_g_cm3, viscosity_cp, toc_ppm, oil_grease_ppm
```

### Process Conditions
```
inlet_flow_m3hr, operating_pressure_bar, residence_time_min, media_type, 
resin_age_days, elution_ratio, feed_temp_process_c
```

### Results (Ground Truth)
```
li_recovery_percent, mg_rejection_percent, ca_rejection_percent, 
na_rejection_percent, li_product_purity_percent, product_grade, mass_balance_error_percent
```

### Economic Data
```
energy_kWh_per_m3, chemical_cost_USD_per_m3
```

### Quality Assurance
```
replicate_number, rsd_percent, outlier_flagged, mass_balance_valid, 
qc_approved, qc_comments, analyst_id, lab_id, analysis_date
```

### Metadata
```
_source_repo, _source_file, _source_sheet, _source_type
```

## 🚀 Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/e12165478-afk/lithium-recovery-data-scraper.git
cd lithium-recovery-data-scraper

pip install -r requirements.txt
```

### 2. Configure GitHub Token (Optional but Recommended)

```bash
# Get token from: https://github.com/settings/tokens
# Scopes needed: public_repo (read-only)

export GITHUB_TOKEN='ghp_xxxxxxxxxxxxxxxxxxxxx'
```

**Why?** Without token: 60 requests/hour. With token: 5,000 requests/hour.

### 3. Run Scraper

```bash
python scraper.py
```

### 4. Output

```
✓ Data saved to: lithium_recovery_aggregated_data.csv
✓ Shape: 2,847 rows × 54 columns
```

## 📈 Data Statistics (Expected)

| Metric | Value |
|--------|-------|
| **Total Rows** | 2,000 - 10,000 (depends on available repos) |
| **Unique Repos** | 30 - 100 |
| **Li Coverage** | 70-85% |
| **Li Recovery Coverage** | 40-60% |
| **Temperature Coverage** | 60-75% |
| **Flow Rate Coverage** | 30-50% |

## 🔍 Search Keywords

The scraper searches for:

1. `lithium recovery brine`
2. `lithium extraction desalination`
3. `DLE adsorption`
4. `lithium from seawater`
5. `brine treatment`
6. `lithium carbonate`
7. `ion exchange resin`
8. `reverse osmosis brine`
9. `produced water lithium`
10. `geothermal brine`

## 📊 Example Output

```csv
sample_id,timestamp_utc,li_ppm,na_ppm,mg_ppm,temperature_c,inlet_flow_m3hr,operating_pressure_bar,li_recovery_percent,li_product_purity_percent,mass_balance_error_percent,_source_repo,_source_file
GH-001,2024-01-15T09:30:00Z,450,12000,8500,28.5,10.5,25,82.5,97.8,1.2,kesieme/lithium-extraction,data_table_1.csv
GH-002,2024-01-16T10:15:00Z,480,11500,8200,30.0,9.5,24,83.1,97.9,1.0,smith-lab/brine-recovery,supplementary_data.xlsx
```

## ⚙️ Customization

Edit `scraper.py` to modify:

```python
# Line 40-51: Add/remove keywords
self.search_keywords = [
    'your_keyword_1',
    'your_keyword_2',
    # ...
]

# Line 365: Change repo limit
scraper.scrape_all(repo_limit=100)  # Default: 50
```

## 🔗 Data Sources

The scraper aggregates data from:

- Academic papers (GitHub research repos)
- Industry projects (lithium extraction companies)
- Open datasets (Kaggle, Zenodo mirrors)
- Jupyter notebooks (computational studies)

## ⚠️ Limitations

1. **Data Quality**: Not all extracted data is peer-reviewed or validated
2. **Unit Inconsistencies**: Some repos may use non-standard units (will attempt normalization)
3. **Missing Values**: Coverage varies by column (see statistics above)
4. **Rate Limiting**: Without GitHub token, max ~600 requests (limits searchable repos)

## 📝 Citation

If you use this dataset in research:

```bibtex
@software{lithium_scraper_2024,
  title={Lithium Recovery Data Scraper},
  author={Your Name},
  url={https://github.com/e12165478-afk/lithium-recovery-data-scraper},
  year={2024}
}
```

## 📞 Support

- **Questions?** Open an Issue
- **Missing repos?** Submit a PR with additional keywords
- **Data quality issues?** Report with CSV row number

## 📜 License

MIT License - See LICENSE file

---

## 🗂️ Repository Structure

```
lithium-recovery-data-scraper/
├── scraper.py                              # Main scraper script
├── requirements.txt                        # Python dependencies
├── README.md                               # This file
├── LICENSE
├── data/
│   ├── lithium_recovery_aggregated_data.csv  # Output (generated)
│   ├── README.md                            # Data dictionary
│   └── examples/
│       └── sample_sources.yaml              # Example extracted repos
└── docs/
    ├── SCHEMA.md                           # Detailed column definitions
    └── DATA_QUALITY.md                     # Validation rules
```

---

**Ready to scrape?** Run: `python scraper.py`
