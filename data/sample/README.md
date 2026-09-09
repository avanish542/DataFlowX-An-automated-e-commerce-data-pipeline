# Sample Data

This folder is intentionally empty in version control.

Source data for the pipeline is generated locally with:

```
python scripts/generate_data.py --scale sample   # ~7,000 rows total, fast
python scripts/generate_data.py --scale full      # ~210,000 rows total
```

Generated files are written to `data/raw/` (git-ignored) rather than
this folder, so large datasets are never committed to the repository.
