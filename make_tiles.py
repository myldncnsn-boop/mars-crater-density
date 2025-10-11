import pandas as pd
from pathlib import Path
from datetime import date
from pyproj import Geod

# Load data
CSV_FILE = "/Users/jessica/Documents/EPSS/MARS_CRATER_DENSITY/Catalog_Mars_Release_2020_1kmPlus_FullMorphData.csv"
df = pd.read_csv(CSV_FILE, engine="python")

# Ensure essential numeric columns
num_cols = ["DIAM_CIRC_IMG", "LAT_CIRC_IMG", "LON_CIRC_IMG"]
df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")

# Assign each crater to a 5° × 5° tile (lower-left corner)
df["tile_lat"] = (df["LAT_CIRC_IMG"] // 5 * 5).astype(int)
df["tile_lon"] = (df["LON_CIRC_IMG"] // 5 * 5).astype(int)

# Output directory
OUT_DIR = Path("tiles_scc")
OUT_DIR.mkdir(exist_ok=True)

# Mars ellipsoid (IAU-2000, km)
A_EQUAT = 3396.19
B_POLAR = 3376.20
GEOD = Geod(a=A_EQUAT*1000, b=B_POLAR*1000)   # metres -> pyproj

# --- helper functions ---

def tile_boundary(lat0: int, lon0: int):
    """Returns the five (lon,lat) vertices that close the square tile."""
    return [
        (lon0,     lat0),
        (lon0+5,   lat0),
        (lon0+5,   lat0+5),
        (lon0,     lat0+5),
        (lon0,     lat0) # close polygon
    ]

def tile_area_km2(lat0: int, lon0: int) -> float:
    """Exact ellipsoidal area of the 5°×5° tile in km²."""
    lons, lats = zip(*tile_boundary(lat0, lon0)[:-1]) # four corners only
    area_m2, _ = GEOD.polygon_area_perimeter(lons, lats)
    return abs(area_m2) / 1_000_000

# --- main loop ---

today = date.today().strftime("%d.%m.%Y")

for (lat0, lon0), tile in df.groupby(["tile_lat", "tile_lon"]):
    area = tile_area_km2(lat0, lon0)

    # centroid
    lat_c = lat0 + 2.5
    lon_c = lon0 + 2.5

    # filename with centroid coordinates
    fname = OUT_DIR / f"tile_lat{lat_c:+07.2f}_lon{lon_c:+08.2f}.scc"

    # ---- header ---------------------------------------------------
    header = [
        "# Spatial crater count",
        "#",
        f"# Date of measurement = {today}",
        "#",
        "# Ellipsoid axes:",
        f"a_axis_radius = {A_EQUAT:.2f} <km>",
        f"b_axis_radius = {B_POLAR:.2f} <km>",
        f"c_axis_radius = {B_POLAR:.2f} <km>",
        "coordinate_system_name = planetocentric",
        "#",
        "# area_shapes:",
        "unit_boundary = {vertex,sub_area,tag,lon,lat",
        "#",
        f"# Area_name1 = tile centroid ({lat_c:.2f}, {lon_c:.2f})",
        f"# Area_size1 = {area:.11f} <km^2>",
        "#",
    ]

    # ---- polygon vertices ----------------------------------------
    bnd = [
        f"{i+1}\t1\text\t{lon:.12f}\t{lat:.12f}"
        for i, (lon, lat) in enumerate(tile_boundary(lat0, lon0))
    ] + ["}"]

    # ---- crater diameters section --------------------------------
    crater_block = [
        "#",
        f"Total_area = {area:.11f} <km^2>",
        "#",
        "# crater_diameters:",
        "crater = {diam,lon,lat"
    ]

    crater_rows = (
        tile[["DIAM_CIRC_IMG", "LON_CIRC_IMG", "LAT_CIRC_IMG"]]
        .round(6)
        .astype(str)
        .agg("\t".join, axis=1)
        .tolist()
        + ["}"]
    )

    # ---- write file ----------------------------------------------
    fname.write_text(
        "\n".join(header + bnd + crater_block + crater_rows),
        encoding="utf-8"
    )

    print(f"✓ {fname.name:45s}  ({len(tile):4d} craters,  area {area:8.1f} km²)")

print(f"\nAll tiles written to {OUT_DIR.resolve()}")
