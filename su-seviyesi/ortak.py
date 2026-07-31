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

DONEMLER = [
    ("makale penceresi", 2010, 2018),
    ("temiz on yil", 2010, 2019),
    ("son bes yil", 2021, 2025),
    ("tum kayit", 2010, 2026),
]


def oku(dosya="bozyazi_temiz.dat"):
    """Ayiklanmis seriyi UTC indeksli pandas Series olarak dondurur."""
    d = pd.read_csv(VERI / dosya, sep=r"\s+", comment="#", header=None,
                    names=["yil", "ay", "gun", "saat", "dk", "sev"])
    t = pd.to_datetime(d[["yil", "ay", "gun", "saat", "dk"]].rename(columns={
        "yil": "year", "ay": "month", "gun": "day", "saat": "hour",
        "dk": "minute"}), utc=True)
    return pd.Series(d.sev.values, index=t, name="seviye")


def kes(s, a, b):
    return s[(s.index.year >= a) & (s.index.year <= b)]


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


def kur(s, coef):
    """Cozulen bilesenlerden gelgit ongorusu (ayni zaman ekseninde)."""
    t = s.index.tz_localize(None)
    return utide.reconstruct(t, coef, verbose=False, min_SNR=0)


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
