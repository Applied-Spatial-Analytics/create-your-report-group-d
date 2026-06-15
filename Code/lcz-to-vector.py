"""
line_raster_start.py
====================
For each linestring in a GeoPackage layer, sample the raster value at
the start point (first coordinate) of the line.

Usage
-----
    python lcz-to-vector.py \
        --raster  path/to/file.tif \
        --vector  path/to/file.gpkg \
        --layer   your_layer_name \       # optional, defaults to first layer
        --output  results.gpkg            # optional, defaults to results.gpkg
        --band    1                        # optional, raster band (default 1)

Dependencies
------------
    pip install rasterio geopandas shapely numpy tqdm
"""

import argparse

import geopandas as gpd
import numpy as np
import rasterio
from tqdm import tqdm

# ── helpers ──────────────────────────────────────────────────────────────────


def sample_at_point(x, y, src, band_index=1):
    """
    Return the raster value at the given (x, y) coordinate.

    Returns NaN if the point falls outside the raster extent or on a nodata cell.
    """
    # Convert coordinates to row/col indices
    row, col = src.index(x, y)

    # Bounds check
    if not (0 <= row < src.height and 0 <= col < src.width):
        return float("nan")

    value = src.read(band_index, window=rasterio.windows.Window(col, row, 1, 1))[0, 0]

    nodata = src.nodata
    if nodata is not None and value == nodata:
        return float("nan")

    return float(value)


def start_point_value(geom, src, band_index=1):
    """
    Return the raster value at the first coordinate of a LineString.
    For MultiLineStrings, uses the start point of the first part.
    """
    if geom.geom_type == "MultiLineString":
        geom = list(geom.geoms)[0]

    x, y = geom.coords[0]
    return sample_at_point(x, y, src, band_index)


# ── main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Sample raster value at the start point of each linestring."
    )
    parser.add_argument("--raster", required=True, help="Path to GeoTIFF")
    parser.add_argument("--vector", required=True, help="Path to GeoPackage")
    parser.add_argument("--layer", default=None, help="Layer name (default: first)")
    parser.add_argument("--output", default="results.gpkg", help="Output GeoPackage")
    parser.add_argument("--band", type=int, default=1, help="Raster band (default: 1)")
    args = parser.parse_args()

    # ── load vector ──────────────────────────────────────────────────────────
    gdf = gpd.read_file(args.vector, layer=args.layer)
    print(
        f"Loaded {len(gdf)} features from '{args.vector}'"
        f"{(' / ' + args.layer) if args.layer else ''}"
    )

    # ── open raster & reproject lines if needed ──────────────────────────────
    with rasterio.open(args.raster) as src:
        print(f"Raster CRS : {src.crs}")
        print(f"Vector CRS : {gdf.crs}")

        if gdf.crs != src.crs:
            print("CRS mismatch — reprojecting vector to raster CRS …")
            gdf = gdf.to_crs(src.crs)

        values = []
        for idx, row in tqdm(
            gdf.iterrows(), total=len(gdf), desc="Sampling start points", unit="line"
        ):
            geom = row.geometry
            if geom is None or geom.is_empty:
                values.append(float("nan"))
                continue
            values.append(start_point_value(geom, src, args.band))

    gdf["lcz"] = values

    nan_count = sum(np.isnan(v) for v in values)
    print(
        f"\nDone. {len(gdf) - nan_count} features have valid values; "
        f"{nan_count} returned NaN (outside raster or nodata)."
    )

    # ── write output ─────────────────────────────────────────────────────────
    gdf.to_file(args.output, driver="GPKG", layer="roads_clustered")
    print(f"Results written to '{args.output}' (layer: roads_clustered)")

    # Quick summary
    valid = gdf["lcz"].dropna()
    if len(valid):
        print(f"\nSummary of start-point raster values:")
        print(f"  min  : {valid.min():.4f}")
        print(f"  mean : {valid.mean():.4f}")
        print(f"  max  : {valid.max():.4f}")


if __name__ == "__main__":
    main()
