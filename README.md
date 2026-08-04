# marine_analysis

> Sea level analysis from Turkish tide gauge records: tidal harmonics, standard tidal datums and the non-tidal residual.

<!-- badges -->
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=for-the-badge&logo=jupyter&logoColor=white)

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/adzetto/marine_analysis/blob/main/su-seviyesi/colab_baslat.ipynb)

![last commit](https://img.shields.io/github/last-commit/adzetto/marine_analysis?style=flat-square&color=informational) ![repo size](https://img.shields.io/github/repo-size/adzetto/marine_analysis?style=flat-square&color=informational) ![top language](https://img.shields.io/github/languages/top/adzetto/marine_analysis?style=flat-square)

---

## What this is

Sea level analysis built on tide gauge records from **TUDES**, the Turkish
national sea level monitoring network run by the General Directorate of Mapping.

The current study takes the **Bozyazı** station on the Levantine coast of the
eastern Mediterranean (36.104° N, 32.948° E) and separates its 15-minute record
into tidal and non-tidal components.

Everything lives under [`su-seviyesi/`](su-seviyesi/), which has its own detailed
README in Turkish covering the method, the analysis window and the validation.

## The pipeline

The scripts are numbered because the order matters — each one consumes what the
previous produced:

| Step | Script | What it does |
|---|---|---|
| 01 | `01_tudes_indir.py` | Download the level record from the TUDES portal |
| 02 | `02_veri_birlestir.py` | Merge the downloaded pieces |
| 03 | `03_veri_ayikla.py` | Screen out bad measurements: spikes, constant blocks, stuck sensors |
| 04 | `04_ayiklama_dogrula.py` | Verify that the screening did what it claims |
| 05 | `05_harmonik_analiz.py` | Harmonic analysis — amplitude and phase of each tidal constituent |
| 06 | `06_gelgit_seviyeleri.py` | Standard tidal datums: HAT, MHWS, MHHW, MHW, MHWN, MSL, MLWN, MLW, MLLW, MLWS, LAT |
| 07 | `07_non_tidal.py` | The non-tidal residual: distribution, PDF/CDF, exceedance |
| 08–14 | station comparison, range diagnosis, Excel export, multi-station validation | |

`00_hepsini_calistir.py` runs the whole chain.

## Analysis window

**01.07.2009 – 13.03.2018**, 8.7 years.

The end date matches a published study exactly so the results can be compared
against it directly. The start date could not: the paper begins in January 2009
but the portal record only starts in July, so the first six months do not exist
to be analysed. That gap is a property of the archive, not a choice.

## Running it

The fastest route is Colab — the badge above opens the notebook directly. Switch
to a **high-RAM** runtime before running; the full record does not fit in the
default one.

Locally:

```bash
cd su-seviyesi
python 00_hepsini_calistir.py
```

Processed data is committed as gzipped `.dat` files under `su-seviyesi/data/`,
so the analysis steps can be re-run without downloading the raw record again.

## Why separate the tide from the residual

The tidal part is deterministic: given the constituents, it can be predicted
decades ahead. The residual is not — it carries storm surge, atmospheric
pressure and the trend. Coastal design needs both, and it needs them apart,
because only one of them can be extrapolated with confidence.
