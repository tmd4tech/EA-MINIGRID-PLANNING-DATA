
# =============================================================================
# ea_minigrid_phase2.py  —  EA-MiniGrid-Bench Experiments (2025 refresh)
#
# Produces, from EA_MiniGrid_Bench_MASTER_FINAL.csv:
#   [A] K-Means clustering (k-scan + final k=4) -> Viability Tiers
#   [B] Per-country and per-admin1 descriptive tables
#   [C] Supervised baselines: RandomForest + XGBoost
#         - Regression  : predict Population_Count (HEADLINE - honest task)
#         - Classification: reproduce Tier (framed as distillation benchmark)
#   [D] Figures: elbow/silhouette, per-tier boxplots, AND geographic tier maps
#
# Requires: pip install pandas scikit-learn xgboost matplotlib seaborn
# =============================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import (silhouette_score, classification_report,
                             confusion_matrix, r2_score, mean_absolute_error,
                             f1_score, accuracy_score)
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from xgboost import XGBClassifier, XGBRegressor

RANDOM_STATE = 42
CSV_PATH = "/content/drive/MyDrive/EA_MiniGrid_Project/EA_MiniGrid_Bench_MASTER_FINAL.csv"
OUT_DIR  = "/content/drive/MyDrive/EA_MiniGrid_Project/"

FEATURES = ["Solar_Irradiance_kWh", "Population_Count", "Dist_to_Road_m"]

plt.rcParams.update({
    "figure.dpi": 150, "font.family": "DejaVu Sans",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3,
    "axes.titlesize": 13, "axes.labelsize": 12,
    "xtick.labelsize": 10, "ytick.labelsize": 10,
})

# Tier colours assigned AFTER we know which tier is which (see below)
TIER_COLORS = {"Tier A": "#1A5276", "Tier B": "#1E8449",
               "Tier C": "#F39C12", "Tier D": "#C0392B"}


# =============================================================================
# [0] LOAD
# =============================================================================
def load_data(path=CSV_PATH):
    df = pd.read_csv(path)
    expected = ['Grid_ID', 'Country', 'Admin1_Name', 'Admin2_Name',
                'Centroid_Lon', 'Centroid_Lat',
                'Solar_Irradiance_kWh', 'Population_Count', 'Dist_to_Road_m']
    assert list(df.columns) == expected, f"Schema mismatch: {list(df.columns)}"
    # alias coordinate columns for the mapping function
    df["lon"] = df["Centroid_Lon"]
    df["lat"] = df["Centroid_Lat"]
    print(f"[0] Loaded {len(df):,} rows, {df['Country'].nunique()} countries.")
    return df


# =============================================================================
# [A] K-MEANS  ->  VIABILITY TIERS
# =============================================================================
def run_clustering(df):
    print("
[A] K-Means clustering...")
    X = StandardScaler().fit_transform(df[FEATURES])

    # k-scan (full-data silhouette; sample only if very large for speed)
    sample = 20000 if len(df) > 20000 else None
    rows = []
    for k in range(2, 10):
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=15, max_iter=500)
        lab = km.fit_predict(X)
        sil = silhouette_score(X, lab, sample_size=sample, random_state=RANDOM_STATE)
        rows.append({"k": k, "inertia": km.inertia_, "silhouette": sil})
        print(f"    k={k}  inertia={km.inertia_}>12,.1f}  silhouette={sil:.4f}")
    scan = pd.DataFrame(rows)

    # Final model: k=4
    km = KMeans(n_clusters=4, random_state=RANDOM_STATE, n_init=15, max_iter=500)
    df["Cluster"] = km.fit_predict(X)
    final_sil = silhouette_score(X, df["Cluster"], sample_size=sample,
                                 random_state=RANDOM_STATE)
    print(f"    FINAL k=4: inertia={km.inertia_:,.1f}  silhouette={final_sil:.4f}")

    # Assign tier letters by ranking clusters on mean population (descending)
    order = (df.groupby("Cluster")["Population_Count"].mean()
             .sort_values(ascending=False).index.tolist())
    tier_map = {cl: f"Tier {'ABCD'[i]}" for i, cl in enumerate(order)}
    df["Viability_Tier"] = df["Cluster"].map(tier_map)

    return df, scan, final_sil, km


def profile_tiers(df):
    """Per-tier profile on ORIGINAL units. Re-derive narrative from data."""
    prof = (df.groupby("Viability_Tier")
            .agg(Cells=("Grid_ID", "count"),
                 Mean_Solar=("Solar_Irradiance_kWh", "mean"),
                 Mean_Pop=("Population_Count", "mean"),
                 Median_Pop=("Population_Count", "median"),
                 Mean_DistRoad_km=("Dist_to_Road_m", lambda s: s.mean()/1000))
            .round(2)
            .reindex(["Tier A", "Tier B", "Tier C", "Tier D"]))
    prof["Pct_Cells"] = (prof["Cells"] / prof["Cells"].sum() * 100).round(1)
    print("
    Tier profiles (re-derive narrative labels from THESE numbers):")
    print(prof.to_string())
    # Identify the high-solar 'goldmine' tier empirically
    goldmine = prof["Mean_Solar"].idxmax()
    print(f"
    -> Highest-solar tier is {goldmine} "
          f"(Mean Solar={prof.loc[goldmine,'Mean_Solar']}). "
          f"This is the empirical 'Mini-Grid Goldmine' for the new data.")
    return prof


# =============================================================================
# [B] PER-COUNTRY & PER-ADMIN1 TABLES  (addresses over-aggregation critique)
# =============================================================================
def country_tables(df):
    print("
[B] Per-country breakdown...")
    by_country = (df.groupby("Country")
                  .agg(Cells=("Grid_ID", "count"),
                       Mean_Solar=("Solar_Irradiance_kWh", "mean"),
                       Median_Pop=("Population_Count", "median"),
                       Mean_DistRoad_km=("Dist_to_Road_m", lambda s: s.mean()/1000))
                  .round(2).sort_values("Cells", ascending=False))
    print(by_country.to_string())

    # Tier composition per country (the cross-border story)
    comp = (pd.crosstab(df["Country"], df["Viability_Tier"], normalize="index")
            .mul(100).round(1))
    print("
    Tier composition by country (% of each country's cells):")
    print(comp.to_string())

    # Top admin1 units in the highest-solar tier (where to invest, by region)
    goldmine = df.groupby("Viability_Tier")["Solar_Irradiance_kWh"].mean().idxmax()
    top = (df[df["Viability_Tier"] == goldmine]
           .groupby(["Country", "Admin1_Name"]).size()
           .sort_values(ascending=False).head(15)
           .rename("Goldmine_Cells").reset_index())
    print(f"
    Top 15 admin1 regions in {goldmine} (high-solar) tier:")
    print(top.to_string(index=False))
    return by_country, comp, top


# =============================================================================
# [C] SUPERVISED BASELINES
# =============================================================================
def supervised_regression(df):
    """HEADLINE honest task: predict Population_Count from solar + road + country.
    Population is NOT trivially recoverable from the others, so this is a real
    predictive benchmark (unlike tier-classification which re-learns clustering).
    """
    print("
[C1] Regression: predict log(Population) from solar, road, country...")
    d = df.copy()
    d["log_pop"] = np.log1p(d["Population_Count"])
    X = pd.get_dummies(d[["Solar_Irradiance_kWh", "Dist_to_Road_m", "Country"]],
                       columns=["Country"], drop_first=True)
    y = d["log_pop"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2,
                                          random_state=RANDOM_STATE)
    results = {}
    models = {
        "RandomForest": RandomForestRegressor(n_estimators=200, n_jobs=-1,
                                              random_state=RANDOM_STATE),
        "XGBoost": XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.1,
                                n_jobs=-1, random_state=RANDOM_STATE),
    }
    for name, m in models.items():
        m.fit(Xtr, ytr)
        pred = m.predict(Xte)
        r2 = r2_score(yte, pred)
        mae = mean_absolute_error(yte, pred)
        results[name] = {"R2": round(r2, 4), "MAE_log": round(mae, 4)}
        print(f"    {name:14s}  R2={r2:.4f}   MAE(log pop)={mae:.4f}")
    return pd.DataFrame(results).T


def supervised_classification(df):
    """DISTILLATION benchmark: reproduce Tier from the 3 features.
    NOTE: tiers were derived by K-Means on these same features, so high scores
    reflect the models re-learning the cluster geometry, NOT novel prediction.
    Framed honestly as a benchmark-task spec, per reviewer guidance.
    """
    print("
[C2] Classification: reproduce Tier (distillation benchmark)...")
    X = df[FEATURES]
    y = df["Viability_Tier"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y,
                                          random_state=RANDOM_STATE)
    results = {}
    models = {
        "RandomForest": RandomForestClassifier(n_estimators=200, n_jobs=-1,
                                               random_state=RANDOM_STATE),
        "XGBoost": XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1,
                                 n_jobs=-1, random_state=RANDOM_STATE,
                                 use_label_encoder=False, eval_metric="mlogloss"),
    }
    # XGBoost needs integer labels
    classes = sorted(y.unique())
    cls_to_int = {c: i for i, c in enumerate(classes)}
    for name, m in models.items():
        if name == "XGBoost":
            m.fit(Xtr, ytr.map(cls_to_int))
            pred_int = m.predict(Xte)
            pred = pd.Series(pred_int).map({v: k for k, v in cls_to_int.items()}).values
        else:
            m.fit(Xtr, ytr)
            pred = m.predict(Xte)
        acc = accuracy_score(yte, pred)
        f1 = f1_score(yte, pred, average="macro")
        results[name] = {"Accuracy": round(acc, 4), "Macro_F1": round(f1, 4)}
        print(f"    {name:14s}  acc={acc:.4f}  macroF1={f1:.4f}")
    print("    (High scores expected — models re-learn the K-Means boundary.)")
    return pd.DataFrame(results).T


# =============================================================================
# [D] FIGURES
# =============================================================================
def fig_elbow_silhouette(scan, path=OUT_DIR + "fig1_elbow_silhouette.png"):
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].plot(scan["k"], scan["inertia"], "o-", color="#1A5276", lw=2)
    ax[0].axvline(4, color="#C0392B", ls="--", label="Selected k = 4")
    ax[0].set(xlabel="Number of clusters (k)", ylabel="Within-cluster SS (inertia)",
              title="Elbow curve")
    ax[0].legend(); ax[0].xaxis.set_major_locator(mticker.MultipleLocator(1))
    ax[1].plot(scan["k"], scan["silhouette"], "s-", color="#1E8449", lw=2)
    ax[1].axvline(4, color="#C0392B", ls="--", label="Selected k = 4")
    ax[1].set(xlabel="Number of clusters (k)", ylabel="Silhouette score",
              title="Silhouette score")
    ax[1].legend(); ax[1].xaxis.set_major_locator(mticker.MultipleLocator(1))
    plt.tight_layout(); plt.savefig(path, bbox_inches="tight", dpi=150); plt.show()
    print(f"    saved {path}")


def fig_tier_map(df, path=OUT_DIR + "fig_tier_map.png"):
    """Geographic maps of cell centroids coloured by Viability Tier.
    Produces (1) a regional map of all cells and (2) per-country small
    multiples. Requires lon/lat columns (added by the updated pipeline)."""
    if not {"lon", "lat"}.issubset(df.columns):
        print("    [map] lon/lat columns missing — re-export CSVs with the "
              "updated pipeline to enable maps.")
        return

    tiers = ["Tier A", "Tier B", "Tier C", "Tier D"]

    # (1) Regional map
    fig, ax = plt.subplots(figsize=(9, 9))
    for tier in tiers:
        sub = df[df["Viability_Tier"] == tier]
        ax.scatter(sub["lon"], sub["lat"], s=2, alpha=0.45,
                   c=TIER_COLORS[tier], label=f"{tier} (n={len(sub):,})")
    ax.set(xlabel="Longitude", ylabel="Latitude",
           title="EA-MiniGrid-Bench — Viability Tier Distribution (Core 4)")
    ax.legend(markerscale=5, fontsize=9, loc="lower left")
    ax.set_aspect("equal")
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight", dpi=150)
    plt.show()
    print(f"    saved {path}")

    # (2) Per-country small multiples
    countries = sorted(df["Country"].unique())
    fig, axes = plt.subplots(1, len(countries),
                             figsize=(4.2 * len(countries), 4.2))
    if len(countries) == 1:
        axes = [axes]
    for ax, country in zip(axes, countries):
        cdf = df[df["Country"] == country]
        for tier in tiers:
            sub = cdf[cdf["Viability_Tier"] == tier]
            ax.scatter(sub["lon"], sub["lat"], s=3, alpha=0.5,
                       c=TIER_COLORS[tier], label=tier)
        ax.set(title=f"{country} (n={len(cdf):,})",
               xlabel="Lon", ylabel="Lat")
        ax.set_aspect("equal")
    handles = [plt.Line2D([0], [0], marker='o', ls='', color=TIER_COLORS[t],
                          label=t) for t in tiers]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=10,
               bbox_to_anchor=(0.5, -0.05))
    fig.suptitle("Viability Tier Distribution by Country", y=1.02, fontsize=13)
    plt.tight_layout()
    panel_path = path.replace(".png", "_by_country.png")
    plt.savefig(panel_path, bbox_inches="tight", dpi=150)
    plt.show()
    print(f"    saved {panel_path}")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    df = load_data()
    df, scan, final_sil, km = run_clustering(df)
    prof = profile_tiers(df)
    by_country, comp, top = country_tables(df)
    reg = supervised_regression(df)
    clf = supervised_classification(df)
    fig_elbow_silhouette(scan)
    fig_tier_map(df)

    # Save enriched dataset + result tables
    df.to_csv(OUT_DIR + "EA_MiniGrid_Bench_CLUSTERED.csv", index=False)
    prof.to_csv(OUT_DIR + "table_tier_profiles.csv")
    by_country.to_csv(OUT_DIR + "table_by_country.csv")
    comp.to_csv(OUT_DIR + "table_tier_composition.csv")
    reg.to_csv(OUT_DIR + "table_regression_results.csv")
    clf.to_csv(OUT_DIR + "table_classification_results.csv")
    print("
DONE. Enriched CSV + 6 result tables saved.")
