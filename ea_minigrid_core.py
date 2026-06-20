
# =============================================================================
# ea_minigrid_core.py
# Shared processing engine for EA-MiniGrid-Bench (2025 data refresh).
# Adds admin1 (province/region) and admin2 (district) labels via spatial join.
# Import this in each per-country file; do not run directly.
# =============================================================================

import geopandas as gpd
import rasterio
import numpy as np
import pandas as pd
from rasterstats import zonal_stats
from shapely.geometry import box
import glob
import os
import gc

PROJECT_ROOT = '/content/drive/MyDrive/EA_MiniGrid_Project/'
SOLAR_FILE   = PROJECT_ROOT + 'GHI.tif'   # one shared world raster


def find_one(folder, pattern, label):
    matches = glob.glob(os.path.join(folder, pattern))
    if len(matches) == 0:
        raise FileNotFoundError(f"No {label} file matching '{pattern}' in {folder}")
    if len(matches) > 1:
        raise RuntimeError(f"Multiple {label} files match '{pattern}': {matches}")
    return matches[0]


def detect_name_column(gdf, level):
    """Find the human-readable name column in an HDX/OCHA admin layer.

    HDX naming varies: ADM1_EN, admin1Name, NAME_1, ADM1_PCODE etc.
    We prefer an English-name column; fall back to any column containing
    the level number and 'name'/'en'. Returns the column name or None.
    """
    cols = list(gdf.columns)
    lvl = str(level)
    # Ranked candidate patterns (most preferred first).
    # Covers HDX/OCHA (ADM1_EN ...) AND Who's On First (name / name_eng ...).
    candidates = [
        # HDX / OCHA / GADM style
        f'ADM{lvl}_EN', f'adm{lvl}_en', f'admin{lvl}Name', f'admin{lvl}Name_en',
        f'NAME_{lvl}', f'ADM{lvl}_NAME', f'shapeName',
        # Who's On First style (these layers have one row per place, so the
        # plain 'name' / 'name_eng' field IS the admin name at this level)
        'name_eng', 'name',
    ]
    for c in candidates:
        if c in cols:
            return c
    # Heuristic fallback: a column mentioning the level and a name/en token
    for c in cols:
        cl = c.lower()
        if lvl in cl and ('name' in cl or cl.endswith('_en')):
            return c
    return None


def process_country(country_name, prefix, folder,
                    pop_pattern, grid_size_deg, utm_epsg):
    print("=" * 60)
    print(f"  EA-MiniGrid-Bench Engine — {country_name.upper()}")
    print("=" * 60)

    folder     = PROJECT_ROOT + folder
    pop_file   = find_one(folder, pop_pattern, "population")
    infra_file = find_one(folder, '*-free.shp.zip', "road")
    admin0_fp  = os.path.join(folder, 'admin0.shp')
    admin1_fp  = os.path.join(folder, 'admin1.shp')
    admin2_fp  = os.path.join(folder, 'admin2.shp')

    print(f"   pop   : {os.path.basename(pop_file)}")
    print(f"   roads : {os.path.basename(infra_file)}")

    # ---- Stage 1: national grid, clipped to admin0 ----
    # IMPORTANT: GHI is now a WORLD raster, so its bounds span the whole globe.
    # We MUST derive the grid extent from the country's admin0 bounding box,
    # not from the raster, or we would generate hundreds of millions of cells.
    print("Mapping grid...")
    with rasterio.open(SOLAR_FILE) as src:
        solar_crs = src.crs   # use the raster CRS so zonal_stats aligns

    adm0 = gpd.read_file(admin0_fp)
    if adm0.crs is None:
        adm0.set_crs('epsg:4326', inplace=True)
    adm0 = adm0.to_crs(solar_crs)

    # Bounding box from the COUNTRY boundary
    minx, miny, maxx, maxy = adm0.total_bounds

    cols = int(np.ceil((maxx - minx) / grid_size_deg))
    rows = int(np.ceil((maxy - miny) / grid_size_deg))
    polygons = [box(minx + i*grid_size_deg, miny + j*grid_size_deg,
                    minx + (i+1)*grid_size_deg, miny + (j+1)*grid_size_deg)
                for i in range(cols) for j in range(rows)]

    grid_gdf = gpd.GeoDataFrame({'geometry': polygons}, crs=solar_crs)
    print(f"   [Stage 1] Bounding box cells: {len(grid_gdf):,}")

    grid_gdf = grid_gdf[grid_gdf.intersects(adm0.geometry.union_all())].copy()
    grid_gdf = grid_gdf.reset_index(drop=True)
    grid_gdf['Grid_ID'] = [f'{prefix}_' + str(i).zfill(6) for i in range(len(grid_gdf))]
    grid_gdf['Country'] = country_name
    print(f"   [Stage 1] After admin0 clip: {len(grid_gdf):,} cells")

    # ---- Stage 2: zonal stats ----
    print("Zonal stats (solar mean, population sum)...")
    with rasterio.open(SOLAR_FILE) as src:
        solar_nodata = src.nodata if src.nodata is not None else -9999
    grid_gdf['Solar_Irradiance_kWh'] = [
        s['mean'] for s in zonal_stats(grid_gdf, SOLAR_FILE, stats="mean", nodata=solar_nodata)]

    with rasterio.open(pop_file) as src:
        pop_nodata = src.nodata if src.nodata is not None else -9999
    grid_gdf['Population_Count'] = [
        s['sum'] for s in zonal_stats(grid_gdf, pop_file, stats="sum", nodata=pop_nodata)]

    # ---- Stage 3: filtering ----
    print("Filtering...")
    n0 = len(grid_gdf)
    grid_gdf = grid_gdf.dropna(subset=['Solar_Irradiance_kWh', 'Population_Count'])
    print(f"   [Stage 3] After NoData drop:   {len(grid_gdf):,}  (-{n0-len(grid_gdf):,})")
    n1 = len(grid_gdf)
    grid_gdf = grid_gdf[grid_gdf['Population_Count'] > 0]
    print(f"   [Stage 3] After Population>0:   {len(grid_gdf):,}  (-{n1-len(grid_gdf):,})")
    n2 = len(grid_gdf)
    grid_gdf = grid_gdf[grid_gdf['Solar_Irradiance_kWh'] > 0.5]
    print(f"   [Stage 3] After Solar>0.5:      {len(grid_gdf):,}  (-{n2-len(grid_gdf):,})")

    # ---- Stage 4: nearest-road distance ----
    print("Nearest-road distance...")
    roads_gdf = gpd.read_file('zip://' + infra_file + '!gis_osm_roads_free_1.shp')
    roads_gdf = roads_gdf[roads_gdf.geometry.notna() & roads_gdf.geometry.is_valid]

    grid_metric  = grid_gdf.to_crs(epsg=utm_epsg)
    roads_metric = roads_gdf[['geometry']].to_crs(epsg=utm_epsg)
    centroids = gpd.GeoDataFrame(geometry=grid_metric.geometry.centroid, crs=grid_metric.crs)

    nearest = gpd.sjoin_nearest(centroids, roads_metric, distance_col="Dist_to_Road_m")
    nearest = nearest[~nearest.index.duplicated(keep='first')]
    grid_gdf = grid_gdf.join(nearest['Dist_to_Road_m'].round(1))
    grid_gdf = grid_gdf.dropna(subset=['Dist_to_Road_m'])
    print(f"   [Stage 4] After road join:      {len(grid_gdf):,}")

    # ---- Stage 4b: admin1 / admin2 labelling via point-in-polygon join ----
    # Join cell CENTROIDS against each admin layer.
    # Compute centroids in the projected (metric) CRS to avoid the
    # "geographic CRS centroid" warning, then reproject back to match admin.
    print("Labelling admin1 / admin2...")
    centroids_proj = grid_gdf.to_crs(epsg=utm_epsg).geometry.centroid
    cell_centroids = gpd.GeoDataFrame(
        {'Grid_ID': grid_gdf['Grid_ID'].values},
        geometry=centroids_proj.to_crs(solar_crs).values,
        crs=solar_crs,
    )

    def attach_admin(level, fp):
        col_out = f'Admin{level}_Name'
        if not os.path.exists(fp):
            print(f"   [admin{level}] file not found — skipping ({col_out} left blank)")
            grid_gdf[col_out] = pd.NA
            return
        adm = gpd.read_file(fp)
        if adm.crs is None:
            adm.set_crs('epsg:4326', inplace=True)
        adm = adm.to_crs(solar_crs)
        name_col = detect_name_column(adm, level)
        if name_col is None:
            print(f"   [admin{level}] no name column detected in {list(adm.columns)} — "
                  f"using index id")
            adm[name_col := f'_adm{level}_id'] = adm.index.astype(str)
        adm = adm[[name_col, 'geometry']].rename(columns={name_col: col_out})

        # Primary: point-in-polygon
        joined = gpd.sjoin(cell_centroids, adm, how='left', predicate='within')
        joined = joined[~joined['Grid_ID'].duplicated(keep='first')]
        mapping = dict(zip(joined['Grid_ID'], joined[col_out]))
        grid_gdf[col_out] = grid_gdf['Grid_ID'].map(mapping)

        # Fallback: snap any unmatched (border-sliver) cells to NEAREST polygon.
        n_before = grid_gdf[col_out].isna().sum()
        if n_before > 0:
            missing_ids = grid_gdf.loc[grid_gdf[col_out].isna(), 'Grid_ID']
            miss_centroids = cell_centroids[cell_centroids['Grid_ID'].isin(missing_ids)]
            # nearest join must be in a metric CRS for correct distances
            nearest = gpd.sjoin_nearest(
                miss_centroids.to_crs(epsg=utm_epsg),
                adm.to_crs(epsg=utm_epsg),
                how='left',
            )
            nearest = nearest[~nearest['Grid_ID'].duplicated(keep='first')]
            fill_map = dict(zip(nearest['Grid_ID'], nearest[col_out]))
            fill_series = grid_gdf['Grid_ID'].map(fill_map)
            grid_gdf[col_out] = grid_gdf[col_out].fillna(fill_series)

        n_after = grid_gdf[col_out].isna().sum()
        print(f"   [admin{level}] labelled via '{name_col}' "
              f"({n_before:,} snapped to nearest, {n_after:,} still NA)")

    attach_admin(1, admin1_fp)
    attach_admin(2, admin2_fp)

    # ---- Stage 4c: store cell centroid coordinates (WGS84) for mapping ----
    # Reuse the centroids already computed; reproject to lon/lat.
    cent_ll = centroids_proj.to_crs('epsg:4326')
    grid_gdf['Centroid_Lon'] = cent_ll.x.values
    grid_gdf['Centroid_Lat'] = cent_ll.y.values

    # ---- Stage 5: export + schema validation ----
    expected = ['Grid_ID', 'Country', 'Admin1_Name', 'Admin2_Name',
                'Centroid_Lon', 'Centroid_Lat',
                'Solar_Irradiance_kWh', 'Population_Count', 'Dist_to_Road_m']
    out = pd.DataFrame(grid_gdf.drop(columns='geometry'))
    out = out[expected]   # enforce column order
    out_csv = os.path.join(folder, f'EA_MiniGrid_{country_name}_Processed.csv')
    out.to_csv(out_csv, index=False)

    chk = pd.read_csv(out_csv)
    assert len(chk) > 0, "Export failed — CSV empty!"
    assert list(chk.columns) == expected, f"Schema mismatch! Got: {list(chk.columns)}"

    print(f"
VALIDATED SUCCESS! {country_name}: {len(chk):,} rows → {out_csv}")
    print("--- numeric sanity (confirm 2025 data) ---")
    print(chk[['Solar_Irradiance_kWh', 'Population_Count', 'Dist_to_Road_m']]
          .describe().round(2).to_string())
    print(f"--- admin1 coverage: {chk['Admin1_Name'].nunique()} unique regions ---")
    print(chk['Admin1_Name'].value_counts(dropna=False).head(10).to_string())

    del grid_gdf, roads_gdf, grid_metric, roads_metric, centroids, nearest, cell_centroids
    gc.collect()
    return out_csv
