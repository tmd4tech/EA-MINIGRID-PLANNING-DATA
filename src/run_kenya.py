# =============================================================================
# run_kenya.py  —  EA-MiniGrid-Bench
# Kenya: 3.0 km grid (~0.027 deg), UTM 36S/37S region (EPSG:32736)
# Requires ea_minigrid_core.py in the same folder / notebook session.
# =============================================================================
import os, sys
# Allow running from repo root or from inside src/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ea_minigrid_core import process_country

process_country(
    country_name = 'Kenya',
    prefix       = 'KE',
    folder       = 'Raw_Data_Kenya/',
    pop_pattern  = 'ken_pop_2025_*.tif',
    grid_size_deg= 0.027,
    utm_epsg     = 32736,
)
