# ==============================================================================
# PROJECT: Applied Spatial Analysis - Guangzhou Map Generation
# LOCATION: Code/Guangzhou/Guangzhou-graphs.R
# RUN FROM: Repository Root (asa2025-report.Rproj)
# ==============================================================================

library(sf)
library(tidyverse)
library(ggplot2)
library(viridis)
library(scales)

# ==============================================================================
# STEP 1: OUTPUT DIRECTORY VALIDATION
# ==============================================================================
map_dir <- "../out/maps"
if (!dir.exists(map_dir)) {
  dir.create(map_dir, recursive = TRUE)
}

# ==============================================================================
# STEP 2: LOAD DATA & ALIGN PROJECTIONS
# ==============================================================================
clustered_geojson_path <- "../data/guangzhou/guangzhou_admin_clustered.geojson"

if (!file.exists(clustered_geojson_path)) {
  stop("CRITICAL: Missing clustered dataset! Run Guangzhou-clustering.R first.")
}

cat("Reading Guangzhou clustered dataset...\n")
admin_maps <- st_read(clustered_geojson_path, quiet = TRUE)
admin_maps <- admin_maps[!st_is_empty(admin_maps), ]

# Enforce WGS84 to align with Earth Engine bounds
admin_maps <- st_transform(admin_maps, 4326)

land_maps <- admin_maps %>%
  filter(!is.na(cluster_id))

bbox <- st_bbox(land_maps)

# ==============================================================================
# STEP 3: SHARED THEME
# ==============================================================================
theme_report_map <- function() {
  theme_minimal() +
    theme(
      plot.title    = element_text(face = "bold", size = 14, color = "#2c3e50"),
      plot.subtitle = element_text(size = 10, color = "#7f8c8d", margin = margin(b = 10)),
      legend.title  = element_text(face = "bold", size = 9),
      legend.text   = element_text(size = 8),
      axis.text     = element_text(size = 8, color = "#bdc3c7"),
      panel.background = element_rect(fill = "#ffffff", color = NA),
      panel.grid.major = element_line(color = "#f3f4f6", linewidth = 0.4),
      panel.grid.minor = element_blank()
    )
}

stroke_weight <- 0.1

# ==============================================================================
# MAP 1: LAND SURFACE TEMPERATURE (LST)
# ==============================================================================
cat("Rendering LST Map...\n")

map_lst <- ggplot(land_maps) +
  geom_sf(aes(fill = mean_LST_celsius), color = "#ffffff", linewidth = stroke_weight) +
  scale_fill_viridis_c(option = "inferno", name = "LST (°C)") +
  coord_sf(xlim = c(bbox["xmin"], bbox["xmax"]), ylim = c(bbox["ymin"], bbox["ymax"]), datum = 4326) +
  labs(
    title    = "Guangzhou Land Surface Temperature",
    subtitle = "Landsat 8/9 Thermal Infrared Sensor (TIRS) Aggregate",
    x = "Longitude", y = "Latitude"
  ) +
  theme_report_map()

ggsave(file.path(map_dir, "guangzhou_lst_map.png"), map_lst, width = 10, height = 8, dpi = 300)

# ==============================================================================
# MAP 2: VEGETATION INDEX (NDVI)
# ==============================================================================
cat("Rendering NDVI Map...\n")

map_ndvi <- ggplot(land_maps) +
  geom_sf(aes(fill = mean_NDVI), color = "#ffffff", linewidth = stroke_weight) +
  scale_fill_viridis_c(option = "mako", direction = -1, name = "NDVI") +
  coord_sf(xlim = c(bbox["xmin"], bbox["xmax"]), ylim = c(bbox["ymin"], bbox["ymax"]), datum = 4326) +
  labs(
    title    = "Guangzhou Vegetation Index (NDVI)",
    subtitle = "Landsat 8/9 Operational Land Imager (OLI) Greenness Matrix",
    x = "Longitude", y = "Latitude"
  ) +
  theme_report_map()

ggsave(file.path(map_dir, "guangzhou_ndvi_map.png"), map_ndvi, width = 10, height = 8, dpi = 300)

# ==============================================================================
# MAP 3: LOCAL CLIMATE ZONES (LCZ)
# ==============================================================================
cat("Rendering LCZ Map...\n")

lcz_labels <- c(
  "1"  = "LCZ 1: Compact High-Rise",    "2"  = "LCZ 2: Compact Mid-Rise",
  "3"  = "LCZ 3: Compact Low-Rise",     "4"  = "LCZ 4: Open High-Rise",
  "5"  = "LCZ 5: Open Mid-Rise",        "6"  = "LCZ 6: Open Low-Rise",
  "7"  = "LCZ 7: Lightweight Low-Rise", "8"  = "LCZ 8: Large Low-Rise",
  "9"  = "LCZ 9: Sparsely Built",       "10" = "LCZ 10: Industry",
  "11" = "LCZ 11: Dense Trees (A)",     "12" = "LCZ 12: Scattered Trees (B)",
  "13" = "LCZ 13: Scrub (C)",           "14" = "LCZ 14: Low Plants (D)",
  "15" = "LCZ 15: Bare/Paved (E)",      "16" = "LCZ 16: Soil (F)",
  "17" = "LCZ G: Water"
)

wmo_colors <- c(
  "1"  = "#8a0000", "2"  = "#d10000", "3"  = "#ff0000",
  "4"  = "#bf4d00", "5"  = "#ff6600", "6"  = "#ff9955",
  "7"  = "#fae61c", "8"  = "#bcbcbc", "9"  = "#ffccaa",
  "10" = "#555555", "11" = "#006600", "12" = "#00cc00",
  "13" = "#66ff33", "14" = "#a6f287", "15" = "#737373",
  "16" = "#f2cca6", "17" = "#0066cc"
)

# Parse fractional labels (e.g. 17.0) into clean integer strings for lookup
land_maps <- land_maps %>%
  mutate(majority_LCZ = as.character(round(as.numeric(majority_LCZ))))

map_lcz <- ggplot(land_maps) +
  geom_sf(aes(fill = majority_LCZ), color = "#ffffff", linewidth = stroke_weight) +
  scale_fill_manual(
    values = wmo_colors,
    labels = lcz_labels,
    name   = "WUDAPT Morphology Class",
    na.value = "#dcdcdc",
    guide  = guide_legend(ncol = 2)
  ) +
  coord_sf(xlim = c(bbox["xmin"], bbox["xmax"]), ylim = c(bbox["ymin"], bbox["ymax"]), datum = 4326) +
  labs(
    title    = "Guangzhou Local Climate Zones",
    subtitle = "RUBCLIM Morphological Urban Layout Baseline",
    x = "Longitude", y = "Latitude"
  ) +
  theme_report_map() +
  theme(legend.position = "bottom")

ggsave(file.path(map_dir, "guangzhou_lcz_map.png"), map_lcz, width = 12, height = 9, dpi = 300)

cat("\nAll 3 maps exported to:", map_dir, "\n\n")