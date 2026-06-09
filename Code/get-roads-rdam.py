import osmnx as ox

G = ox.graph_from_place("Rotterdam, Netherlands", network_type="walk")

# Save to file
ox.save_graphml(G, "../QGIS project files/Rotterdam Network/rotterdam_roads.graphml")

# Or as GeoPackage for use in QGIS etc.
ox.save_graph_geopackage(G, filepath="../QGIS project files/Rotterdam Network/rotterdam_roads.gpkg")

# Basic stats
print(ox.basic_stats(G))