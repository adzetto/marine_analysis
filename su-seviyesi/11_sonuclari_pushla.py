"""
11_sonuclari_pushla.py
======================
Uretilen butun ciktilari (tablolar, figurler, cozulmus seriler, Excel
kitabi) depoya gonderir. Colab'da calisan analizin sonucu boylece kalici
oluyor.

Kimlik dogrulama
----------------
Colab'da git kimlik bilgisi yok. Bir GitHub kisisel erisim jetonu (PAT)
gerekiyor:

    from google.colab import userdata
    import os
    os.environ["GITHUB_TOKEN"] = userdata.get("GITHUB_TOKEN")

Colab'in sol panelindeki anahtar simgesinden "GITHUB_TOKEN" adiyla
saklayabilirsiniz; boylece jeton defterin icine YAZILMAZ ve paylasilan
deftere sizmaz. Jetonu uretirken "repo" yetkisi yeterlidir.

Jeton uzak adrese yazilmaz, yalniz tek seferlik push komutunda kullanilir
ve ekrana basilan hicbir yerde gorunmez.

Calistirma:  python 11_sonuclari_pushla.py ["commit mesaji"]
"""

import os
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
DEPO = BASE.parent
KULLANICI = "adzetto"
AD = "marine_analysis"

# Sonuc olarak kabul edilen, .gitignore'a ragmen gonderilecek yollar.
SONUC_YOLLARI = [
    "su-seviyesi/tables",
    "su-seviyesi/figures",
    "su-seviyesi/data",
    "su-seviyesi/BOZYAZI_SU_SEVIYESI.xlsx",
]


def calistir(*args, **kw):
    return subprocess.run(args, cwd=str(DEPO), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", **kw)


def main():
    mesaj = (sys.argv[1] if len(sys.argv) > 1
             else "Analiz sonuclarini guncelle")

    if not (DEPO / ".git").exists():
        sys.exit(f"HATA: {DEPO} bir git deposu degil.")

    jeton = (os.environ.get("GITHUB_TOKEN")
             or os.environ.get("GH_TOKEN") or "").strip()
    if not jeton:
        print("GITHUB_TOKEN tanimli degil.\n")
        print("Colab'da:")
        print("    from google.colab import userdata")
        print("    import os")
        print("    os.environ['GITHUB_TOKEN'] = "
              "userdata.get('GITHUB_TOKEN')\n")
        print("Jetonu Colab'in sol panelindeki anahtar simgesinden "
              "saklayin ki deftere yazilmasin.")
        sys.exit(1)

    calistir("git", "config", "user.name", "Muhammet Yagcioglu")
    calistir("git", "config", "user.email",
             "muhammet.y.resmi@gmail.com")

    # Ciktilar .gitignore'da; sonuclari bilerek gonderiyoruz.
    for y in SONUC_YOLLARI:
        if (DEPO / y).exists():
            calistir("git", "add", "-A", "-f", y)

    d = calistir("git", "status", "--porcelain")
    if not d.stdout.strip():
        print("Degisiklik yok, gonderilecek bir sey bulunamadi.")
        return
    print("Gonderilecek:")
    for s in d.stdout.strip().splitlines()[:40]:
        print("   ", s)
    n = len(d.stdout.strip().splitlines())
    if n > 40:
        print(f"    ... ve {n-40} dosya daha")

    c = calistir("git", "commit", "-m", mesaj)
    if c.returncode:
        print(c.stdout, c.stderr)
        sys.exit("commit basarisiz")
    print("\n" + calistir("git", "log", "--oneline", "-1").stdout.strip())

    # Once uzaktakini al: Colab ile yerel makine arasinda ayrisma olabilir.
    uzak = f"https://x-access-token:{jeton}@github.com/{KULLANICI}/{AD}.git"
    p = calistir("git", "pull", "--rebase", uzak, "main")
    if p.returncode:
        print(p.stdout[-1500:], p.stderr[-1500:])
        sys.exit("pull --rebase basarisiz; catisma olabilir")

    p = calistir("git", "push", uzak, "HEAD:main")
    if p.returncode:
        # Jeton hata metnine sizmasin
        print(p.stderr.replace(jeton, "***")[-1500:])
        sys.exit("push basarisiz")

    print(f"\nGonderildi: https://github.com/{KULLANICI}/{AD}")


if __name__ == "__main__":
    main()
