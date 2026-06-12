import osmnx as ox
from shapely.ops import unary_union

guangzhou = ox.geocode_to_gdf("Guangzhou, China")

guangzhou_buffered = (
    guangzhou
    .to_crs("EPSG:4491")  # CGCS2000 / 3-degree Gauss-Kruger zone 38 — covers Guangzhou
    .buffer(1000)
    .to_crs("EPSG:4326")
)

G = ox.graph_from_polygon(
    unary_union(guangzhou_buffered),
    network_type="walk"
)

nodes, edges = ox.graph_to_gdfs(G)
nodes = nodes.to_crs("EPSG:4491")
edges = edges.to_crs("EPSG:4491")

nodes.to_file("../QGIS project files/Rotterdam Network/guangzhou_roads.gpkg", layer="nodes", driver="GPKG")
edges.to_file("../QGIS project files/Rotterdam Network/guangzhou_roads.gpkg", layer="edges", driver="GPKG")

# Basic stats
print(ox.basic_stats(G))