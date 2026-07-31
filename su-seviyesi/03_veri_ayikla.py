"""
03_veri_ayikla.py
=================
Ham seviye kaydindan hatali olcumleri ayiklar, MSL'i hesaplar ve harmonik
analize hazir seriyi yazar.

Neden katmanli
--------------
Kayitta birbirinden farkli iki bozulma tipi var ve tek bir olcut ikisini
birden yakalamiyor:

  * TEKIL SIVRI (spike): bir-iki olcumluk ani sicrama. Hocanin gonderdigi
    Eylul 2025 grafigindeki 3.57 m'lik cizgi boyle. Kisa pencereli medyan
    bunu keskin biçimde ele verir.
  * SUREKLI BLOK: saatler-gunler suren kaymis kayit. 27 Nisan 2024'te seviye
    saatlerce ~328 m okumus. Kisa pencereli medyan bunu YAKALAYAMAZ, cunku
    medyanin kendisi de bloga kayar. Bunun icin uzun pencere gerekiyor.

Bu yuzden esikler sirayla uygulanir ve her katmanin ne kadar sildigi
raporlanir.

Esiklerin dayanagi
------------------
2010-2019 arasi saglam donemde seviye 0.85-2.29 m bandinda, yillik standart
sapma 0.12-0.15 m. Yani gercek fiziksel degisim ~+-0.5 m mertebesinde.
Asagidaki esikler bu bandin cok uzagina konuldu ki gercek firtina
kabarmalari silinmesin.

Makale (Ozturk & Yuksel 2023) da ayni yolu izlemis: "The series of
observations were carefully checked by eliminating shifts and spikes. Short
gaps (shorter than 1 day) were interpolated."

Calistirma: python 03_veri_ayikla.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
GIRDI = BASE / "data" / "bozyazi_ham.dat"
CIKTI = BASE / "data" / "bozyazi_temiz.dat"
RAPOR = BASE / "tables" / "00_ayiklama_raporu.txt"

ADIM = "15min"

# --- esikler ---
MUTLAK_BANT = 2.00     # m; genel medyandan bu kadar sapan olcum fiziksel degil
KISA_PENCERE = 9       # olcum (~2 saat); tekil sivri yakalama
KISA_ESIK = 0.10       # m; kisa pencere medyanindan sapma siniri
KISA_SIGMA = 10.0      # ya da bu kadar robust sigma (hangisi buyukse)
UZUN_PENCERE = 2881    # olcum (~30 gun); surekli blok/kayma yakalama
UZUN_ESIK = 0.80       # m
DUZ_KOSU = 12          # ayni deger bu kadar ust uste -> sensor takilmis (3 saat)
INTERP_SINIR = 96      # 1 gunden kisa bosluk doldurulur (makaledeki kural)


def oku(p):
    d = pd.read_csv(p, sep=r"\s+", comment="#", header=None,
                    names=["yil", "ay", "gun", "saat", "dk", "seviye"])
    t = pd.to_datetime(d[["yil", "ay", "gun", "saat", "dk"]].rename(columns={
        "yil": "year", "ay": "month", "gun": "day",
        "saat": "hour", "dk": "minute"}), utc=True)
    return pd.Series(d.seviye.values, index=t, name="seviye")


def robust_sigma(x):
    x = x[np.isfinite(x)]
    return 1.4826 * np.median(np.abs(x - np.median(x))) if len(x) else np.nan


def main():
    s = oku(GIRDI)
    # Tam 15 dk izgarasina otur; eksikler NaN olur.
    tam = pd.date_range(s.index.min(), s.index.max(), freq=ADIM, tz="UTC")
    s = s.reindex(tam)
    n0 = int(s.notna().sum())

    satir = []

    def kayit(baslik, maske):
        n = int(maske.sum())
        satir.append((baslik, n))
        print(f"  {baslik:<46}{n:>8,} olcum")
        return n

    print("=" * 74)
    print("AYIKLAMA")
    print("=" * 74)
    print(f"izgara   : {len(tam):,} adim   dolu {n0:,}   "
          f"bos {len(tam)-n0:,}")
    print(f"baslangic: min {s.min():.3f}  max {s.max():.3f} m\n")

    # --- katman 1: mutlak fiziksel bant ---
    med = s.median()
    m1 = (s - med).abs() > MUTLAK_BANT
    kayit(f"1) |x - medyan| > {MUTLAK_BANT} m", m1)
    s[m1] = np.nan

    # --- katman 2: surekli blok / kayma (uzun pencere) ---
    uzun = s.rolling(UZUN_PENCERE, center=True, min_periods=200).median()
    m2 = (s - uzun).abs() > UZUN_ESIK
    kayit(f"2) 30 gun medyanindan > {UZUN_ESIK} m sapma", m2)
    s[m2] = np.nan

    # --- katman 3: tekil sivri (kisa pencere), iki gecis ---
    for gecis in (1, 2):
        kisa = s.rolling(KISA_PENCERE, center=True, min_periods=5).median()
        art = s - kisa
        sg = robust_sigma(art.values)
        esik = max(KISA_ESIK, KISA_SIGMA * sg)
        m3 = art.abs() > esik
        kayit(f"3.{gecis}) kisa medyandan sapma > {esik:.3f} m "
              f"(robust sigma {sg:.4f})", m3)
        s[m3] = np.nan

    # --- katman 4: takilmis sensor (ayni deger ust uste) ---
    v = s.copy()
    grup = (v != v.shift()).cumsum()
    uzunluk = v.groupby(grup).transform("size")
    m4 = v.notna() & (uzunluk >= DUZ_KOSU)
    kayit(f"4) ayni deger {DUZ_KOSU}+ kez ust uste (takilma)", m4)
    s[m4] = np.nan

    atilan = n0 - int(s.notna().sum())
    print("-" * 74)
    print(f"  {'TOPLAM ATILAN':<46}{atilan:>8,} olcum  "
          f"(ham verinin %{100*atilan/n0:.3f}'u)")
    print(f"  {'KALAN':<46}{int(s.notna().sum()):>8,} olcum")
    print(f"\nayiklama sonrasi: min {s.min():.3f}  max {s.max():.3f}  "
          f"ort {s.mean():.4f}  std {s.std():.4f} m")

    # --- 1 gunden kisa bosluklari doldur ---
    dolu_once = int(s.notna().sum())
    s_i = s.interpolate(method="time", limit=INTERP_SINIR, limit_area="inside")
    eklenen = int(s_i.notna().sum()) - dolu_once
    print(f"\n1 gunden kisa bosluklar dolduruldu: +{eklenen:,} olcum")
    print(f"analize giren toplam              : {int(s_i.notna().sum()):,}")

    # --- MSL ---
    print("\n" + "=" * 74)
    print("ORTALAMA DENIZ SEVIYESI (MSL)")
    print("=" * 74)
    donemler = {
        "tum kayit  2010-2026": (2010, 2026),
        "temiz on yil  2010-2019": (2010, 2019),
        "makale penceresi 2010-2018": (2010, 2018),
        "son bes yil  2021-2025": (2021, 2025),
    }
    msl = {}
    for ad, (a, b) in donemler.items():
        x = s_i[(s_i.index.year >= a) & (s_i.index.year <= b)]
        msl[ad] = x.mean()
        print(f"  {ad:<30} MSL = {x.mean():.4f} m   "
              f"(n={int(x.notna().sum()):,}, std {x.std():.4f})")

    print("\n  yillik ortalama:")
    yil_ort = s_i.groupby(s_i.index.year).mean()
    for y, v_ in yil_ort.items():
        print(f"    {y}  {v_:.4f}")

    # --- yaz ---
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    RAPOR.parent.mkdir(parents=True, exist_ok=True)
    d = s_i.dropna()
    with open(CIKTI, "w", encoding="utf-8") as f:
        f.write("# Bozyazi mareograf - AYIKLANMIS deniz seviyesi\n")
        f.write("# kaynak: TUDES / Harita Genel Mudurlugu, istasyon id 11\n")
        f.write("# zaman UTC, seviye metre (istasyon yerel datumu)\n")
        f.write(f"# ayiklanan {atilan} olcum, 1 gunden kisa bosluk "
                f"interpolasyonla dolduruldu\n")
        f.write("# yil ay gun saat dakika seviye_m\n")
        for t, v_ in d.items():
            f.write(f"{t.year} {t.month:2d} {t.day:2d} {t.hour:2d} "
                    f"{t.minute:2d} {v_:9.4f}\n")
    print(f"\nyazildi: {CIKTI}")

    with open(RAPOR, "w", encoding="utf-8") as f:
        f.write("BOZYAZI SEVIYE VERISI - AYIKLAMA RAPORU\n")
        f.write("=" * 60 + "\n")
        f.write(f"ham dolu olcum : {n0:,}\n")
        for b, n in satir:
            f.write(f"  {b:<50}{n:>8,}\n")
        f.write(f"toplam atilan  : {atilan:,} (%{100*atilan/n0:.3f})\n")
        f.write(f"kalan          : {int(s.notna().sum()):,}\n")
        f.write(f"interpolasyon  : +{eklenen:,}\n\n")
        for ad, v_ in msl.items():
            f.write(f"MSL {ad:<30} = {v_:.4f} m\n")
    print(f"yazildi: {RAPOR}")


if __name__ == "__main__":
    main()
