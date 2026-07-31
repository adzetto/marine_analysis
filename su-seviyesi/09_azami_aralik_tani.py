"""
09_azami_aralik_tani.py
=======================
Makaleyle kalan tek belirgin farki inceler: gelgit disi AZAMI ARALIK.

    makale (01.01.2009-13.03.2018) : 129 cm
    bizim  (01.07.2009-13.03.2018) :  97 cm

Ayni kaynaktan, ayni istasyondan, ortusen bir donemde standart sapma
(10.10 vs 10.43 cm) ve TD (1.08 vs 1.06) neredeyse birebir tutarken azami
araligin tutmamasi sasirtici degil: azami aralik TEK BIR OLAYA bagli bir
istatistiktir, standart sapma ise yuz binlerce olcumun ortalamasidir.
Yine de farkin nereden geldigi tahmin edilmemeli, olculmelidir.

Uc olasilik sinanir
-------------------
A) EKSIK ALTI AY. Makale 01.01.2009'da basliyor, portalda kayit
   06.07.2009'da. Aradaki Ocak-Haziran 2009 kis firtinasi mevsimini
   iceriyor. Yillik azami aralik yildan yila ne kadar oynuyor? Oynama
   32 cm mertebesindeyse tek basina aciklar.

B) AYIKLAMANIN FAZLA SERT OLMASI. Katman 3 (kisa medyandan 10 cm sapma)
   hizli bir kabarmayi ya da salinimi kirpiyor olabilir. Ayni yillar
   yalniz katman 1+2 ile (fiziksel bant + surekli blok) yeniden
   ayiklanip azami aralik karsilastirilir.

C) SILINENLERIN NITELIGI. Gercek bir firtina kabarmasi saatler surer ve
   komsu olcumlerle TUTARLIDIR; ariza kaynakli sivri yalnizdir. Atilan
   uc noktalarin komsulariyla uyumu olculur.

Her yil ayri ayri cozulur; tek yil 35 bin nokta oldugu icin bellek sorunu
olmaz ve nodal duzeltmeler yil bazinda zaten dogru uygulanir.

Calistirma: python 09_azami_aralik_tani.py
"""

import sys

import numpy as np
import pandas as pd

from ortak import TABLO, coz, kur, oku, veri_yolu

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MUTLAK_BANT = 2.00
KISA_PENCERE, KISA_ESIK = 9, 0.10
UZUN_PENCERE, UZUN_ESIK = 2881, 0.80
DUZ_KOSU = 12
INTERP = 96


def ayikla(s, sert=True, bayrak_dondur=False):
    """sert=True  : 03'teki dort katmanin tamami
       sert=False : yalniz katman 1+2 (fiziksel bant + surekli blok)

    bayrak_dondur=True ise (temiz_seri, atildi_mi) ikilisi doner.
    Bayrak INTERPOLASYONDAN ONCE alinir; aksi halde silinen noktalarin
    cogu bosluk doldurmayla geri geldigi icin sayilamaz.
    """
    x = s.copy()
    x[(x - x.median()).abs() > MUTLAK_BANT] = np.nan
    uzun = x.rolling(UZUN_PENCERE, center=True, min_periods=200).median()
    x[(x - uzun).abs() > UZUN_ESIK] = np.nan
    if sert:
        for _ in range(2):
            kisa = x.rolling(KISA_PENCERE, center=True,
                             min_periods=5).median()
            x[(x - kisa).abs() > KISA_ESIK] = np.nan
        g = (x != x.shift()).cumsum()
        x[x.notna() & (x.groupby(g).transform("size") >= DUZ_KOSU)] = np.nan
    atildi = s.notna() & x.isna()
    y = x.interpolate(method="time", limit=INTERP, limit_area="inside")
    return (y, atildi) if bayrak_dondur else y


def artik(x):
    """Bir yillik seriden gelgit disi artigi cikarir."""
    v = x.dropna()
    if len(v) < 20000:
        return None
    coef = coz(v)
    gelgit = pd.Series(np.asarray(kur(v, coef, trend=False).h, float),
                       index=v.index)
    return v - gelgit


def main():
    ham = oku("bozyazi_ham.dat")
    tam = pd.date_range(ham.index.min(), ham.index.max(), freq="15min",
                        tz="UTC")
    ham = ham.reindex(tam)

    yillar = [y for y in range(2010, 2026)]

    print("=" * 78)
    print("A) YILLIK AZAMI ARALIK - yildan yila ne kadar oynuyor?")
    print("=" * 78)
    print(f"  {'yil':<6}{'std cm':>9}{'en dusuk':>10}{'en yuksek':>11}"
          f"{'ARALIK cm':>11}{'olcum':>9}   uc degerin tarihi")
    print("-" * 78)

    kayit = []
    for y in yillar:
        s = ayikla(ham[ham.index.year == y])
        a = artik(s)
        if a is None:
            print(f"  {y:<6}{'yetersiz veri':>40}")
            continue
        t_max = a.idxmax()
        kayit.append((y, a.std() * 100, a.min() * 100, a.max() * 100,
                      (a.max() - a.min()) * 100, len(a), t_max))
        print(f"  {y:<6}{a.std()*100:>9.2f}{a.min()*100:>10.1f}"
              f"{a.max()*100:>11.1f}{(a.max()-a.min())*100:>11.1f}"
              f"{len(a):>9,}   {t_max:%Y-%m-%d}")

    d = pd.DataFrame(kayit, columns=["yil", "std_cm", "min_cm", "max_cm",
                                     "aralik_cm", "n", "uc_tarih"])
    print("-" * 78)
    print(f"  yillik araligin ortalamasi : {d.aralik_cm.mean():.1f} cm")
    print(f"  en dusuk / en yuksek yil   : {d.aralik_cm.min():.1f} / "
          f"{d.aralik_cm.max():.1f} cm")
    print(f"  yillar arasi oynama        : "
          f"{d.aralik_cm.max()-d.aralik_cm.min():.1f} cm")
    print(f"  standart sapmanin oynamasi : "
          f"{d.std_cm.min():.2f} - {d.std_cm.max():.2f} cm")
    print()
    print("  YORUM: azami aralik yillar arasinda "
          f"{d.aralik_cm.max()-d.aralik_cm.min():.0f} cm oynuyor, standart")
    print("  sapma ise cok daha kararli. Yani azami aralik tek bir olaya")
    print("  bagli ve eksik bir kis mevsimi bu buyuklugu kolayca degistirir.")
    d.to_csv(TABLO / "07_yillik_azami_aralik.csv", index=False)

    print("\n" + "=" * 78)
    print("B) AYIKLAMA FAZLA SERT MI?")
    print("=" * 78)
    print("  Sinama SAGLAM yillarda yapilir (2010-2019). 2020 sonrasinda")
    print("  belgelenmis cihaz arizalari var (2023'te -371/+776 m gibi")
    print("  okumalar); orada 'yumusak' ayiklama gercek kabarmayi degil")
    print("  arizayi birakir ve karsilastirmayi anlamsizlastirir.\n")
    saglam = d[(d.yil >= 2010) & (d.yil <= 2019)]
    sinama = list(saglam.nlargest(3, "aralik_cm").yil)
    print(f"  {'yil':<6}{'sert (4 katman)':>18}{'yumusak (1+2)':>16}"
          f"{'fark':>9}{'atilan':>9}")
    print("-" * 78)
    for y in sinama:
        h = ham[ham.index.year == y]
        s1, bay = ayikla(h, sert=True, bayrak_dondur=True)
        a1 = artik(s1)
        a2 = artik(ayikla(h, sert=False))
        r1 = (a1.max() - a1.min()) * 100
        r2 = (a2.max() - a2.min()) * 100
        print(f"  {y:<6}{r1:>18.1f}{r2:>16.1f}{r2-r1:>+9.1f}"
              f"{int(bay.sum()):>9}")
    print()
    print("  Saglam yillarda fark kucukse ayiklama gercek kabarmalari")
    print("  kirpmiyor demektir.")

    print("\n" + "=" * 78)
    print("C) ATILAN UC NOKTALAR YALNIZ MI, TUTARLI MI?")
    print("=" * 78)
    print("  Gercek bir firtina kabarmasi saatler surer: komsu olcumler de")
    print("  yuksektir. Ariza kaynakli sivri ise yalnizdir.\n")
    for y in sinama:
        h = ham[ham.index.year == y]
        _, bay = ayikla(h, sert=True, bayrak_dondur=True)
        atilan = h[bay]
        if not len(atilan):
            print(f"  {y}: atilan olcum yok")
            continue
        med = h.rolling(9, center=True, min_periods=5).median()
        fark = (atilan - med.reindex(atilan.index)).abs()
        # Komsulari da atildi mi? Gercek bir olay coklu ardisik atilma
        # uretir; yalniz sivri tek basina kalir.
        g = (bay != bay.shift()).cumsum()
        boy = bay.groupby(g).sum()[bay.groupby(g).first()]
        tek = int((boy == 1).sum())
        print(f"  {y}: {len(atilan)} olcum atildi, {len(boy)} ayri olayda")
        print(f"      komsu medyandan sapma : ortanca "
              f"{fark.median()*100:.1f} cm, en buyuk {fark.max()*100:.1f} cm")
        print(f"      tek olcumluk olay     : {tek}/{len(boy)} "
              f"(%{100*tek/max(len(boy),1):.0f})")
        print(f"      en uzun olay          : {int(boy.max())} olcum "
              f"({int(boy.max())*15} dk)")
    print()
    print("  Olaylarin cogu tek/birkac olcumlukse bunlar sivridir; saatler")
    print("  suren bir kabarma bu bicimde gorunmez.")


if __name__ == "__main__":
    main()
