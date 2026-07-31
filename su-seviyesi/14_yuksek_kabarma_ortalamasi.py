"""
14_yuksek_kabarma_ortalamasi.py
===============================
Gelgit disi su YUKSELMELERININ ortalamasi.

Neden ayri bir betik
--------------------
Hoca "non-tidal su yukselmelerinin ortalamasi lazim" derken artigin
TUMUNUN ortalamasini degil, YUKSEK degerlerin ortalamasini kastetmis.
Bu ayrim onemli:

  * Artigin tumunun ortalamasi tanimi geregi SIFIRDIR (seriden hem gelgit
    hem ortalama seviye cikarilmistir). Makalenin Tablo 3'unde de 18
    istasyonun hepsi icin "Mean = 0" yazmasinin sebebi budur.
  * Yuksek degerlerin ortalamasi ise gercek bir muhendislik buyuklugudur:
    "tipik bir firtina bu istasyonda suyu ne kadar kabartir?" sorusunun
    cevabi.

Tanim secimi
------------
"Yuksek" tek bir tanimla gelmez; bu yuzden hepsi hesaplanip yan yana
konur ve hangisinin raporlanacagi secilebilir:

  A) Pozitif artiklarin ortalamasi
     En basit tanim. Ama zamanin yarisi zaten hafif pozitiftir; bu deger
     firtinayi degil, gunluk salinimi olcer. Alt sinir olarak verilir.

  B) Esik ustundeki degerlerin ortalamasi
     %90, %95, %99 yuzdelikleri esik alinir. Hala her 15 dakikalik olcumu
     ayri sayar: uzun bir firtina, kisa bir firtinadan daha cok agirlik
     kazanir.

  C) BAGIMSIZ TEPELERIN ortalamasi  <- muhendislikte kullanilan tanim
     Esigi asan ardisik olcumler tek bir OLAY sayilir (peak-over-threshold,
     POT). Iki olay ancak aralarinda yeterli sure varsa ayri sayilir;
     aksi halde ayni firtina birden fazla kez sayilir. Firtina kabarmasi
     icin alisilmis ayrim suresi 24-72 saattir, burada 48 saat alinip
     duyarlilik ayrica gosterilir.

  D) Yillik en yuksek degerlerin ortalamasi
     Her yilin en buyugu alinip ortalanir. Makaledeki "129 cm" gibi tek
     seferlik bir uc degerin karsiligi olan, ama tekrarlanabilir buyukluk
     budur. Yil sayisi kadar veri noktasi oldugu icin belirsizligi de
     hesaplanabilir.

Onkosul: 13_donem_kosucu.py (artik serilerini uretir)
Calistirma: python 14_yuksek_kabarma_ortalamasi.py
"""

import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ortak import FIG, TABLO, VERI, ENLEM, BOYLAM, oku

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Bagimsiz olay ayrimi (saat). Firtina kabarmasinda alisilmis aralik.
AYRIM_SAAT = 48
DUYARLILIK = [24, 48, 72]

# Esik olarak kullanilan yuzdelikler
ESIKLER = [90, 95, 98, 99, 99.5]

DPI = 300


def donem_kodlari():
    return sorted({p.name.replace("bozyazi_artik_", "").replace(".dat.gz", "")
                   for p in VERI.glob("bozyazi_artik_*.dat.gz")},
                  key=lambda x: {"makale": 0, "son5": 1, "son10": 2,
                                 "tum": 3}.get(x, 9))


def bagimsiz_tepeler(s, esik, ayrim_saat=AYRIM_SAAT):
    """Esigi asan BAGIMSIZ olaylarin tepe degerleri.

    Esigi asan ardisik olcumler tek bir olay sayilir. Iki asim arasinda
    `ayrim_saat`ten uzun bir ara varsa ayri olay kabul edilir; boylece
    uzun bir firtina birden fazla kez sayilmaz.
    """
    ust = s[s > esik].dropna()
    if len(ust) == 0:
        return pd.Series(dtype=float)
    ara = ust.index.to_series().diff() > pd.Timedelta(hours=ayrim_saat)
    grup = ara.cumsum()
    # Her grubun en buyugu, KENDI ZAMAN DAMGASIYLA alinir. Dogrudan
    # .max() kullanilirsa sonuc grup numarasiyla indekslenir ve tepeler
    # figurde 1970 civarina dusuyordu (degerler dogru, konumlar yanlis).
    return ust.loc[ust.groupby(grup.values).idxmax()]


def analiz(a, kod):
    """Bir donem icin butun tanimlari hesaplar."""
    v = a.dropna()
    n_yil = len(v) * 15 / 60 / 24 / 365.25
    sat = []

    # --- A) pozitif artiklarin ortalamasi ---
    poz = v[v > 0]
    sat.append({
        "tanim": "A. Butun pozitif artiklarin ortalamasi",
        "esik_cm": 0.0, "olay": len(poz),
        "ortalama_cm": poz.mean() * 100, "std_cm": poz.std() * 100,
        "en_buyuk_cm": poz.max() * 100, "olay_yil": len(poz) / n_yil,
    })

    # --- B) esik ustu degerlerin ortalamasi ---
    for p in ESIKLER:
        e = np.percentile(v.values, p)
        ust = v[v > e]
        sat.append({
            "tanim": f"B. %{p} yuzdeligin ustu (her olcum ayri)",
            "esik_cm": e * 100, "olay": len(ust),
            "ortalama_cm": ust.mean() * 100, "std_cm": ust.std() * 100,
            "en_buyuk_cm": ust.max() * 100, "olay_yil": len(ust) / n_yil,
        })

    # --- C) bagimsiz tepeler (POT) ---
    for p in ESIKLER:
        e = np.percentile(v.values, p)
        t = bagimsiz_tepeler(v, e)
        if len(t) < 2:
            continue
        sat.append({
            "tanim": f"C. %{p} ustu BAGIMSIZ tepeler ({AYRIM_SAAT} sa ayrim)",
            "esik_cm": e * 100, "olay": len(t),
            "ortalama_cm": t.mean() * 100, "std_cm": t.std() * 100,
            "en_buyuk_cm": t.max() * 100, "olay_yil": len(t) / n_yil,
        })

    # --- D) yillik en yuksekler ---
    yil = v.groupby(v.index.year)
    say = yil.count()
    # Yilin en az yarisi dolu degilse o yilin maksimumu temsil etmez.
    tam = say[say > 0.5 * 35040].index
    ym = yil.max()[lambda s: s.index.isin(tam)]
    if len(ym) >= 2:
        sat.append({
            "tanim": f"D. Yillik en yuksek degerlerin ortalamasi "
                     f"({len(ym)} yil)",
            "esik_cm": np.nan, "olay": len(ym),
            "ortalama_cm": ym.mean() * 100, "std_cm": ym.std() * 100,
            "en_buyuk_cm": ym.max() * 100, "olay_yil": 1.0,
        })
        # aylik en yuksekler
        am = v.resample("1ME").max().dropna()
        sat.append({
            "tanim": f"D. Aylik en yuksek degerlerin ortalamasi "
                     f"({len(am)} ay)",
            "esik_cm": np.nan, "olay": len(am),
            "ortalama_cm": am.mean() * 100, "std_cm": am.std() * 100,
            "en_buyuk_cm": am.max() * 100, "olay_yil": 12.0,
        })

    d = pd.DataFrame(sat)
    d.insert(0, "donem", kod)
    return d, (ym if len(ym) >= 2 else None)


def duyarlilik(v):
    """Ayrim suresinin bagimsiz tepe ortalamasina etkisi."""
    e = np.percentile(v.dropna().values, 99)
    sat = []
    for h in DUYARLILIK:
        t = bagimsiz_tepeler(v, e, h)
        sat.append({"ayrim_saat": h, "olay": len(t),
                    "ortalama_cm": t.mean() * 100})
    return pd.DataFrame(sat), e * 100


def figur(v, kod, esik, tepeler):
    """Bagimsiz tepelerin zaman icindeki dagilimi."""
    f, ax = plt.subplots(figsize=(7.6, 3.0))
    ax.plot(v.index, v.values * 100, lw=0.15, color="0.6",
            label="gelgit disi seviye")
    ax.axhline(esik, color="#1f4e9c", lw=0.9, ls="--",
               label=f"esik %99 = {esik:.1f} cm")
    if len(tepeler):
        ax.plot(tepeler.index, tepeler.values * 100, "o", ms=3.5,
                color="#c0392b", label=f"bagimsiz tepe ({len(tepeler)})")
        ax.axhline(tepeler.mean() * 100, color="#c0392b", lw=1.1,
                   label=f"tepe ortalamasi = {tepeler.mean()*100:.1f} cm")
    ax.set_ylabel("gelgit disi seviye (cm)")
    ax.set_title(f"Bozyazi - bagimsiz firtina kabarmalari ({kod})")
    ax.legend(fontsize=7, ncol=2, loc="upper left", framealpha=0.9)
    ax.grid(alpha=0.3, lw=0.4)
    f.tight_layout()
    f.savefig(FIG / f"04_kabarma_tepeleri_{kod}.png", dpi=DPI)
    plt.close(f)


def komsu_sinamasi():
    """Yillik en yuksek kabarmalar komsu istasyonlarda da artiyor mu?

    Bozyazi'da yillik en yuksek kabarma 2019'dan sonra kabaca ikiye
    katlaniyor. Iki aciklamasi olabilir:
      * gercekten daha siddetli firtinalar
      * ayiklamadan gecen artik cihaz sorunlari (silme orani ayni
        donemde %0.1'den %2-6'ya cikiyor)

    Ayrimi komsu istasyonlar yapar. Harmonik cozum gerekmeden kaba bir
    kabarma olcusu elde etmek icin seviyeden 30 gunluk hareketli medyan
    cikarilir: bu hem datumu hem mevsimsel salinimi siler, geriye kisa
    sureli oynamalar kalir. Gelgit de icinde kalir ama genligi (+-30 cm)
    butun istasyonlarda ve butun yillarda ayni oldugu icin YILLAR ARASI
    karsilastirmayi bozmaz.
    """
    istasyonlar = ["bozyazi", "tasucu", "erdemli", "antalya"]
    sut = {}
    for ad in istasyonlar:
        try:
            s = oku(f"{ad}_temiz.dat")
        except FileNotFoundError:
            continue
        kaba = s - s.rolling("30D", center=True).median()
        g = kaba.groupby(kaba.index.year)
        say = g.count()
        tam = say[say > 0.5 * 35040].index
        sut[ad] = (g.max()[lambda x: x.index.isin(tam)] * 100).round(1)
    if len(sut) < 2:
        return None
    return pd.DataFrame(sut)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    TABLO.mkdir(parents=True, exist_ok=True)
    kodlar = donem_kodlari()
    if not kodlar:
        sys.exit("Artik serisi yok. Once 13_donem_kosucu.py calistirilmali.")
    print(f"bulunan donemler: {', '.join(kodlar)}\n")

    hepsi = []
    for kod in kodlar:
        a = oku(f"bozyazi_artik_{kod}.dat")
        d, ym = analiz(a, kod)
        hepsi.append(d)

        print("=" * 78)
        print(f"{kod.upper()}   ({a.index.min():%Y-%m-%d} .. "
              f"{a.index.max():%Y-%m-%d})")
        print("=" * 78)
        print(f"  {'tanim':<48}{'esik':>8}{'olay':>7}{'ORT':>8}{'+-':>7}")
        print("  " + "-" * 76)
        for _, s in d.iterrows():
            e = f"{s.esik_cm:.1f}" if np.isfinite(s.esik_cm) else "-"
            print(f"  {s.tanim:<48}{e:>8}{int(s.olay):>7}"
                  f"{s.ortalama_cm:>8.1f}{s.std_cm:>7.1f}")

        du, e99 = duyarlilik(a)
        print(f"\n  Ayrim suresinin etkisi (esik %99 = {e99:.1f} cm):")
        for _, s in du.iterrows():
            print(f"    {int(s.ayrim_saat):>3} saat -> {int(s.olay):>4} olay,"
                  f" ortalama {s.ortalama_cm:.1f} cm")

        if ym is not None:
            print(f"\n  Yillik en yuksekler (cm):")
            print("   ", "  ".join(f"{y}:{v*100:.0f}"
                                   for y, v in ym.items()))

        t99 = bagimsiz_tepeler(a.dropna(), e99 / 100)
        figur(a.dropna(), kod, e99, t99)
        print(f"\n  figur: 04_kabarma_tepeleri_{kod}.png")
        print()

    d = pd.concat(hepsi, ignore_index=True)
    yol = TABLO / "11_yuksek_kabarma_ortalamasi.csv"
    d.round(3).to_csv(yol, index=False)

    # --- donemler arasi buyuk fark var mi, varsa gercek mi? ---
    k = komsu_sinamasi()
    if k is not None:
        print("=" * 78)
        print("YILLIK EN YUKSEK KABARMA - ISTASYONLAR ARASI")
        print("(seviye eksi 30 gunluk hareketli medyan; cm)")
        print("=" * 78)
        print(f"  {'yil':<6}" + "".join(f"{c:>11}" for c in k.columns))
        print("-" * 78)
        for y, r in k.iterrows():
            print(f"  {y:<6}" + "".join(
                f"{v:>11.1f}" if np.isfinite(v) else f"{'-':>11}"
                for v in r))
        erken = k[k.index <= 2018].mean()
        gec = k[k.index >= 2019].mean()
        print("-" * 78)
        print(f"  {'<=2018':<6}" + "".join(f"{v:>11.1f}" for v in erken))
        print(f"  {'>=2019':<6}" + "".join(f"{v:>11.1f}" for v in gec))
        print(f"  {'oran':<6}" + "".join(f"{g/e:>11.2f}"
                                         for e, g in zip(erken, gec)))
        print()
        oranlar = (gec / erken).dropna()
        b = oranlar.get("bozyazi", np.nan)
        digerleri = oranlar.drop("bozyazi", errors="ignore")
        if len(digerleri) and np.isfinite(b):
            if b > 1.4 and (digerleri > 1.2).all():
                print("  YORUM: artis butun istasyonlarda var -> BOLGESEL,")
                print("  yani gercek. Son donem degerleri kullanilabilir.")
            elif b > 1.4 and (digerleri < 1.2).any():
                print("  YORUM: artis agirlikli olarak Bozyazi'ya OZGU.")
                print("  Ayni donemde Bozyazi'da silme orani da %0.1'den")
                print("  %2-6'ya cikiyor; artik cihaz sorunu suphesi var.")
                print("  Bu yuzden ONERILEN deger makale penceresinden")
                print("  (temiz donem) alinmalidir.")
            else:
                print("  YORUM: donemler arasi belirgin fark yok.")
        k.to_csv(TABLO / "12_yillik_kabarma_istasyonlar.csv",
                 index_label="yil")
        print(f"\n  yazildi: {TABLO/'12_yillik_kabarma_istasyonlar.csv'}")
        print()

    print("=" * 78)
    print("ONERILEN DEGER")
    print("=" * 78)
    m = d[(d.donem == kodlar[0]) &
          d.tanim.str.startswith("C. %99 ustu")]
    y = d[(d.donem == kodlar[0]) & d.tanim.str.contains("Yillik")]
    if len(m):
        s = m.iloc[0]
        print(f"  Ortalama firtina kabarmasi (bagimsiz tepeler, %99 ustu):")
        print(f"     {s.ortalama_cm:.1f} cm   "
              f"({int(s.olay)} olay, yilda {s.olay_yil:.1f} kez)")
    if len(y):
        s = y.iloc[0]
        print(f"  Yillik en yuksek kabarmanin ortalamasi:")
        print(f"     {s.ortalama_cm:.1f} +- {s.std_cm:.1f} cm")
    print(f"\n  Karsilastirma: makalenin verdigi 129 cm, kaydin TAMAMINDA")
    print(f"  bir kez gorulen en genis aralik (en yuksek - en dusuk).")
    print(f"\nyazildi: {yol}")


if __name__ == "__main__":
    main()
