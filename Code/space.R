# Read the freshly generated space syntax layer
buurten_final <- st_read("data/processed/rotterdam_wijkenbuurten_enriched.gpkg", 
                         layer = "buurten_clustered")

# Generate your final presentation summary table
summary_table <- buurten_final %>%
  st_drop_geometry() %>%
  group_by(cluster_id) %>%
  summarise(
    Neighborhood_Count     = n(),
    Avg_Temperature_C      = round(mean(mean_LST, na.rm = TRUE), 2),
    Avg_Vegetation_NDVI    = round(mean(mean_NDVI, na.rm = TRUE), 3),
    Avg_PST_Accessibility  = round(mean(pst_accessibility_score, na.rm = TRUE), 2) # New Space Syntax Metric!
  )

print(summary_table)