# EA-MiniGrid-Bench

**A High-Resolution Spatial Benchmark Dataset for Machine Learning in East African Energy Planning**

EA-MiniGrid-Bench is an open, ML-ready tabular benchmark dataset for solar
mini-grid viability assessment across the "Core 4" East African nations —
**Rwanda, Kenya, Uganda, and Tanzania**. It packages the three core spatial
features of mini-grid viability (solar irradiance, population, and road
proximity) into a single clean CSV at 2–3 km resolution, enriched with country
and two levels of administrative labels plus per-cell coordinates, so that
classification, regression, and clustering workflows can be applied without any
GIS engineering.

- **175,253** validated grid-cell records
- **4 countries**, labelled to admin-1 (region/county) and admin-2 (district)
- Derived from fully open data sources via a reproducible Python pipeline
- Released with the complete processing and experiment code

> If you use this dataset, please cite the accompanying paper (see
> [Citation](#citation)).

---

## Table of contents

1. [Dataset](#dataset)
2. [Repository structure](#repository-structure)
3. [Quick start](#quick-start)
4. [Reproducing the dataset from raw sources](#reproducing-the-dataset-from-raw-sources)
5. [Data sources](#data-sources)
6. [Running the experiments](#running-the-experiments)
7. [Schema](#schema)
8. [Benchmark tasks](#benchmark-tasks)
9. [Limitations](#limitations)
10. [Citation](#citation)
11. [License](#license)

---

## Dataset

The ready-to-use dataset is `data/EA_MiniGrid_Bench_MASTER_FINAL.csv`. To start
working with it immediately:

```python
import pandas as pd
df = pd.read_csv("data/EA_MiniGrid_Bench_MASTER_FINAL.csv")
print(df.shape)        # (175253, 9)
print(df.head())
```

No GIS libraries, rasters, or shapefiles are required to use the dataset — it is
a plain CSV. The raw geospatial sources are only needed if you wish to rebuild
the dataset from scratch (see
[Reproducing the dataset](#reproducing-the-dataset-from-raw-sources)).

---

## Repository structure

```
ea-minigrid-bench/
├── README.md
├── requirements.txt
├── data/
│   ├── EA_MiniGrid_Bench_MASTER_FINAL.csv     # the benchmark dataset
│   └── EA_MiniGrid_Bench_CLUSTERED.csv        # dataset + Viability Tier labels
├── src/
│   ├── ea_minigrid_core.py                    # shared processing engine (Stages 1–5)
│   ├── run_rwanda.py                          # per-country runners
│   ├── run_kenya.py
│   ├── run_uganda.py
│   ├── run_tanzania.py
│   ├── merge_master.py                        # concatenates the 4 country CSVs
│   └── ea_minigrid_phase2.py                  # clustering + supervised baselines + figures
├── results/
│   ├── fig1_elbow_silhouette.png
│   ├── fig_tier_map.png
│   ├── fig_tier_map_by_country.png
│   ├── table_tier_profiles.csv
│   ├── table_by_country.csv
│   ├── table_tier_composition.csv
│   ├── table_regression_results.csv
│   └── table_classification_results.csv
└── config.py                                  # paths (edit before running)
```

> **Note on raw data:** the raw rasters and shapefiles (several GB) are **not**
> included in this repository. They are freely available from their original
> providers; see [Data sources](#data-sources) for download links and the
> expected folder layout.

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/<your-org>/ea-minigrid-bench.git
cd ea-minigrid-bench

# 2. Create an environment and install dependencies
python -m venv .venv && source .venv/bin/activate      # optional
pip install -r requirements.txt

# 3. Use the dataset directly
python -c "import pandas as pd; print(pd.read_csv('data/EA_MiniGrid_Bench_MASTER_FINAL.csv').describe())"
```

To reproduce the figures and baseline results from the released dataset:

```bash
python src/ea_minigrid_phase2.py
```

---

## Reproducing the dataset from raw sources

The full pipeline runs **modularly per country** on commodity hardware (a single
standard-tier CPU instance is sufficient — no high-RAM machine required) and
takes roughly minutes per country, with Tanzania the slowest owing to its
1.8 GB road network.

### Expected folder layout

After downloading the raw sources (next section), arrange them like this. The
GHI raster is a single global file shared by all four countries; everything else
is per country.

```
EA_MiniGrid_Project/
├── GHI.tif                              # global GHI raster (clipped per country)
├── Raw_Data_Rwanda/
│   ├── rwa_pop_2025_*.tif               # WorldPop 2025
│   ├── rwanda-*-free.shp.zip            # Geofabrik OSM extract
│   ├── admin0.shp (+ .shx .dbf .prj)    # national boundary
│   ├── admin1.shp (+ sidecars)          # regions/provinces
│   └── admin2.shp (+ sidecars)          # districts
├── Raw_Data_Kenya/      …  (ken_pop_2025_*.tif, kenya-*-free.shp.zip, admin0–2)
├── Raw_Data_Uganda/     …  (uga_pop_2025_*.tif, uganda-*-free.shp.zip, admin0–2)
└── Raw_Data_Tanzania/   …  (tza_pop_2025_*.tif, tanzania-*-free.shp.zip, admin0–2)
```

> **Important:** each shapefile is a set of files (`.shp`, `.shx`, `.dbf`,
> `.prj`). The `.dbf` holds the region/district names — without it the admin
> labels fall back to numeric IDs. Make sure all sidecar files are present.

### Run order

```bash
# Set the project root in config.py first (see below), then:
python src/run_rwanda.py        # → EA_MiniGrid_Rwanda_Processed.csv
python src/run_kenya.py         # → EA_MiniGrid_Kenya_Processed.csv
python src/run_uganda.py        # → EA_MiniGrid_Uganda_Processed.csv
python src/run_tanzania.py      # → EA_MiniGrid_Tanzania_Processed.csv
python src/merge_master.py      # → EA_MiniGrid_Bench_MASTER_FINAL.csv
```

Each country script prints per-stage row counts and a `describe()` summary, and
asserts the output schema before writing. The merge script verifies `Grid_ID`
uniqueness across all four files.

### Configuring paths

The scripts read the project root from `config.py`:

```python
# config.py
PROJECT_ROOT = "/path/to/EA_MiniGrid_Project/"   # edit this
```

Per-country settings (grid cell size and UTM zone) are defined in each runner
and documented inline.

### Pipeline overview

| Stage | What it does |
|-------|--------------|
| 1 | Generate a regular grid over the country's admin-0 bounding box; clip to the national boundary. Cell sizes: 2.0 km (RW), 2.5 km (UG), 3.0 km (KE, TZ). |
| 2 | Zonal statistics — mean GHI and summed population per cell (both aggregated *up* to the cell). |
| 3 | Dynamic NoData filtering: drop null cells, population ≤ 0, and solar ≤ 0.5. |
| 4 | Reproject to UTM; compute Euclidean distance to nearest OSM road; label each cell with admin-1/admin-2 (border-gap cells snapped to nearest unit); store centroid lon/lat. |
| 5 | Per-country export with schema assertion; concatenate to master. |

---

## Data sources

All sources are open and were refreshed to their most recent available vintage
at the time of processing. **Download these from the original providers** — they
are not redistributed here.

| Feature | Source | Resolution / vintage | Link |
|---------|--------|----------------------|------|
| Solar irradiance (GHI) | World Bank Global Solar Atlas / Solargis | ~1 km, multi-year climatology | https://globalsolaratlas.info |
| Population | WorldPop 2025 (Constrained, 100 m) | 100 m, 2025 | https://www.worldpop.org |
| Roads | OpenStreetMap via Geofabrik | current | https://download.geofabrik.de/africa.html |
| Admin boundaries (0–2) | Who's On First / UN OCHA (HDX) | 2025 | https://hdx.org · https://whosonfirst.org |

Administrative boundary shapefiles were inspected and validated in QGIS prior to
processing to confirm boundary accuracy and geometric integrity across all
administrative levels.

---

## Running the experiments

`src/ea_minigrid_phase2.py` reproduces the paper's analysis end to end from the
master CSV:

- **K-Means clustering** (k-scan for k = 2…9, final k = 4) → four Viability Tiers
- **Per-country and per-admin-1 breakdown tables**
- **Supervised baselines** — RandomForest and XGBoost for (a) log-population
  regression and (b) tier classification
- **Figures** — elbow/silhouette curves, regional tier map, per-country tier maps

```bash
python src/ea_minigrid_phase2.py
```

Outputs are written to `results/`. All models use `random_state=42` for
reproducibility.

---

## Schema

| Column | Type | Description |
|--------|------|-------------|
| `Grid_ID` | string | Unique cell ID with country prefix (e.g. `RW_000123`) |
| `Country` | string | Country name |
| `Admin1_Name` | string | Region / province / county |
| `Admin2_Name` | string | District |
| `Centroid_Lon` | float | Cell centroid longitude (WGS84) |
| `Centroid_Lat` | float | Cell centroid latitude (WGS84) |
| `Solar_Irradiance_kWh` | float | Mean GHI (kWh/m²/day), filtered > 0.5 |
| `Population_Count` | float | Sum of WorldPop 100 m pixels, filtered > 0 |
| `Dist_to_Road_m` | float | Euclidean distance to nearest OSM road (m) |

**Summary statistics (N = 175,253):** solar mean 5.68 kWh/m²/day (range
3.38–6.71); population mean 1,093, median 190 (right-skewed); road distance mean
2,282 m (up to ~51 km).

---

## Benchmark tasks

The dataset supports several ML tasks out of the box:

- **Clustering / segmentation** — group cells into viability tiers (the paper's
  proof-of-concept).
- **Regression** — predict `Population_Count` (or log-population) from solar and
  accessibility features. Baseline: XGBoost R² ≈ 0.50.
- **Classification** — predict the Viability Tier (or a binary "mini-grid viable"
  label). Note this is a *distillation* benchmark: tiers are derived from the
  same features, so high scores reflect re-learning the cluster geometry.
- **Cross-border / sub-national clustering** — using the country and admin
  labels, study how viability typologies generalise across national contexts.

---

## Limitations

- **Temporal alignment:** GHI is a multi-year climatological mean, population is
  a 2025 snapshot, roads are current OSM — slow-changing but not co-temporal.
- **Intra-cell population:** the per-cell sum captures headcount, not its
  arrangement; rural settlement is clustered, so a cell total may overstate
  serviceable density.
- **Cell geometry:** cells are defined on a geographic (degree) grid, so cell
  area varies modestly with latitude; the 2–3 km figures are approximate.
- **Admin granularity:** admin-1 means different things across countries
  (47 counties in Kenya vs. 4 regions in Uganda); compare within, not across,
  national conventions.

---

## Citation

```bibtex
@inproceedings{eaminigridbench2025,
  title     = {EA-MiniGrid-Bench: A High-Resolution Spatial Benchmark Dataset
               for Machine Learning in East African Energy Planning},
  author    = {<Authors>},
  booktitle = {<Venue>},
  year      = {2025},
  doi       = {<INSERT ZENODO DOI>},
  url       = {<INSERT REPOSITORY URL>}
}
```

---

## License

- **Dataset and code:** released under <CHOOSE A LICENSE, e.g. CC BY 4.0 for the
  data and MIT for the code>.
- **Source data** retains the licenses of its original providers (Global Solar
  Atlas, WorldPop, OpenStreetMap/ODbL, Who's On First, UN OCHA). Please observe
  their attribution requirements when redistributing derived products.
```
