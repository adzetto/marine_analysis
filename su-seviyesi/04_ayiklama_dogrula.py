"""
04_ayiklama_dogrula.py
======================
03'teki ayiklamanin DOGRU seyi sildigini sinar. Iki bagimsiz kontrol:

  A) Katman x yil dagilimi. Esikler dogruysa silinen olcumlerin ezici
     cogunlugu bozuk yillarda (2023-2026) toplanmali; 2010-2019 saglam
     doneminde neredeyse hic silme olmamali. Orada cok silme cikiyorsa esik
     gercek sinyali kesiyor demektir.

  B) Hocanin WhatsApp'ta gonderdigi iki ekran goruntusuyle karsilastirma:
     Temmuz 2025 (bir gun suren ~3.2 m'lik blok) ve Eylul 2025 (tek noktalik
     3.57 m sivri). Temizleyici tam olarak bu iki anomaliyi kaldirmali,
     cevresindeki gelgit salinimina dokunmamali.

Calistirma: python 04_ayiklama_dogrula.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
FIG = BASE / "figures"

MUTLAK_BANT = 2.00
KISA_PENCERE = 9
KISA_ESIK = 0.10
UZUN_PENCERE = 2881
UZUN_ESIK = 0.80
DUZ_KOSU = 12


def oku(p):
    d = pd.read_csv(p, sep=r"\s+", comment="#", header=None,
                    names=["yil", "ay", "gun", "saat", "dk", "seviye"])
    t = pd.to_datetime(d[["yil", "ay", "gun", "saat", "dk"]].rename(columns={
        "yil": "year", "ay": "month", "gun": "day",
        "saat": "hour", "dk": "minute"}), utc=True)
    return pd.Series(d.seviye.values, index=t, name="seviye")


def etiketle(s):
    """Her olcume onu ilk yakalayan katmanin numarasini yazar (0 = temiz)."""
    bayrak = pd.Series(0, index=s.index)
    x = s.copy()

    m = (x - x.median()).abs() > MUTLAK_BANT
    bayrak[m & (bayrak == 0)] = 1
    x[m] = np.nan

    uzun = x.rolling(UZUN_PENCERE, center=True, min_periods=200).median()
    m = (x - uzun).abs() > UZUN_ESIK
    bayrak[m & (bayrak == 0)] = 2
    x[m] = np.nan

    for _ in range(2):
        kisa = x.rolling(KISA_PENCERE, center=True, min_periods=5).median()
        m = (x - kisa).abs() > KISA_ESIK
        bayrak[m & (bayrak == 0)] = 3
        x[m] = np.nan

    grup = (x != x.shift()).cumsum()
    m = x.notna() & (x.groupby(grup).transform("size") >= DUZ_KOSU)
    bayrak[m & (bayrak == 0)] = 4
    x[m] = np.nan

    return bayrak, x


def pencere_ciz(ham, temiz, bas, bit, baslik, dosya):
    a = pd.Timestamp(bas, tz="UTC")
    b = pd.Timestamp(bit, tz="UTC")
    h = ham[(ham.index >= a) & (ham.index <= b)]
    t = temiz[(temiz.index >= a) & (temiz.index <= b)]
    atilan = h[t.reindex(h.index).isna() & h.notna()]

    f, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    ax[0].plot(h.index, h.values, lw=0.7, color="#c0392b")
    ax[0].set_title(f"{baslik} - HAM (portalin cizdigi)", fontsize=10)
    ax[0].set_ylabel("Seviye (m)")
    ax[1].plot(t.index, t.values, lw=0.7, color="#1f6f3f")
    if len(atilan):
        ax[1].plot(atilan.index, np.full(len(atilan), t.min()), "x",
                   color="#c0392b", ms=5,
                   label=f"atilan {len(atilan)} olcum")
        ax[1].legend(fontsize=8, loc="upper left")
    ax[1].set_title(f"{baslik} - AYIKLANMIS", fontsize=10)
    ax[1].set_ylabel("Seviye (m)")
    for a_ in ax:
        a_.grid(alpha=0.3, lw=0.4)
    f.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    f.savefig(FIG / dosya, dpi=130)
    plt.close(f)
    print(f"    {dosya}: ham {len(h)} olcum, atilan {len(atilan)}, "
          f"ham araligi {h.min():.2f}-{h.max():.2f} m, "
          f"temiz araligi {t.min():.2f}-{t.max():.2f} m")


def main():
    from ortak import veri_yolu
    ham = oku(veri_yolu("bozyazi_ham.dat"))
    tam = pd.date_range(ham.index.min(), ham.index.max(), freq="15min",
                        tz="UTC")
    ham = ham.reindex(tam)
    bayrak, temiz = etiketle(ham)

    print("=" * 78)
    print("A) KATMAN x YIL DAGILIMI")
    print("=" * 78)
    ad = {1: "mutlak bant", 2: "surekli blok", 3: "tekil sivri",
          4: "takilma"}
    tb = pd.crosstab(bayrak.index.year, bayrak)
    print(f"{'yil':>6}{'dolu':>9}", end="")
    for k in (1, 2, 3, 4):
        print(f"{ad[k]:>14}", end="")
    print(f"{'silinen %':>11}")
    print("-" * 78)
    for y in tb.index:
        dolu = int(ham[ham.index.year == y].notna().sum())
        if not dolu:
            continue
        print(f"{y:>6}{dolu:>9,}", end="")
        tot = 0
        for k in (1, 2, 3, 4):
            n = int(tb.loc[y, k]) if k in tb.columns else 0
            tot += n
            print(f"{n:>14,}", end="")
        print(f"{100*tot/dolu:>10.2f}%")

    saglam = bayrak[(bayrak.index.year >= 2010) & (bayrak.index.year <= 2019)]
    dolu_s = int(ham[(ham.index.year >= 2010) &
                     (ham.index.year <= 2019)].notna().sum())
    print("-" * 78)
    print(f"SAGLAM DONEM 2010-2019: {int((saglam > 0).sum()):,} silindi / "
          f"{dolu_s:,} = %{100*(saglam > 0).sum()/dolu_s:.3f}")

    print("\n" + "=" * 78)
    print("B) HOCANIN EKRAN GORUNTULERIYLE KARSILASTIRMA")
    print("=" * 78)
    pencere_ciz(ham, temiz, "2025-07-01", "2025-07-31 23:45",
                "Temmuz 2025", "00_dogrulama_temmuz2025.png")
    pencere_ciz(ham, temiz, "2025-09-01", "2025-09-30 23:45",
                "Eylul 2025", "00_dogrulama_eylul2025.png")
    pencere_ciz(ham, temiz, "2024-04-25", "2024-04-29 23:45",
                "27 Nisan 2024 blogu", "00_dogrulama_nisan2024.png")


if __name__ == "__main__":
    main()
