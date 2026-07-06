install.packages("terra")

library(terra)
library(readr)
library(sf)
library(dplyr)
library(data.table)

# ── 1. Loading NNS dataframe ──────────────────────────────────────────────
# Read raw CSV
nns_df <- read_csv("nns_analysis/final_data.csv")

# Get just the province-geometry pairs BEFORE converting to sf
# This is a tiny dataframe - only unique province rows
provinces_raw <- nns_df %>%
  filter(!is.na(geometry)) %>%
  distinct(name_lower_cleaned, geometry)

# NOW convert only this tiny dataframe to sf
nns_provinces <- st_as_sf(provinces_raw, wkt = "geometry", crs = 4326)

# ── 2. Load GAEZ suitability raster ───────────────────────────────────────────
suit <- rast("nns_analysis/suit_data/DATA_GAEZ-V5_MAPSET_RES05-SXX_GAEZ-V5.RES05-SXX.HP0120.AGERA5.HIST.YAM.LRLM.tif")

# Check CRS match (both should be EPSG:4326)
crs(suit)
crs(nns_provinces)

# ── 3. Extract mean suitability per province ───────────────────────────────────
# Convert provinces to SpatVector for terra
nns_vect <- vect(nns_provinces)

# Extract mean suitability per province
suit_extracted <- extract(suit, nns_vect, fun = mean, na.rm = TRUE)

# Add province name
suit_extracted$province <- nns_provinces$name_lower_cleaned

# rename second column in suit_extracted to "yam_suitability"
names(suit_extracted)[2] <- "yam_suitability"

# ── 4. Join NNS and suitability data ───────────────────────────────────
# join nns and suitability dataframes on province column
nns_final <- nns_df %>%
  filter(!is.na(geometry)) %>%
  left_join(
    suit_extracted %>% select(province, yam_suitability),
    by = c("name_lower_cleaned" = "province")
  )

# Sanity check: nns_final hould have same rows as nns_df minus the NA geometry rows, with a new yam_suitability column
nrow(nns_final) == sum(!is.na(nns_df$geometry))
head(nns_final %>% select(name_lower_cleaned, yam_suitability, bmi))

# ── TEMPORARY!!! Until I get access to the PSA data. Manually add ube prices per year  ───────────────────────────────────
nns_final <- nns_final %>%
  mutate(ube_price_1kg = case_when(
    enns_year == 2018 ~ 59.56,
    enns_year == 2019 ~ 56.08,
    enns_year == 2021 ~ 63.81
  ))

# save nns_final as a csv
fwrite(nns_final, "merged_dfs/merged_18_19_21.csv")

# ── 5. Make a new column to average bmi over provhuc ───────────────────────────────────

library(dplyr)

nns_final_grouped <- nns_final |>
  group_by(provhuc) |>
  mutate(bmi_by_provhuc = mean(bmi, na.rm = TRUE)) |>
  ungroup()

# save nns_final_grouped as csv
fwrite(nns_final, "merged_dfs/merged_18_19_21_grouped.csv")
