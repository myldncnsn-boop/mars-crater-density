import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from pyproj import Geod

craters_file = "Catalog_Mars_Release_2020_1kmPlus_FullMorphData.csv"

craters_df = pd.read_csv(
    craters_file,
    usecols=["LAT_CIRC_IMG", "LON_CIRC_IMG", "DIAM_CIRC_IMG"],
)
craters_df = craters_df.dropna(subset=["LAT_CIRC_IMG", "LON_CIRC_IMG", "DIAM_CIRC_IMG"]).reset_index(drop=True)

# Mars ellipsoid (IAU-2000, km)
A_EQUAT = 3396.19
B_POLAR = 3376.20
GEOD = Geod(a=A_EQUAT*1000, b=B_POLAR*1000)   # metres -> pyproj

#convert coords to xyz for cKDTree
def lat_lon_to_xyz(lat, lon):
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)

    x = np.cos(lat_rad) * np.cos(lon_rad)
    y = np.cos(lat_rad) * np.sin(lon_rad)
    z = np.sin(lat_rad)
    return np.stack([x, y, z], axis=-1)

xyz = lat_lon_to_xyz(craters_df["LAT_CIRC_IMG"].values, craters_df["LON_CIRC_IMG"].values)

tree = cKDTree(xyz)

def craters_within(center_lat, center_lon, radius_km):
    # Stage 1: tree prefilter on the unit sphere
    center_xyz = lat_lon_to_xyz(center_lat, center_lon)
    theta = radius_km / B_POLAR
    chord = 2 * np.sin(theta / 2) * 1.02          # 1.02 = safety margin
    indices = tree.query_ball_point(center_xyz, chord)
    if len(indices) == 0:
        return craters_df.iloc[0:0]

    # Stage 2: exact geodesic distance on the Mars ellipsoid (lon first, then lat)
    cand = craters_df.iloc[indices]
    n = len(cand)
    _, _, dist_m = GEOD.inv(
        np.full(n, center_lon), np.full(n, center_lat),
        cand["LON_CIRC_IMG"].to_numpy(), cand["LAT_CIRC_IMG"].to_numpy(),
    )

    # Stage 3: keep only craters truly inside the radius
    return cand[dist_m <= radius_km * 1000]
def craters_within_bruteforce(center_lat, center_lon, radius_km):
    """Slow reference version: exact distance to every crater. Used only to verify."""
    n = len(craters_df)
    _, _, dist_m = GEOD.inv(
        np.full(n, center_lon), np.full(n, center_lat),
        craters_df["LON_CIRC_IMG"].to_numpy(), craters_df["LAT_CIRC_IMG"].to_numpy(),
    )
    return craters_df[dist_m <= radius_km * 1000]

#crater area function

R_MARS = 3389.5  # km

def loop_Area(radius_km, R=R_MARS):
    return 2 * np.pi * R**2 * (1 - np.cos(radius_km / R))

