#!/bin/bash

input_dir="tiles_scc"
output_dir="test_southern_highlands"
mkdir -p "$output_dir"

for file in "$input_dir"/tile_lat*lon*.scc; do
    basename=$(basename "$file" .scc)

    # Extract raw lat/lon
    raw_lat=$(echo $basename | sed -E 's/.*lat([-+0-9]+)_lon.*/\1/')
    raw_lon=$(echo $basename | sed -E 's/.*lon([-+0-9]+).*/\1/')

    # Normalize (strip +, force decimal, preserve negatives)
    lat=$((10#${raw_lat#"+"""}))
    lon=$((10#${raw_lon#"+"""}))

    # Only southern highlands (≤ -30 latitude)
    if [ "$lat" -le -30 ]; then
        # Compute ranges (tiles are 5° each)
        lat_start=$lat
        lat_end=$((lat+5))
        lon_start=$lon
        lon_end=$((lon+5))

        # Format with N/S, E/W
        format_lat() {
            if [ $1 -lt 0 ]; then
                printf "%02d°S" $((-1*$1))
            else
                printf "%02d°N" $1
            fi
        }
        format_lon() {
            if [ $1 -lt 0 ]; then
                printf "%03d°W" $((-1*$1))
            else
                printf "%03d°E" $1
            fi
        }

        lat1=$(format_lat $lat_start)
        lat2=$(format_lat $lat_end)
        lon1=$(format_lon $lon_start)
        lon2=$(format_lon $lon_end)

        # Output directory name like "tile05S005E"
        lat_str=$(echo $lat1 | sed 's/°//')
        lon_str=$(echo $lon1 | sed 's/°//')
        out="${output_dir}/tile${lat_str}${lon_str}"

        # Title with ranges
        title="Differential plot|Tile ${lat1}–${lat2}, ${lon1}–${lon2}"

        echo "Processing $basename ..."

        /opt/anaconda3/envs/craterstats/bin/craterstats \
          -o "$out" \
          -title "$title" \
          -cs neukumivanov \
          -p source="$file",psym=o \
          -p type=d-fit,range=[1,5],isochron=1 \
          -p range=[2,5],colour=red \
          -f png csv
    fi
done