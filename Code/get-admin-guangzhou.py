import geopandas as gpd
import osmnx as ox

# Fetch administrative boundaries within Guangzhou
# admin_level=6 corresponds to districts in China (区/县)
guangzhou_districts = ox.features_from_place(
    "Guangzhou, China", tags={"boundary": "administrative", "admin_level": "6"}
)

# Keep only polygon geometries (boundaries, not points/lines)
guangzhou_districts = guangzhou_districts[
    guangzhou_districts.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
].copy()

# Select useful columns if they exist
cols_to_keep = ["name", "name:en", "admin_level", "geometry"]
cols_present = [c for c in cols_to_keep if c in guangzhou_districts.columns]
guangzhou_districts = guangzhou_districts[cols_present]

# Reproject to CGCS2000 (metres) for accurate area/length calculations
guangzhou_districts_proj = guangzhou_districts.to_crs("EPSG:4491")

# Save to GeoPackage
out_path = "../qgis-project/network/guangzhou_roads.gpkg"
guangzhou_districts_proj.to_file(out_path, layer="admin_boundaries", driver="GPKG")

print(f"Saved {len(guangzhou_districts_proj)} district boundaries to {out_path}")
print(guangzhou_districts_proj[["name", "admin_level"]].to_string())
