# The Local Impact of the Ube Export Boom

> Honors thesis: does international demand for ube (*Dioscorea alata*) translate into measurable economic and health benefits for the Filipino farming communities that grow it, or does the value bypass producers?

**Author:** Lois Tanglao ([loistanglao@berkeley.edu](mailto:loistanglao@berkeley.edu))

---

## About this project

Ube has surged in global popularity — a 250% increase in new ube-flavored products between 2018 and 2022 (McCormick's Flavor Insight Report) — appearing everywhere from Trader Joe's to Starbucks. In the Philippines, though, ube has long been a subsistence crop and a livelihood source for Indigenous and smallholder farmers. This thesis asks whether the export boom has produced tangible gains for those growing communities, using a difference-in-differences design that compares outcomes (anthropometric health, via BMI) in provinces with high agro-ecological suitability for ube against provinces with low suitability, before and after the period of rising export demand.

This repository contains the code used to clean, merge, and analyze the data behind the thesis. The written thesis itself is not included here.

## Repository structure

All code lives in `code/`. Scripts and notebooks reference sibling `data/` (`raw/` and `processed/`) and `output/` directories at the project root — some notebooks save figures there, others currently save directly into `code/` (noted below):

```
honors_thesis/
├── code/
│   ├── nns_pipeline.py         # CLI: clean + geocode one year's NNS survey data (production version of nns.ipynb)
│   ├── nns.ipynb                # Dev notebook: same NNS cleaning/geocoding workflow, plus multi-year NNS exploration
│   ├── suitability.R            # Extracts mean GAEZ yam-suitability per province, joins to NNS data, adds ube prices
│   ├── sanity_check.ipynb       # Cross-checks pipeline output for consistency across NNS survey years (2003–2021)
│   ├── ube_eda.ipynb            # EDA of PSA ube retail price and production time series
│   ├── ube_suit.ipynb           # Explores the yam_suitability distribution; BMI ~ suitability x price regression and heatmap
│   ├── summary_stats.ipynb      # Summary statistics for the suitability raster and the merged NNS dataset
│   ├── regression.R             # Difference-in-differences / fixed-effects regression models (feols), exports result tables
│   ├── heatmap.svg              # Output: retail price trend (saved here by ube_eda.ipynb)
│   ├── stats_table.png          # Output: suitability raster summary stats (saved here by summary_stats.ipynb)
│   └── ube_retail_production.png # Output: retail price vs. production plot
├── data/
│   ├── raw/                     # Source data (see Data section — largely not committed)
│   └── processed/               # Cleaned and merged datasets produced by the pipeline
├── output/                      # Additional generated figures and tables (suitmap_green.svg, model_table.png, etc.)
└── README.md
```

## Getting started

### Prerequisites

- **Python 3.10+** — pandas, numpy, matplotlib, seaborn, geopandas, rasterio, scikit-learn, statsmodels, dataframe_image
- **R 4.x** — terra, readr, sf, dplyr, data.table, fixest, modelsummary

```bash
pip install pandas numpy matplotlib seaborn geopandas rasterio scikit-learn statsmodels dataframe_image
```
```r
install.packages(c("terra", "readr", "sf", "dplyr", "data.table", "fixest", "modelsummary"))
```

### Running the pipeline

The scripts are meant to be run roughly in this order, each producing an input the next step depends on:

1. **Clean and geocode NNS survey data.** For the 2018/19/21 round:
   ```bash
   python code/nns_pipeline.py \
     --nns_file "data/raw/nns/nns_18_19_21/<...>_data-set_anthrop.csv" \
     --dict_file "data/raw/nns/nns_18_19_21/<...>_data-dictionary_anthrop.csv" \
     --shapefile "data/raw/ne_10m_admin_1_states_provinces/ne_10m_admin_1_states_provinces.shp" \
     --output "data/processed/pipeline_18_19_21.csv"
   ```
   This normalizes province/HUC names in the survey against a Natural Earth shapefile, attaches province geometry, and computes BMI. `nns.ipynb` is the exploratory version of this same step and additionally loads the older NNS rounds (2003–2015) used by `sanity_check.ipynb`.

2. **Attach yam suitability and price.** Run `suitability.R`, which extracts mean GAEZ yam-suitability per province from the raster, joins it to the cleaned NNS data, adds ube retail prices by survey year, and writes `data/processed/merged_18_19_21.csv` (and a province/HUC-averaged BMI variant).

3. **Sanity-check and explore.** `sanity_check.ipynb` confirms the pipeline output is consistent across survey years; `summary_stats.ipynb` and `ube_suit.ipynb` summarize the suitability and merged datasets and generate exploratory plots (distribution, heatmap, suitability map); `ube_eda.ipynb` explores PSA retail price and production trends independently.

4. **Run the regressions.** `regression.R` fits the fixed-effects and interaction models (`bmi ~ yam_suitability`, with `ube_price_1kg` and year fixed effects, clustered by `provhuc`) on `merged_18_19_21.csv` and exports result tables to `output/`.

## Data

| Source | Description | Included in repo? |
|---|---|---|
| National Nutrition Survey (NNS), rounds 2003–2021 | Individual/household-level anthropometric survey data (Philippine Statistics Authority / FNRI), including BMI-relevant height and weight | No — restricted-access microdata, obtained via data request |
| `ne_10m_admin_1_states_provinces` (Natural Earth) | Province/administrative-unit boundaries used to geocode survey responses and extract raster values | Not committed (downloadable from naturalearthdata.com) |
| GAEZ v5 yam suitability raster (`...HP0120.AGERA5.HIST.YAM.LRLM.tif`) | FAO/IIASA Global Agro-Ecological Zones agro-climatic suitability index for yam (*Dioscorea* spp.) | Not committed (downloadable from the GAEZ Data Portal) |
| PSA retail price and production data | Annual Philippine ube retail prices (2018–2025) and production in metric tons (2010–2025) | Not committed |

Because the NNS microdata is restricted, `data/raw/` is not tracked in this repository. `data/processed/` outputs (e.g. `merged_18_19_21.csv`) are the working datasets used downstream; regenerate them by running the pipeline above against your own copy of the raw data.

**Note:** in `suitability.R`, ube prices are currently hard-coded per survey year (2018, 2019, 2021) as a placeholder until province-level PSA price data is available.

## Methods (brief)

The analysis links each NNS respondent to their province's agro-ecological suitability for yam cultivation (GAEZ) and the national ube retail price in their survey year, then estimates whether BMI outcomes differ by suitability and price using OLS models with an interaction term, a suitability-only model with survey-year fixed effects, and a model with standard errors clustered by province/HUC (`provhuc`). This is a first step toward the thesis's full difference-in-differences design comparing high- and low-suitability provinces over time.

## Outputs

Generated figures and tables are written to `output/`, including:
- `heatmap.svg` / `heatmap.png` — predicted BMI by suitability and price quantile
- `suitmap_green.svg` — yam suitability raster with province boundaries overlaid
- `ube_retail_production.png` — retail price vs. production over time
- `stats_table.png`, `bmi_stats_table.png`, `suit_stats_table.png` — summary statistics tables
- `model_table.png` / `model_table.html` — regression results

## Contact

Lois Tanglao — [loistanglao@berkeley.edu](mailto:loistanglao@berkeley.edu)
