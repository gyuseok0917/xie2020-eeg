#!/bin/bash

echo "========================================"
echo "[1/4] Checking/installing the osfclient Python package..."
echo "========================================"
# Install osfclient if it's not already installed.
if ! command -v osf &> /dev/null; then
    echo "osfclient is not installed. Installing via pip..."
    pip install osfclient
else
    echo "osfclient is already installed."
fi

echo ""
echo "========================================"
echo "[2/4] Safely downloading data from the OSF server one file at a time..."
echo "========================================"
# Clone the entire project structure into a temporary folder (to avoid 500 errors)
# -p ykp9w: specifies the project ID
osf -p ykp9w clone osf_temp_download

echo ""
echo "========================================"
echo "[3/4] Moving the downloaded data into the 'data' directory..."
echo "========================================"
mkdir -p data

# osfclient creates a top-level folder called 'osfstorage' by default.
# Move its contents (PreprocData, RawData, etc.) up into our desired data/ location.
if [ -d "osf_temp_download/osfstorage" ]; then
    mv osf_temp_download/osfstorage/* data/
fi

# Remove the now-unneeded temporary folder
rm -rf osf_temp_download
echo " -> Data directory cleanup complete."

echo ""
echo "========================================"
echo "[4/4] Extracting per-subject .tar files and cleaning up the originals..."
echo "========================================"

BASE_DIR="data"
DIRECTORIES=("PreprocData" "RawData")

for SUB_DIR in "${DIRECTORIES[@]}"; do
    DIR="$BASE_DIR/$SUB_DIR"
    
    if [ ! -d "$DIR" ]; then
        echo "[Warning] Directory '$DIR' not found, skipping."
        continue
    fi

    echo " -> Working inside '$DIR'..."

    for tar_file in "$DIR"/*.tar; do
        [ -e "$tar_file" ] || continue
        
        base_name=$(basename "$tar_file" .tar)
        target_dir="$DIR/$base_name"
        
        mkdir -p "$target_dir"
        
        if tar -xf "$tar_file" -C "$target_dir"; then
            echo "    [Success] Created folder $base_name and extracted -> deleted original $(basename "$tar_file")"
            rm "$tar_file"
        else
            echo "    [Failed] Error occurred while extracting $tar_file"
        fi
    done
done

echo ""
echo "========================================"
echo "😊 The entire data setup pipeline has completed successfully!"