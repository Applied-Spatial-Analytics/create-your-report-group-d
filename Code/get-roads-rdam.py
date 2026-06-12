import osmnx as ox
from shapely.ops import unary_union

# Get the Rotterdam boundary
rotterdam = ox.geocode_to_gdf("Rotterdam, Netherlands")

# Reproject to Dutch RD New, buffer 1000m, reproject back
rotterdam_buffered = (
    rotterdam
    .to_crs("EPSG:28992")
    .buffer(2000)
    .to_crs("EPSG:4326")
)

# Query using the buffered polygon
G = ox.graph_from_polygon(
    unary_union(rotterdam_buffered),
    network_type="walk"
)

nodes, edges = ox.graph_to_gdfs(G)
nodes = nodes.to_crs("EPSG:28992")
edges = edges.to_crs("EPSG:28992")

# Save to file
ox.save_graphml(G, "../QGIS project files/Rotterdam Network/rotterdam_roads.graphml")

# Save manually using geopandas
nodes.to_file("../QGIS project files/Rotterdam Network/rotterdam_roads.gpkg", layer="nodes", driver="GPKG")
edges.to_file("../QGIS project files/Rotterdam Network/rotterdam_roads.gpkg", layer="edges", driver="GPKG")

# Or as GeoPackage for use in QGIS etc.
# ox.save_graph_geopackage(G, filepath="../QGIS project files/Rotterdam Network/rotterdam_roads.gpkg")

# Basic stats
print(ox.basic_stats(G))