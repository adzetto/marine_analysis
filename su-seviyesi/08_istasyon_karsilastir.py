"""
08_istasyon_karsilastir.py
==========================
Bozyazi'daki gorunur egilimin GERCEK mi yoksa CIHAZ kaymasi mi oldugunu
ayirt eder.

Sorun
-----
05'te cozulen dogrusal trend 2010-2019 icin -11.3 mm/yil cikiyor. Bu, deniz
seviyesinin yilda 11 mm ALCALDIGI anlamina gelir; kuresel yukselis
+3.4 mm/yil oldugu dusunulurse fiziksel degil. Yillik ortalamalara bakinca
sebep goruluyor: seri V bicimli.

    2010  1.574 m
    2017  1.402 m     -> 7 yilda -172 mm
    2024  1.598 m     -> 7 yilda +196 mm

~19 cm'lik bir inis-cikis, Dogu Akdeniz'in yillar arasi gercek
degiskenligi (birkac cm) icin cok buyuk.

Sinama
------
Ayni kiyidaki komsu istasyonlar (Tasucu, Erdemli, Antalya) ayni donemde
ayni V'yi gosteriyor mu?

  * gosteriyorsa  -> olay bolgesel, yani gercek deniz seviyesi degisimi
  * gostermiyorsa -> Bozyazi'nin datumu/cihazi kaymis, trend raporlanamaz

Bu, tek istasyona bakarak verilemeyecek bir karar. TUDES seviyeleri zaten
her istasyonun KENDI yerel datumunda oldugu icin mutlak degerler
karsilastirilamaz; her seri kendi ortalamasindan cikarilarak yalnizca
DEGISIM karsilastirilir.

Onkosul: python 01_tudes_indir.py tasucu   (erdemli, antalya icin de)

Calistirma: python 08_istasyon_karsilastir.py
"""

import json
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ortak import FIG, TABLO, VERI

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ISTASYONLAR = ["bozyazi", "tasucu", "erdemli", "antalya"]
KARSILASTIRMA_A, KARSILASTIRMA_B = 2010, 2026

# 03'teki ayiklama esikleri (ayni mantik, tek istasyona bagimli degil)
MUTLAK_BANT = 2.00
KISA_PENCERE = 9
KISA_ESIK = 0.10
UZUN_PENCERE = 2881
UZUN_ESIK = 0.80
DUZ_KOSU = 12


def istasyon_yukle(ad):
    """Bir istasyonun ham parcalarini okuyup ayiklanmis seri dondurur."""
    kls = VERI / "ham" / ad
    if not kls.exists():
        return None
    kayit = []
    for f in sorted(kls.glob("*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            kayit.append((r["Tarih"], r["Deger"]))
    if not kayit:
        return None
    d = pd.DataFrame(kayit, columns=["ms", "sev"])
    t = pd.to_datetime(d.ms, unit="ms", utc=True)
    s = pd.Series(d.sev.values, index=t).groupby(level=0).first().sort_index()
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="15min",
                                tz="UTC"))

    # --- 03 ile ayni katmanli ayiklama ---
    s[(s - s.median()).abs() > MUTLAK_BANT] = np.nan
    uzun = s.rolling(UZUN_PENCERE, center=True, min_periods=200).median()
    s[(s - uzun).abs() > UZUN_ESIK] = np.nan
    for _ in range(2):
        kisa = s.rolling(KISA_PENCERE, center=True, min_periods=5).median()
        s[(s - kisa).abs() > KISA_ESIK] = np.nan
    grup = (s != s.shift()).cumsum()
    s[s.notna() & (s.groupby(grup).transform("size") >= DUZ_KOSU)] = np.nan
    return s


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    TABLO.mkdir(parents=True, exist_ok=True)

    yillik = {}
    print("=" * 74)
    print("ISTASYON KARSILASTIRMASI - yillik ortalama seviye")
    print("=" * 74)
    for ad in ISTASYONLAR:
        s = istasyon_yukle(ad)
        if s is None:
            print(f"  {ad}: veri yok, atlandi "
                  f"(once 'python 01_tudes_indir.py {ad}')")
            continue
        y = s.groupby(s.index.year).mean()
        n = s.groupby(s.index.year).count()
        # Yilin en az yarisi dolu degilse ortalama guvenilmez.
        y = y[n > 0.5 * 35040]
        y = y[(y.index >= KARSILASTIRMA_A) & (y.index <= KARSILASTIRMA_B)]
        yillik[ad] = y
        print(f"  {ad:<10} {len(s.dropna()):>8,} olcum, "
              f"{len(y)} kullanilabilir yil")

    if len(yillik) < 2:
        sys.exit("\nKarsilastirma icin en az iki istasyon gerekiyor.")

    # --- her seri kendi ortalamasindan cikarilir (datumlar farkli) ---
    df = pd.DataFrame(yillik)
    sapma = (df - df.mean()) * 100.0        # cm

    print("\n" + "=" * 74)
    print("ORTALAMADAN SAPMA (cm) - datumlar farkli oldugu icin merkezlendi")
    print("=" * 74)
    print(f"  {'yil':<6}" + "".join(f"{a:>12}" for a in sapma.columns))
    print("-" * 74)
    for y, r in sapma.iterrows():
        print(f"  {y:<6}" + "".join(
            f"{v:>12.1f}" if np.isfinite(v) else f"{'-':>12}" for v in r))

    # --- dogrusal egimler ---
    print("\n" + "=" * 74)
    print("DOGRUSAL EGIM (mm/yil)")
    print("=" * 74)
    print(f"  {'istasyon':<12}{'2010-2019':>14}{'2021-2026':>14}"
          f"{'tum donem':>14}")
    print("-" * 74)
    egimler = {}
    for a in sapma.columns:
        satir = []
        for lo, hi in [(2010, 2019), (2021, 2026),
                       (KARSILASTIRMA_A, KARSILASTIRMA_B)]:
            v = sapma[a][(sapma.index >= lo) & (sapma.index <= hi)].dropna()
            satir.append(np.polyfit(v.index, v.values, 1)[0] * 10
                         if len(v) > 2 else np.nan)
        egimler[a] = satir
        print(f"  {a:<12}" + "".join(
            f"{x:>+14.1f}" if np.isfinite(x) else f"{'-':>14}"
            for x in satir))

    # --- Bozyazi digerleriyle ne kadar uyumlu? ---
    if "bozyazi" in sapma.columns and len(sapma.columns) > 1:
        print("\n" + "=" * 74)
        print("BOZYAZI ile ESLESME")
        print("=" * 74)
        for a in sapma.columns:
            if a == "bozyazi":
                continue
            ort = sapma[["bozyazi", a]].dropna()
            if len(ort) < 4:
                continue
            r = np.corrcoef(ort.bozyazi, ort[a])[0, 1]
            fark = (ort.bozyazi - ort[a])
            print(f"  bozyazi - {a:<10} r = {r:+.3f}   "
                  f"fark araligi {fark.min():+.1f} .. {fark.max():+.1f} cm   "
                  f"(n={len(ort)} yil)")

        # --- sayilardan hukum ---
        rr = []
        for a in sapma.columns:
            if a == "bozyazi":
                continue
            ort = sapma[["bozyazi", a]].dropna()
            if len(ort) >= 4:
                rr.append(np.corrcoef(ort.bozyazi, ort[a])[0, 1])
        ortalama_r = float(np.mean(rr)) if rr else np.nan

        print("\n  HUKUM:")
        if ortalama_r > 0.6:
            print(f"  Ortalama r = {ortalama_r:+.2f}. Bozyazi'daki egilim "
                  f"komsu istasyonlarda")
            print("  da var -> BOLGESEL bir isaret, cihaz hatasi degil.")
            print("  Ancak bu, dogrusal trendin raporlanabilecegi anlamina")
            print("  GELMEZ: seri V bicimli oldugu icin secilen pencere")
            print("  isaretin yonunu belirliyor (2010-2019 negatif,")
            print("  2021-2026 pozitif). On yillik degiskenlik baskin.")
            print("  Guvenilir trend icin 30+ yil ve ropere indirgenmis")
            print("  (PSMSL RLR) kayit gerekir.")
        else:
            print(f"  Ortalama r = {ortalama_r:+.2f}. Egilim Bozyazi'ya OZGU")
            print("  gorunuyor -> datum/cihaz kaymasi suphesi. Trend bu")
            print("  kayittan raporlanamaz; HGM'den nivelman/roper gecmisi")
            print("  istenmelidir.")

        # Bozyazi'nin salinimi komsulardan buyuk mu?
        gen = {a: float(sapma[a].max() - sapma[a].min())
               for a in sapma.columns}
        print(f"\n  Salinim genligi (cm): " + "  ".join(
            f"{a}={v:.1f}" for a, v in gen.items()))
        if gen.get("bozyazi", 0) > 1.5 * np.median(
                [v for a, v in gen.items() if a != "bozyazi"]):
            print("  NOT: Bozyazi'nin salinimi komsularin belirgin uzerinde.")
            print("  Bolgesel isaretin uzerine istasyona ozgu bir bilesen")
            print("  binmis olabilir; kesinlestirmek icin roper gecmisi.")

    # --- figur ---
    f, ax = plt.subplots(figsize=(7.5, 4.0))
    for a in sapma.columns:
        v = sapma[a].dropna()
        ax.plot(v.index, v.values, "o-", ms=4, lw=1.2, label=a)
    ax.axhline(0, color="0.6", lw=0.6)
    ax.set_xlabel("yil")
    ax.set_ylabel("yillik ortalama seviyenin sapmasi (cm)")
    ax.set_title("Levantin kiyisi mareograf istasyonlari - "
                 "yillik ortalama seviye")
    ax.legend()
    ax.grid(alpha=0.3, lw=0.4)
    f.tight_layout()
    f.savefig(FIG / "03_istasyon_karsilastirma.png", dpi=200)
    f.savefig(FIG / "03_istasyon_karsilastirma.pdf")
    plt.close(f)
    print(f"\nfigur : {FIG/'03_istasyon_karsilastirma.png'}")

    sapma.round(2).to_csv(TABLO / "06_istasyon_yillik_sapma.csv",
                          index_label="yil")
    print(f"tablo : {TABLO/'06_istasyon_yillik_sapma.csv'}")


if __name__ == "__main__":
    main()
