"""
13_donem_kosucu.py
==================
Ayni analizi birden fazla donem icin AYRI AYRI calistirir ve sonuclari
yan yana koyar.

Donemler
--------
    makale     : 2009-07-01 .. 2018-03-13   yayimlanmis degerlerle
                                            karsilastirma penceresi
    son5       : son bes yil                hocanin asgari istegi
    son10      : son on yil
    tum        : kaydin tamami

Her donem icin uretilenler
--------------------------
    tables/01_gelgit_bilesenleri_<donem>.csv
    tables/02_gelgit_duzeyleri_<donem>.csv
    tables/09_famagusta_bicimi_<donem>.csv      (hocanin Tablo 2-2 bicimi)
    tables/03_nontidal_ozet.csv                 (butun donemler tek dosyada)
    figures/01_nontidal_pdf_cdf_<donem>.png
    data/coef_<donem>.pkl                       (cozum saklanir)

Neden parca parca
-----------------
Her donem ayri bir sureste cozulup sonucu HEMEN diske yaziliyor. Boylece
bir donem bellek yetmedigi icin durursa oncekiler kaybolmuyor.

Calistirma:
    python 13_donem_kosucu.py                # hepsi
    python 13_donem_kosucu.py son5 tum       # secilenler
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ortak import (FIG, TABLO, VERI, ENLEM, BOYLAM, PAPER_BAS, PAPER_BIT,
                   MAKALE_GENLIK, MAKALE_F, MAKALE_E, MAKALE_NONTIDAL_STD,
                   MAKALE_TD, bilesen_sozlugu, coz, coz_kaydet,
                   form_enerji, gelgit_tipi, kes, kur, oku, trend_mm_yil,
                   yaz)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent

# Hocanin ornek verdigi Famagusta tablosundaki bilesenler, o siradayla.
FAMAGUSTA = ["M2", "S2", "K1", "O1", "N2", "K2", "P1", "MS4"]


def donemler(s):
    """Kaydin gercek bitisine gore donemleri kurar."""
    son = s.index.max().normalize()
    return [
        ("makale", PAPER_BAS, PAPER_BIT,
         "makale penceresi - yayimlanmis degerlerle karsilastirma"),
        ("son5", (son - pd.DateOffset(years=5)).strftime("%Y-%m-%d"),
         son.strftime("%Y-%m-%d"), "son bes yil"),
        ("son10", (son - pd.DateOffset(years=10)).strftime("%Y-%m-%d"),
         son.strftime("%Y-%m-%d"), "son on yil"),
        ("tum", s.index.min().strftime("%Y-%m-%d"),
         son.strftime("%Y-%m-%d"), "kaydin tamami"),
    ]


KARSILASTIRMA = "10_donem_karsilastirma.csv"


def birikimli_yaz(yeni):
    """Donem ozetini var olan tabloya EKLER.

    Betik donem basina ayri bir surecte calisabildigi icin (bkz.
    00_hepsini_calistir.py) tabloyu dogrudan yazmak onceki donemleri
    siliyordu: her kosu tek satirlik bir dosya birakiyordu. Bu yuzden
    once diskteki tablo okunur, ayni donem varsa guncellenir, sonra
    hepsi birlikte yazilir.
    """
    yol = TABLO / KARSILASTIRMA
    d = pd.DataFrame(yeni)
    if yol.exists():
        eski = pd.read_csv(yol)
        eski = eski[~eski.donem.isin(d.donem)]
        d = pd.concat([eski, d], ignore_index=True)
    sira = {"makale": 0, "son5": 1, "son10": 2, "tum": 3}
    d = d.sort_values("donem", key=lambda s: s.map(sira).fillna(9))
    d.to_csv(yol, index=False)
    return d


def famagusta_tablosu(h, yol, msl):
    """Hocanin ornek verdigi Tablo 2-2 bicimi: ad, genlik [m], faz [deg]."""
    sat = []
    for k in FAMAGUSTA:
        if k in h:
            sat.append({"Name tidal component": k,
                        "Amplitude [m]": round(h[k]["A"] / 100.0, 4),
                        "Phase [deg]": round(h[k]["g"], 1)})
        else:
            sat.append({"Name tidal component": k,
                        "Amplitude [m]": None, "Phase [deg]": None})
    pd.DataFrame(sat).to_csv(yol, index=False)
    return sat


def main():
    istenen = [a for a in sys.argv[1:] if not a.startswith("-")]
    s = oku()
    ozet = []

    for kod, a, b, aciklama in donemler(s):
        if istenen and kod not in istenen:
            continue
        x = kes(s, a, b).dropna()
        print("=" * 78)
        print(f"{kod.upper()}  ({a} .. {b})  -  {aciklama}")
        print(f"n = {len(x):,} olcum  ({len(x)*15/60/24/365.25:.2f} yil)")
        print("=" * 78)
        if len(x) < 20000:
            print("  yetersiz veri, atlandi\n")
            continue

        coef = coz(x)
        h = bilesen_sozlugu(coef)
        coz_kaydet(coef, kod)

        gelgit = pd.Series(np.asarray(kur(x, coef, trend=False).h, float),
                           index=x.index)
        artik = x - gelgit
        yaz(gelgit, f"bozyazi_gelgit_{kod}.dat",
            [f"Bozyazi gelgit ongorusu, {a}..{b}, egim haric"])
        yaz(artik, f"bozyazi_artik_{kod}.dat",
            [f"Bozyazi gelgit disi artik, {a}..{b}"])

        # bilesenler
        sec = sorted([(k, v) for k, v in h.items() if v["snr"] > 2],
                     key=lambda kv: -kv[1]["A"])
        with open(TABLO / f"01_gelgit_bilesenleri_{kod}.csv", "w",
                  encoding="utf-8") as f:
            f.write("bilesen,genlik_m,genlik_cm,genlik_hata_cm,"
                    "faz_derece,SNR\n")
            for k, v in sec:
                f.write(f"{k},{v['A']/100:.6f},{v['A']:.4f},"
                        f"{v['A_ci']:.4f},{v['g']:.2f},{v['snr']:.1f}\n")

        msl = float(x.mean())
        fam = famagusta_tablosu(
            h, TABLO / f"09_famagusta_bicimi_{kod}.csv", msl)
        print("  Hocanin istedigi bicimde (Tablo 2-2):")
        print(f"    {'bilesen':<10}{'genlik [m]':>13}{'faz [deg]':>12}")
        for r in fam:
            av = r["Amplitude [m]"]
            fv = r["Phase [deg]"]
            print(f"    {r['Name tidal component']:<10}"
                  f"{av if av is not None else '-':>13}"
                  f"{fv if fv is not None else '-':>12}")

        F, E = form_enerji(h)
        tr = trend_mm_yil(coef)
        print(f"\n  MSL = {msl:.4f} m   F = {F:.3f}   E = {E:.3f}   "
              f"({gelgit_tipi(F)})")
        print(f"  dogrusal egim = {tr:+.2f} mm/yil  "
              f"[trend olarak okunmamali, bkz. 08]")

        gt = (gelgit - gelgit.mean()).values
        at = (artik - artik.mean()).values
        TD = float(np.sqrt(np.nansum(gt**2) / np.nansum(at**2)))
        print(f"\n  gelgit disi: ortalama {artik.mean()*100:+.4f} cm, "
              f"std {artik.std()*100:.2f} cm, "
              f"aralik {(artik.max()-artik.min())*100:.1f} cm, TD {TD:.3f}")

        ozet.append({
            "donem": kod, "aciklama": aciklama, "baslangic": a, "bitis": b,
            "olcum": len(x), "yil": round(len(x)*15/60/24/365.25, 2),
            "MSL_m": round(msl, 4),
            "M2_m": round(h.get("M2", {}).get("A", np.nan)/100, 5),
            "S2_m": round(h.get("S2", {}).get("A", np.nan)/100, 5),
            "F": round(F, 4), "E": round(E, 4),
            "egim_mm_yil": round(tr, 2),
            "nontidal_ortalama_cm": round(artik.mean()*100, 4),
            "nontidal_std_cm": round(artik.std()*100, 3),
            "nontidal_aralik_cm": round((artik.max()-artik.min())*100, 2),
            "TD": round(TD, 4),
        })
        birikimli_yaz(ozet)

        # gelgit duzeyleri ve figurler, o donemin cozumuyle
        for betik in ("06_gelgit_seviyeleri.py", "07_non_tidal.py"):
            subprocess.run([sys.executable, "-u", betik, kod],
                           cwd=str(BASE))
        print()

    if not ozet:
        return
    # Diskteki tablo butun donemleri tasiyor; ozet yalniz bu kosudakini.
    d = pd.read_csv(TABLO / KARSILASTIRMA)
    print("=" * 78)
    print(f"DONEMLER YAN YANA  ({len(d)} donem)")
    print("=" * 78)
    print(f"  {'donem':<8}{'yil':>6}{'MSL m':>9}{'M2 m':>9}{'F':>7}"
          f"{'std cm':>9}{'TD':>7}{'aralik cm':>11}")
    print("-" * 78)
    for _, r in d.iterrows():
        print(f"  {r.donem:<8}{r.yil:>6.1f}{r.MSL_m:>9.4f}{r.M2_m:>9.5f}"
              f"{r.F:>7.3f}{r.nontidal_std_cm:>9.2f}{r.TD:>7.3f}"
              f"{r.nontidal_aralik_cm:>11.1f}")
    print("-" * 78)
    print(f"  makale (2009-2018) :  M2 {MAKALE_GENLIK['M2']/100:.5f} m   "
          f"F {MAKALE_F:.2f}   std {MAKALE_NONTIDAL_STD:.2f} cm   "
          f"TD {MAKALE_TD:.2f}")
    print()
    print("  Gelgit bilesenleri donemden donem neredeyse degismez -- gelgit")
    print("  astronomik bir olgudur. Gelgit DISI istatistikler ise")
    print("  meteorolojiye bagli oldugu icin donemle degisir.")
    print(f"\nyazildi: {TABLO/'10_donem_karsilastirma.csv'}")


if __name__ == "__main__":
    main()
