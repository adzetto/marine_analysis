"""
05_harmonik_analiz.py
=====================
Ayiklanmis Bozyazi seviye kaydindan gelgit harmonik bilesenlerini cozer.

Yontem
------
Makale (Ozturk & Yuksel 2023) MATLAB T_TIDE'i (Pawlowicz vd. 2002)
kullanmis. Burada onun bakimi surdurulen Python karsiligi UTide
kullaniliyor: ayni klasik en kucuk kareler harmonik cozumu, ayni nodal
duzeltmeler, ayni guven araligi mantigi.

Makaledeki gibi yalniz SNR > 2 olan bilesenler raporlanir; SNR, makalenin
tanimiyla genligin genlik hatasina oraninin karesidir.

Cozum dort pencerede tekrarlanir (bkz. ortak.DONEMLER). "makale penceresi"
yayimlanmis degerlerle karsilastirma icindir; birincil sonuc "temiz on yil".

Trend: hocanin ilk cumlesi "deniz seviyesindeki degisime bakacagiz" oldugu
icin dogrusal trend gelgit bilesenleriyle AYNI ANDA cozulur (boylece
mevsimsel SA/SSA harmonikleri trendi kirletmez) ve mm/yil raporlanir.

Calistirma: python 05_harmonik_analiz.py
"""

import sys

import numpy as np

from ortak import (BASE, TABLO, DONEMLER, MAKALE_GENLIK, MAKALE_F, MAKALE_E,
                   bilesen_sozlugu, coz, form_enerji, gelgit_tipi, kes, oku,
                   trend_mm_yil)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    s = oku()
    TABLO.mkdir(parents=True, exist_ok=True)
    sonuc = {}

    for ad, a, b in DONEMLER:
        x = kes(s, a, b)
        print("=" * 78)
        print(f"{ad.upper()}  ({a}-{b})   n = {len(x):,} olcum "
              f"({len(x)*15/60/24/365.25:.2f} yil)")
        print("=" * 78)
        coef = coz(x)
        h = bilesen_sozlugu(coef)
        sonuc[ad] = h

        secili = {k: v for k, v in h.items() if v["snr"] > 2}
        sirali = sorted(secili.items(), key=lambda kv: -kv[1]["A"])
        print(f"SNR > 2 olan {len(secili)} bilesen "
              f"({len(h)} bilesen cozuldu). En buyuk 14:")
        print(f"  {'bilesen':<9}{'genlik cm':>11}{'+- cm':>8}"
              f"{'faz deg':>10}{'SNR':>12}")
        for k, v in sirali[:14]:
            print(f"  {k:<9}{v['A']:>11.3f}{v['A_ci']:>8.3f}"
                  f"{v['g']:>10.1f}{v['snr']:>12,.0f}")

        F, E = form_enerji(h)
        print(f"\n  Form faktoru F = {F:.3f}   Enerji faktoru E = {E:.3f}"
              f"   ->  {gelgit_tipi(F)}")
        print(f"  Dogrusal trend = {trend_mm_yil(coef):+.2f} mm/yil\n")

    # ---- makale ile karsilastirma ----
    print("=" * 78)
    print("DOGRULAMA: Ozturk & Yuksel (2023) Tablo 2, Bozyazi satiri")
    print("makale donemi 01.01.2009-13.03.2018 | bizim 2010-2018")
    print("=" * 78)
    h = sonuc["makale penceresi"]
    print(f"  {'bilesen':<9}{'makale cm':>11}{'bizim cm':>11}"
          f"{'fark cm':>10}{'fark %':>9}{'faz deg':>10}")
    farklar = []
    for k, mv in MAKALE_GENLIK.items():
        if k in h:
            bv = h[k]["A"]
            farklar.append(abs(bv - mv))
            print(f"  {k:<9}{mv:>11.2f}{bv:>11.2f}{bv-mv:>+10.2f}"
                  f"{100*(bv-mv)/mv:>+8.1f}%{h[k]['g']:>10.1f}")
        else:
            print(f"  {k:<9}{mv:>11.2f}{'yok':>11}")
    print(f"\n  ortalama mutlak fark: {np.mean(farklar):.3f} cm")
    F, E = form_enerji(h)
    print(f"  Form faktoru F : makale {MAKALE_F:.2f}  bizim {F:.3f}")
    print(f"  Enerji fakt. E : makale {MAKALE_E:.2f}  bizim {E:.3f}")

    # ---- tablolari yaz ----
    for ad in ("temiz on yil", "son bes yil"):
        h = sonuc[ad]
        secili = sorted([(k, v) for k, v in h.items() if v["snr"] > 2],
                        key=lambda kv: -kv[1]["A"])
        dosya = ("01_gelgit_bilesenleri.csv" if ad == "temiz on yil"
                 else "01b_gelgit_bilesenleri_son5yil.csv")
        with open(TABLO / dosya, "w", encoding="utf-8") as f:
            f.write("bilesen,genlik_cm,genlik_hata_cm,faz_derece,SNR\n")
            for k, v in secili:
                f.write(f"{k},{v['A']:.4f},{v['A_ci']:.4f},{v['g']:.2f},"
                        f"{v['snr']:.1f}\n")
        print(f"\nyazildi: {TABLO/dosya}  ({len(secili)} bilesen)")


if __name__ == "__main__":
    main()
