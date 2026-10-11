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

tests = [
    (79.26, 211.91, 50),    # near the first catalog row, high latitude
    (0.0, 359.5, 100),      # near the 0/360 seam, equator
    (-30.0, 90.0, 200),     # mid-latitude, larger radius
    (85.0, 10.0, 150),      # near the pole
]

for lat, lon, r in tests:
    fast = craters_within(lat, lon, r)
    slow = craters_within_bruteforce(lat, lon, r)
    same = set(fast.index) == set(slow.index)
    print(lat, lon, r, len(fast), len(slow), same)

big_tests = [
    (79.26, 211.91, 300),
    (85.0, 10.0, 500),
    (0.0, 0.5, 400),      # straddles the 0/360 seam
    (-60.0, 180.0, 800),
]
print("\nLarger radii:")
for lat, lon, r in big_tests:
    fast = craters_within(lat, lon, r)
    slow = craters_within_bruteforce(lat, lon, r)
    print(lat, lon, r, len(fast), len(slow), set(fast.index) == set(slow.index))

# ---------- Test 3: boundary test (is the cutoff exactly at radius_km?) ----------
# Take a center, find the crater nearest to a target distance, then set the radius
# 1 m above and 1 m below that crater's true distance. It must flip from excluded to included.
center_lat, center_lon = 0.0, 359.5
n = len(craters_df)
_, _, d_m = GEOD.inv(
    np.full(n, center_lon), np.full(n, center_lat),
    craters_df["LON_CIRC_IMG"].to_numpy(), craters_df["LAT_CIRC_IMG"].to_numpy(),
)
i = int(np.argmin(np.abs(d_m - 60_000)))      # crater closest to 60 km away
d_km = d_m[i] / 1000
just_below = craters_within(center_lat, center_lon, d_km - 0.001)   # radius 1 m too small
just_above = craters_within(center_lat, center_lon, d_km + 0.001)   # radius 1 m too big
print("\nBoundary test:")
print("crater", i, "is", round(d_km, 3), "km away")
print("excluded when radius is just below:", i not in just_below.index)
print("included when radius is just above:", i in just_above.index)


# ---------- Test 4: independent hand check (haversine, no pyproj) ----------
# Plain spherical great-circle formula, written separately from GEOD.inv.
def haversine_km(lat1, lon1, lat2, lon2, R=3389.5):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))

res = craters_within(0.0, 359.5, 100)
h = haversine_km(0.0, 359.5, res["LAT_CIRC_IMG"].to_numpy(), res["LON_CIRC_IMG"].to_numpy())
print("\nHaversine check on the 100 km result:")
print("max haversine distance among returned craters:", round(h.max(), 2), "km (should be ~100 or less)")

all_h = haversine_km(0.0, 359.5, craters_df["LAT_CIRC_IMG"].to_numpy(), craters_df["LON_CIRC_IMG"].to_numpy())
print("craters within 100 km by haversine:", int((all_h <= 100).sum()), "vs function:", len(res), "(should be close, not necessarily equal)")