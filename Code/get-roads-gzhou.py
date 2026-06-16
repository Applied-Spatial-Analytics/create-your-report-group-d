import geopandas as gpd
import osmnx as ox
from shapely.ops import unary_union

# Geocode each district individually
districts = [
    "Huangpu District, Guangzhou, China",
    "Tianhe District, Guangzhou, China",
    "Yuexiu District, Guangzhou, China",
    "Baiyun District, Guangzhou, China",
    "Liwan District, Guangzhou, China",
    "Panyu District, Guangzhou, China",
    "Haizhu District, Guangzhou, China",
]

district_gdfs = [ox.geocode_to_gdf(d) for d in districts]

# Union all district polygons in a projected CRS, then reproject back
district_union = unary_union(
    [gdf.to_crs("EPSG:4491").geometry.iloc[0] for gdf in district_gdfs]
)

# Buffer the union by 1 000 m (still in EPSG:4491), then back to WGS 84
union_gdf = gpd.GeoDataFrame(geometry=[district_union], crs="EPSG:4491")
union_buffered_wgs84 = union_gdf.buffer(1000).to_crs("EPSG:4326").iloc[0]

G = ox.graph_from_polygon(union_buffered_wgs84, network_type="walk")

nodes, edges = ox.graph_to_gdfs(G)
nodes = nodes.to_crs("EPSG:4491")
edges = edges.to_crs("EPSG:4491")

nodes.to_file(
    "../qgis-project/network/guangzhou_roads.gpkg", layer="nodes", driver="GPKG"
)
edges.to_file(
    "../qgis-project/network/guangzhou_roads.gpkg", layer="edges", driver="GPKG"
)

print(ox.basic_stats(G))
