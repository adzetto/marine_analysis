"""
12_cok_istasyon_dogrula.py
==========================
Zincirin dogrulugunu Bozyazi disindaki istasyonlarla sinar.

Neden gerekli
-------------
Tek istasyonda tutan bir sonuc sansa da bagli olabilir. Makale (Ozturk &
Yuksel 2023) ayni Levantin kiyisindaki Antalya, Tasucu ve Erdemli icin de
hem gelgit bilesenlerini (Tablo 2) hem gelgit disi istatistikleri
(Tablo 3) veriyor. Bu istasyonlarin ham verisi zaten indirilmis durumda
(08_istasyon_karsilastir.py icin). Ayni ayiklama ve ayni harmonik cozum
onlara da uygulanip yayimlanmis degerlerle karsilastirilir.

Dort istasyonda birden tutuyorsa yontem dogrudur; yalniz Bozyazi'da
tutuyorsa sans olabilir.

Iki asama
---------
    python 12_cok_istasyon_dogrula.py --hazirla
        Ham JSON parcalarini okur, ayiklar ve data/<istasyon>_temiz.dat.gz
        yazar. Hafif islem; utide kullanmaz. Ham veri gerektirir
        (01_tudes_indir.py ile indirilir, istasyon basina ~33 MB).

    python 12_cok_istasyon_dogrula.py
        Ayiklanmis serileri okuyup harmonik cozumu yapar ve yayimlanmis
        degerlerle karsilastirir. AGIR adim; bol bellekli ortam ister.

Ayrik tutulmasinin sebebi: ham parcalar depoya sigmayacak kadar buyuk
(4 istasyon x 33 MB), ayiklanmis seriler ise sikistirilinca ~2.4 MB.
Boylece hazirlik bir kez yapilir, dogrulama her yerde calisir.

Her istasyonun sonucu tamamlanir tamamlanmaz diske yazilir; bir istasyon
bellek yetmedigi icin durursa oncekiler kaybolmaz.
"""

import json
import sys

import numpy as np
import pandas as pd

from ortak import (TABLO, VERI, bilesen_sozlugu, coz, form_enerji, kes, kur)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MUTLAK_BANT = 2.00
KISA_PENCERE, KISA_ESIK = 9, 0.10
UZUN_PENCERE, UZUN_ESIK = 2881, 0.80
DUZ_KOSU, INTERP = 12, 96

# Makale Tablo 1'deki olcum donemleri ve Tablo 2/3'teki yayimlanmis
# degerler. Genlikler cm.
ISTASYONLAR = {
    "bozyazi": {
        "enlem": 36.104, "donem": ("2009-01-01", "2018-03-13"),
        "T2": {"M2": 9.39, "S2": 5.48, "N2": 1.56, "K2": 1.66, "K1": 2.54,
               "O1": 1.91, "P1": 0.88, "S1": 0.82, "SSA": 3.89, "SA": 9.42},
        "F": 0.30, "E": 0.09,
        "T3": {"aralik": 129.0, "std": 10.43, "TD": 1.06},
    },
    "tasucu": {
        "enlem": 36.275, "donem": ("2008-08-22", "2018-03-13"),
        "T2": {"M2": 9.55, "S2": 5.61, "N2": 1.61, "K2": 1.63, "K1": 2.48,
               "O1": 2.05, "P1": 1.42, "S1": 0.93, "SSA": 3.87, "SA": 8.23},
        "F": 0.30, "E": 0.10,
        "T3": {"aralik": 120.0, "std": 10.6, "TD": 1.0},
    },
    "erdemli": {
        "enlem": 36.563, "donem": ("2008-08-22", "2018-03-13"),
        "T2": {"M2": 10.13, "S2": 5.95, "N2": 1.71, "K2": 1.80, "K1": 2.93,
               "O1": 2.05, "P1": 0.94, "S1": 0.64, "SSA": 3.63,
               "SA": 10.12},
        "F": 0.31, "E": 0.10,
        "T3": {"aralik": 158.0, "std": 12.0, "TD": 1.32},
    },
    "antalya": {
        "enlem": 36.836, "donem": ("2008-08-22", "2015-10-27"),
        "T2": {"M2": 7.56, "S2": 4.64, "N2": 1.20, "K2": 1.45, "K1": 2.29,
               "O1": 1.49, "P1": 0.81, "S1": 0.21, "SSA": 4.13, "SA": 7.79},
        "F": 0.31, "E": 0.10,
        "T3": {"aralik": 90.5, "std": 9.37, "TD": 0.978},
    },
}


def ham_yukle(ad):
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
    return s.reindex(pd.date_range(s.index.min(), s.index.max(),
                                   freq="15min", tz="UTC"))


def ayikla(s):
    x = s.copy()
    x[(x - x.median()).abs() > MUTLAK_BANT] = np.nan
    uzun = x.rolling(UZUN_PENCERE, center=True, min_periods=200).median()
    x[(x - uzun).abs() > UZUN_ESIK] = np.nan
    for _ in range(2):
        kisa = x.rolling(KISA_PENCERE, center=True, min_periods=5).median()
        x[(x - kisa).abs() > KISA_ESIK] = np.nan
    g = (x != x.shift()).cumsum()
    x[x.notna() & (x.groupby(g).transform("size") >= DUZ_KOSU)] = np.nan
    return x.interpolate(method="time", limit=INTERP, limit_area="inside")


def hazirla():
    """Ham parcalari ayiklayip sikistirilmis seri olarak yazar."""
    from ortak import yaz
    for ad in ISTASYONLAR:
        ham = ham_yukle(ad)
        if ham is None:
            print(f"{ad:<10} ham veri yok -> "
                  f"'python 01_tudes_indir.py {ad}'")
            continue
        t = ayikla(ham).dropna()
        p = yaz(t, f"{ad}_temiz.dat", [
            f"{ad} mareograf - AYIKLANMIS deniz seviyesi",
            "kaynak: TUDES / Harita Genel Mudurlugu",
            "zaman UTC, seviye metre (istasyonun yerel datumu)",
        ])
        print(f"{ad:<10} {len(t):>8,} olcum  "
              f"{t.index.min():%Y-%m-%d}..{t.index.max():%Y-%m-%d}  "
              f"-> {p.name} ({p.stat().st_size/1024/1024:.2f} MB)")


def main():
    if "--hazirla" in sys.argv:
        hazirla()
        return

    sonuc = []
    yol = TABLO / "08_cok_istasyon_dogrulama.csv"
    for ad, bilgi in ISTASYONLAR.items():
        print("=" * 78)
        print(f"{ad.upper()}")
        print("=" * 78)
        try:
            from ortak import oku
            ham = oku(f"{ad}_temiz.dat")
        except FileNotFoundError:
            ham = ham_yukle(ad)
            if ham is not None:
                ham = ayikla(ham)
        if ham is None:
            print(f"  veri yok -> once '--hazirla' calistirin\n")
            continue

        a, b = bilgi["donem"]
        s = kes(ham, a, b).dropna()
        ort_a = max(pd.Timestamp(a, tz="UTC"), ham.index.min())
        print(f"  makale donemi   : {a} .. {b}")
        print(f"  bizde mevcut    : {ort_a:%Y-%m-%d} .. "
              f"{min(pd.Timestamp(b, tz='UTC'), ham.index.max()):%Y-%m-%d}")
        print(f"  olcum           : {len(s):,} "
              f"({len(s)*15/60/24/365.25:.2f} yil)")
        if len(s) < 50000:
            print("  yetersiz veri, atlandi\n")
            continue

        coef = coz(s)
        h = bilesen_sozlugu(coef)
        gelgit = pd.Series(np.asarray(kur(s, coef, trend=False).h, float),
                           index=s.index)
        artik = s - gelgit
        gt = (gelgit - gelgit.mean()).values
        at = (artik - artik.mean()).values
        TD = float(np.sqrt(np.nansum(gt**2) / np.nansum(at**2)))
        F, E = form_enerji(h)

        print(f"\n  {'bilesen':<8}{'makale':>9}{'bizim':>9}{'fark':>9}")
        print("  " + "-" * 34)
        farklar = []
        for k, mv in bilgi["T2"].items():
            if k in h:
                bv = h[k]["A"]
                farklar.append(abs(bv - mv))
                print(f"  {k:<8}{mv:>9.2f}{bv:>9.2f}{bv-mv:>+9.2f}")
        omf = float(np.mean(farklar))
        print(f"\n  ortalama mutlak fark : {omf:.3f} cm")
        print(f"  F : makale {bilgi['F']:.2f}  bizim {F:.3f}")
        print(f"  E : makale {bilgi['E']:.2f}  bizim {E:.3f}")

        t3 = bilgi["T3"]
        std = artik.std() * 100
        ar = (artik.max() - artik.min()) * 100
        print(f"\n  {'buyukluk':<16}{'makale':>9}{'bizim':>9}{'fark %':>10}")
        print("  " + "-" * 44)
        for et, mv, bv in [("std sapma (cm)", t3["std"], std),
                           ("TD", t3["TD"], TD),
                           ("azami aralik (cm)", t3["aralik"], ar)]:
            print(f"  {et:<16}{mv:>9.2f}{bv:>9.2f}"
                  f"{100*(bv-mv)/mv:>+9.1f}%")
        print(f"  {'ortalama (cm)':<16}{0.0:>9.2f}{artik.mean()*100:>9.4f}")
        print()

        sonuc.append({
            "istasyon": ad, "n": len(s),
            "yil": round(len(s) * 15 / 60 / 24 / 365.25, 2),
            "bilesen_ort_mutlak_fark_cm": round(omf, 3),
            "F_makale": bilgi["F"], "F_bizim": round(F, 3),
            "E_makale": bilgi["E"], "E_bizim": round(E, 3),
            "std_makale": t3["std"], "std_bizim": round(std, 2),
            "TD_makale": t3["TD"], "TD_bizim": round(TD, 3),
            "aralik_makale": t3["aralik"], "aralik_bizim": round(ar, 1),
            "ortalama_bizim_cm": round(artik.mean() * 100, 4),
        })
        # Her istasyon biter bitmez yazilir.
        pd.DataFrame(sonuc).to_csv(yol, index=False)

    if not sonuc:
        sys.exit("Hicbir istasyon islenemedi.")

    d = pd.DataFrame(sonuc)
    print("=" * 78)
    print("OZET - dort istasyonda birden")
    print("=" * 78)
    print(f"  {'istasyon':<10}{'yil':>6}{'bilesen fark':>14}"
          f"{'std M/B':>16}{'TD M/B':>15}")
    print("-" * 78)
    for _, s_ in d.iterrows():
        print(f"  {s_.istasyon:<10}{s_.yil:>6.1f}"
              f"{s_.bilesen_ort_mutlak_fark_cm:>13.2f}cm"
              f"{s_.std_makale:>8.2f}/{s_.std_bizim:<7.2f}"
              f"{s_.TD_makale:>7.2f}/{s_.TD_bizim:<7.2f}")
    print("-" * 78)
    print(f"  bilesen farkinin ortalamasi : "
          f"{d.bilesen_ort_mutlak_fark_cm.mean():.3f} cm")
    print(f"  std sapmada ortalama hata   : "
          f"{(100*(d.std_bizim-d.std_makale)/d.std_makale).abs().mean():.1f}%")
    print(f"  TD'de ortalama hata         : "
          f"{(100*(d.TD_bizim-d.TD_makale)/d.TD_makale).abs().mean():.1f}%")
    print(f"  azami aralikta ort. hata    : "
          f"{(100*(d.aralik_bizim-d.aralik_makale)/d.aralik_makale).abs().mean():.1f}%"
          "   <- tek olaya bagli istatistik")

    d.to_csv(yol, index=False)
    print(f"\nyazildi: {yol}")


if __name__ == "__main__":
    main()
