# config.py — EA-MiniGrid-Bench
# Central place for all filesystem paths. No Google Drive mounts.
#
# By default, raw data is expected in an "EA_MiniGrid_Project/" folder placed
# at the repository root (next to this file). You can override that location
# without editing code by setting the EA_MINIGRID_DATA environment variable:
#
#   Linux/Mac : export EA_MINIGRID_DATA=/path/to/EA_MiniGrid_Project
#   Windows   : setx EA_MINIGRID_DATA "C:\path\to\EA_MiniGrid_Project"
#   Colab     : os.environ["EA_MINIGRID_DATA"] = "/content/drive/MyDrive/EA_MiniGrid_Project"
#
# Expected layout inside PROJECT_ROOT (see README.md):
#   PROJECT_ROOT/GHI.tif
#   PROJECT_ROOT/Raw_Data_Rwanda/   (pop tif, roads zip, admin0/1/2 shp)
#   PROJECT_ROOT/Raw_Data_Kenya/    ...
#   PROJECT_ROOT/Raw_Data_Uganda/   ...
#   PROJECT_ROOT/Raw_Data_Tanzania/ ...

import os

# Repo root = the directory this config.py lives in.
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# Raw-data root: env var if set, else "EA_MiniGrid_Project" under the repo root.
PROJECT_ROOT = os.environ.get(
    "EA_MINIGRID_DATA",
    os.path.join(REPO_ROOT, "EA_MiniGrid_Project"),
)

# Single global GHI raster, shared across all four countries.
SOLAR_FILE = os.path.join(PROJECT_ROOT, "GHI.tif")

# Where merged outputs / master CSV / result tables are written.
OUTPUT_DIR  = os.path.join(REPO_ROOT, "data")
RESULTS_DIR = os.path.join(REPO_ROOT, "results")
