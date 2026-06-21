# =============================================================================
# run_uganda.py  —  EA-MiniGrid-Bench
# Uganda: 2.5 km grid (~0.0225 deg), UTM 36N (EPSG:32636)
# NOTE: Uganda sits north of the equator, so a Northern-hemisphere UTM zone
#       (32636) is geographically correct. The original paper used 32736;
#       change utm_epsg below to 32736 if you need to match the paper exactly.
# Requires ea_minigrid_core.py in the same folder / notebook session.
# =============================================================================
import os, sys
# Allow running from repo root or from inside src/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ea_minigrid_core import process_country

process_country(
    country_name = 'Uganda',
    prefix       = 'UG',
    folder       = 'Raw_Data_Uganda/',
    pop_pattern  = 'uga_pop_2025_*.tif',
    grid_size_deg= 0.0225,
    utm_epsg     = 32636,
)
