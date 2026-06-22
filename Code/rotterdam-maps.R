# ==============================================================================
# PROJECT: Applied Spatial Analysis - Rotterdam Map Generation
# CORE TASK: Generate and Export Publication-Ready Spatial Visualizations
# ==============================================================================

library(sf)
library(ggplot2)
library(viridis)
library(scales) # For clean legend formatting

# 1. SETUP OUTPUT DIRECTORIES
# ==============================================================================
map_dir <- "../out/maps"
if (!dir.exists(map_dir)) {
  dir.create(map_dir, recursive = TRUE)
  cat("Created directory:", map_dir, "\n")
}

# 2. LOAD DATA
# ==============================================================================
gpkg_path <- "../data/rotterdam/rotterdam_wijkenbuurten_enriched.gpkg"
cat("Reading data layer 'buurten_enriched'...\n")
buurten_maps <- st_read(gpkg_path, layer = "buurten_enriched", quiet = TRUE)

# Ensure geometry type and drop empty features if they exist
buurten_maps <- buurten_maps[!st_is_empty(buurten_maps), ]

# Shared design theme elements for report styling consistency
theme_report_map <- function() {
  theme_minimal() +
    theme(
      plot.title = element_text(face = "bold", size = 14, color = "#2c3e50", margin = margin(b = 4)),
      plot.subtitle = element_text(size = 10, color = "#7f8c8d", margin = margin(b = 12)),
      legend.position = "right",
      legend.title = element_text(face = "bold", size = 9, color = "#2c3e50"),
      legend.text = element_text(size = 8, color = "#34495e"),
      panel.grid.major = element_line(color = "#f0f3f4", size = 0.5),
      panel.grid.minor = element_blank(),
      axis.text = element_text(size = 7, color = "#95a5a6")
    )
}

# ==============================================================================
# MAP 2: LAND SURFACE TEMPERATURE (LST) MAP (Continuous Temperature)
# ==============================================================================
cat("Generating Land Surface Temperature Map...\n")

map_lst <- ggplot(data = buurten_maps) +
  geom_sf(aes(fill = mean_LST_normalized), color = "#ffffff", size = 0.05) +
  scale_fill_viridis_c(
    option = "inferno",
    name = "LST (°C)",
    labels = label_number(suffix = "°C")
  ) +
  labs(
    title = "Rotterdam Land Surface Temperature Surface (LST)",
    subtitle = "Aggregated thermal baseline map at neighborhood scale",
    x = "Longitude", y = "Latitude"
  ) +
  theme_report_map()

ggsave(file.path(map_dir, "rotterdam_lst_map.png"), plot = map_lst, width = 10, height = 7, dpi = 300)

# ==============================================================================
# MAP 3: VEGETATION INDICES (NDVI) MAP (Continuous Greenness)
# ==============================================================================
cat("Generating Normalized Difference Vegetation Index Map...\n")

map_ndvi <- ggplot(data = buurten_maps) +
  geom_sf(aes(fill = mean_NDVI), color = "#ffffff", size = 0.05) +
  scale_fill_viridis_c(
    option = "mako",
    direction = -1, # Invert so higher vegetation values appear deep green/blue
    name = "Mean NDVI score"
  ) +
  labs(
    title = "Rotterdam NDVI Vegetation Index Distribution",
    subtitle = "Mean Normalized Difference Vegetation Index (NDVI) values",
    x = "Longitude", y = "Latitude"
  ) +
  theme_report_map()

ggsave(file.path(map_dir, "rotterdam_ndvi_map.png"), plot = map_ndvi, width = 10, height = 7, dpi = 300)

# ==============================================================================
# MAP 4: LOCAL CLIMATE ZONES (LCZ) MAP (Official WMO Color Scheme)
# ==============================================================================
cat("Generating Local Climate Zones Map with official WMO colors...\n")

# 1. Define the complete official WMO LCZ Lookup Table
lcz_labels <- c(
  "0"  = "No Data / Unclassified",
  "1"  = "LCZ 1: Compact High-Rise",
  "2"  = "LCZ 2: Compact Mid-Rise",
  "3"  = "LCZ 3: Compact Low-Rise",
  "4"  = "LCZ 4: Open High-Rise",
  "5"  = "LCZ 5: Open Mid-Rise",
  "6"  = "LCZ 6: Open Low-Rise",
  "7"  = "LCZ 7: Lightweight Low-Rise",
  "8"  = "LCZ 8: Large Low-Rise",
  "9"  = "LCZ 9: Sparsely Built",
  "10" = "LCZ 10: Heavy Industry",
  "11" = "LCZ A: Dense Trees",
  "12" = "LCZ B: Scattered Trees",
  "13" = "LCZ C: Bush/Scrub",
  "14" = "LCZ D: Low Plants",
  "15" = "LCZ E: Bare Rock/Paved",
  "16" = "LCZ F: Bare Soil/Sand",
  "17" = "LCZ G: Water"
)

# 2. Define the Official WMO Hex Color Palette mapping to your dataset codes
wmo_colors <- c(
  "0"  = "#222222", # Dark Gray
  "1"  = "#8a0000", # Dark Red
  "2"  = "#d10000", # Red
  "3"  = "#ff0000", # Bright Red
  "4"  = "#bf4d4d", # Muted Light Red
  "5"  = "#ff6666", # Light Pink-Red
  "6"  = "#ffb3b3", # Pale Pink
  "7"  = "#fae61c", # Lemon Yellow
  "8"  = "#bcbcbc", # Light Industrial Gray
  "9"  = "#ffcc00", # Amber/Sand
  "10" = "#555555", # Heavy Industrial Dark Gray
  "11" = "#006600", # Dark Forest Green
  "12" = "#00cc00", # Apple Green
  "13" = "#66ff33", # Light Green
  "14" = "#a6f287", # Soft Pasture Green
  "15" = "#737373", # Paved Gray
  "16" = "#f2cca6", # Beach/Sand Tan
  "17" = "#0066cc"  # Deep Water Blue
)

# 3. Ensure the column is a character vector for manual mapping
buurten_maps$majority_LCZ <- as.character(buurten_maps$majority_LCZ)

# 4. Build the map using the manual color scales
map_lcz <- ggplot(data = buurten_maps) +
  geom_sf(aes(fill = majority_LCZ), color = "#ffffff", size = 0.08) +
  scale_fill_manual(
    values = wmo_colors,
    labels = lcz_labels,
    name = "Dominant LCZ Class",
    na.value = "#d3d3d3"
  ) +
  labs(
    title = "Rotterdam Local Climate Zone Layouts (LCZ)",
    subtitle = "Standardized WMO classification scheme for urban microclimate typologies",
    x = "Longitude", y = "Latitude"
  ) +
  theme_report_map() +
  theme(
    legend.position = "right",
    legend.text = element_text(size = 9),
    legend.title = element_text(face = "bold", size = 10)
  ) +
  guides(fill = guide_legend(ncol = 1))

# 5. Save the plot
ggsave(file.path(map_dir, "rotterdam_lcz_map.png"), plot = map_lcz, width = 12, height = 7, dpi = 300)

cat("✔ LCZ map successfully saved with official WMO colors!\n")

cat("\n✔ All 3 spatial maps successfully exported to:", map_dir, "\n\n")
