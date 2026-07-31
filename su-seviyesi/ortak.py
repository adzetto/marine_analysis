"""
ortak.py
========
Su seviyesi analizinin butun betiklerinin paylastigi sabitler ve islevler.
Tek tanim yeri; bir yerde degistirilince hepsi degisir.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
import utide

BASE = Path(__file__).resolve().parent
VERI = BASE / "data"
TABLO = BASE / "tables"
FIG = BASE / "figures"

# Makale Tablo 1'deki istasyon konumu
ENLEM = 36.104
BOYLAM = 32.948
ISTASYON = "Bozyazi"
YAZAR = "MUHAMMET YAGCIOGLU"

# Makale Tablo 2, Bozyazi satiri (genlikler cm) - dogrulama hedefi
MAKALE_GENLIK = {"M2": 9.39, "S2": 5.48, "N2": 1.56, "K2": 1.66,
                 "K1": 2.54, "O1": 1.91, "P1": 0.88, "S1": 0.82,
                 "SSA": 3.89, "SA": 9.42}
MAKALE_F = 0.30
MAKALE_E = 0.09
# Makale Tablo 3, Bozyazi satiri
MAKALE_NONTIDAL_MAX = 129.0     # cm
MAKALE_NONTIDAL_STD = 10.43     # cm
MAKALE_TD = 1.06
MAKALE_MSL = 0.135              # m, Tablo 1

YARIGUNLUK = ["M2", "S2", "N2", "K2"]
GUNLUK = ["K1", "O1", "P1", "S1"]

# Birincil analiz donemi: makalenin Bozyazi penceresi.
#
# Makale 01.01.2009-13.03.2018 kullanmis. Portalda Bozyazi kaydi 1 Temmuz
# 2009'da basliyor (2009-06 ve oncesi "Veri bulunamadi"), yani makalenin
# ilk alti ayi alinamiyor. Baslangic portalin verebildigi en erken tarihe,
# bitis makaleyle birebir ayni tarihe konuldu; boylece ortusme en genis
# haliyle 8.7 yil oluyor ve sonuclar yayimlanmis degerlerle dogrudan
# karsilastirilabiliyor.
#
# Bu ayni zamanda kaydin en saglam bolumu: 2010-2019 doluluk %99.7-100,
# buna karsilik 2023'te -371/+776 m gibi okumalar, 2024'te saatlerce suren
# kaymis blok, 2025-2026'da %93 ve %79 doluluk var.
PAPER_BAS = "2009-07-01"
PAPER_BIT = "2018-03-13"

DONEMLER = [
    ("makale penceresi", PAPER_BAS, PAPER_BIT),
]

# Istege bagli ek pencereler. Hocanin "son bes yil" istegi ya da trend
# incelemesi icin DONEMLER'e eklenebilir; varsayilan olarak kapali, cunku
# her ek pencere 15 dakikalik cozunurlukte ayri bir en kucuk kareler
# cozumu demek.
EK_DONEMLER = [
    ("temiz on yil", "2010-01-01", "2019-12-31"),
    ("son bes yil", "2021-01-01", "2025-12-31"),
    ("tum kayit", "2010-01-01", "2026-12-31"),
]


def veri_yolu(dosya):
    """Verinin sikistirilmis ya da duz halini bulur.

    Depoya veri .gz olarak konuluyor (15 MB metin 2.3 MB'a iniyor). Yerelde
    calisirken duz .dat da olusabildigi icin once o aranir. pandas ve gzip
    uzantiya bakarak acmayi kendisi hallettiginden okuyucularin fark
    gormesi gerekmiyor.
    """
    p = VERI / dosya
    if p.exists():
        return p
    gz = VERI / (dosya + ".gz")
    if gz.exists():
        return gz
    raise FileNotFoundError(f"{p} ya da {gz} bulunamadi. Once 01/02/03 "
                            f"betiklerini calistirin.")


def yaz(seri, dosya, basliklar):
    """Seriyi .dat.gz olarak yazar.

    Ayni adin sikistirilmamis surumu varsa SILINIR. Aksi halde veri_yolu()
    onu tercih edip yeni yazilan .gz'i golgeliyor; betikler sessizce eski
    veriyle calisiyor. (Bir kez basimiza geldi: 2009 verisi eklendigi halde
    ayiklama eski kaydi okumaya devam etti.)
    """
    import gzip
    VERI.mkdir(parents=True, exist_ok=True)
    hedef = VERI / (dosya + ".gz")
    with gzip.open(hedef, "wt", encoding="utf-8") as f:
        for b in basliklar:
            f.write(f"# {b}\n")
        f.write("# yil ay gun saat dakika seviye_m\n")
        for t, v in seri.items():
            f.write(f"{t.year} {t.month:2d} {t.day:2d} {t.hour:2d} "
                    f"{t.minute:2d} {v:9.4f}\n")
    duz = VERI / dosya
    if duz.exists():
        duz.unlink()
        print(f"  (eski sikistirilmamis {duz.name} silindi)")
    return hedef


def oku(dosya="bozyazi_temiz.dat"):
    """Ayiklanmis seriyi UTC indeksli pandas Series olarak dondurur."""
    d = pd.read_csv(veri_yolu(dosya), sep=r"\s+", comment="#", header=None,
                    names=["yil", "ay", "gun", "saat", "dk", "sev"])
    t = pd.to_datetime(d[["yil", "ay", "gun", "saat", "dk"]].rename(columns={
        "yil": "year", "ay": "month", "gun": "day", "saat": "hour",
        "dk": "minute"}), utc=True)
    return pd.Series(d.sev.values, index=t, name="seviye")


def kes(s, a, b):
    """Seriyi [a, b] araligina keser.

    a ve b ya yil (int) ya da 'YYYY-AA-GG' metni olabilir. Metin verilirse
    bitis gunu tumuyle dahil edilir; boylece makale penceresinin bitisi
    (13.03.2018) birebir yakalanir.
    """
    if isinstance(a, int):
        return s[(s.index.year >= a) & (s.index.year <= b)]
    lo = pd.Timestamp(a, tz="UTC")
    hi = pd.Timestamp(b, tz="UTC") + pd.Timedelta(days=1)
    return s[(s.index >= lo) & (s.index < hi)]


def saatlik(s):
    """Seriyi saat basi degerlere seyreltir (ortalama ALMAZ).

    Analiz tam 15 dakikalik cozunurlukte yapilir; bu islev yalnizca hizli
    on deneme yapmak istendiginde kullanilir. Ortalama yerine anlik ornek
    alinir, cunku saatlik ORTALAMA hareketli ortalama filtresi gibi davranip
    kisa periyotlu bilesenlerin genligini sistematik olarak kucultur.
    """
    return s[s.index.minute == 0]


def coz(s, trend=True):
    """UTide harmonik cozumu.

    DIKKAT: utide'a zaman DatetimeIndex olarak verilmelidir. matplotlib 3.3
    ile date2num'un epoch'u 1970'e tasindigi icin sayisal datenum yolu bu
    surumde sessizce cokuyor (hic bilesen bulunamiyor, genlikler 1e10
    cikiyor). datetime yolu dogru sonucu veriyor.
    """
    t = s.index.tz_localize(None)
    return utide.solve(t, s.values, lat=ENLEM, method="ols",
                       conf_int="linear", nodal=True, trend=trend,
                       verbose=False)


def kur(s, coef, trend=True, constit=None, min_SNR=0):
    """Cozulen bilesenlerden gelgit ongorusu.

    trend
        UTide'in reconstruct'i dogrusal egimi VARSAYILAN olarak ongoruye
        ekler (_reconstruct.py: `trend = not coef.aux.opt.notrend`) ve bunu
        kapatan bir parametre sunmaz; bayrak cozumden tasinir. Burada gecici
        olarak degistirilip geri konuluyor.

        Bunun iki yerde onemi var:
          * Gelgit DUZEYLERI icin egim kapatilmalidir. HAT/LAT tanimi geregi
            astronomik uc degerlerdir; 19 yillik bir ongoruye -18.7 mm/yil
            eklenirse tahmin 35 cm suruklenir ve HAT-LAT yapay olarak buyur.
          * Gelgit DISI artik icin egim, makaleyle karsilastirilabilirlik
            adina ongoruden CIKARILMAMALIDIR: T_TIDE'da egim terimi yoktur,
            yani makalenin artigi bu suruklenmeyi hala icerir.

    constit
        Yalniz belirli bilesenlerle kurmak icin ad listesi. Ornegin mevsimsel
        SA/SSA haric tutulabilir.
    """
    t = s.index.tz_localize(None)
    opt = coef["aux"]["opt"]
    onceki = opt["notrend"]
    opt["notrend"] = not trend
    try:
        return utide.reconstruct(t, coef, verbose=False, min_SNR=min_SNR,
                                 constit=constit)
    finally:
        opt["notrend"] = onceki


def bilesen_sozlugu(coef):
    """utide cozumunu {ad: {A cm, g derece, A_ci cm, snr}} sozluguna cevirir."""
    ci = np.where(coef.A_ci > 0, coef.A_ci, np.nan)
    snr = (coef.A / ci) ** 2
    return {str(ad): {"A": a * 100.0, "g": float(g), "A_ci": c * 100.0,
                      "snr": float(sn)}
            for ad, a, g, c, sn in
            zip(coef.name, coef.A, coef.g, coef.A_ci, snr)}


def form_enerji(h):
    """Form faktoru F (makale Denk. 1) ve enerji faktoru E (Denk. 2)."""
    g = lambda k: h.get(k, {}).get("A", 0.0)
    payda = g("M2") + g("S2")
    F = (g("K1") + g("O1")) / payda if payda else np.nan
    ed = sum(g(k) ** 2 for k in GUNLUK)
    esd = sum(g(k) ** 2 for k in YARIGUNLUK)
    E = ed / esd if esd else np.nan
    return F, E


def gelgit_tipi(F):
    if not np.isfinite(F):
        return "-"
    if F < 0.25:
        return "yari-gunluk"
    if F < 1.50:
        return "karisik, agirlikli yari-gunluk (MSD)"
    if F < 3.0:
        return "karisik, agirlikli gunluk"
    return "gunluk"


def trend_mm_yil(coef):
    """utide'in dogrusal egimini mm/yil'a cevirir (egim birim/gun)."""
    if not hasattr(coef, "slope"):
        return np.nan
    return float(np.atleast_1d(coef.slope)[0]) * 365.25 * 1000.0
