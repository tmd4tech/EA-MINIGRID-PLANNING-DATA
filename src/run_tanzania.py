# =============================================================================
# run_tanzania.py  —  EA-MiniGrid-Bench
# Tanzania: 3.0 km grid (~0.027 deg), UTM 36S/37S (EPSG:32736)
# NOTE: Tanzania spans UTM zones 36S and 37S; 32736 is used country-wide as a
#       standard approximation (matches the original paper).
# Requires ea_minigrid_core.py in the same folder / notebook session.
# =============================================================================
import os, sys
# Allow running from repo root or from inside src/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ea_minigrid_core import process_country

process_country(
    country_name = 'Tanzania',
    prefix       = 'TZ',
    folder       = 'Raw_Data_Tanzania/',
    pop_pattern  = 'tza_pop_2025_*.tif',
    grid_size_deg= 0.027,
    utm_epsg     = 32736,
)
