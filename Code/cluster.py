"""
K-Means Clustering for GeoPackage Linestrings
==============================================
Clusters linestring features based on numeric attributes and writes
the cluster label to a new attribute in the GeoPackage.

Usage:
    python cluster_geopackage.py [OPTIONS]

Options:
    --input         Path to input GeoPackage (.gpkg)          [required]
    --layer         Layer name inside the GeoPackage           [default: first layer]
    --attributes    Space-separated list of attribute names    [required]
    --k             Number of clusters                         [default: auto via elbow]
    --output        Path to output GeoPackage (.gpkg)          [default: <input>_clustered.gpkg]
    --cluster-col   Name of the new cluster column             [default: cluster]
    --elbow         Show elbow plot to help choose k           [flag]
    --elbow-max     Max k to evaluate in elbow plot            [default: 15]
    --random-seed   Random seed for reproducibility            [default: 42]

Examples:
    # Show elbow plot first to pick k:
    python cluster_geopackage.py --input roads.gpkg --attributes speed_limit width lanes --elbow

    # Run clustering with k=5:
    python cluster_geopackage.py --input roads.gpkg --attributes speed_limit width lanes --k 5

    # Full example with all options:
    python cluster_geopackage.py \\
        --input roads.gpkg \\
        --layer road_segments \\
        --attributes speed_limit width lanes traffic_count \\
        --k 6 \\
        --output roads_clustered.gpkg \\
        --cluster-col road_cluster \\
        --random-seed 42
"""

import argparse
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import geopandas as gpd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, MiniBatchKMeans
from sklearn.impute import SimpleImputer


def parse_args():
    parser = argparse.ArgumentParser(
        description="K-Means clustering on GeoPackage linestring attributes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--input", required=True, help="Path to input GeoPackage")
    parser.add_argument("--layer", default=None, help="Layer name (default: first layer)")
    parser.add_argument("--attributes", nargs="+", required=True, help="Attribute names to cluster on")
    parser.add_argument("--k", type=int, default=None, help="Number of clusters (omit to use --elbow)")
    parser.add_argument("--output", default=None, help="Output GeoPackage path")
    parser.add_argument("--cluster-col", default="cluster", help="New column name for cluster labels")
    parser.add_argument("--elbow", action="store_true", help="Show elbow plot to help choose k")
    parser.add_argument("--elbow-max", type=int, default=15, help="Max k for elbow plot (default: 15)")
    parser.add_argument("--random-seed", type=int, default=42, help="Random seed (default: 42)")
    return parser.parse_args()


def load_layer(input_path, layer_name):
    import fiona
    layers = fiona.listlayers(input_path)
    if not layers:
        print(f"ERROR: No layers found in {input_path}")
        sys.exit(1)

    if layer_name is None:
        layer_name = layers[0]
        print(f"  No layer specified — using first layer: '{layer_name}'")
    elif layer_name not in layers:
        print(f"ERROR: Layer '{layer_name}' not found. Available layers: {layers}")
        sys.exit(1)

    print(f"  Loading layer '{layer_name}' from {input_path} ...")
    gdf = gpd.read_file(input_path, layer=layer_name)
    print(f"  Loaded {len(gdf):,} features.")
    return gdf, layer_name


def validate_attributes(gdf, attributes):
    missing = [a for a in attributes if a not in gdf.columns]
    if missing:
        print(f"ERROR: Attributes not found in layer: {missing}")
        print(f"  Available columns: {list(gdf.columns)}")
        sys.exit(1)

    # Check for non-numeric
    non_numeric = []
    for a in attributes:
        if not np.issubdtype(gdf[a].dtype, np.number):
            non_numeric.append(f"{a} (dtype: {gdf[a].dtype})")
    if non_numeric:
        print(f"ERROR: Non-numeric attributes detected: {non_numeric}")
        print("  All clustering attributes must be numeric.")
        sys.exit(1)


def prepare_features(gdf, attributes):
    X_raw = gdf[attributes].values

    # Report missing values
    n_missing = np.isnan(X_raw).sum()
    if n_missing > 0:
        print(f"  Warning: {n_missing:,} missing values found — imputing with column medians.")
        imputer = SimpleImputer(strategy="median")
        X_raw = imputer.fit_transform(X_raw)

    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)
    return X_scaled


def plot_elbow(X_scaled, elbow_max, random_seed):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not installed. Run: pip install matplotlib")
        sys.exit(1)

    print(f"\n  Computing inertia for k=2 to k={elbow_max} ...")
    ks = range(2, elbow_max + 1)
    inertias = []

    for k in ks:
        km = MiniBatchKMeans(n_clusters=k, random_state=random_seed, n_init=3)
        km.fit(X_scaled)
        inertias.append(km.inertia_)
        print(f"    k={k:2d}  inertia={km.inertia_:,.0f}")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(list(ks), inertias, marker="o", linewidth=2, color="#2563EB")
    ax.set_xlabel("Number of clusters (k)", fontsize=12)
    ax.set_ylabel("Inertia (within-cluster sum of squares)", fontsize=12)
    ax.set_title("Elbow Plot — choose k where the curve bends", fontsize=13)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
    print("\n  Inspect the plot and re-run with --k <your_choice>")


def run_clustering(X_scaled, k, random_seed, n_features):
    print(f"\n  Running K-Means with k={k}, {len(X_scaled):,} features, {n_features} attributes ...")

    # MiniBatchKMeans is much faster for large datasets (>50k rows)
    if len(X_scaled) > 50_000:
        print("  Using MiniBatchKMeans for speed (dataset > 50k rows).")
        km = MiniBatchKMeans(n_clusters=k, random_state=random_seed, n_init=10, max_iter=300)
    else:
        km = KMeans(n_clusters=k, random_state=random_seed, n_init=10, max_iter=300)

    labels = km.fit_predict(X_scaled)
    inertia = km.inertia_

    counts = np.bincount(labels)
    print(f"\n  Clustering complete. Inertia: {inertia:,.0f}")
    print(f"  Cluster sizes:")
    for i, c in enumerate(counts):
        print(f"    Cluster {i}: {c:,} features ({100*c/len(labels):.1f}%)")

    return labels


def save_output(gdf, layer_name, labels, cluster_col, output_path):
    gdf = gdf.copy()
    gdf[cluster_col] = labels.astype(int)

    print(f"\n  Writing output to {output_path} (layer: '{layer_name}') ...")
    gdf.to_file(output_path, layer=layer_name, driver="GPKG")
    print(f"  Done. New column '{cluster_col}' written with cluster labels 0–{labels.max()}.")


def main():
    args = parse_args()

    # Default output path
    if args.output is None:
        base = args.input.rsplit(".", 1)[0]
        args.output = f"{base}_clustered.gpkg"

    print("\n=== GeoPackage K-Means Clustering ===")
    print(f"  Input:       {args.input}")
    print(f"  Attributes:  {args.attributes}")
    print(f"  Cluster col: {args.cluster_col}")
    print(f"  Output:      {args.output}")

    # Load
    gdf, layer_name = load_layer(args.input, args.layer)

    # Validate
    validate_attributes(gdf, args.attributes)

    # Prepare feature matrix
    X_scaled = prepare_features(gdf, args.attributes)

    # Elbow plot (optional)
    if args.elbow:
        plot_elbow(X_scaled, args.elbow_max, args.random_seed)
        if args.k is None:
            print("\n  Re-run with --k <value> to perform clustering.")
            return

    # Require k if not doing elbow-only
    if args.k is None:
        print("\nERROR: Please specify --k (number of clusters) or use --elbow to explore first.")
        sys.exit(1)

    if args.k < 2:
        print("ERROR: --k must be at least 2.")
        sys.exit(1)

    # Cluster
    labels = run_clustering(X_scaled, args.k, args.random_seed, len(args.attributes))

    # Save
    save_output(gdf, layer_name, labels, args.cluster_col, args.output)
    print("\n=== All done! ===\n")


if __name__ == "__main__":
    main()