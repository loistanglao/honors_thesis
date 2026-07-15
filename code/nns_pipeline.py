"""
NNS Data Processing Pipeline
=============================
Loads NNS survey data, cleans and aligns province labels against a
Natural Earth shapefile, then outputs a joined dataset ready for
spatial analysis.

Usage
-----
    python code/nns_pipeline.py --nns_file "data/raw/nns/nns_18_19_21/Beatrix Eloise_Tanglao_2026-03-24055951_data-set_anthrop.csv" --dict_file "data/raw/nns/nns_18_19_21/Beatrix Eloise_Tanglao_2026-03-24055951_data-dictionary_anthrop.csv" --shapefile "data/raw/ne_10m_admin_1_states_provinces/ne_10m_admin_1_states_provinces.shp" --output "data/processed/pipeline_18_19_21.csv"

All four arguments are required.
"""

import argparse
import sys
import numpy as np
import pandas as pd
import geopandas as gpd


# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------

def load_nns(nns_file: str) -> pd.DataFrame:
    """Load the NNS survey CSV."""
    print(f"[1/5] Loading NNS data from: {nns_file}")
    data = pd.read_csv(nns_file)
    print(f"      {len(data):,} rows loaded.")
    return data


def load_province_dict(dict_file: str) -> pd.DataFrame:
    """
    Load the data dictionary and extract the Province / HUC rows.
    Lines with more than the expected number of columns are skipped.
    """
    print(f"[1/5] Loading data dictionary from: {dict_file}")
    label_dict = pd.read_csv(dict_file, error_bad_lines=False, warn_bad_lines=False)
    prov_dict = label_dict[label_dict["variable_label"] == "Province and HUCs Level"].copy()
    print(f"      {len(prov_dict)} province/HUC entries found in dictionary.")
    return prov_dict


def load_shapefile(shapefile: str) -> gpd.GeoDataFrame:
    """Load the Natural Earth provinces shapefile and filter to the Philippines."""
    print(f"[1/5] Loading shapefile from: {shapefile}")
    provinces = gpd.read_file(shapefile)
    philippines = provinces[provinces["admin"] == "Philippines"].copy()
    print(f"      {len(philippines)} Philippine administrative units found.")
    return philippines


# ---------------------------------------------------------------------------
# 2. Clean province dictionary
# ---------------------------------------------------------------------------

def clean_province_dict(prov_dict: pd.DataFrame) -> pd.DataFrame:
    """Normalise province labels in the data dictionary."""
    print("[2/5] Cleaning province dictionary labels …")
    df = prov_dict.copy()

    # Lowercase
    df["value_label_lower_cleaned"] = df["value_label"].str.lower()

    # 'city of X' → 'X city'
    df["value_label_lower_cleaned"] = df["value_label_lower_cleaned"].str.replace(
        r"^city of (.+)", r"\1 city", regex=True
    )

    # Edge cases
    df["value_label_lower_cleaned"] = (
        df["value_label_lower_cleaned"]
        .str.replace("?", "n", regex=False)               # ñ approximation
        .str.replace(r"\s*\(opon\)", "", regex=True)       # remove '(opon)'
        .str.replace("western samar", "samar")
        .str.replace("baguio", "baguio city")
        .str.replace("cagayan de oro", "cagayan de oro city")
        .str.replace("north cotabato", "cotabato province")
    )

    # Convert var_value to integer for merging
    df["var_value_int"] = pd.to_numeric(df["var_value"], errors="coerce").astype("Int64")

    return df


# ---------------------------------------------------------------------------
# 3. Clean shapefile province names
# ---------------------------------------------------------------------------

def clean_shapefile(philippines: gpd.GeoDataFrame, prov_dict_cleaned: pd.DataFrame) -> gpd.GeoDataFrame:
    """Normalise province names in the shapefile to match the dictionary."""
    print("[3/5] Cleaning shapefile province names …")
    df = philippines.copy()

    # Lowercase baseline
    df["name_lower"] = df["name"].str.lower()

    # Strip 'city of ' / ' city' as a starting point, then re-add for HUCs
    df["name_lower_cleaned"] = (
        df["name_lower"]
        .str.replace(" city", "", regex=False)
        .str.replace("city of ", "", regex=False)
    )

    # Highly Urbanized Cities get ' city' suffix
    df["name_lower_cleaned"] = np.where(
        df["type"] == "Highly Urbanized City",
        df["name_lower_cleaned"] + " city",
        df["name_lower_cleaned"],
    )

    # Independent Component Cities get ' city' suffix
    df["name_lower_cleaned"] = np.where(
        df["type"] == "Independent Component City",
        df["name_lower_cleaned"] + " city",
        df["name_lower_cleaned"],
    )

    # If a province in the shapefile matches a name in the dictionary that
    # carries ' province', append ' province' to the shapefile name.
    names_with_province = set()
    for name in df["name_lower_cleaned"].unique():
        match = prov_dict_cleaned[
            prov_dict_cleaned["value_label_lower_cleaned"].str.contains(name, case=False, na=False)
            & prov_dict_cleaned["value_label_lower_cleaned"].str.contains(" province", case=False, na=False)
        ]
        if not match.empty:
            names_with_province.add(name)

    df["name_lower_cleaned"] = np.where(
        (df["type"] == "Lalawigan|Probinsya")
        & df["name_lower_cleaned"].isin(names_with_province)
        & ~df["name_lower_cleaned"].str.contains(" province", case=False, na=False),
        df["name_lower_cleaned"] + " province",
        df["name_lower_cleaned"],
    )

    # Orientation fixes
    df["name_lower_cleaned"] = (
        df["name_lower_cleaned"]
        .str.replace("mindoro oriental", "oriental mindoro", regex=False)
        .str.replace("mindoro occidental", "occidental mindoro", regex=False)
    )

    # Cotabato province fix (the province, not the city)
    df["name_lower_cleaned"] = np.where(
        (df["name_lower_cleaned"] == "cotabato") & (df["type"] == "Lalawigan|Probinsya"),
        "cotabato province",
        df["name_lower_cleaned"],
    )

    return df


# ---------------------------------------------------------------------------
# 4. Join datasets
# ---------------------------------------------------------------------------

def join_datasets(
    data: pd.DataFrame,
    prov_dict_cleaned: pd.DataFrame,
    philippines_cleaned: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    1. Merge NNS data with the province dictionary on provhuc → var_value_int.
    2. Merge the result with the shapefile on cleaned province name.
    3. Calculate BMI.
    Returns a GeoDataFrame.
    """
    print("[4/5] Joining datasets …")

    # Step 1: attach cleaned province labels to every NNS row
    data_with_prov = data.merge(
        prov_dict_cleaned[["var_value_int", "value_label_lower_cleaned"]],
        left_on="provhuc",
        right_on="var_value_int",
        how="left",
    )

    # Step 2: attach geometry from shapefile
    final_data = data_with_prov.merge(
        philippines_cleaned[["name_lower_cleaned", "geometry"]],
        left_on="value_label_lower_cleaned",
        right_on="name_lower_cleaned",
        how="left",
    )

    # Step 3: compute BMI (weight kg / height m²)
    if "weight" in final_data.columns and "height" in final_data.columns:
        final_data["bmi"] = final_data["weight"] / (final_data["height"] / 100) ** 2
    else:
        print("      WARNING: 'weight' or 'height' columns not found — BMI not calculated.")

    # Promote to GeoDataFrame
    final_gdf = gpd.GeoDataFrame(final_data, geometry="geometry")

    # Summary stats
    total = len(final_gdf)
    null_geometry_pct = final_gdf["geometry"].isna().sum() / total * 100
    print(f"      Rows in output:  {total:,}")
    print(f"      Null geometry:   {null_geometry_pct:.1f}%")
    if "bmi" in final_gdf.columns:
        null_bmi_pct = final_gdf["bmi"].isna().sum() / total * 100
        print(f"      Null BMI:        {null_bmi_pct:.1f}%")

    # Report unmatched province labels (useful for debugging)
    unmatched = final_gdf[final_gdf["geometry"].isna()]["value_label_lower_cleaned"].dropna().unique()
    if len(unmatched):
        print(f"      Province labels with no geometry match ({len(unmatched)}):")
        for label in sorted(unmatched):
            print(f"          {label}")

    return final_gdf


# ---------------------------------------------------------------------------
# 5. Export
# ---------------------------------------------------------------------------

def export(final_gdf: gpd.GeoDataFrame, output_path: str) -> None:
    """Export the joined dataset. CSV if the path ends in .csv, else GeoJSON."""
    print(f"[5/5] Exporting to: {output_path}")
    if output_path.endswith(".csv"):
        # geometry serialises to WKT in CSV
        df = final_gdf.copy()
        if "geometry" in df.columns:
            df["geometry"] = df["geometry"].apply(
                lambda g: g.wkt if g is not None else None
            )
        df.to_csv(output_path, index=False)
    else:
        final_gdf.to_file(output_path, driver="GeoJSON")
    print("      Done.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NNS data processing pipeline: clean, join NNS + province shapefile."
    )
    parser.add_argument("--nns_file",   required=True, help="Path to the NNS CSV data file.")
    parser.add_argument("--dict_file",  required=True, help="Path to the NNS data dictionary CSV.")
    parser.add_argument("--shapefile",  required=True, help="Path to the Natural Earth .shp file.")
    parser.add_argument(
        "--output",
        default="final_data.csv",
        help="Output path. Use .csv for CSV (geometry as WKT) or .geojson for GeoJSON. Default: final_data.csv",
    )
    return parser.parse_args()


def run_pipeline(nns_file: str, dict_file: str, shapefile: str, output: str) -> gpd.GeoDataFrame:
    """Run the full pipeline and return the final GeoDataFrame."""
    data           = load_nns(nns_file)
    prov_dict      = load_province_dict(dict_file)
    philippines    = load_shapefile(shapefile)

    prov_dict_clean    = clean_province_dict(prov_dict)
    philippines_clean  = clean_shapefile(philippines, prov_dict_clean)

    final_gdf = join_datasets(data, prov_dict_clean, philippines_clean)
    export(final_gdf, output)
    return final_gdf


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(
        nns_file=args.nns_file,
        dict_file=args.dict_file,
        shapefile=args.shapefile,
        output=args.output,
    )
