# Brigade Bangalore — Challenge Dataset

Bundled reference data for **STORE_BLR_002** (Brigade Road, Bangalore).

## Contents

| Path | Description |
|------|-------------|
| `CCTV Footage/CAM 1.mp4` … `CAM 5.mp4` | Five store camera clips (entry, floor, billing, skincare, makeup) |
| `Brigade_Bangalore_10_April_26 (1)bc6219c.csv` | POS transactions (10 April 2026) |
| `Brigade Road - Store layoutc5f5d56.xlsx` | Store layout reference |

## Usage

**Docker** mounts this folder at `/app/dataset` automatically.

**Local pipeline:**

```bash
cd storeiq
./pipeline/run.sh
```

**Load POS only:**

```bash
python -m pipeline.pos_loader dataset/Brigade_Bangalore_10_April_26\ \(1\)bc6219c.csv
```

## Git / GitHub

Video files total ~650 MB. For GitHub, use **Git LFS** before pushing:

```bash
git lfs install
git lfs track "dataset/CCTV Footage/*.mp4"
git add .gitattributes
```

Or attach videos as a **Release** asset if LFS is not available.
