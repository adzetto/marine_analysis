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


def slug(ad):
    return (ad.replace(" ", "_").replace("ı", "i").replace("ö", "o")
            .replace("ü", "u").replace("ç", "c").replace("ş", "s")
            .replace("ğ", "g"))


def tablo_yaz(ad, h):
    """Bir donemin bilesenlerini hemen diske yazar.

    Donem donem yazmak onemli: en buyuk pencere (tum kayit, 568 bin nokta)
    dar bellekli ortamlarda islemin oldurulmesine yol acabiliyor. Tablolar
    en sonda toplu yazilsaydi, basariyla tamamlanan onceki donemlerin
    sonuclari da birlikte kaybolurdu -- nitekim ilk kosuda oyle oldu.
    """
    secili = sorted([(k, v) for k, v in h.items() if v["snr"] > 2],
                    key=lambda kv: -kv[1]["A"])
    yol = TABLO / f"01_gelgit_bilesenleri_{slug(ad)}.csv"
    with open(yol, "w", encoding="utf-8") as f:
        f.write("bilesen,genlik_cm,genlik_hata_cm,faz_derece,SNR\n")
        for k, v in secili:
            f.write(f"{k},{v['A']:.4f},{v['A_ci']:.4f},{v['g']:.2f},"
                    f"{v['snr']:.1f}\n")
    print(f"  yazildi: {yol.name}  ({len(secili)} bilesen)")


def makale_karsilastir(h):
    print("\n" + "=" * 78)
    print("DOGRULAMA: Ozturk & Yuksel (2023) Tablo 2, Bozyazi satiri")
    print("makale donemi 01.01.2009-13.03.2018 | bizim 2010-2018")
    print("=" * 78)
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


def main():
    s = oku()
    TABLO.mkdir(parents=True, exist_ok=True)
    sonuc = {}
    trendler = []

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
        tr = trend_mm_yil(coef)
        trendler.append((ad, a, b, F, E, tr))
        print(f"\n  Form faktoru F = {F:.3f}   Enerji faktoru E = {E:.3f}"
              f"   ->  {gelgit_tipi(F)}")
        print(f"  Dogrusal trend = {tr:+.2f} mm/yil")

        # Her donem biter bitmez diske yazilir.
        tablo_yaz(ad, h)
        with open(TABLO / "05_donem_ozeti.csv", "w", encoding="utf-8") as f:
            f.write("donem,baslangic,bitis,form_faktoru_F,enerji_faktoru_E,"
                    "trend_mm_yil\n")
            for t in trendler:
                f.write(f"{t[0]},{t[1]},{t[2]},{t[3]:.4f},{t[4]:.4f},"
                        f"{t[5]:.3f}\n")
        if ad == "makale penceresi":
            makale_karsilastir(h)
        print()

    print("=" * 78)
    print("TREND HAKKINDA")
    print("=" * 78)
    print("Bu pencerede cozulen dogrusal egim, deniz seviyesi yukselisi")
    print("olarak RAPORLANMAMALIDIR. Yillik ortalamalar dogrusal degil, V")
    print("bicimli: 2010'da +6.0 cm, 2017'de -11.1 cm, 2024'te +8.9 cm")
    print("(kendi ortalamasindan sapma). Bir V'nin inen koluna dogru")
    print("cekilen bir dogru, egilim degil o kolun egimidir.")
    print()
    print("08_istasyon_karsilastir.py bu V'nin Tasucu, Erdemli ve Antalya'da")
    print("da AYNI sekilde bulundugunu gosterdi (2017 minimumu dortunde de")
    print("var, r = 0.75-0.81). Yani olay BOLGESEL ve gercek; Bozyazi'nin")
    print("cihaz hatasi degil. Ancak 16 yil, on yillik degiskenligin")
    print("baskin oldugu bir seride trend kestirmek icin kisa; guvenilir")
    print("bir deniz seviyesi trendi icin genelde 30+ yil gerekir.")
    print()
    print("Bagimsiz dogrulama: TUDES aylik ortalamalari her yil PSMSL'e")
    print("gonderiyor ve PSMSL kayitlari ropere indirgenmis (RLR) oldugu")
    print("icin trend sorusu asil orada yanitlanmalidir.")


if __name__ == "__main__":
    main()
