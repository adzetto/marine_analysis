"""
06_gelgit_seviyeleri.py
=======================
Cozulen harmonik bilesenlerden standart gelgit duzeylerini uretir:
HAT, MHWS, MHHW, MHW, MHWN, MSL, MLWN, MLW, MLLW, MLWS, LAT.

Hocanin ornek olarak gonderdigi tablo (Famagusta, Kibris - IHO) tam olarak
bu satirlardan olusuyor; cikti onunla ayni bicimde verilir.

Nasil hesaplaniyor
------------------
Duzeyler dogrudan olcumden degil, cozulen bilesenlerden URETILEN gelgit
ongorusunden cikarilir. Bunun nedeni HAT/LAT'in tanimi geregi *astronomik*
uc degerler olmasi: firtina kabarmasi gibi meteorolojik katkilar
girmemelidir. Ongoru 18.6 yillik nodal dongunun tamamini kapsayacak sekilde
19 yil boyunca uretilir; aksi halde HAT/LAT sistematik olarak kucuk cikar.

Bahar (spring) ve olusum (neap) ayrimi veriye dayali yapilir: M2 ile S2
arasindaki vurum 14.77 gunluk bir zarf uretir; gunluk gelgit genliginin
yerel tepe noktalari bahar, yerel dip noktalari olusum gelgitidir.

Iki yontem birden raporlanir:
  * ampirik : 19 yillik ongoruden dogrudan sayilarak (BIRINCIL)
  * formul  : MHWS = MSL + (H_M2 + H_S2), MHWN = MSL + (H_M2 - H_S2) ...
              denizcilik el kitaplarindaki klasik yaklasiklik

Calistirma: python 06_gelgit_seviyeleri.py
"""

import sys

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

from ortak import (TABLO, PAPER_BAS, PAPER_BIT, bilesen_sozlugu, coz, kes,
                   kur, oku)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ANALIZ_A, ANALIZ_B = PAPER_BAS, PAPER_BIT   # bilesenlerin cozuldugu donem
ONGORU_YIL = 19                      # 18.6 yillik nodal dongu icin
ADIM_DK = 10                         # ongoru adimi (uc degerleri kacirmamak)
VURUM_GUN = 14.765                   # M2-S2 bahar/olusum vurum periyodu


def uc_noktalar(y):
    """Yerel tepe ve dip indekslerini dondurur."""
    tepe = argrelextrema(y, np.greater, order=3)[0]
    dip = argrelextrema(y, np.less, order=3)[0]
    return tepe, dip


def main():
    s = oku()
    x = kes(s, ANALIZ_A, ANALIZ_B)
    msl_gozlem = float(x.mean())

    print("=" * 76)
    print(f"GELGIT DUZEYLERI - Bozyazi   (bilesenler {ANALIZ_A}-{ANALIZ_B})")
    print("=" * 76)
    print(f"gozlenen MSL (ayiklanmis veri) = {msl_gozlem:.4f} m "
          f"(istasyon yerel datumu)")

    coef = coz(x)
    h = bilesen_sozlugu(coef)

    # --- 19 yillik astronomik ongoru ---
    #
    # DIKKAT: egim KAPATILIR. UTide'in reconstruct'i dogrusal egimi
    # varsayilan olarak ekliyor; 19 yillik bir ongoruye -18.7 mm/yil
    # eklenince tahmin ~35 cm suruklenir ve HAT-LAT yapay olarak buyur.
    # HAT/LAT tanimi geregi ASTRONOMIK uc degerlerdir; ne meteorolojik
    # katki ne de ekstrapole edilmis bir egilim girmelidir.
    t = pd.date_range(ANALIZ_A, periods=int(ONGORU_YIL * 365.25 * 24 * 60
                                            / ADIM_DK),
                      freq=f"{ADIM_DK}min")
    ong = kur(pd.Series(0.0, index=t.tz_localize("UTC")), coef,
              trend=False, min_SNR=2)
    y = np.asarray(ong.h, float)
    # Ongoru mutlak datumda gelir; MSL'e gore merkezle.
    y = y - np.nanmean(y)
    print(f"ongoru: {t[0].date()} -> {t[-1].date()}  "
          f"({len(t):,} adim, {ADIM_DK} dk, egim haric)")

    # --- SA/SSA'siz surum ---
    #
    # SA (yillik) ve SSA (yarim yillik) bu istasyonda 9.4 ve 4.2 cm, yani
    # M2'den (9.6 cm) buyuk. Ancak bunlar buyuk olcude ISINIMSAL/mevsimsel
    # (suyun mevsimlik isinip genlesmesi), gravitasyonel gelgit degil.
    # Denizcilik gelgit tablolari (hocanin ornek verdigi Famagusta IHO
    # tablosu gibi) tipik olarak kisa periyotlu gravitasyonel gelgiti
    # verir; mevsimsel dongu ayri raporlanir. Ikisi de hesaplanir.
    mevsimsel = {"SA", "SSA", "MSM", "MM", "MSF", "MF"}
    kisa_ad = [a for a in coef["name"] if a not in mevsimsel]
    ong2 = kur(pd.Series(0.0, index=t.tz_localize("UTC")), coef,
               trend=False, constit=kisa_ad, min_SNR=2)
    y2 = np.asarray(ong2.h, float)
    y2 = y2 - np.nanmean(y2)
    HAT2, LAT2 = float(np.nanmax(y2)), float(np.nanmin(y2))

    tepe, dip = uc_noktalar(y)
    HW, LW = y[tepe], y[dip]
    tHW, tLW = t[tepe], t[dip]
    print(f"bulunan yuksek su : {len(HW):,}   alcak su : {len(LW):,}")

    # --- gunluk (gelgit gunu) yuksek/alcak ---
    gHW = pd.Series(HW, index=tHW).resample("1D").max().dropna()
    gLW = pd.Series(LW, index=tLW).resample("1D").min().dropna()

    # --- bahar / olusum ayrimi: gunluk genligin vurum zarfi ---
    ortak_gun = gHW.index.intersection(gLW.index)
    genlik = (gHW[ortak_gun] - gLW[ortak_gun])
    pencere = int(round(VURUM_GUN / 2))          # ~7 gun
    g = genlik.values
    bahar_i = argrelextrema(g, np.greater, order=pencere)[0]
    olusum_i = argrelextrema(g, np.less, order=pencere)[0]
    bahar_gun = ortak_gun[bahar_i]
    olusum_gun = ortak_gun[olusum_i]
    print(f"bahar gelgiti     : {len(bahar_gun):,} olay   "
          f"olusum gelgiti : {len(olusum_gun):,} olay")
    print(f"ortalama gelgit genligi (HHW-LLW) = {genlik.mean()*100:.1f} cm")

    def gun_ort(seri, gunler):
        return float(seri.reindex(gunler).dropna().mean())

    # HW/LW'yi bahar-olusum gunlerine gore ayir
    hw_ser = pd.Series(HW, index=tHW)
    lw_ser = pd.Series(LW, index=tLW)
    hw_gun = hw_ser.groupby(hw_ser.index.normalize()).mean()
    lw_gun = lw_ser.groupby(lw_ser.index.normalize()).mean()

    duzey = {
        "HAT": float(np.nanmax(y)),
        "MHWS": gun_ort(hw_gun, bahar_gun),
        "MHHW": float(gHW.mean()),
        "MHW": float(HW.mean()),
        "MHWN": gun_ort(hw_gun, olusum_gun),
        "MSL": 0.0,
        "MLWN": gun_ort(lw_gun, olusum_gun),
        "MLW": float(LW.mean()),
        "MLLW": float(gLW.mean()),
        "MLWS": gun_ort(lw_gun, bahar_gun),
        "LAT": float(np.nanmin(y)),
    }

    # --- formul yaklasikligi ---
    M2 = h.get("M2", {}).get("A", 0.0) / 100.0
    S2 = h.get("S2", {}).get("A", 0.0) / 100.0
    formul = {"MHWS": M2 + S2, "MHWN": M2 - S2,
              "MSL": 0.0, "MLWN": -(M2 - S2), "MLWS": -(M2 + S2)}

    aciklama = {
        "HAT": "En yuksek astronomik gelgit",
        "MHWS": "Bahar gelgiti ortalama yuksek su",
        "MHHW": "Ortalama yuksek-yuksek su",
        "MHW": "Ortalama yuksek su",
        "MHWN": "Olusum gelgiti ortalama yuksek su",
        "MSL": "Ortalama deniz seviyesi",
        "MLWN": "Olusum gelgiti ortalama alcak su",
        "MLW": "Ortalama alcak su",
        "MLLW": "Ortalama alcak-alcak su",
        "MLWS": "Bahar gelgiti ortalama alcak su",
        "LAT": "En dusuk astronomik gelgit",
    }

    print("\n" + "=" * 76)
    print("GELGIT DUZEYLERI  (MSL'e gore, m)")
    print("=" * 76)
    print(f"  {'duzey':<7}{'aciklama':<38}{'ampirik':>10}{'formul':>10}"
          f"{'datum m':>10}")
    print("-" * 76)
    for k, v in duzey.items():
        f_ = formul.get(k)
        fs = f"{f_:+.3f}" if f_ is not None else "-"
        print(f"  {k:<7}{aciklama[k]:<38}{v:>+10.3f}{fs:>10}"
              f"{msl_gozlem+v:>10.3f}")

    print(f"\n  Ortalama gelgit araligi (MHWS-MLWS) = "
          f"{(duzey['MHWS']-duzey['MLWS'])*100:.1f} cm")
    print(f"  Azami astronomik aralik (HAT-LAT)   = "
          f"{(duzey['HAT']-duzey['LAT'])*100:.1f} cm")

    print("\n" + "=" * 76)
    print("HAT / LAT: MEVSIMSEL BILESENLER HARIC")
    print("=" * 76)
    print(f"  {'':<34}{'SA/SSA dahil':>16}{'SA/SSA haric':>16}")
    print(f"  {'HAT (m, MSL ustu)':<34}{duzey['HAT']:>+16.3f}{HAT2:>+16.3f}")
    print(f"  {'LAT (m, MSL alti)':<34}{duzey['LAT']:>+16.3f}{LAT2:>+16.3f}")
    print(f"  {'aralik (cm)':<34}"
          f"{(duzey['HAT']-duzey['LAT'])*100:>16.1f}"
          f"{(HAT2-LAT2)*100:>16.1f}")
    print()
    print("  SA = 9.4 cm ve SSA = 4.2 cm bu istasyonda M2'den (9.6 cm)")
    print("  buyuk, ama buyuk olcude isinimsal/mevsimsel: suyun mevsimlik")
    print("  isinip genlesmesi. Denizcilik gelgit tablolari (hocanin ornek")
    print("  verdigi Famagusta IHO tablosu gibi) kisa periyotlu")
    print("  gravitasyonel gelgiti verir. Karsilastirma icin:")
    print("    Famagusta  HAT +0.23 / LAT -0.22, M2+S2 = 0.183 m")
    print(f"    Bozyazi    HAT {HAT2:+.2f} / LAT {LAT2:+.2f}, "
          f"M2+S2 = {M2+S2:.3f} m")
    print("  Hangisinin raporlanacagi hocaya sorulmalidir; ikisi de yazildi.")

    # --- yaz ---
    TABLO.mkdir(parents=True, exist_ok=True)
    yol = TABLO / "02_gelgit_duzeyleri.csv"
    haric = {"HAT": HAT2, "LAT": LAT2}
    with open(yol, "w", encoding="utf-8") as fo:
        fo.write("duzey,aciklama,su_seviyesi_m_MSL,"
                 "su_seviyesi_m_MSL_mevsimsel_haric,formul_m_MSL,"
                 "istasyon_datumu_m\n")
        for k, v in duzey.items():
            f_ = formul.get(k)
            hv = haric.get(k)
            fo.write(f"{k},{aciklama[k]},{v:.4f},"
                     f"{'' if hv is None else f'{hv:.4f}'},"
                     f"{'' if f_ is None else f'{f_:.4f}'},"
                     f"{msl_gozlem+v:.4f}\n")
    print(f"\nyazildi: {yol}")


if __name__ == "__main__":
    main()
