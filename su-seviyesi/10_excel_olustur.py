"""
10_excel_olustur.py
===================
Butun analizi tek bir Excel kitabinda toplar: ham veri, ayiklanmis veri,
kurulan gelgit, gelgit disi artik, harmonik bilesenler, gelgit duzeyleri ve
figurler.

Ruzgar analizindeki kitaplardan farki
-------------------------------------
D3/D4 ruzgar kitaplarinda her sonuc hucre formuluyle hesaplaniyordu
(COUNTIFS vb.), cunku oradaki islemler sayma ve oranlamaydi. Burada
durum farkli: harmonik cozum 300 bin noktali bir en kucuk kareler
problemi, gelgit duzeyleri 19 yillik bir ongorunun uc noktalarindan
cikiyor. Bunlar Excel hucre formulleriyle yapilamaz. Bu yuzden kitap
SONUCLARI tasiyor; uretimi Python betikleri yapiyor ve her sonucun hangi
betikten geldigi kitapta yaziyor.

Onkosul: 03, 05, 06, 07 calistirilmis olmali.
Calistirma: python 10_excel_olustur.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xlsxwriter

from ortak import (FIG, TABLO, VERI, ENLEM, BOYLAM, ISTASYON, YAZAR,
                   PAPER_BAS, PAPER_BIT, MAKALE_GENLIK, MAKALE_NONTIDAL_STD,
                   MAKALE_TD, kes, oku, veri_yolu)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CIKTI = Path(__file__).resolve().parent / "BOZYAZI_SU_SEVIYESI.xlsx"

# Donem kodu SABIT YAZILMAZ, diskten bulunur.
#
# Betikler donem kodunu cagirma bicimine gore uretiyor: dogrudan
# calistirildiginda "makale_penceresi", 13_donem_kosucu.py'den
# calistirildiginda "makale"/"son5"/"son10"/"tum". Kod burada sabit
# yazildiginda dosya adlari tutmuyor ve sayfalar SESSIZCE bos kaliyordu
# (gelgit duzeyleri, PDF/CDF verisi ve grafigi, yuzdelikler, gomulu
# figurler, 01_VERI'nin gelgit ve artik sutunlari).
SLUG = "makale"
KODLAR = [SLUG]


def donem_kodlari():
    """Diskteki ciktilardan hangi donemlerin uretildigini bulur."""
    k = {p.stem.replace("02_gelgit_duzeyleri_", "")
         for p in TABLO.glob("02_gelgit_duzeyleri_*.csv")}
    sira = {"makale": 0, "makale_penceresi": 0, "son5": 1, "son10": 2,
            "tum": 3}
    return sorted(k, key=lambda x: (sira.get(x, 9), x))


def guvenli_oku(ad):
    try:
        return oku(ad)
    except FileNotFoundError:
        return None


def csv_oku(ad):
    p = TABLO / ad
    return pd.read_csv(p) if p.exists() else None


def resim_ekle(ws, satir, sutun, png, olcek=0.62):
    p = FIG / png
    if p.exists():
        ws.insert_image(satir, sutun, str(p),
                        {"x_scale": olcek, "y_scale": olcek})
        return True
    return False


def main():
    global SLUG, KODLAR
    KODLAR = donem_kodlari()
    if KODLAR:
        SLUG = KODLAR[0]
        print(f"bulunan donemler: {', '.join(KODLAR)}")
        print(f"birincil donem  : {SLUG}")
    else:
        KODLAR = [SLUG]
        print(f"UYARI: tables/ altinda donem ciktisi yok, '{SLUG}' "
              f"varsayiliyor. Once 13_donem_kosucu.py calistirilmali.")

    print("veriler okunuyor...")
    ham = guvenli_oku("bozyazi_ham.dat")
    temiz = guvenli_oku("bozyazi_temiz.dat")
    gelgit = guvenli_oku(f"bozyazi_gelgit_{SLUG}.dat")
    artik = guvenli_oku(f"bozyazi_artik_{SLUG}.dat")
    if temiz is None:
        sys.exit("HATA: bozyazi_temiz.dat yok. Once 03 calistirilmali.")
    if gelgit is None:
        print("UYARI: gelgit/artik serileri yok (05 calismamis). "
              "Kitap onlarsiz uretilecek.")

    wb = xlsxwriter.Workbook(str(CIKTI), {"default_date_format":
                                          "yyyy-mm-dd hh:mm"})
    wb.set_properties({"title": f"{ISTASYON} deniz seviyesi analizi",
                       "author": YAZAR})

    bic = {
        "baslik": wb.add_format({"bold": True, "font_size": 13,
                                 "font_color": "#1F3864"}),
        "alt": wb.add_format({"bold": True, "font_size": 10,
                              "font_color": "#404040"}),
        "bas": wb.add_format({"bold": True, "bg_color": "#1F3864",
                              "font_color": "white", "border": 1,
                              "align": "center", "valign": "vcenter",
                              "text_wrap": True}),
        "s4": wb.add_format({"num_format": "0.0000", "border": 1}),
        "s3": wb.add_format({"num_format": "0.000", "border": 1}),
        "s2": wb.add_format({"num_format": "0.00", "border": 1}),
        "s1": wb.add_format({"num_format": "0.0", "border": 1}),
        "tam": wb.add_format({"num_format": "#,##0", "border": 1}),
        "met": wb.add_format({"border": 1}),
        "tar": wb.add_format({"num_format": "yyyy-mm-dd hh:mm", "border": 1}),
        "not": wb.add_format({"font_size": 9, "italic": True,
                              "font_color": "#606060", "text_wrap": True}),
        "vur": wb.add_format({"num_format": "0.000", "border": 1,
                              "bold": True, "bg_color": "#FFF2CC"}),
    }

    # ---------------------------------------------------------------- 00
    ws = wb.add_worksheet("00_OZET")
    ws.set_column(0, 0, 38)
    ws.set_column(1, 3, 20)
    r = 0
    ws.write(r, 0, f"{ISTASYON} mareograf istasyonu - deniz seviyesi analizi",
             bic["baslik"]); r += 2

    x = kes(temiz, PAPER_BAS, PAPER_BIT)
    ozet = [
        ("Istasyon", f"{ISTASYON} (TUDES id 11)"),
        ("Konum", f"{ENLEM} K, {BOYLAM} D"),
        ("Kaynak", "TUDES / Harita Genel Mudurlugu"),
        ("Olcum araligi", "15 dakika (10 sn olcumun ortalamasi)"),
        ("Kayit", f"{ham.index.min():%Y-%m-%d} .. "
                  f"{ham.index.max():%Y-%m-%d}" if ham is not None else "-"),
        ("Ham olcum", len(ham) if ham is not None else 0),
        ("Ayiklama sonrasi", len(temiz)),
        ("", ""),
        ("ANALIZ PENCERESI", f"{PAPER_BAS} .. {PAPER_BIT}"),
        ("Neden bu pencere", "Makalenin (Ozturk & Yuksel 2023) Bozyazi "
                             "penceresiyle ortusen en genis aralik"),
        ("Penceredeki olcum", len(x)),
        ("MSL (istasyon datumu)", round(float(x.mean()), 4)),
        ("", ""),
        ("Datum notu", "Seviyeler istasyonun YEREL datumunda; ulke "
                       "yukseklik sistemine baglanmis degil"),
        ("Zaman", "UTC"),
    ]
    for k, v in ozet:
        if k:
            ws.write(r, 0, k, bic["alt"])
            ws.write(r, 1, v)
        r += 1

    r += 1
    ws.write(r, 0, "SAYFALAR", bic["baslik"]); r += 1
    for k, v in [
        ("01_VERI", "ham, ayiklanmis, kurulan gelgit ve artik seriler"),
        ("02_BILESENLER", "harmonik gelgit bilesenleri (05_harmonik_analiz)"),
        ("03_GELGIT_DUZEYLERI", "HAT..LAT (06_gelgit_seviyeleri)"),
        ("04_NONTIDAL", "gelgit disi su seviyesi (07_non_tidal)"),
        ("05_DENIZ_SEVIYESI", "yillik ortalamalar, istasyon karsilastirmasi"),
        ("06_FIGURLER", "uretilen butun grafikler"),
    ]:
        ws.write(r, 0, k, bic["alt"])
        ws.write(r, 1, v)
        r += 1

    r += 1
    ws.write(r, 0,
             "NOT: Bu kitaptaki sonuclar hucre formulleriyle uretilmemistir. "
             "Harmonik cozum 300 bin noktali bir en kucuk kareler problemi, "
             "gelgit duzeyleri 19 yillik bir ongorunun uc noktalari; ikisi "
             "de Excel formulleriyle yapilamaz. Uretim Python betikleriyle "
             "yapilmis, her sayfada hangi betikten geldigi yazilmistir.",
             bic["not"])
    ws.set_row(r, 46)

    # ---------------------------------------------------------------- 01
    print("01_VERI yaziliyor...")
    ws = wb.add_worksheet("01_VERI")
    ws.set_column(0, 0, 18)
    ws.set_column(1, 4, 13)
    ws.write(0, 0, "Butun seriler tek izgarada. Bos hucre = o anda olcum yok "
                   "ya da ayiklanmis.", bic["not"])
    bas = ["Zaman (UTC)", "Ham (m)", "Ayiklanmis (m)",
           "Kurulan gelgit (m)", "Artik = olculen - gelgit (m)"]
    for j, b in enumerate(bas):
        ws.write(1, j, b, bic["bas"])
    ws.freeze_panes(2, 1)

    izgara = ham.index if ham is not None else temiz.index
    d = pd.DataFrame(index=izgara)
    d["ham"] = ham
    d["temiz"] = temiz
    if gelgit is not None:
        d["gelgit"] = gelgit
        d["artik"] = artik
    else:
        d["gelgit"] = np.nan
        d["artik"] = np.nan

    # tz bilgisi Excel'e yazilamaz; UTC oldugu baslikta belirtiliyor
    zaman = d.index.tz_localize(None)
    for i, (t, sat) in enumerate(zip(zaman, d.itertuples(index=False)), 2):
        ws.write_datetime(i, 0, t, bic["tar"])
        for j, v in enumerate(sat, 1):
            if v is not None and np.isfinite(v):
                ws.write_number(i, j, float(v), bic["s4"])
    print(f"   {len(d):,} satir")

    # ---------------------------------------------------------------- 02
    ws = wb.add_worksheet("02_BILESENLER")
    ws.set_column(0, 0, 14)
    ws.set_column(1, 6, 16)
    r = 0
    ws.write(r, 0, "Harmonik gelgit bilesenleri", bic["baslik"]); r += 1
    ws.write(r, 0, "UTide (Codiga) ile cozuldu; T_TIDE'in surdurulen Python "
                   "karsiligi. Yalniz SNR > 2 olan bilesenler. "
                   "Kaynak: 05_harmonik_analiz.py", bic["not"])
    ws.set_row(r, 26); r += 2

    # --- hocanin istedigi bicimde (Famagusta Tablo 2-2), BUTUN DONEMLER ---
    fams = {k: csv_oku(f"09_famagusta_bicimi_{k}.csv") for k in KODLAR}
    fams = {k: v for k, v in fams.items() if v is not None}
    if fams:
        ws.write(r, 0, "Hocanin istedigi bicimde (Famagusta Tablo 2-2)",
                 bic["alt"]); r += 1
        ws.write(r, 0, "Her donem icin ayri ayri. Gelgit astronomik bir "
                       "olgu oldugu icin genlikler donemden doneme "
                       "neredeyse degismemeli.", bic["not"])
        ws.set_row(r, 26); r += 1
        ws.write(r, 0, "Bilesen", bic["bas"])
        for i, k in enumerate(fams):
            ws.merge_range(r - 1, 1 + 2 * i, r - 1, 2 + 2 * i, k, bic["bas"])
            ws.write(r, 1 + 2 * i, "Genlik [m]", bic["bas"])
            ws.write(r, 2 + 2 * i, "Faz [deg]", bic["bas"])
        r += 1
        ilk = next(iter(fams.values()))
        for idx in range(len(ilk)):
            ws.write(r, 0, str(ilk.iloc[idx, 0]), bic["met"])
            for i, d_ in enumerate(fams.values()):
                for j, sut in enumerate(("Amplitude [m]", "Phase [deg]")):
                    v = d_.iloc[idx][sut] if idx < len(d_) else None
                    if pd.notna(v):
                        ws.write_number(r, 1 + 2 * i + j, float(v),
                                        bic["s4"] if j == 0 else bic["s1"])
            r += 1
        r += 2

    ws.write(r, 0, "Cozulen butun bilesenler", bic["alt"]); r += 1
    bil = csv_oku(f"01_gelgit_bilesenleri_{SLUG}.csv")
    if bil is not None:
        bas = ["Bilesen", "Genlik (m)", "Genlik (cm)", "Hata (cm)",
               "Faz (derece)", "SNR", "Makale (cm)"]
        for j, b in enumerate(bas):
            ws.write(r, j, b, bic["bas"])
        r += 1
        for _, s in bil.iterrows():
            mk = MAKALE_GENLIK.get(s.bilesen)
            ws.write(r, 0, s.bilesen, bic["met"])
            ws.write_number(r, 1, s.genlik_cm / 100.0, bic["s4"])
            ws.write_number(r, 2, s.genlik_cm,
                            bic["vur"] if mk else bic["s3"])
            ws.write_number(r, 3, s.genlik_hata_cm, bic["s3"])
            ws.write_number(r, 4, s.faz_derece, bic["s1"])
            ws.write_number(r, 5, s.SNR, bic["tam"])
            if mk:
                ws.write_number(r, 6, mk, bic["s2"])
            r += 1
        r += 1
        ws.write(r, 0, "Sari hucreler makalede de raporlanan bilesenler; "
                       "son sutun yayimlanmis deger.", bic["not"])
    else:
        ws.write(r, 0, "05_harmonik_analiz.py henuz calistirilmamis.")

    # ---------------------------------------------------------------- 03
    ws = wb.add_worksheet("03_GELGIT_DUZEYLERI")
    ws.set_column(0, 0, 10)
    ws.set_column(1, 1, 36)
    ws.set_column(2, 5, 18)
    r = 0
    ws.write(r, 0, "Gelgit duzeyleri", bic["baslik"]); r += 1
    ws.write(r, 0, "19 yillik astronomik ongoruden (18.6 yillik nodal "
                   "dongu) sayilarak. Dogrusal egim ongoruye katilmaz; "
                   "HAT/LAT tanimi geregi astronomik uc degerlerdir. "
                   "Kaynak: 06_gelgit_seviyeleri.py", bic["not"])
    ws.set_row(r, 32); r += 2

    duzs = {k: csv_oku(f"02_gelgit_duzeyleri_{k}.csv") for k in KODLAR}
    duzs = {k: v for k, v in duzs.items() if v is not None}
    if not duzs:
        d0 = csv_oku("02_gelgit_duzeyleri.csv")
        if d0 is not None:
            duzs = {SLUG: d0}
    if duzs:
        ws.write(r, 0, "Butun donemler icin, MSL'e gore (m)", bic["alt"])
        r += 1
        ws.write(r, 0, "Duzey", bic["bas"])
        ws.write(r, 1, "Aciklama", bic["bas"])
        for i, k in enumerate(duzs):
            ws.write(r, 2 + 2 * i, f"{k}", bic["bas"])
            ws.write(r, 3 + 2 * i, f"{k} (mevsimsiz)", bic["bas"])
        son = 2 + 2 * len(duzs)
        ws.write(r, son, "formul (m)", bic["bas"])
        ws.write(r, son + 1, f"{SLUG} istasyon datumu (m)", bic["bas"])
        r += 1
        ilk = next(iter(duzs.values()))
        for idx in range(len(ilk)):
            s0 = ilk.iloc[idx]
            ws.write(r, 0, s0.duzey, bic["met"])
            ws.write(r, 1, s0.aciklama, bic["met"])
            for i, d_ in enumerate(duzs.values()):
                sr = d_[d_.duzey == s0.duzey]
                if not len(sr):
                    continue
                sr = sr.iloc[0]
                ws.write_number(r, 2 + 2 * i, float(sr.su_seviyesi_m_MSL),
                                bic["vur"])
                v = sr.get("su_seviyesi_m_MSL_mevsimsel_haric")
                if pd.notna(v):
                    ws.write_number(r, 3 + 2 * i, float(v), bic["s3"])
            for j, k in enumerate(["formul_m_MSL", "istasyon_datumu_m"]):
                v = s0.get(k)
                if pd.notna(v):
                    ws.write_number(r, son + j, float(v), bic["s3"])
            r += 1
        r += 1
        ws.write(r, 0, "SA (yillik) ve SSA (yarim yillik) bu istasyonda "
                       "M2'den buyuk ama buyuk olcude isinimsal/mevsimsel. "
                       "Denizcilik tablolari kisa periyotlu gravitasyonel "
                       "gelgiti verir; iki surum de sunuldu.", bic["not"])
        ws.set_row(r, 32)

    # ---------------------------------------------------------------- 04
    ws = wb.add_worksheet("04_NONTIDAL")
    ws.set_column(0, 0, 26)
    ws.set_column(1, 6, 16)
    r = 0
    ws.write(r, 0, "Gelgit disi (non-tidal) su seviyesi", bic["baslik"])
    r += 1
    ws.write(r, 0, "artik = olculen - kurulan gelgit. Kaynak: "
                   "07_non_tidal.py", bic["not"])
    r += 2

    # Ozet iki kaynaktan derlenir.
    #
    # 03_nontidal_ozet.csv bir donemde eksik kalabiliyor (07 eskiden her
    # kosuda ustune yaziyordu). 10_donem_karsilastirma.csv ise butun
    # donemleri tasiyor ama en dusuk/en yuksek sutunlari yok. Ikisi
    # birlestirilir; boylece eski ciktilarla da dogru kitap uretiliyor.
    oz = csv_oku("03_nontidal_ozet.csv")
    dk0 = csv_oku("10_donem_karsilastirma.csv")
    if dk0 is not None:
        t = dk0[["donem", "nontidal_ortalama_cm", "nontidal_std_cm",
                 "nontidal_aralik_cm", "TD"]].rename(columns={
            "nontidal_ortalama_cm": "ortalama_cm",
            "nontidal_std_cm": "std_cm",
            "nontidal_aralik_cm": "aralik_cm"})
        if oz is not None:
            t = t.merge(oz[["donem", "min_cm", "max_cm"]], on="donem",
                        how="left")
        oz = t
    if oz is not None:
        for j, b in enumerate(["Donem", "Ortalama (cm)", "Std sapma (cm)",
                               "En dusuk (cm)", "En yuksek (cm)",
                               "Aralik (cm)", "TD"]):
            ws.write(r, j, b, bic["bas"])
        r += 1
        for _, s in oz.iterrows():
            ws.write(r, 0, s.donem, bic["met"])
            for j, k in enumerate(["ortalama_cm", "std_cm", "min_cm",
                                   "max_cm", "aralik_cm", "TD"], 1):
                v = s.get(k)
                if pd.notna(v):
                    ws.write_number(r, j, float(v),
                                    bic["vur"] if k in ("std_cm", "TD")
                                    else bic["s2"])
            r += 1
        r += 1
        ws.write(r, 0, "ONEMLI: artigin ORTALAMASI tanimi geregi sifirdir "
                       "(seriden hem gelgit hem ortalama seviye "
                       "cikarilmistir). Makalenin Tablo 3'unde de 18 "
                       "istasyonun hepsi icin 'Mean = 0' yazar. Dagilimi "
                       "temsil eden buyukluk STANDART SAPMA ve asagidaki "
                       "yuzdeliklerdir.", bic["not"])
        ws.set_row(r, 46); r += 2
        ws.write(r, 0, f"Makale ile karsilastirma (Tablo 3, Bozyazi) - "
                       f"{SLUG} donemi", bic["alt"]); r += 1
        for j, b in enumerate(["Buyukluk", "Makale", "Bizim"]):
            ws.write(r, j, b, bic["bas"])
        r += 1
        # Karsilastirma MAKALE PENCERESIYLE yapilmali; ilk satir alinirsa
        # tabloya hangi donem once yazildiysa o kiyaslanir ve yanlis
        # sonuc cikar.
        sr = oz[oz.donem == SLUG]
        ana = sr.iloc[0] if len(sr) else oz.iloc[0]
        for et, mv, bv in [("Standart sapma (cm)", MAKALE_NONTIDAL_STD,
                            float(ana.std_cm)),
                           ("TD", MAKALE_TD, float(ana.TD)),
                           ("Ortalama (cm)", 0.0, float(ana.ortalama_cm))]:
            ws.write(r, 0, et, bic["met"])
            ws.write_number(r, 1, mv, bic["s2"])
            ws.write_number(r, 2, bv, bic["s2"])
            r += 1

    # --- PDF/CDF verisi + Excel'in kendi grafigi ---
    hist = csv_oku(f"01_nontidal_pdf_cdf_{SLUG}_veri.csv")
    if hist is not None:
        r += 2
        ws.write(r, 0, "PDF / CDF grafiginin verisi", bic["alt"]); r += 1
        ws.write(r, 0, "Asagidaki sayilar figurde cizilen degerlerin ta "
                       "kendisi. Yandaki grafik bu hucrelerden kuruludur; "
                       "hucreler degistirilirse grafik de degisir.",
                 bic["not"])
        ws.set_row(r, 26); r += 1
        veri_bas = r
        for j, b in enumerate(["Kutu ortasi (m)", "Kutu ortasi (cm)",
                               "Sayim", "PDF", "CDF",
                               "Kutu alt (m)", "Kutu ust (m)"]):
            ws.write(r, j, b, bic["bas"])
        r += 1
        ilk = r
        for _, s in hist.iterrows():
            ws.write_number(r, 0, float(s.kutu_orta_m), bic["s4"])
            ws.write_number(r, 1, float(s.kutu_orta_cm), bic["s2"])
            ws.write_number(r, 2, int(s.sayim), bic["tam"])
            ws.write_number(r, 3, float(s.PDF), bic["s4"])
            ws.write_number(r, 4, float(s.CDF), bic["s4"])
            ws.write_number(r, 5, float(s.kutu_alt_m), bic["s4"])
            ws.write_number(r, 6, float(s.kutu_ust_m), bic["s4"])
            r += 1
        son = r - 1

        sh = "04_NONTIDAL"
        ch = wb.add_chart({"type": "scatter",
                           "subtype": "straight_with_markers"})
        ch.add_series({
            "name": "PDF (olusum olasiligi)",
            "categories": [sh, ilk, 0, son, 0],
            "values": [sh, ilk, 3, son, 3],
            "line": {"color": "#C0392B", "width": 1.75},
            "marker": {"type": "circle", "size": 4,
                       "fill": {"color": "#C0392B"}},
        })
        ch.add_series({
            "name": "CDF (asilmama olasiligi)",
            "categories": [sh, ilk, 0, son, 0],
            "values": [sh, ilk, 4, son, 4],
            "line": {"color": "#1F4E9C", "width": 1.75},
            "marker": {"type": "none"},
            "y2_axis": True,
        })
        ch.set_x_axis({"name": "Gelgit disi su seviyesi (m)",
                       "major_gridlines": {"visible": True}})
        ch.set_y_axis({"name": "PDF", "major_gridlines": {"visible": True}})
        ch.set_y2_axis({"name": "CDF", "min": 0, "max": 1})
        ch.set_title({"name": "Bozyazi - gelgit disi su seviyesi dagilimi"})
        ch.set_size({"width": 640, "height": 420})
        ch.set_legend({"position": "bottom"})
        ws.insert_chart(veri_bas, 8, ch)

        if resim_ekle(ws, veri_bas + 23, 8,
                      f"01_nontidal_pdf_cdf_{SLUG}.png", 0.55):
            ws.write(veri_bas + 22, 8,
                     "Ayni dagilimin betikle uretilen surumu "
                     "(istasyon konumu yildizla):", bic["alt"])

    r += 1
    yuzs = {k: csv_oku(f"04_nontidal_yuzdelikler_{k}.csv") for k in KODLAR}
    yuzs = {k: v for k, v in yuzs.items() if v is not None}
    if yuzs:
        ws.write(r, 0, "Asilma yuzdelikleri (cm) - butun donemler",
                 bic["alt"]); r += 1
        ws.write(r, 0, "Hocanin sordugu 'ortalama' yerine dagilimi temsil "
                       "eden buyukluk budur. Ornek: %95 satiri, seviyenin "
                       "zamanin %95'inde bu degerin altinda kaldigini "
                       "gosterir.", bic["not"])
        ws.set_row(r, 26); r += 1
        ws.write(r, 0, "Yuzdelik (%)", bic["bas"])
        for i, k in enumerate(yuzs):
            ws.write(r, 1 + i, f"{k} (cm)", bic["bas"])
        ws.write(r, 1 + len(yuzs), f"{SLUG} (m)", bic["bas"])
        r += 1
        ilk = next(iter(yuzs.values()))
        for idx in range(len(ilk)):
            p_ = float(ilk.iloc[idx].yuzdelik)
            ws.write_number(r, 0, p_, bic["s1"])
            for i, d_ in enumerate(yuzs.values()):
                sr = d_[d_.yuzdelik == p_]
                if len(sr):
                    ws.write_number(r, 1 + i, float(sr.iloc[0].seviye_cm),
                                    bic["s2"])
            ws.write_number(r, 1 + len(yuzs),
                            float(ilk.iloc[idx].seviye_cm) / 100.0,
                            bic["s4"])
            r += 1

    # ---------------------------------------------------------------- 05
    ws = wb.add_worksheet("05_DENIZ_SEVIYESI")
    ws.set_column(0, 0, 12)
    ws.set_column(1, 6, 16)
    r = 0
    ws.write(r, 0, "Deniz seviyesi degisimi", bic["baslik"]); r += 1
    ws.write(r, 0, "Yillik ortalamalar dogrusal degil V bicimli; 2017'de "
                   "minimum. Ayni V komsu istasyonlarda da var, yani isaret "
                   "BOLGESEL. Bir V'nin inen koluna cekilen dogru trend "
                   "degildir. Kaynak: 08_istasyon_karsilastir.py",
             bic["not"])
    ws.set_row(r, 32); r += 2

    yil = temiz.groupby(temiz.index.year).mean()
    say = temiz.groupby(temiz.index.year).count()
    for j, b in enumerate(["Yil", "Ortalama seviye (m)", "Olcum sayisi"]):
        ws.write(r, j, b, bic["bas"])
    r += 1
    for y in yil.index:
        ws.write_number(r, 0, int(y), bic["tam"])
        ws.write_number(r, 1, float(yil[y]), bic["s4"])
        ws.write_number(r, 2, int(say[y]), bic["tam"])
        r += 1

    # --- donemler yan yana ---
    dk = csv_oku("10_donem_karsilastirma.csv")
    if dk is not None and len(dk) > 1:
        r += 2
        ws.write(r, 0, "Ayni analiz farkli donemlerde", bic["alt"]); r += 1
        ws.write(r, 0, "Gelgit bilesenleri (M2, F) donemden doneme "
                       "neredeyse degismez -- gelgit astronomik bir "
                       "olgudur. Gelgit DISI istatistikler ise "
                       "meteorolojiye bagli oldugu icin degisir. Kaynak: "
                       "13_donem_kosucu.py", bic["not"])
        ws.set_row(r, 32); r += 1
        sut = ["donem", "yil", "olcum", "MSL_m", "M2_m", "F",
               "nontidal_std_cm", "TD", "nontidal_aralik_cm"]
        basl = ["Donem", "Yil", "Olcum", "MSL (m)", "M2 (m)", "F",
                "Gelgit disi std (cm)", "TD", "Azami aralik (cm)"]
        for j, b in enumerate(basl):
            ws.write(r, j, b, bic["bas"])
        r += 1
        for _, s in dk.iterrows():
            for j, k in enumerate(sut):
                v = s.get(k)
                if isinstance(v, str):
                    ws.write(r, j, v, bic["met"])
                elif pd.notna(v):
                    ws.write_number(r, j, float(v),
                                    bic["tam"] if k == "olcum"
                                    else bic["s4"] if k in ("MSL_m", "M2_m")
                                    else bic["s3"])
            r += 1

    # --- azami araligin yillik oynamasi ---
    yl = csv_oku("07_yillik_azami_aralik.csv")
    if yl is not None:
        r += 2
        ws.write(r, 0, "Gelgit disi azami araligin yillik oynamasi",
                 bic["alt"]); r += 1
        ws.write(r, 0, "Azami aralik TEK BIR OLAYA baglidir. Asagida "
                       "yildan yila ne kadar oynadigi goruluyor; standart "
                       "sapma ise cok daha kararli. Makaleyle aradaki fark "
                       "bu sacilmanin icinde kaliyor. Kaynak: "
                       "09_azami_aralik_tani.py", bic["not"])
        ws.set_row(r, 32); r += 1
        for j, b in enumerate(["Yil", "std (cm)", "en dusuk (cm)",
                               "en yuksek (cm)", "ARALIK (cm)"]):
            ws.write(r, j, b, bic["bas"])
        r += 1
        for _, s in yl.iterrows():
            ws.write_number(r, 0, int(s.yil), bic["tam"])
            for j, k in enumerate(["std_cm", "min_cm", "max_cm",
                                   "aralik_cm"], 1):
                ws.write_number(r, j, float(s[k]),
                                bic["vur"] if k == "aralik_cm"
                                else bic["s2"])
            r += 1

    # --- cok istasyonlu dogrulama ---
    ci = csv_oku("08_cok_istasyon_dogrulama.csv")
    if ci is not None:
        r += 2
        ws.write(r, 0, "Zincirin dort istasyonda dogrulanmasi", bic["alt"])
        r += 1
        ws.write(r, 0, "Ayni ayiklama ve ayni harmonik cozum, makalenin "
                       "sonuc verdigi diger Levantin istasyonlarina da "
                       "uygulandi. Kaynak: 12_cok_istasyon_dogrula.py",
                 bic["not"])
        ws.set_row(r, 26); r += 1
        for j, b in enumerate(ci.columns):
            ws.write(r, j, str(b), bic["bas"])
        r += 1
        for _, s in ci.iterrows():
            for j, k in enumerate(ci.columns):
                v = s[k]
                if isinstance(v, str):
                    ws.write(r, j, v, bic["met"])
                elif pd.notna(v):
                    ws.write_number(r, j, float(v), bic["s3"])
            r += 1

    kar = csv_oku("06_istasyon_yillik_sapma.csv")
    if kar is not None:
        r += 1
        ws.write(r, 0, "Istasyon karsilastirmasi - yillik ortalamanin "
                       "kendi ortalamasindan sapmasi (cm)", bic["alt"])
        r += 1
        for j, b in enumerate(kar.columns):
            ws.write(r, j, str(b), bic["bas"])
        r += 1
        for _, s in kar.iterrows():
            for j, k in enumerate(kar.columns):
                v = s[k]
                if pd.isna(v):
                    continue
                ws.write_number(r, j, float(v),
                                bic["tam"] if j == 0 else bic["s1"])
            r += 1

    # ---------------------------------------------------------------- 06
    print("06_FIGURLER yaziliyor...")
    ws = wb.add_worksheet("06_FIGURLER")
    ws.set_column(0, 0, 4)
    r = 0
    ws.write(r, 1, "Uretilen figurler", bic["baslik"]); r += 2
    figurler = []
    for k in KODLAR:
        figurler += [
            (f"01_nontidal_pdf_cdf_{k}.png",
             f"[{k}] Gelgit disi su seviyesi - PDF / CDF "
             f"(makaledeki gibi 10 kutu)"),
            (f"01b_nontidal_pdf_cdf_ince_{k}.png",
             f"[{k}] Ayni dagilim, ince kutulama (2 cm)"),
            (f"02_nontidal_zaman_serisi_{k}.png",
             f"[{k}] Gelgit disi su seviyesinin zaman serisi"),
        ]
    for png, baslik in figurler + [
        ("03_istasyon_karsilastirma.png",
         "Levantin kiyisi istasyonlari - yillik ortalama seviye"),
        ("00_dogrulama_temmuz2025.png",
         "Ayiklama dogrulamasi - Temmuz 2025 (blok hata)"),
        ("00_dogrulama_eylul2025.png",
         "Ayiklama dogrulamasi - Eylul 2025 (tekil sivri)"),
        ("00_dogrulama_nisan2024.png",
         "Ayiklama dogrulamasi - 27 Nisan 2024"),
        ("00_tani_kesikler.png",
         "Kesiklerin kaynagi: portalda olmayan olcumler"),
    ]:
        ws.write(r, 1, baslik, bic["alt"])
        r += 1
        if resim_ekle(ws, r, 1, png):
            r += 28
        else:
            ws.write(r, 1, "(figur bulunamadi)", bic["not"])
            r += 2

    wb.close()
    mb = CIKTI.stat().st_size / 1024 / 1024
    print(f"\nyazildi: {CIKTI}  ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
