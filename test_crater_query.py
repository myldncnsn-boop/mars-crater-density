import numpy as np
from Craters_query import craters_df, GEOD, craters_within, lat_lon_to_xyz


def craters_within_bruteforce(center_lat, center_lon, radius_km):
    """Slow reference: exact distance to every crater."""
    n = len(craters_df)
    _, _, dist_m = GEOD.inv(
        np.full(n, center_lon), np.full(n, center_lat),
        craters_df["LON_CIRC_IMG"].to_numpy(), craters_df["LAT_CIRC_IMG"].to_numpy(),
    )
    return craters_df[dist_m <= radius_km * 1000]


def haversine_km(lat1, lon1, lat2, lon2, R=3389.5):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def test_fast_matches_bruteforce():
    cases = [
        (79.26, 211.91, 50), (0.0, 359.5, 100), (-30.0, 90.0, 200), (85.0, 10.0, 150),
        (79.26, 211.91, 300), (85.0, 10.0, 500), (0.0, 0.5, 400), (-60.0, 180.0, 800),
    ]
    for lat, lon, r in cases:
        fast = craters_within(lat, lon, r)
        slow = craters_within_bruteforce(lat, lon, r)
        assert set(fast.index) == set(slow.index), (lat, lon, r)


def test_boundary_cutoff():
    center_lat, center_lon = 0.0, 359.5
    n = len(craters_df)
    _, _, d_m = GEOD.inv(
        np.full(n, center_lon), np.full(n, center_lat),
        craters_df["LON_CIRC_IMG"].to_numpy(), craters_df["LAT_CIRC_IMG"].to_numpy(),
    )
    i = int(np.argmin(np.abs(d_m - 60_000)))
    d_km = d_m[i] / 1000
    assert i not in craters_within(center_lat, center_lon, d_km - 0.001).index
    assert i in craters_within(center_lat, center_lon, d_km + 0.001).index


def test_haversine_independent_check():
    res = craters_within(0.0, 359.5, 100)
    h = haversine_km(0.0, 359.5, res["LAT_CIRC_IMG"].to_numpy(), res["LON_CIRC_IMG"].to_numpy())
    assert h.max() <= 100 * 1.01          # within ~1% (sphere vs ellipsoid)
    all_h = haversine_km(0.0, 359.5, craters_df["LAT_CIRC_IMG"].to_numpy(), craters_df["LON_CIRC_IMG"].to_numpy())
    assert abs(int((all_h <= 100).sum()) - len(res)) <= 3