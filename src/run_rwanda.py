# =============================================================================
# run_rwanda.py  —  EA-MiniGrid-Bench
# Rwanda: 2.0 km grid (~0.018 deg), UTM 35S (EPSG:32735)
# Requires ea_minigrid_core.py in the same folder / notebook session.
# =============================================================================
import os, sys
# Allow running from repo root or from inside src/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ea_minigrid_core import process_country

process_country(
    country_name = 'Rwanda',
    prefix       = 'RW',
    folder       = 'Raw_Data_Rwanda/',
    pop_pattern  = 'rwa_pop_2025_*.tif',
    grid_size_deg= 0.018,
    utm_epsg     = 32735,
)
