"""
00_hepsini_calistir.py
======================
Butun analizi tek komutla bastan sona calistirir ve sonuclari GitHub'a
gonderir.

Adimlar
-------
    1  ayiklamanin dogrulanmasi                    (04)
    2  donem donem analiz: makale / son5 / son10 / tum   (13)
    3  zincirin dort istasyonda dogrulanmasi       (12)
    4  azami araligin yillik oynamasi              (09)
    5  komsu istasyonlarla deniz seviyesi kiyasi   (08)
    6  Excel kitabi                                (10)
    7  GitHub'a gonderim                           (11)

Dayaniklilik
------------
Her adim ayri bir surecte calisir ve ciktisini HEMEN diske yazar. Bir adim
bellek yetmedigi ya da baska bir sebeple durursa digerleri calismaya devam
eder; sonunda hangi adimin durdugu raporlanir. Boylece uzun bir kosuda tek
bir hata butun sonuclari goturmuyor.

En agir adim 2: her donem 15 dakikalik cozunurlukte ayri bir en kucuk
kareler cozumu demek. Bol bellekli bir ortam gerekir.

Calistirma:
    python 00_hepsini_calistir.py                 # hepsi + gonderim
    python 00_hepsini_calistir.py --gondermeden   # yalniz hesap
"""

import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent

ADIMLAR = [
    ("Ayiklamanin dogrulanmasi", ["04_ayiklama_dogrula.py"], False),
    ("Donem: makale penceresi", ["13_donem_kosucu.py", "makale"], True),
    ("Donem: son bes yil", ["13_donem_kosucu.py", "son5"], True),
    ("Donem: son on yil", ["13_donem_kosucu.py", "son10"], True),
    ("Donem: kaydin tamami", ["13_donem_kosucu.py", "tum"], True),
    ("Yuksek kabarmalarin ortalamasi",
     ["14_yuksek_kabarma_ortalamasi.py"], False),
    ("Dort istasyonda dogrulama", ["12_cok_istasyon_dogrula.py"], True),
    ("Azami araligin yillik oynamasi", ["09_azami_aralik_tani.py"], True),
    ("Komsu istasyon kiyaslamasi", ["08_istasyon_karsilastir.py"], False),
    ("Excel kitabi", ["10_excel_olustur.py"], False),
]


def calistir(baslik, komut, agir):
    print("\n" + "#" * 78)
    print(f"# {baslik}" + ("   [agir]" if agir else ""))
    print("#" * 78, flush=True)
    t0 = time.time()
    p = subprocess.run([sys.executable, "-u"] + komut, cwd=str(BASE))
    sure = time.time() - t0
    if p.returncode:
        print(f"\n!! DURDU (cikis kodu {p.returncode}, {sure/60:.1f} dk) "
              f"-- sonraki adima geciliyor", flush=True)
        return False, sure
    print(f"\n-- bitti ({sure/60:.1f} dk)", flush=True)
    return True, sure


def main():
    gonder = "--gondermeden" not in sys.argv
    print("=" * 78)
    print("BOZYAZI SU SEVIYESI - TAM KOSU")
    print("=" * 78)
    try:
        import psutil
        gb = psutil.virtual_memory().total / 1e9
        print(f"RAM: {gb:.1f} GB")
        if gb < 20:
            print("UYARI: agir adimlar icin 20+ GB onerilir. Dusuk bellekte")
            print("       donem cozumleri durabilir; digerleri yine calisir.")
    except Exception:
        pass

    sonuc = []
    for baslik, komut, agir in ADIMLAR:
        ok, sure = calistir(baslik, komut, agir)
        sonuc.append((baslik, ok, sure))

    print("\n" + "=" * 78)
    print("OZET")
    print("=" * 78)
    for baslik, ok, sure in sonuc:
        print(f"  {'TAMAM' if ok else 'DURDU':<7}{sure/60:>7.1f} dk   {baslik}")
    basarili = sum(1 for _, ok, _ in sonuc if ok)
    toplam_sure = sum(s for _, _, s in sonuc)
    print("-" * 78)
    print(f"  {basarili}/{len(sonuc)} adim tamamlandi, "
          f"toplam {toplam_sure/60:.1f} dakika")

    print("\n--- uretilen dosyalar ---")
    for kls in ("tables", "figures", "data"):
        p = BASE / kls
        if p.exists():
            n = len(list(p.glob("*")))
            mb = sum(f.stat().st_size for f in p.rglob("*")
                     if f.is_file()) / 1e6
            print(f"  {kls:<10}{n:>5} dosya{mb:>10.1f} MB")
    for x in BASE.glob("*.xlsx"):
        print(f"  {x.name:<10}{x.stat().st_size/1e6:>19.1f} MB")

    if gonder:
        ok, _ = calistir("GitHub'a gonderim",
                         ["11_sonuclari_pushla.py",
                          "Tam kosu - butun donemler ve dogrulamalar"],
                         False)
        if not ok:
            print("\nGonderim yapilamadi. GITHUB_TOKEN tanimli mi?")
            print("Sonuclar diskte duruyor; zip olarak indirebilirsiniz.")
    else:
        print("\n(--gondermeden verildi, GitHub'a gonderilmedi)")


if __name__ == "__main__":
    main()
