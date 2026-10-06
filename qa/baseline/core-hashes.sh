#!/bin/sh
# Prints sha256 of the core results and the core caches (concatenated files, sorted by path).
# Run from the repo root; compare with core-hashes.txt. Any difference means the core changed.
shasum -a 256 data/results/regret.parquet tests/fixture_results/regret.parquet
for d in data/cache/era5.zarr data/cache/hres.zarr data/cache/graphcast.zarr data/cache/pangu.zarr \
         tests/fixtures/era5.zarr tests/fixtures/hres.zarr tests/fixtures/graphcast.zarr tests/fixtures/pangu.zarr; do
  printf "%s  %s\n" "$(find "$d" -type f | sort | xargs cat | shasum -a 256 | cut -c1-64)" "$d"
done
