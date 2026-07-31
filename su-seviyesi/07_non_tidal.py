"""
07_non_tidal.py
===============
Gelgit disi (non-tidal) su seviyesi bilesenini cikarir ve karakterize eder.

    artik(t) = olculen(t) - ongorulen gelgit(t)

Geriye kalan, meteorolojik (ruzgar kabarmasi, basinc) ve hidrolojik
etkilerdir. Hocanin "gelgitin disinda firtina ile yukselen su seviyesi"
dedigi buyuk budur.

Hocanin talebi uzerine bir not
------------------------------
Hoca "129 cm gibi bir kez olmus max degil, ORTALAMA lazim" dedi. Ancak
non-tidal artigin ortalamasi TANIMI GEREGI sifirdir: seriden hem gelgit hem
de ortalama seviye cikarilmistir. Nitekim makalenin kendi Tablo 3'unde
"Mean" sutunu butun 18 istasyon icin tek bir deger olarak "≈0" yazilmistir.
Yani duz ortalama, tasarim icin bilgi tasimaz.

Muhendislikte bu dagilimi temsil eden buyukluk STANDART SAPMADIR (makale
Tablo 3'te Bozyazi icin 10.43 cm) ve asilma yuzdeleridir. Bu yuzden burada
ortalama da (sifira yakinligini gostermek icin) hesaplanir, ama asil olarak
standart sapma, yuzdelikler ve asilma olasiliklari verilir. Hocanin ikinci
secenegi olan "paperdaki plot" (Fig. 6 PDF/CDF) da uretilir; zaten dogru
sorunun cevabi odur.

TD (gelgit baskinlik orani), makale Denk. 3:
    TD = sqrt( sum(gelgit^2) / sum(artik^2) )  =  RMS_gelgit / RMS_artik
Makale Bozyazi icin 1.06 vermis.

Calistirma: python 07_non_tidal.py
"""

import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import scienceplots  # noqa: F401

from ortak import (FIG, TABLO, DONEMLER, ENLEM, BOYLAM, MAKALE_NONTIDAL_MAX,
                   MAKALE_NONTIDAL_STD, MAKALE_TD, coz_yukle, kes, kur, oku)
from harita import konum_haritasi

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DPI = 300

# Histogram kutulamasi.
#
# Makale Fig. 6'nin kutu genisligi yazmiyor, ama tepe PDF degerlerinden
# geri hesaplanabiliyor: bir normal dagilimda 'probability' normalizasyonlu
# tepe yaklasik w / (sigma*sqrt(2pi)).
#     Erdemli  sigma 12.00 cm, tepe 0.52  ->  w = 15.6 cm
#     Mentes   sigma 10.00 cm, tepe 0.40  ->  w = 10.0 cm
#     Trabzon  sigma  9.15 cm, tepe 0.355 ->  w =  8.1 cm
#     Yalova   sigma 13.78 cm, tepe 0.37  ->  w = 12.8 cm
# Her birinde w, o istasyonun veri araligini yaklasik 10'a boluyor. Yani
# sabit bir genislik degil, sabit bir KUTU SAYISI kullanilmis: MATLAB'in
# eski hist() cagrisinin varsayilani olan 10.
#
# Karsilastirilabilirlik icin ayni sey yapilir. 10 kutu gorsel olarak cok
# kaba oldugundan ayrica ince bir surum de uretilir.
BIN_SAYISI = 10              # makaleyle ayni
BIN_M_INCE = 0.02            # ikinci, bilgi amacli surum (2 cm)
YUZDELIK = [0.1, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9]

def latex_var():
    """Sistemde calisan bir LaTeX kurulumu var mi?

    Figurler LaTeX dizgisiyle uretiliyor, ama Colab gibi ortamlarda texlive
    kurulu olmayabiliyor. Varligi denenmeden kabul edilirse betik figure
    asamasinda cokuyor; bu yuzden once sinaniyor ve yoksa matplotlib'in
    kendi matematik dizgisine duruluyor.
    """
    from shutil import which
    if not (which("latex") and which("dvipng")):
        return False
    try:
        import matplotlib.pyplot as _p
        _p.rcParams["text.usetex"] = True
        f = _p.figure()
        f.text(0.5, 0.5, r"$\eta_{nt}$")
        f.canvas.draw()
        _p.close(f)
        return True
    except Exception:
        _p.rcParams["text.usetex"] = False
        return False


plt.style.use(["science", "grid"])
LATEX = latex_var()
plt.rcParams.update({
    "text.usetex": LATEX,
    "font.family": "serif",
    "figure.dpi": DPI, "savefig.dpi": DPI, "savefig.bbox": "tight",
    "axes.labelsize": 9, "axes.titlesize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
})
print(f"LaTeX dizgisi: {'acik' if LATEX else 'KAPALI (texlive yok)'}")


def yz(latex_metin, duz_metin):
    """LaTeX varsa birinci, yoksa ikinci metni dondurur."""
    return latex_metin if LATEX else duz_metin


def slug(ad):
    return (ad.replace(" ", "_").replace("ı", "i").replace("ö", "o")
            .replace("ü", "u").replace("ç", "c").replace("ş", "s")
            .replace("ğ", "g"))


def pdf_cdf_ciz(art, baslik, dosya, kutu=None):
    """Makale Fig. 6 duzeninde: kirmizi PDF (sol), mavi CDF (sag).

    kutu=None  -> makaledeki gibi 10 kutu (aralik 10'a bolunur)
    kutu=sayi  -> o genislikte sabit kutu (metre), ince surum icin
    """
    v = art.dropna().values
    if kutu is None:
        kenar = np.linspace(v.min(), v.max(), BIN_SAYISI + 1)
    else:
        kenar = np.arange(np.floor(v.min() / kutu) * kutu,
                          np.ceil(v.max() / kutu) * kutu + kutu, kutu)
    say, kenar = np.histogram(v, bins=kenar)
    p = say / say.sum()
    orta = 0.5 * (kenar[:-1] + kenar[1:])
    cdf = np.cumsum(p)

    # Cizilen sayilar CSV'ye de yazilir; Excel'de ayni grafik kurulabilsin.
    pd.DataFrame({
        "kutu_alt_m": kenar[:-1], "kutu_ust_m": kenar[1:],
        "kutu_orta_m": orta, "kutu_orta_cm": orta * 100,
        "sayim": say, "PDF": p, "CDF": cdf,
    }).to_csv(TABLO / f"{dosya}_veri.csv", index=False)

    f, ax = plt.subplots(figsize=(4.6, 3.4))
    ax.plot(orta, p, color="#c0392b", lw=1.0)
    ax.set_xlabel(yz(r"Gelgit d\i{}\c{s}\i{} su seviyesi, $\eta_{nt}$ (m)",
                     "Gelgit dışı su seviyesi, $\\eta_{nt}$ (m)"))
    ax.set_ylabel("PDF")
    # Ust bosluk, sol ustteki ic haritanin egriyle cakismamasi icin.
    ax.set_ylim(0, p.max() * 1.55)
    ax.tick_params(axis="y", colors="#c0392b")
    ax.yaxis.label.set_color("#c0392b")

    ax2 = ax.twinx()
    ax2.plot(orta, cdf, color="#1f4e9c", lw=1.0)
    ax2.set_ylabel("CDF")
    ax2.set_ylim(0, 1.02)
    ax2.grid(False)
    ax2.tick_params(axis="y", colors="#1f4e9c")
    ax2.yaxis.label.set_color("#1f4e9c")

    ax.set_title(baslik)

    # Makaledeki gibi: sol uste istasyonu yildizla gosteren kucuk harita.
    # PDF egrisi tepe noktasindan sonra sagda kaldigi ve y ekseninde ust
    # bosluk birakildigi icin sol ust kose bostur.
    konum_haritasi(ax, BOYLAM, ENLEM, konum="sol_ust", boyut=0.34)

    f.savefig(FIG / f"{dosya}.png")
    f.savefig(FIG / f"{dosya}.pdf")
    plt.close(f)
    w = (kenar[1] - kenar[0]) * 100
    print(f"    figur: {dosya}  (kutu {w:.1f} cm, "
          f"tepe PDF {p.max():.3f}, veri -> {dosya}_veri.csv)")


def zaman_serisi_ciz(art, baslik, dosya):
    """Makale Fig. 5 duzeni: anlik + aylik + yillik ortalama."""
    f, ax = plt.subplots(figsize=(6.8, 2.8))
    ax.plot(art.index, art.values, lw=0.15, color="0.35",
            label=yz(r"anl\i{}k (15 dk)", "anlık (15 dk)"))
    ax.plot(art.index, art.rolling("30D").mean().values, lw=0.9,
            color="#c0392b",
            label=yz(r"ayl\i{}k hareketli ortalama",
                     "aylık hareketli ortalama"))
    yil = art.resample("1YE").mean()
    ax.step(yil.index, yil.values, where="mid", lw=0.9, color="#1f6f3f",
            label=yz(r"y\i{}ll\i{}k ortalama", "yıllık ortalama"))
    ax.set_ylabel("$\\eta_{nt}$ (m)")
    ax.set_title(baslik)
    ax.legend(ncol=3, loc="upper left", framealpha=0.9)
    konum_haritasi(ax, BOYLAM, ENLEM, konum="sag_alt", boyut=0.16,
                   etiketler=False)
    f.savefig(FIG / f"{dosya}.png")
    f.savefig(FIG / f"{dosya}.pdf")
    plt.close(f)
    print(f"    figur: {dosya}")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    TABLO.mkdir(parents=True, exist_ok=True)
    s = oku()
    ozet = {}

    # 13_donem_kosucu.py bu betigi donem kodu vererek cagirabiliyor.
    # O durumda cozum zaten kaydedilmis olur ve yalniz o donem islenir.
    if len(sys.argv) > 1:
        kod = sys.argv[1]
        d = pd.read_csv(TABLO / "10_donem_karsilastirma.csv")
        r = d[d.donem == kod].iloc[-1]
        donem_listesi = [(kod, r.baslangic, r.bitis)]
    else:
        donem_listesi = DONEMLER

    for ad, a, b in donem_listesi:
        x = kes(s, a, b)
        print("=" * 76)
        print(f"{ad.upper()}  ({a}-{b})   n = {len(x):,}")
        print("=" * 76)

        # Cozum 05'te bir kez yapilip saklandi; burada tekrar cozulmez.
        coef = coz_yukle(slug(ad))

        # Artik IKI turlu hesaplanir.
        #
        # T_TIDE'da dogrusal egim terimi YOKTUR; makalenin artigi bu yuzden
        # kaydin yavas suruklenmesini hala icerir. UTide ise egimi cozup
        # ongoruye ekliyor, dolayisiyla varsayilan artik daha DAR cikiyor.
        # Makaleyle elmayla elma karsilastirmasi yapabilmek icin egimin
        # ongoruden cikarilmadigi surum esas alinir; egimi arindirilmis
        # surum de bilgi olarak verilir.
        gelgit_tr = pd.Series(np.asarray(kur(x, coef, trend=True).h, float),
                              index=x.index)
        gelgit = pd.Series(np.asarray(kur(x, coef, trend=False).h, float),
                           index=x.index)
        artik = x - gelgit                 # makaleyle karsilastirilabilir
        artik_tr = x - gelgit_tr           # egimden arindirilmis

        # TD: makale Denk. 3. Gelgit sinyali ortalamasindan arindirilir,
        # cunku "enerji" salinim enerjisidir, datum degil.
        gt = (gelgit - gelgit.mean()).values
        at = (artik - artik.mean()).values
        TD = float(np.sqrt(np.nansum(gt**2) / np.nansum(at**2)))

        ist = {
            "ortalama_cm": artik.mean() * 100,
            "std_cm": artik.std() * 100,
            "min_cm": artik.min() * 100,
            "max_cm": artik.max() * 100,
            "aralik_cm": (artik.max() - artik.min()) * 100,
            "TD": TD,
        }
        ozet[ad] = (ist, artik)

        print(f"  ortalama       : {ist['ortalama_cm']:+.4f} cm   "
              f"<-- tanimi geregi ~0")
        print(f"  standart sapma : {ist['std_cm']:.2f} cm   "
              f"<-- dagilimi temsil eden buyukluk")
        print(f"  en dusuk / en yuksek : {ist['min_cm']:+.1f} / "
              f"{ist['max_cm']:+.1f} cm")
        print(f"  azami aralik   : {ist['aralik_cm']:.1f} cm")
        print(f"  TD (gelgit baskinligi) : {TD:.3f}")
        gt = (gelgit_tr - gelgit_tr.mean()).values
        at2 = (artik_tr - artik_tr.mean()).values
        print(f"  [egimden arindirilmis surum: std "
              f"{artik_tr.std()*100:.2f} cm, aralik "
              f"{(artik_tr.max()-artik_tr.min())*100:.1f} cm, TD "
              f"{np.sqrt(np.nansum(gt**2)/np.nansum(at2**2)):.3f}]")

        print("  yuzdelikler (cm):")
        q = np.percentile(artik.dropna().values * 100, YUZDELIK)
        print("   ", "  ".join(f"%{p}={v:+.1f}" for p, v in
                               zip(YUZDELIK, q)))

        # Her donem biter bitmez yazilir/cizilir. En buyuk pencere dar
        # bellekli ortamlarda islemin oldurulmesine yol acabildigi icin,
        # sonda toplu yazmak tamamlanmis donemleri de kaybettiriyordu.
        with open(TABLO / "03_nontidal_ozet.csv", "w", encoding="utf-8") as f:
            f.write("donem,ortalama_cm,std_cm,min_cm,max_cm,aralik_cm,TD\n")
            for k_, (i_, _) in ozet.items():
                f.write(f"{k_},{i_['ortalama_cm']:.4f},{i_['std_cm']:.3f},"
                        f"{i_['min_cm']:.2f},{i_['max_cm']:.2f},"
                        f"{i_['aralik_cm']:.2f},{i_['TD']:.4f}\n")
        with open(TABLO / f"04_nontidal_yuzdelikler_{slug(ad)}.csv", "w",
                  encoding="utf-8") as f:
            f.write("yuzdelik,seviye_cm\n")
            for p_, v_ in zip(YUZDELIK, q):
                f.write(f"{p_},{v_:.2f}\n")
        bas_ = yz(rf"Bozyaz\i{{}} - gelgit d\i{{}}\c{{s}}\i{{}} su "
                  rf"seviyesi ({a}--{b})",
                  f"Bozyazı - gelgit dışı su seviyesi ({a}-{b})")
        pdf_cdf_ciz(artik, bas_, f"01_nontidal_pdf_cdf_{slug(ad)}")
        pdf_cdf_ciz(artik, bas_, f"01b_nontidal_pdf_cdf_ince_{slug(ad)}",
                    kutu=BIN_M_INCE)
        zaman_serisi_ciz(artik,
                         yz(rf"Bozyaz\i{{}} - $\eta_{{nt}}$ ({a}--{b})",
                            f"Bozyazı - $\\eta_{{nt}}$ ({a}-{b})"),
                         f"02_nontidal_zaman_serisi_{slug(ad)}")
        print()

    # --- makale ile karsilastirma ---
    #
    # Donem adi cagirma bicimine gore degisiyor: dogrudan calistirildiginda
    # ortak.DONEMLER'den "makale penceresi", 13_donem_kosucu.py'den
    # cagrildiginda "makale"/"son5"/"son10"/"tum". Ad sabit varsayilirsa
    # KeyError ile duruluyor; islenen donem hangisiyse o alinir.
    anahtar = next((k for k in ("makale penceresi", "makale") if k in ozet),
                   None)
    if anahtar is None:
        print(f"\ntablolar ve figurler yazildi: {TABLO} , {FIG}")
        return
    ist, artik = ozet[anahtar]
    print("\n" + "=" * 76)
    print("DOGRULAMA: Ozturk & Yuksel (2023) Tablo 3, Bozyazi")
    print("=" * 76)
    print(f"  {'buyukluk':<26}{'makale':>10}{'bizim':>10}{'fark':>10}")
    print("-" * 76)
    for et, mv, bv in [
        ("azami aralik (cm)", MAKALE_NONTIDAL_MAX, ist["aralik_cm"]),
        ("standart sapma (cm)", MAKALE_NONTIDAL_STD, ist["std_cm"]),
        ("TD", MAKALE_TD, ist["TD"]),
        ("ortalama (cm)", 0.0, ist["ortalama_cm"]),
    ]:
        print(f"  {et:<26}{mv:>10.2f}{bv:>10.2f}{bv-mv:>+10.2f}")

    print(f"\ntablolar ve figurler yazildi: {TABLO} , {FIG}")


if __name__ == "__main__":
    main()
