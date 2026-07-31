# Bozyazı deniz seviyesi analizi

[![Colab'da aç](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/adzetto/marine_analysis/blob/main/su-seviyesi/colab_baslat.ipynb)

Bozyazı mareograf istasyonunun (TUDES / Harita Genel Müdürlüğü, istasyon
id 11) deniz seviyesi kaydından gelgit ve gelgit dışı bileşenlerin
çıkarılması.

Yukarıdaki düğme defteri doğrudan Colab'da açar. Çalıştırmadan önce
**yüksek RAM** çalışma zamanına geçin.

Konum: 36.104° K, 32.948° D — Levantin (Doğu Akdeniz) kıyısı.

## Ne yapılıyor

1. TUDES portalından 15 dakikalık seviye kaydının indirilmesi
2. Hatalı ölçümlerin ayıklanması (sıçrama, sürekli blok, takılmış sensör)
3. Ortalama deniz seviyesi (MSL)
4. Harmonik analiz — gelgit bileşenlerinin genlik ve fazları
5. Standart gelgit düzeyleri (HAT, MHWS, MHHW, MHW, MHWN, MSL, MLWN,
   MLW, MLLW, MLWS, LAT)
6. Gelgit dışı (non-tidal) su seviyesi: dağılım, PDF/CDF, aşılma

## Analiz dönemi

Birincil ve tek analiz dönemi **01.01.2010 – 13.03.2018**, yani makalenin
Bozyazı penceresi. Makale 2009'da başlıyor ama portalda Bozyazı kaydı 2010
başında başlıyor; bitiş tarihi makaleyle birebir aynı tutuldu ki sonuçlar
yayımlanmış değerlerle doğrudan karşılaştırılabilsin.

Bu aynı zamanda kaydın en sağlam bölümü (aşağıya bakınız). Başka pencereler
gerekirse `ortak.EK_DONEMLER` içinde hazır duruyor.

## Veri

Portal `POST /Portal/VeriSorgula` uç noktasıyla JSON döndürüyor; sayfadaki
"CSV indir" düğmesi sunucuya gitmeyen bir istemci tarafı export olduğu için
kullanılmıyor. Tek istekte en fazla **60 gün** alınabiliyor, bu yüzden kayıt
55 günlük parçalar hâlinde indirilip birleştiriliyor.

Kapsam: **2010-01-01 → bugün**, ~566.000 kayıt, %97,4 doluluk.

Veri kalitesi yıllara göre çok değişiyor:

| Dönem | Durum |
|---|---|
| 2010–2019 | Temiz, %99,7–100 dolu |
| 2020–2022 | Bozulma başlıyor |
| 2023–2024 | Ağır bozuk (−371 m ve +776 m gibi okumalar) |
| 2025–2026 | %93 ve %79 dolu |

Bu yüzden birincil sonuçlar **2010–2019** dönemi üzerinden veriliyor; bu
aynı zamanda karşılaştırma yapılan makalenin penceresiyle örtüşüyor.
"Son beş yıl" (2021–2025) ayrıca raporlanıyor.

## Doğrulama

Sonuçlar Ozturk & Yuksel (2023), *Regional Studies in Marine Science* 61,
102848 — "Tidal and non-tidal sea level analysis in enclosed and inland
basins" çalışmasının Bozyazı satırlarına karşı sınanıyor. O çalışma
2009–2018 dönemini ve MATLAB T_TIDE'ı kullanmış; burada aynı yöntemin
sürdürülen Python karşılığı UTide kullanılıyor.

Yayımlanmış Bozyazı değerleri (genlikler cm):

| M₂ | S₂ | N₂ | K₂ | K₁ | O₁ | P₁ | S₁ | S_SA | S_A | F | E |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 9,39 | 5,48 | 1,56 | 1,66 | 2,54 | 1,91 | 0,88 | 0,82 | 3,89 | 9,42 | 0,30 | 0,09 |

Gelgit dışı: azami aralık 129 cm, ortalama ≈0, σ = 10,43 cm, TD = 1,06.

## Betikler

Sırayla çalıştırılır:

| Betik | İş |
|---|---|
| `01_tudes_indir.py` | Portaldan 55 günlük parçalar hâlinde indirir (`data/ham/` önbelleğe alınır) |
| `02_veri_birlestir.py` | Parçaları birleştirir, ham `.dat` yazar, veriyi profiller |
| `03_veri_ayikla.py` | Hatalı ölçümleri ayıklar, boşlukları doldurur, MSL hesaplar |
| `04_ayiklama_dogrula.py` | Ayıklamanın doğru şeyi sildiğini sınar |
| `05_harmonik_analiz.py` | UTide harmonik çözümü, makaleyle karşılaştırma, trend |
| `06_gelgit_seviyeleri.py` | Standart gelgit düzeyleri tablosu |
| `07_non_tidal.py` | Gelgit dışı bileşen, PDF/CDF, TD |
| `08_istasyon_karsilastir.py` | Komşu istasyonlarla karşılaştırma (trend sorusu) |

`ortak.py` paylaşılan sabitleri ve işlevleri tutar — tek tanım yeri.

## Deniz seviyesi trendi hakkında

Yıllık ortalamalar doğrusal değil, **V biçimli**: kendi ortalamasından sapma
2010'da +6,0 cm, 2017'de −11,1 cm, 2024'te +8,9 cm. Bir V'nin inen koluna
doğru çekilen doğru eğilim değil, o kolun eğimidir — nitekim 2010–2019 için
−11,3 mm/yıl, 2021–2026 için +4,6 mm/yıl çıkıyor.

`08_istasyon_karsilastir.py` bu V'nin **Taşucu, Erdemli ve Antalya'da da
aynı şekilde bulunduğunu** gösterdi (2017 minimumu dördünde de var,
r = 0,75–0,81). Yani sinyal bölgesel ve gerçek, Bozyazı'nın cihaz hatası
değil. Ancak 16 yıl, on yıllık değişkenliğin baskın olduğu bir seride trend
kestirmek için kısadır; güvenilir bir deniz seviyesi trendi genelde 30+ yıl
ister.

Bağımsız doğrulama yolu: TUDES aylık ortalamalarını her yıl **PSMSL**'e
gönderiyor ve PSMSL kayıtları röpere indirgenmiş (RLR) olduğu için trend
sorusu asıl orada yanıtlanmalıdır.

## Veri kalitesi üzerine

TUDES 10 saniyede bir ölçüp **15 dakikalık ortalama** yazıyor; yani
elimizdeki değerler anlık değil. Tekil elektriksel gürültü bu ortalamada
zaten sönümlendiği için geriye kalan sivriler gerçek arızadır.

Portalın kendi kaydında 1.066 boşluk olayı var: 694'ü tek ölçüm (15 dk),
204'ü 2–4 ölçüm, 158'i 1 saat–1 gün, 10'u 1 günden uzun. Olayların %84'ü
bir saatten kısa. 1 günden kısa boşluklar interpolasyonla doldurulur
(makalenin izlediği kural).

## Kurulum

```bash
pip install -r requirements.txt
python 01_tudes_indir.py
python 02_veri_birlestir.py
python 03_veri_ayikla.py
python 05_harmonik_analiz.py
python 06_gelgit_seviyeleri.py
python 07_non_tidal.py
```

Colab için `colab_baslat.ipynb` kullanılabilir.

## Kaynak yükü

`05` betiği 15 dakikalık çözünürlükte, 16 yıllık kayıtta çalışırken UTide'ın
en küçük kareler tasarım matrisi **~9 GB** bellek istiyor. 16 GB'lık bir
makinede takasa giriyor; bol bellekli bir ortamda (Colab yüksek-RAM vb.)
sorunsuz çalışır.

## Notlar

- Seviyeler istasyonun **yerel datumunda**; ülke yükseklik sistemine
  bağlanmış değil. Gelgit düzeyleri ve artıklar için sorun değil, çünkü
  hepsi göreli büyüklükler.
- Zaman damgaları UTC.
- Depoda ham veri tutulmuyor; `01_tudes_indir.py` yeniden üretir.
