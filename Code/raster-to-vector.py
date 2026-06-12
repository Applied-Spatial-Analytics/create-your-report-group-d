"""
line_raster_mean.py
====================
For each linestring in a GeoPackage layer, compute the mean value of
all GeoTIFF pixels whose centres lie within a tiny buffer around the line
(default 0.5 × pixel size), i.e. every pixel the line actually crosses.

Usage
-----
    python line_raster_mean.py \
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
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import mapping
from tqdm import tqdm


# ── helpers ──────────────────────────────────────────────────────────────────

def pixel_size(transform):
    """Return (pixel_width, pixel_height) in CRS units."""
    return abs(transform.a), abs(transform.e)


def mean_under_line(geom, src, band_index=1, buffer_fraction=0.5):
    """
    Return the mean raster value for pixels touched by `geom` (a LineString).

    Strategy
    --------
    1. Buffer the line by `buffer_fraction` × pixel diagonal so that every
       pixel the line passes through is captured.
    2. Mask the raster to that buffer window.
    3. Exclude nodata and return the mean of remaining values.
    """
    px_w, px_h = pixel_size(src.transform)
    buf_dist = buffer_fraction * (px_w**2 + px_h**2) ** 0.5

    buffered = geom.buffer(buf_dist)

    # Window covering the bounding box of the buffer
    from rasterio.windows import from_bounds
    bounds = buffered.bounds          # (minx, miny, maxx, maxy)
    window = from_bounds(*bounds, transform=src.transform).round_lengths().round_offsets()

    # Clamp window to raster extent
    window = window.intersection(
        rasterio.windows.Window(0, 0, src.width, src.height)
    )
    if window.width < 1 or window.height < 1:
        return float("nan")

    win_transform = src.window_transform(window)
    data = src.read(band_index, window=window).astype(float)

    # Mask nodata
    nodata = src.nodata
    if nodata is not None:
        data[data == nodata] = np.nan

    # Mask pixels outside the buffer polygon
    msk = geometry_mask(
        [mapping(buffered)],
        transform=win_transform,
        invert=True,           # True = inside polygon
        out_shape=data.shape,
    )
    data[~msk] = np.nan

    valid = data[~np.isnan(data)]
    return float(np.mean(valid)) if len(valid) > 0 else float("nan")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Compute mean raster value under each linestring."
    )
    parser.add_argument("--raster",  required=True, help="Path to GeoTIFF")
    parser.add_argument("--vector",  required=True, help="Path to GeoPackage")
    parser.add_argument("--layer",   default=None,  help="Layer name (default: first)")
    parser.add_argument("--output",  default="results.gpkg", help="Output GeoPackage")
    parser.add_argument("--band",    type=int, default=1, help="Raster band (default: 1)")
    args = parser.parse_args()

    # ── load vector ──────────────────────────────────────────────────────────
    gdf = gpd.read_file(args.vector, layer=args.layer)
    print(f"Loaded {len(gdf)} features from '{args.vector}'"
          f"{(' / ' + args.layer) if args.layer else ''}")

    # ── open raster & reproject lines if needed ──────────────────────────────
    with rasterio.open(args.raster) as src:
        print(f"Raster CRS : {src.crs}")
        print(f"Vector CRS : {gdf.crs}")

        if gdf.crs != src.crs:
            print("CRS mismatch — reprojecting vector to raster CRS …")
            gdf = gdf.to_crs(src.crs)

        means = []
        for idx, row in tqdm(gdf.iterrows(), total=len(gdf), desc="Processing lines", unit="line"):
            geom = row.geometry
            if geom is None or geom.is_empty:
                means.append(float("nan"))
                continue
            # Handle MultiLineString by computing weighted mean over parts
            if geom.geom_type == "MultiLineString":
                parts = list(geom.geoms)
                vals = [mean_under_line(p, src, args.band) for p in parts]
                vals = [v for v in vals if not np.isnan(v)]
                means.append(float(np.mean(vals)) if vals else float("nan"))
            else:
                means.append(mean_under_line(geom, src, args.band))

    gdf["mean_ndvi"] = means

    nan_count = sum(np.isnan(m) for m in means)
    print(f"\nDone. {len(gdf) - nan_count} features have valid mean values; "
          f"{nan_count} returned NaN (outside raster or no valid pixels).")

    # ── write output ─────────────────────────────────────────────────────────
    gdf.to_file(args.output, driver="GPKG", layer="roads_LST_NDVI")
    print(f"Results written to '{args.output}' (layer: roads_LST_NDVI)")

    # Quick summary
    valid = gdf["mean_lst"].dropna()
    if len(valid):
        print(f"\nSummary of mean_raster:")
        print(f"  min  : {valid.min():.4f}")
        print(f"  mean : {valid.mean():.4f}")
        print(f"  max  : {valid.max():.4f}")


if __name__ == "__main__":
    main()