import numpy as np
import pandas as pd
from Craters_query import craters_within, loop_Area, R_MARS
from Craters_loop import crater_loop
import Craters_loop, inspect
print(Craters_loop.__file__)
print(inspect.getsource(Craters_loop.crater_loop)[-400:])

rng = np.random.default_rng(0)
N = 500
lons = rng.uniform(-180, 180, N)
lats = np.degrees(np.arcsin(rng.uniform(-1, 1, N)))

df = pd.DataFrame([crater_loop(la, lo) for la, lo in zip(lats, lons)],
                  columns=["density", "label", "radius_km", "n"])

df["hit_max"] = df.radius_km >= 250
df["overshoot_ratio"] = df.n / 50
df["grew"] = df.radius_km > 100
df["over"] = df.n > 75

print("never grew:", (~df.grew).mean())
print("never grew AND over 75:", ((~df.grew) & df.over).mean())
print("grew AND over 75:", (df.grew & df.over).mean())
print("over rate among points that grew:", df[df.grew].over.mean())

print("hit max radius:", df.hit_max.mean())
print("hit max AND insufficient:", (df.hit_max & (df.label == "Insufficient Craters")).mean())
print("would need step-back:", ((df.n > 75) & (df.label == "Sufficient Craters")).mean())