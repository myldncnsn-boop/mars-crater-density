import pandas as pd
from pathlib import Path
from datetime import date
from pyproj import Geod
import numpy as np

# Load data
CSV_FILE = "Catalog_Mars_Release_2020_1kmPlus_FullMorphData.csv"
df = pd.read_csv(CSV_FILE, engine="python")

# Ensure essential numeric columns
num_cols = ["DIAM_CIRC_IMG", "LAT_CIRC_IMG", "LON_CIRC_IMG"]
df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")

# Assign each crater to a 5° × 5° tile (lower-left corner)
df["tile_lat"] = (df["LAT_CIRC_IMG"] // 5 * 5).astype(int)
df["tile_lon"] = (df["LON_CIRC_IMG"] // 5 * 5).astype(int)

# Output directory
OUT_DIR = Path("tiles_adaptive")
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

def circle_boundary(center_lat, center_lon, radius_km, n_vertices=72):
    """Returns (lon, lat) vertices of a circle, closed like tile_boundary."""
    az = np.linspace(0, 360, n_vertices, endpoint=False)   # directions around the circle
    lons, lats, _ = GEOD.fwd(
        np.full(n_vertices, center_lon),
        np.full(n_vertices, center_lat),
        az,
        np.full(n_vertices, radius_km * 1000),              # fwd wants meters
    )
    pts = list(zip(lons, lats))
    return pts + [pts[0]]                                   # close the polygon

def tile_area_km2(lat0: int, lon0: int) -> float:
    """Exact ellipsoidal area of the 5°×5° tile in km²."""
    lons, lats = zip(*tile_boundary(lat0, lon0)[:-1]) # four corners only
    area_m2, _ = GEOD.polygon_area_perimeter(lons, lats)
    return abs(area_m2) / 1_000_000

def circle_area_km2(center_lat, center_lon, radius_km, n_vertices=72):
    """Ellipsoidal area (km²) of a circle approximated as an n-sided polygon."""
    lons, lats = zip(*circle_boundary(center_lat, center_lon, radius_km, n_vertices)[:-1])  # drop the repeated closing point
    area_m2, _ = GEOD.polygon_area_perimeter(lons, lats)
    return abs(area_m2) / 1_000_000

def hex_grid(spacing_km=150.0, R=3389.5):
    """Approximate hexagonal grid of (lat, lon) centers over a sphere."""
    row_km = spacing_km * np.sqrt(3) / 2                 # distance between rows (~150 km)
    n_rows = int(np.ceil(np.pi * R / row_km))            # rows needed, pole to pole
    lats = np.linspace(-90, 90, n_rows + 1)              # evenly spaced rows, ends are the poles

    pts = []
    for i, lat in enumerate(lats):
        circumference = 2 * np.pi * R * np.cos(np.radians(lat))
        n = max(1, int(np.ceil(circumference / spacing_km)))   # dots in this ring (1 at a pole)
        step = 360 / n
        offset = step / 2 if i % 2 else 0                # shift every other row: honeycomb
        lons = (offset + step * np.arange(n) + 180) % 360 - 180
        pts += [(float(lat), float(lon)) for lon in lons]
    return pts

def write_circle_scc(center_lat, center_lon, radius_km, craters, out_dir=OUT_DIR, n_vertices=72):
    """Write one .scc file for a circle. `craters` = DataFrame from craters_within()."""
    area = circle_area_km2(center_lat, center_lon, radius_km, n_vertices)
    today = date.today().strftime("%d.%m.%Y")
    fname = out_dir / f"circle_lat{center_lat:+07.2f}_lon{center_lon:+08.2f}.scc"

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
        f"# Area_name1 = circle centre ({center_lat:.2f}, {center_lon:.2f}), radius {radius_km:.1f} km",
        f"# Area_size1 = {area:.11f} <km^2>",
        "#",
    ]

    bnd = [
        f"{i+1}\t1\text\t{lon:.12f}\t{lat:.12f}"
        for i, (lon, lat) in enumerate(circle_boundary(center_lat, center_lon, radius_km, n_vertices))
    ] + ["}"]

    crater_block = [
        "#",
        f"Total_area = {area:.11f} <km^2>",
        "#",
        "# crater_diameters:",
        "crater = {diam,lon,lat",
    ]

    cols = ["DIAM_CIRC_IMG", "LON_CIRC_IMG", "LAT_CIRC_IMG"]
    crater_rows = [
        "\t".join(map(str, row))
        for row in craters[cols].round(6).itertuples(index=False)
    ] + ["}"]

    fname.write_text("\n".join(header + bnd + crater_block + crater_rows), encoding="utf-8")
    return fname, area

# --- main loop ---
if __name__ == "__main__":

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
