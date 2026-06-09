# ==============================================================================
# PROJECT: Applied Spatial Analysis - Rotterdam Microclimate Clustering
# CORE TASK: Intersect Vector Layers, Process OSM Assets, and Run Gower Matrix
# ==============================================================================

library(sf)
library(tidyverse)
library(cluster)     # Handles Gower distance matrix tracking
library(factoextra)  # Required for cluster diagnostic parsing

# Bypass strict spherical topology rules to prevent OSM multi-vertex duplicate edge crashes
sf_use_s2(FALSE)

# ==============================================================================
# 1. LOAD DATASETS WITH CLEAN PATHS
# ==============================================================================
cat("\n--- STEP 1: Loading project data layers ---\n")

gpkg_path <- "data/processed/rotterdam_wijkenbuurten_enriched.gpkg"
shp_path  <- "QGIS project files/Rotterdam Shapefile/rotterdam.shp"
osm_path  <- "data/export.geojson"

if (!file.exists(gpkg_path)) stop(paste("Missing GeoPackage file at:", gpkg_path))
if (!file.exists(shp_path))  stop(paste("Missing strict Rotterdam boundary shapefile at:", shp_path))
if (!file.exists(osm_path))  stop(paste("Missing OSM GeoJSON download at:", osm_path))

buurten_all        <- st_read(gpkg_path, layer = "buurten_enriched", quiet = TRUE)
rotterdam_boundary <- st_read(shp_path, quiet = TRUE)
osm_features       <- st_read(osm_path, quiet = TRUE)

# ==============================================================================
# 2. CRS COORDINATE RE-ALIGNMENT & TOPOLOGY CLEANING (STRICT CONTAINMENT)
# ==============================================================================
cat("\n--- STEP 2: Aligning map projections & validating geometries ---\n")
target_crs <- st_crs(rotterdam_boundary)

buurten_all    <- st_transform(buurten_all, target_crs) %>% st_make_valid()
osm_features   <- st_transform(osm_features, target_crs) %>% st_make_valid()

# STRICT FIX: Use centroids to determine if a neighborhood truly belongs to Rotterdam
cat("Slicing neighborhoods down using strict centroid containment filtering...\n")
buurten_centroids <- st_centroid(buurten_all)
containment_matrix <- st_intersects(buurten_centroids, rotterdam_boundary, sparse = FALSE)

# Only keep neighborhoods whose central mass is within the boundary
buurten_rotterdam <- buurten_all[rowSums(containment_matrix) > 0, ]
cat(sprintf("-> Strictly isolated %d core urban neighborhoods. Leaks eliminated!\n", nrow(buurten_rotterdam)))
# ==============================================================================
# 3. DETECT NEIGHBORHOOD CODE COLUMN NAME CYCLICALLY
# ==============================================================================
cat("\n--- STEP 3: Scanning attribute table schema for primary keys ---\n")
available_cols <- names(buurten_rotterdam)

# Look for standard Dutch administrative designations
id_col <- case_when(
  "BU_CODE" %in% available_cols  ~ "BU_CODE",
  "bu_code" %in% available_cols  ~ "bu_code",
  "statcode" %in% available_cols ~ "statcode",
  "STATCODE" %in% available_cols ~ "STATCODE",
  TRUE                           ~ NA_character_
)

if (is.na(id_col)) {
  # Fallback to the very first column if structural patterns are missing
  id_col <- available_cols[1]
  cat(sprintf("⚠️ Warning: Standard keys not matched. Defaulting to first column: '%s'\n", id_col))
} else {
  cat(sprintf("✔ Found primary neighborhood code column identifier: '%s'\n", id_col))
}

# ==============================================================================
# 4. SPATIAL INTERSECTION WITH OSM INFRASTRUCTURE
# ==============================================================================
cat("\n--- STEP 4: Calculating blue and green infrastructure density metrics ---\n")

# Count how many individual water/park features cross into each distinct polygon boundary
buurten_rotterdam$osm_count <- lengths(st_intersects(buurten_rotterdam, osm_features))

# Calculate accurate area footprint dimensions in square kilometers
buurten_rotterdam$area_km2   <- as.numeric(st_area(buurten_rotterdam)) / 1e6
buurten_rotterdam$osm_density <- buurten_rotterdam$osm_count / buurten_rotterdam$area_km2

# ==============================================================================
# 5. GOWER MIXED-DATA CLUSTERING DEVELOPMENT (RECALIBRATED SCHEMA)
# ==============================================================================
cat("\n--- STEP 5: Executing Partitioning Around Medoids (PAM) Matrix ---\n")

# 1. Check which columns actually exist to dynamically adapt selection
actual_cols <- names(buurten_rotterdam)
lst_target <- if("mean_LST_celsius" %in% actual_cols) "mean_LST_celsius" else "mean_LST"
ndvi_target <- "mean_NDVI"

cat(sprintf("-> Mapping clustering matrix using: %s and %s\n", lst_target, ndvi_target))

# 2. Isolate target metrics cleanly
cluster_prep <- buurten_rotterdam %>%
  st_drop_geometry() %>%
  select(all_of(id_col), !!sym(lst_target), !!sym(ndvi_target)) %>%
  drop_na()

if (nrow(cluster_prep) == 0) {
  stop("Fatal Error: No rows remain after dropping NA values. Check column matching or spatial overlap!")
}

# 3. Generate Gower distances based on available spatial indicators
gower_matrix <- daisy(cluster_prep[, c(lst_target, ndvi_target)], metric = "gower")

# 4. Configure cluster groupings (Optimized for 4 microclimate profiles)
set.seed(42)
k_groups    <- 4
pam_results <- pam(gower_matrix, diss = TRUE, k = k_groups)

# 5. Append cluster assignments back onto structured data sets
cluster_prep$cluster_id <- as.factor(pam_results$clustering)

# 6. Execute join operation using dynamic keys
buurten_final <- buurten_rotterdam %>%
  inner_join(select(cluster_prep, all_of(id_col), cluster_id), by = id_col)
# ==============================================================================
# 6. GENERATE ANALYTICAL REPORT SUMMARY
# ==============================================================================
cat("\n========================================================\n")
cat("      ROTTERDAM SPATIAL CLUSTER PROFILE ANALYSIS REPORT\n")
cat("========================================================\n")

summary_table <- buurten_final %>%
  st_drop_geometry() %>%
  group_by(cluster_id) %>%
  summarise(
    Neighborhood_Count  = n(),
    Avg_Temperature_C   = round(mean(!!sym(lst_target), na.rm = TRUE), 2),
    Avg_Vegetation_NDVI = round(mean(!!sym(ndvi_target), na.rm = TRUE), 3),
    Avg_OSM_Asset_Ratio = round(mean(osm_density, na.rm = TRUE), 2)
  )

print(summary_table)

# ==============================================================================
# 7. WRITE BACK TO PROCESSED PIPELINE STORAGE
# ==============================================================================
cat("\n--- STEP 7: Exporting results into GeoPackage architecture ---\n")
st_write(buurten_final, gpkg_path, layer = "buurten_clustered", 
         delete_layer = TRUE, append = FALSE, quiet = TRUE)

cat("✔ Pipeline completed successfully! 'buurten_clustered' is ready for Quarto compilation.\n\n")