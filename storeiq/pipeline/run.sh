#!/bin/bash
# StoreIQ Pipeline Runner
# Processes all 5 Brigade Bangalore CCTV clips for STORE_BLR_002.
# Run from the storeiq/ directory: ./pipeline/run.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATASET_DIR="${DATASET_DIR:-$PROJECT_ROOT/dataset}"
FOOTAGE_DIR="$DATASET_DIR/CCTV Footage"

export STORE_ID="STORE_BLR_002"
export ZONE_CONFIG_PATH="$PROJECT_ROOT/pipeline/zone_config.json"
export USE_MOCK_DETECTION="${USE_MOCK_DETECTION:-false}"

declare -A CAMERAS=(
    ["CAM 1.mp4"]="CAM_ENTRY_01"
    ["CAM 2.mp4"]="CAM_FLOOR_02"
    ["CAM 3.mp4"]="CAM_BILLING_03"
    ["CAM 4.mp4"]="CAM_SKINCARE_04"
    ["CAM 5.mp4"]="CAM_MAKEUP_05"
)

echo "Running StoreIQ Pipeline for $STORE_ID"
echo "Dataset directory: $DATASET_DIR"
echo "--------------------------------------"

cd "$PROJECT_ROOT"

for clip in "CAM 1.mp4" "CAM 2.mp4" "CAM 3.mp4" "CAM 4.mp4" "CAM 5.mp4"
do
    clip_path="$FOOTAGE_DIR/$clip"
    cam_id="${CAMERAS[$clip]}"
    if [ -f "$clip_path" ]; then
        echo "Processing $clip as $cam_id..."
        export CAMERA_SOURCES="${cam_id}=${clip_path}"
        python -m pipeline.run_pipeline
    else
        echo "Warning: Clip not found at $clip_path"
    fi
done

echo "Pipeline execution completed."
