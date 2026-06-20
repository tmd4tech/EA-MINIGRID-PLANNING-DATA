# =============================================================================
# merge_master.py  —  EA-MiniGrid-Bench
# Concatenate the four validated per-country CSVs into the master dataset.
# Run only after all four "VALIDATED SUCCESS" messages.
# =============================================================================
import pandas as pd
import os

print("Initiating Dataset Merger...")
project_root = '/content/drive/MyDrive/EA_MiniGrid_Project/'

target_files = [
    project_root + 'Raw_Data_Rwanda/EA_MiniGrid_Rwanda_Processed.csv',
    project_root + 'Raw_Data_Kenya/EA_MiniGrid_Kenya_Processed.csv',
    project_root + 'Raw_Data_Uganda/EA_MiniGrid_Uganda_Processed.csv',
    project_root + 'Raw_Data_Tanzania/EA_MiniGrid_Tanzania_Processed.csv',
]

valid = [f for f in target_files if os.path.exists(f)]
print(f"Found {len(valid)} of 4 expected datasets:")
for f in valid:
    print(f"  - {os.path.basename(f)}")

if len(valid) < 4:
    missing = [os.path.basename(f) for f in target_files if f not in valid]
    print(f"
  WARNING: missing {missing} — do not proceed to Phase 2 until all 4 exist.")

EXPECTED = ['Grid_ID', 'Country', 'Admin1_Name', 'Admin2_Name',
            'Centroid_Lon', 'Centroid_Lat',
            'Solar_Irradiance_kWh', 'Population_Count', 'Dist_to_Road_m']

frames = []
for f in valid:
    d = pd.read_csv(f)
    assert list(d.columns) == EXPECTED, f"Schema mismatch in {os.path.basename(f)}: {list(d.columns)}"
    frames.append(d)

master = pd.concat(frames, ignore_index=True)

# Grid_ID uniqueness check across the merged set
assert master['Grid_ID'].is_unique, "Duplicate Grid_IDs after concat!"

out = project_root + 'EA_MiniGrid_Bench_MASTER_FINAL.csv'
master.to_csv(out, index=False)

final = pd.read_csv(out)
print(f"
MASTER BENCHMARK COMPLETE.")
print(f"Total validated rows covering East Africa: {len(final):,}")
print(f"
Per-country counts:")
print(final['Country'].value_counts().to_string())
print(f"
Columns: {list(final.columns)}")
print(final.head().to_string())
