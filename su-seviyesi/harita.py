"""
harita.py
=========
Figurlerin kosesine, istasyonun yerini yildizla gosteren kucuk bir konum
haritasi cizer. Makale Fig. 6'daki ic haritanin ayni islevi.

Neden hazir bir harita kutuphanesi kullanilmiyor
------------------------------------------------
cartopy/basemap kiyi cizgisini calisma aninda indirir; Colab'da bu ek bir
kurulum ve ag bagimliligi demek. Onun yerine Natural Earth 50m kara
poligonlari bir kez bolgeye kirpilip sadelestirildi ve depoya konuldu
(data/kiyi_dogu_akdeniz.npz, 327 nokta / 4 KB). Cizim yalniz numpy ve
matplotlib ile yapiliyor.

M_MAP gorunumu
--------------
MATLAB'daki M_MAP paketinin alisildik ic harita bicimi taklit edilir:
ince cerceve, acik gri kara dolgusu, koyu kiyi cizgisi, deniz adlari
kucuk italik, istasyon kirmizi yildiz.
"""

from pathlib import Path

import numpy as np
from matplotlib.patches import Polygon

VERI = Path(__file__).resolve().parent / "data"
KIYI = VERI / "kiyi_dogu_akdeniz.npz"

# Ic haritanin gosterdigi alan (bati, dogu, guney, kuzey)
KAPSAM = (25.0, 42.0, 33.2, 43.5)

KARA = "#d9d4c5"
KIYI_RENK = "#4a4a4a"
DENIZ = "#eef3f7"
YILDIZ = "#c0392b"

# Makaledeki ic haritada oldugu gibi havza adlari.
# "Levantine Sea" hem Kibris'in (32.3-34.6 D, 34.5-35.7 K) uzerine
# gelmeyecek hem de sol kenardan tasmayacak sekilde yerlestirildi.
DENIZLER = [
    (34.5, 42.9, "Black Sea"),
    (33.5, 39.0, "Turkey"),
    (30.2, 33.8, "Levantine Sea"),
]


def halkalar():
    """Kirpilmis kara poligonlarini dondurur."""
    if not KIYI.exists():
        return []
    with np.load(KIYI) as z:
        return [z[k] for k in z.files]


def konum_haritasi(ax, lon, lat, konum="sol_ust", boyut=0.30,
                   etiketler=True, yazi=7.0):
    """Verilen eksenin kosesine konum haritasi yerlestirir.

    ax       : ana eksen
    lon,lat  : yildizla isaretlenecek istasyon
    konum    : "sol_ust" | "sag_ust" | "sol_alt" | "sag_alt"
    boyut    : ana eksenin genisliginin kesri
    """
    hs = halkalar()
    if not hs:
        return None

    b, d, g, k = KAPSAM
    en_boy = (k - g) / (d - b)          # yukseklik/genislik
    w = boyut
    h = boyut * en_boy * 1.15           # eksen en-boy orani icin duzeltme

    pay = 0.025
    yer = {
        "sol_ust": (pay, 1 - pay - h),
        "sag_ust": (1 - pay - w, 1 - pay - h),
        "sol_alt": (pay, pay),
        "sag_alt": (1 - pay - w, pay),
    }[konum]

    iax = ax.inset_axes([yer[0], yer[1], w, h])
    iax.set_facecolor(DENIZ)

    for p in hs:
        iax.add_patch(Polygon(p, closed=True, facecolor=KARA,
                              edgecolor=KIYI_RENK, linewidth=0.35,
                              zorder=2))

    if etiketler:
        for x, y, ad in DENIZLER:
            iax.text(x, y, ad, fontsize=yazi - 1.2, style="italic",
                     ha="center", va="center", color="#33475b", zorder=4)

    iax.plot([lon], [lat], marker="*", ms=yazi + 3.5, color=YILDIZ,
             markeredgecolor="white", markeredgewidth=0.5, zorder=5)

    iax.set_xlim(b, d)
    iax.set_ylim(g, k)
    iax.set_xticks([])
    iax.set_yticks([])
    for s in iax.spines.values():
        s.set_linewidth(0.6)
        s.set_color("#333333")
    iax.patch.set_alpha(0.97)
    return iax
