#!/bin/bash

input_dir="tiles_scc"
output_dir="run_2_tiles"
mkdir -p "$output_dir"

# Log file for tiles that fail
fail_log="${output_dir}/failed_tiles.log"
> "$fail_log"  # empty the file

# Count total tiles
total=$(find "$input_dir" -maxdepth 1 -name "tile_lat*lon*.scc" | wc -l)
echo "Found $total tiles to process."

process_tile() {
    file="$1"
    job_num="$2"
    total="$3"

    basename=$(basename "$file" .scc)

    # Extract centroid lat/lon (keep full precision from filename!)
    centroid_lat=$(echo "$basename" | sed -E 's/.*lat([-+0-9.]+)_lon.*/\1/')
    centroid_lon=$(echo "$basename" | sed -E 's/.*lon([-+0-9.]+).*/\1/')

    # Pretty strings for the plot title only (rounded degrees, N/S/E/W)
    lat_int=$(printf "%.0f" "$centroid_lat")
    lon_int=$(printf "%.0f" "$centroid_lon")

    format_lat() {
        if [ "$1" -lt 0 ]; then
            printf "%02dS" $((-1*$1))
        else
            printf "%02dN" $1
        fi
    }
    format_lon() {
        if [ "$1" -lt 0 ]; then
            printf "%03dW" $((-1*$1))
        else
            printf "%03dE" $1
        fi
    }

    lat_str=$(format_lat "$lat_int")
    lon_str=$(format_lon "$lon_int")

    # Output prefix: keep the centroided basename so we can parse it later
    out="${output_dir}/${basename}"

    # Title: cosmetic, helpful on plots
    title="Cumulative fit|Tile centered at ${lat_str}, ${lon_str}"

    echo "[$job_num/$total] Processing $basename ..."

    # Run craterstats with your cumulative-fit + resurfacing command
    if ! craterstats \
        -o "$out" \
        -title "$title" \
        -pr cumul \
        -cs neukumivanov \
        -p source="$file",psym=sq \
        -p type=c-fit,range=[1,10],resurf=1,psym=fsq \
        -f png csv
    then
        echo "$basename" >> "$fail_log"
        echo "  ❌ Tile failed: $basename (logged to $fail_log)"
    fi
}

export -f process_tile
export output_dir
export fail_log

# Run all tiles in parallel using 4 jobs
find "$input_dir" -maxdepth 1 -name "tile_lat*lon*.scc" | \
  nl -w1 -s' ' | \
  parallel -j 4 --colsep ' ' process_tile {2} {1} $total

echo "All tiles processed. Failed tiles, if any, are listed in $fail_log."
