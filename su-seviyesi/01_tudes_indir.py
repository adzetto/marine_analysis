"""
01_tudes_indir.py
=================
Bozyazi mareograf istasyonunun deniz seviyesi verisini TUDES portalindan
(Harita Genel Mudurlugu) indirir.

Portal nasil calisiyor
----------------------
https://tudes.harita.gov.tr/Portal/VeriSorgula sayfasindaki "Bul" dugmesi
su cagriyi atiyor:

    POST /Portal/VeriSorgula
    __RequestVerificationToken, IstasyonId, VeriCesit,
    BaslamaTarihi, BitisTarihi          (tarihler g.AA.yyyy)

Yanit JSON:  {"Durum":1, "Mesaj":"", "Data":[{"Id":..,"Deger":1.4782,
                                              "Tarih":1735689600000}, ...]}
"Tarih" epoch milisaniye (UTC), "Deger" metre.

Sayfadaki "CSV indir" dugmesi sunucuya gitmez; amCharts4'un istemci tarafi
export'udur. Yani veriyi almak icin CSV'ye hic gerek yok, JSON dogrudan
alinabiliyor. Formdaki Ad Soyad / E-posta / Kurum / lisans onayi alanlari
ayri bir forma (frmDownload) ait ve yalnizca indirme KAYDI tutmak icin;
sorgunun kendisi bunlari istemiyor.

Sinir: tek istekte en fazla 60 gun ("Tarih araligi en fazla 60 gun
olmalidir"). Hocanin "en fazla 1 ay" bilgisi bu yuzden fazla temkinliydi.

SSL notu
--------
Sunucu ara sertifikayi gondermiyor; Python'un certifi zinciri
tamamlayamadigi icin dogrulama basarisiz oluyor. Dogrulamayi KAPATMAK
yerine truststore ile Windows sertifika deposu kullaniliyor.

Onbellek
--------
Her parca data/ham/ altina JSON olarak yazilir. Betik tekrar
calistirildiginda mevcut parcalar atlanir; yalniz eksikler indirilir.

Calistirma:  python 01_tudes_indir.py
"""

import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

import truststore
truststore.inject_into_ssl()
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
HAM = BASE / "data" / "ham"

SORGU = "https://tudes.harita.gov.tr/Portal/VeriSorgula"
ISTASYON = "11"          # Bozyazi
ISTASYON_ADI = "Bozyazi"
VERI_CESIDI = "DenizSeviyesi"

# Portalda Bozyazi icin en eski veri 2010 basi. Bugune kadar indirilir.
BASLANGIC = dt.date(2010, 1, 1)
BITIS = dt.date.today()

PARCA_GUN = 55           # 60 gun sinirinin altinda guvenli pay
BEKLE_SN = 0.7           # sunucuyu yormamak icin istekler arasi bekleme
TOKEN_OMRU = 40          # kac istekte bir token/oturum yenilensin

AJAN = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")


def oturum_ac():
    """Yeni oturum + antiforgery token dondurur."""
    s = requests.Session()
    s.headers.update({"User-Agent": AJAN})
    h = s.get(SORGU, timeout=60).text
    m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', h)
    if not m:
        raise RuntimeError("Sayfada __RequestVerificationToken bulunamadi.")
    return s, m.group(1)


def parcalar(bas, bit, gun):
    """[bas, bit] araligini en fazla `gun` uzunlugunda dilimlere boler."""
    t = bas
    while t <= bit:
        son = min(t + dt.timedelta(days=gun - 1), bit)
        yield t, son
        t = son + dt.timedelta(days=1)


def tarih_yaz(d):
    """Portalin bekledigi bicim: gun basinda sifir yok -> 1.03.2010"""
    return f"{d.day}.{d.month:02d}.{d.year}"


def indir(s, tok, bas, bit, deneme=4):
    veri = {
        "__RequestVerificationToken": tok,
        "IstasyonId": ISTASYON,
        "VeriCesit": VERI_CESIDI,
        "BaslamaTarihi": tarih_yaz(bas),
        "BitisTarihi": tarih_yaz(bit),
    }
    basliklar = {"X-Requested-With": "XMLHttpRequest", "Referer": SORGU}
    for k in range(deneme):
        try:
            r = s.post(SORGU, data=veri, headers=basliklar, timeout=300)
            r.raise_for_status()
            j = r.json()
        except Exception as e:
            if k == deneme - 1:
                raise
            print(f"      ! {type(e).__name__}, yeniden deneniyor "
                  f"({k+1}/{deneme-1})")
            time.sleep(5 * (k + 1))
            continue

        if j.get("Durum") == 1:
            return j.get("Data") or []
        mesaj = (j.get("Mesaj") or "").strip()
        # Gercekten veri yoksa bos donmek dogru sonuctur, hata degil.
        if "bulunamad" in mesaj.lower():
            return []
        raise RuntimeError(f"Portal reddetti: {mesaj!r}")
    return []


def main():
    HAM.mkdir(parents=True, exist_ok=True)
    dilimler = list(parcalar(BASLANGIC, BITIS, PARCA_GUN))

    print("=" * 72)
    print(f"TUDES INDIRME  |  istasyon: {ISTASYON_ADI} (id={ISTASYON})")
    print(f"aralik: {BASLANGIC} -> {BITIS}   ({len(dilimler)} parca x "
          f"{PARCA_GUN} gun)")
    print("=" * 72)

    s, tok = oturum_ac()
    sayac = 0
    toplam = 0
    yeni = 0

    for i, (a, b) in enumerate(dilimler, 1):
        hedef = HAM / f"bozyazi_{a:%Y%m%d}_{b:%Y%m%d}.json"
        if hedef.exists():
            n = len(json.loads(hedef.read_text(encoding="utf-8")))
            toplam += n
            print(f"[{i:3d}/{len(dilimler)}] {a} -> {b}  onbellek  {n:>6,} kayit")
            continue

        if sayac and sayac % TOKEN_OMRU == 0:
            s, tok = oturum_ac()
            print("      (oturum yenilendi)")

        d = indir(s, tok, a, b)
        hedef.write_text(json.dumps(d), encoding="utf-8")
        sayac += 1
        yeni += 1
        toplam += len(d)
        bekl = (b - a).days * 96 + 96
        print(f"[{i:3d}/{len(dilimler)}] {a} -> {b}  indi      "
              f"{len(d):>6,} kayit  (%{100*len(d)/bekl:.0f})")
        time.sleep(BEKLE_SN)

    print("-" * 72)
    print(f"parca: {len(dilimler)}  (yeni indirilen {yeni})")
    print(f"toplam kayit: {toplam:,}")
    print(f"ham dosyalar: {HAM}")


if __name__ == "__main__":
    main()
