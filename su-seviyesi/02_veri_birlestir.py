"""
02_veri_birlestir.py
====================
01'in indirdigi parca JSON'lari tek bir zaman serisinde birlestirir, hocanin
gonderdigi 2025 CSV'leri ile capraz dogrular ve veriyi TANIR: yillik
istatistikler, bosluklar, en buyuk sicramalar.

Bu asamada HICBIR temizlik yapilmaz. Amac, ayiklama esiklerini veriye
bakmadan secmemek.

Cikti: data/bozyazi_ham.dat   (# yil ay gun saat dakika seviye_m, UTC)
Calistirma: python 02_veri_birlestir.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
HAM = BASE / "data" / "ham"
HOCA = BASE / "tudes_raw" / "tudes"
CIKTI = BASE / "data" / "bozyazi_ham.dat"

ADIM_DK = 15                       # olcum araligi


def yukle():
    kayit = []
    for f in sorted(HAM.glob("*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            kayit.append((r["Tarih"], r["Deger"]))
    d = pd.DataFrame(kayit, columns=["epoch_ms", "seviye"])
    d["t"] = pd.to_datetime(d.epoch_ms, unit="ms", utc=True)
    # Ayni damga birden fazla parcada gorunebilir; ilkini tut.
    d = d.drop_duplicates("t").sort_values("t").reset_index(drop=True)
    return d


def hoca_csv():
    """Hocanin gonderdigi 2025 aylik CSV'lerini okur (dogrulama icin)."""
    if not HOCA.exists():
        return None
    p = []
    for f in sorted(HOCA.glob("*.csv")):
        d = pd.read_csv(f, skiprows=6)
        d.columns = [c.strip() for c in d.columns]
        d["t"] = pd.to_datetime(d["Tarih"], utc=True, format="ISO8601")
        p.append(d[["t", "Deger"]])
    return (pd.concat(p).drop_duplicates("t").sort_values("t")
            .reset_index(drop=True))


def main():
    d = yukle()
    print("=" * 72)
    print("BOZYAZI DENIZ SEVIYESI - HAM VERI")
    print("=" * 72)
    print(f"kayit    : {len(d):,}")
    print(f"aralik   : {d.t.min()}  ->  {d.t.max()}")
    bekl = int((d.t.max() - d.t.min()).total_seconds() / 60 / ADIM_DK) + 1
    print(f"beklenen : {bekl:,}  (15 dk adim)   doluluk %{100*len(d)/bekl:.1f}")
    print(f"seviye   : min {d.seviye.min():.4f}  max {d.seviye.max():.4f}  "
          f"ort {d.seviye.mean():.4f}  medyan {d.seviye.median():.4f} m")

    # --- hocanin CSV'leri ile capraz dogrulama ---
    h = hoca_csv()
    if h is not None:
        ort = d.merge(h, on="t", how="inner")
        fark = (ort.seviye - ort.Deger).abs()
        print("\n--- hocanin 2025 CSV'leri ile capraz dogrulama ---")
        print(f"hoca kayit    : {len(h):,}")
        print(f"eslesen damga : {len(ort):,}")
        print(f"en buyuk fark : {fark.max():.6f} m")
        print(f"birebir ayni  : {(fark < 1e-9).sum():,} / {len(ort):,}")
        sadece_h = len(h) - len(ort)
        if sadece_h:
            print(f"UYARI: hocada olup bizde olmayan {sadece_h} damga")

    # --- yillik ---
    print("\n--- yillik ---")
    print(f"{'yil':>6}{'kayit':>9}{'doluluk':>9}{'min':>9}{'ort':>9}"
          f"{'max':>9}{'std':>8}")
    g = d.groupby(d.t.dt.year)
    for y, x in g:
        gun = 366 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 365
        if y == d.t.dt.year.max():
            gun = d[d.t.dt.year == y].t.dt.dayofyear.max()
        bek = gun * 96
        print(f"{y:>6}{len(x):>9,}{100*len(x)/bek:>8.1f}%{x.seviye.min():>9.3f}"
              f"{x.seviye.mean():>9.3f}{x.seviye.max():>9.3f}"
              f"{x.seviye.std():>8.3f}")

    # --- ardisik fark (sicrama) dagilimi ---
    dt_dk = d.t.diff().dt.total_seconds() / 60
    bitisik = dt_dk == ADIM_DK
    df = d.seviye.diff()[bitisik]
    print("\n--- ardisik 15 dk farki (yalniz bitisik ciftler) ---")
    for q in [50, 90, 99, 99.9, 99.99, 100]:
        print(f"  %{q:<6} |dfark| = {np.percentile(df.abs(), q):.4f} m")

    # --- bosluklar ---
    bos = d[dt_dk > ADIM_DK].copy()
    bos["sure_saat"] = dt_dk[dt_dk > ADIM_DK] / 60
    print(f"\n--- bosluklar: {len(bos)} adet ---")
    print(f"  1 gunden uzun : {(bos.sure_saat > 24).sum()}")
    print(f"  toplam kayip  : {bos.sure_saat.sum()/24:.1f} gun")
    print("  en uzun 10:")
    for _, r in bos.nlargest(10, "sure_saat").iterrows():
        print(f"    {r.t - pd.Timedelta(minutes=r.sure_saat*60)} -> {r.t}"
              f"   {r.sure_saat/24:>7.1f} gun")

    # --- en uc degerler ---
    print("\n--- en yuksek 12 olcum ---")
    for _, r in d.nlargest(12, "seviye").iterrows():
        print(f"    {r.t}   {r.seviye:.4f}")
    print("\n--- en dusuk 12 olcum ---")
    for _, r in d.nsmallest(12, "seviye").iterrows():
        print(f"    {r.t}   {r.seviye:.4f}")

    # --- yaz ---
    from ortak import yaz
    p = yaz(pd.Series(d.seviye.values, index=d.t), "bozyazi_ham.dat", [
        "Bozyazi mareograf istasyonu - deniz seviyesi (ham)",
        "kaynak: TUDES / Harita Genel Mudurlugu, istasyon id 11",
        "zaman UTC, seviye metre (istasyon yerel datumu)",
    ])
    print(f"\nyazildi: {p}  ({p.stat().st_size/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()
