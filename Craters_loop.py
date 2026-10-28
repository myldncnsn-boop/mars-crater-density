import pandas as pd
import numpy as np
from Craters_query import craters_within, loop_Area, R_MARS



#crater_Loop function takes in center_lat, center_lon, radius_km with default value = 100
    #step 1, run craters within with default radius, if return n >= 50, return density

def crater_loop(center_lat, center_lon, radius_km=100):
    num_Craters = craters_within(center_lat, center_lon, radius_km).shape[0]

    #stopping conditon chosen arbitratily, should choose another
    while(num_Craters < 50 and radius_km < 250):

        if num_Craters == 0:
            new_R = radius_km * 1.2
        else: 
            new_R = radius_km *(2 - num_Craters/50)
        new_R = min(new_R, 250)
            
        num_Craters = craters_within(center_lat, center_lon, new_R).shape[0]
        radius_km = new_R
    valid_area = loop_Area(radius_km)
    density = num_Craters / valid_area
    if num_Craters >= 50:
        return (density, "Sufficient Craters", radius_km, num_Craters)
    else:
        return(density, "Insufficient Craters", radius_km, num_Craters)