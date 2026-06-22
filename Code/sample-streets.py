import random

import geopandas as gpd
import pandas as pd

# ── Configuration ────────────────────────────────────────────────────────────
INPUT_GPKG = "../QGIS project files/Rotterdam Network/rotterdam-roads-final.gpkg"  # path to your GeoPackage
LAYER = None  # layer name inside the GeoPackage, or None for default
CLUSTER_VAL = 3  # value of the "cluster" attribute to filter on
N_SAMPLES = 50  # number of random start points to draw
OUTPUT_CSV = "../data/street-view-points.csv"  # output file
RANDOM_SEED = 42  # set to None for a different result each run
# ─────────────────────────────────────────────────────────────────────────────

# Load the GeoPackage (optionally specifying a layer)
gdf = gpd.read_file(INPUT_GPKG, layer=LAYER)

# Filter to the desired cluster
cluster_gdf = gdf[gdf["cluster"] == CLUSTER_VAL].copy()
print(f"Found {len(cluster_gdf)} linestrings with cluster == {CLUSTER_VAL}")

if len(cluster_gdf) < N_SAMPLES:
    print(
        f"Warning: only {len(cluster_gdf)} features available; "
        f"sampling all of them instead of {N_SAMPLES}."
    )
    N_SAMPLES = len(cluster_gdf)

# Draw a random sample (reproducible with RANDOM_SEED)
sample = cluster_gdf.sample(n=N_SAMPLES, random_state=RANDOM_SEED)


# Extract the first coordinate of each linestring (the start point)
def start_point(geom):
    coords = list(geom.coords)
    return coords[0]  # (x, y) or (x, y, z)


start_coords = sample.geometry.apply(start_point)

# Build a tidy DataFrame
has_z = len(start_coords.iloc[0]) == 3
if has_z:
    df_out = pd.DataFrame(
        [(c[1], c[0], c[2]) for c in start_coords],
        columns=["x", "y", "z"],
        index=sample.index,
    )
else:
    df_out = pd.DataFrame(
        [(c[1], c[0]) for c in start_coords],
        columns=["x", "y"],
        index=sample.index,
    )

# Optionally keep the original index / any other attributes alongside coords
df_out.insert(0, "original_index", sample.index)

df_out.to_csv(OUTPUT_CSV, index=False)
print(f"Written {len(df_out)} start points to '{OUTPUT_CSV}'")
print(df_out.head())
