# Kalkulator Average Down Saham & Compounding — ARA/ARB dan Right Issue (Python)

**Kalkulator average down saham** ini membantu Anda menghitung harga rata-rata beli, harga impas setelah fee, dan berapa lot yang perlu dibeli agar average turun ke target tertentu. Di dalamnya juga ada kalkulator compounding (bunga majemuk), kalkulator ARA/ARB yang mengikuti fraksi harga BEI terbaru, dan kalkulator right issue untuk menghitung harga teoretis. Semua rumus terbuka, sudah diuji dengan contoh nyata dari pengumuman BEI, dan berjalan offline dengan Python tanpa instal pustaka tambahan.

> 🛠️ Tool gratis & open source ini adalah karya **[JoinBareng](https://joinbareng.com)** — platform patungan langganan premium di Indonesia.

> ⚠️ **Bukan rekomendasi atau ajakan jual-beli saham.** Tool ini hanya alat hitung. Keputusan investasi sepenuhnya tanggung jawab Anda, jadi selalu lakukan riset sendiri (*DYOR — Do Your Own Research*).

## Daftar Isi

- [Apa Itu Kalkulator Average Down Saham?](#apa-itu-kalkulator-average-down-saham)
- [Fitur](#fitur)
- [Cara Install & Menjalankan](#cara-install--menjalankan)
- [Cara Pakai dan Contoh Output](#cara-pakai-dan-contoh-output)
- [Rumus & Contoh Hitung Langkah demi Langkah](#rumus--contoh-hitung-langkah-demi-langkah)
- [Tabel Fraksi Harga & Auto Rejection BEI](#tabel-fraksi-harga--auto-rejection-bei)
- [Risiko Average Down](#risiko-average-down)
- [Tips & Kesalahan Umum](#tips--kesalahan-umum)
- [FAQ](#faq)
- [Metodologi, Pengujian & Sumber](#metodologi-pengujian--sumber)
- [Tentang Pembuat](#tentang-pembuat)
- [Disclaimer](#disclaimer)
- [Kontribusi](#kontribusi)
- [Lisensi](#lisensi)
- [Dukung Proyek Ini](#dukung-proyek-ini)
- [Tools Lainnya dari Seri Ini](#tools-lainnya-dari-seri-ini)

## Apa Itu Kalkulator Average Down Saham?

*Average down* berarti membeli lagi saham yang sama saat harganya turun agar harga rata-rata ikut turun, sedangkan *average up* berarti menambah posisi saat harga naik. Kalkulator average down saham menjawab tiga pertanyaan praktis:

1. Berapa harga rata-rata saya setelah beberapa kali membeli?
2. Di harga berapa saya impas setelah fee beli dan fee jual?
3. Berapa lot yang harus saya beli di harga sekarang agar average menjadi Rp X?

Selain kalkulator average down, repo ini memuat kalkulator compounding, kalkulator ARA/ARB, dan kalkulator right issue. Bagi yang biasa memakai kalkulator saham online, hitungan yang sama di sini berjalan offline dan rumusnya bisa diperiksa.

## Fitur

- **`average`** (kalkulator average saham): rata-rata dari banyak pembelian (1 lot = 100 lembar), fee beli/jual yang bisa diatur (contoh default 0,15%/0,25%), harga impas sesuai fraksi, dan **target average** dengan deteksi target mustahil.
- **`compounding`** (kalkulator bunga majemuk): modal awal, setoran bulanan, return per tahun, durasi, frekuensi bulanan/tahunan, plus tabel per tahun.
- **`ara-arb`**: batas ARA/ARB hari berikutnya sesuai fraksi BEI, preset aturan (`terkini`, `simetris`, `akselerasi`), persentase kustom `--ara`/`--arb`, dan simulasi beruntun.
- **`right-issue`**: harga teoretis (TERP), nilai HMETD, dilusi, dan dampak ke average.
- **Mode interaktif** berbahasa Indonesia, tanpa dependency (Python 3.8+).

## Cara Install & Menjalankan

```bash
git clone https://github.com/redyopa2929/kalkulator-saham.git
cd kalkulator-saham
python3 kalkulator_saham.py
```

Tanpa argumen, tool membuka menu interaktif. Bantuan tersedia lewat `--help`, dan angka boleh ditulis gaya Indonesia (`1.250.000`, `0,15`) maupun internasional (`1250000`, `0.15`).

## Cara Pakai dan Contoh Output

Semua output di bawah adalah hasil asli menjalankan tool.

### Kalkulator average down saham dan target average

Misalkan Anda membeli 10 lot di Rp1.000, lalu 10 lot lagi di Rp900, dan ingin average turun ke Rp920 dengan membeli di Rp800:

```text
$ python3 kalkulator_saham.py average --beli 1000:10 900:10 --target-avg 920 --harga-beli 800
Rincian pembelian:
  1. 10 lot @ Rp1.000 = Rp1.000.000
  2. 10 lot @ Rp900 = Rp900.000
Total                : 20 lot (2.000 lembar)
Nilai pembelian      : Rp1.900.000
Fee beli (0,15%)     : Rp2.850,00
Total modal          : Rp1.902.850,00
Harga rata-rata      : Rp950,00 per lembar (tanpa fee)
Rata-rata + fee beli : Rp951,43 per lembar
Harga impas (BEP)    : Rp953,81 -> jual minimal Rp955 (fraksi Rp5, fee jual 0,25%)

Target average Rp920 dengan membeli di Rp800:
  Beli minimal       : 5 lot (500 lembar)
  Dana tambahan      : Rp400.000 + fee beli Rp600,00
  Average baru       : Rp920,00 (total 25 lot)
```

Bila target tidak mungkin dicapai, kalkulator average down menolak dengan jelas:

```text
$ python3 kalkulator_saham.py average --beli 1000:10 --target-avg 750 --harga-beli 800
Galat: Mustahil: membeli di Rp800 hanya bisa menurunkan average ke antara Rp800 dan Rp1.000,00. Target harus di rentang itu.
```

### Kalkulator compounding (bunga majemuk)

Modal Rp10 juta, setoran Rp1 juta per bulan, asumsi return 10% per tahun, selama 10 tahun:

```text
$ python3 kalkulator_saham.py compounding --modal 10000000 --setoran 1000000 --return 10 --tahun 10
Modal awal Rp10.000.000, setoran Rp1.000.000/bulan, return 10,00%/tahun, compounding bulanan, 10 tahun

Tahun |      Total setoran |        Imbal hasil |        Saldo akhir
--------------------------------------------------------------------
    1 |       Rp22.000.000 |        Rp1.612.699 |       Rp23.612.699
    2 |       Rp34.000.000 |        Rp4.650.825 |       Rp38.650.825
    3 |       Rp46.000.000 |        Rp9.263.640 |       Rp55.263.640
    4 |       Rp58.000.000 |       Rp15.616.033 |       Rp73.616.033
    5 |       Rp70.000.000 |       Rp23.890.162 |       Rp93.890.162
    6 |       Rp82.000.000 |       Rp34.287.256 |      Rp116.287.256
    7 |       Rp94.000.000 |       Rp47.029.620 |      Rp141.029.620
    8 |      Rp106.000.000 |       Rp62.362.832 |      Rp168.362.832
    9 |      Rp118.000.000 |       Rp80.558.189 |      Rp198.558.189
   10 |      Rp130.000.000 |      Rp101.915.394 |      Rp231.915.394

Nilai akhir          : Rp231.915.394
Total setoran        : Rp130.000.000
Total imbal hasil    : Rp101.915.394
Kelipatan setoran    : 1,78x
```

Return 10% hanya asumsi simulasi; return saham sungguhan naik-turun dan bisa negatif.

### Kalkulator ARA dan ARB

```text
$ python3 kalkulator_saham.py ara-arb 1000
Aturan       : Kep-00158/BEI/10-2026, berlaku 20 Okt-31 Des 2026 (Papan Utama, Pengembangan, Ekonomi Baru)
Harga acuan  : Rp1.000 (fraksi Rp5)
Batas ARA    : Rp1.250 (batas 25%; naik Rp250 = 25,00%)
Batas ARB    : Rp930 (batas 7%; turun Rp70 = 7,00%)
```

Simulasi ARA dan ARB beruntun lima hari dari harga Rp100:

```text
$ python3 kalkulator_saham.py ara-arb 100 --hari 5
Aturan       : Kep-00158/BEI/10-2026, berlaku 20 Okt-31 Des 2026 (Papan Utama, Pengembangan, Ekonomi Baru)
Harga acuan  : Rp100 (fraksi Rp1)
Batas ARA    : Rp135 (batas 35%; naik Rp35 = 35,00%)
Batas ARB    : Rp93 (batas 7%; turun Rp7 = 7,00%)

Simulasi 5 hari beruntun (acuan berikutnya = batas hari ini):
Hari |        ARA |        ARB
   1 |      Rp135 |       Rp93
   2 |      Rp182 |       Rp87
   3 |      Rp245 |       Rp81
   4 |      Rp306 |       Rp76
   5 |      Rp382 |       Rp71
```

Aturan lain bisa dipilih dengan `--aturan simetris` atau `--ara 20 --arb 15`.

### Kalkulator right issue

Harga pasar Rp1.000, harga tebus Rp600, rasio 5:2, dan Anda memegang 10 lot dengan average Rp1.200:

```text
$ python3 kalkulator_saham.py right-issue --harga 1000 --tebus 600 --rasio 5:2 --lot 10 --avg 1200
Rasio 5:2 -> tiap 5 saham lama mendapat 2 HMETD @ Rp600
Harga teoretis (TERP): Rp885,714 -> sesuai fraksi Rp885
Nilai teoretis HMETD : Rp285,71 per hak
Dilusi maksimal      : 28,57% kepemilikan (bila tidak menebus)

Posisi Anda: 10 lot (1.000 lembar), average Rp1.200,00, dapat 400 HMETD

A. Jika menebus semua HMETD:
   Dana tebus        : Rp240.000
   Jumlah saham      : 1.400 lembar
   Average baru      : Rp1.028,57
   Nilai pasar (TERP): Rp1.240.000

B. Jika tidak menebus:
   Average tetap     : Rp1.200,00
   Nilai pasar (TERP): Rp885.714 (sebelumnya Rp1.000.000)
   Turun teoretis    : Rp114.286
   Bila HMETD dijual di nilai teoretis: +Rp114.286
```

## Rumus & Contoh Hitung Langkah demi Langkah

### 1. Harga rata-rata, fee, dan harga impas

```text
lembar        = Σ lot × 100
nilai beli    = Σ (harga × lot × 100)
average       = nilai beli / lembar
modal         = nilai beli × (1 + fee_beli)
harga impas   = modal / (lembar × (1 − fee_jual))
```

Dari contoh di atas: 2.000 lembar senilai Rp1.900.000 menghasilkan average Rp950. Fee beli 0,15% = Rp2.850, sehingga modal menjadi Rp1.902.850. Harga impas = 1.902.850 ÷ (2.000 × 0,9975) = 1.902.850 ÷ 1.995 = Rp953,81. Karena harga di rentang Rp500–Rp2.000 bergerak per Rp5, harga jual impas terdekat ke atas adalah **Rp955**.

Fee 0,15%/0,25% hanyalah contoh. **Fee berbeda di tiap sekuritas**, jadi isi `--fee-beli` dan `--fee-jual` sesuai aplikasi Anda. Penjualan saham di bursa juga dikenai PPh final 0,1% dari nilai bruto (PP 41/1994 jo. PP 14/1997), jadi periksa apakah fee jual Anda sudah mencakupnya.

### 2. Lot yang dibutuhkan untuk target average

Dengan L₀ lot di average P₀, beli L lot di harga P agar average menjadi T:

```text
(P₀·L₀ + P·L) / (L₀ + L) = T   →   L = L₀ × (P₀ − T) / (T − P)
```

Hasilnya dibulatkan **ke atas** karena lot harus bulat. Contoh: L = 20 × (950 − 920) ÷ (920 − 800) = 20 × 30 ÷ 120 = **5 lot**. Cek: (1.900.000 + 500 × 800) ÷ 2.500 = Rp920.

Target **mustahil** bila T tidak berada di antara P dan P₀. Membeli di Rp800 tidak akan pernah membuat average menyentuh Rp800, berapa pun lot yang dibeli, jadi kalkulator average down saham ini menolak target seperti itu.

### 3. Bunga majemuk (compounding)

Untuk setoran rutin di akhir periode, nilai akhirnya:

```text
FV = M·(1 + i)ⁿ + S·[(1 + i)ⁿ − 1] / i
```

- **Bulanan:** i = r/12, n = tahun × 12, S = setoran bulanan.
- **Tahunan:** i = r, n = tahun, S = 12 × setoran bulanan. Setoran tahun berjalan baru mulai berbunga tahun berikutnya. Ini asumsi penyederhanaan yang perlu Anda sadari.

Contoh bulanan di atas: i = 0,1/12, (1 + i)¹²⁰ = 2,707041. FV = 10.000.000 × 2,707041 + 1.000.000 × (2,707041 − 1) ÷ 0,008333 = 27.070.415 + 204.844.979 = **Rp231.915.394**, persis sama dengan tabel.

### 4. ARA/ARB dan pembulatan fraksi

```text
ARA = acuan × (1 + %ARA), dibulatkan KE BAWAH ke kelipatan fraksi
ARB = acuan × (1 − %ARB), dibulatkan KE ATAS ke kelipatan fraksi
```

Arah pembulatan dipilih agar harga tidak melampaui batas persentase. Contoh: acuan Rp50 dengan ARA 35% menghasilkan 67,5, dibulatkan menjadi **Rp67**. Hasil ini cocok dengan kasus nyata saham DFAM pada 4 Januari 2024 yang ARA dari Rp50 ke Rp67 (naik 34%).

**Asumsi fraksi:** situs BEI menyebut fraksi berlaku untuk satu hari bursa penuh dan baru disesuaikan pada hari bursa berikutnya bila harga penutupan pindah rentang. Karena itu tool memakai fraksi dari **rentang harga acuan**. Contohnya, acuan Rp197 menghasilkan ARA Rp265. Bila Anda ingin fraksi mengikuti harga hasil (Rp264), gunakan `--fraksi-dari hasil`. Cocokkan selalu dengan aplikasi sekuritas Anda.

### 5. Harga teoretis right issue (TERP)

```text
TERP = (P × N + Pe × R) / (N + R)
```

P adalah harga saat cum, Pe harga tebus, dan rasio N:R berarti tiap N saham lama mendapat R HMETD (1 HMETD = hak membeli 1 saham baru). Nilai teoretis HMETD = TERP − Pe, dan dilusi maksimal bila tidak menebus = R/(N+R).

Contoh nyata VKTR (Oktober 2026): P = Rp835, Pe = Rp200, rasio 35:12. TERP = (835 × 35 + 200 × 12) ÷ 47 = 31.625 ÷ 47 = **Rp672,872**, yang oleh BEI disesuaikan dengan fraksi menjadi Rp675. Berdasarkan contoh ini dan contoh SMGR (Rp6.731,272 menjadi Rp6.725), tool membulatkan TERP ke fraksi **terdekat**.

Pecahan HMETD dibulatkan ke bawah (asumsi; cek prospektus emiten).

## Tabel Fraksi Harga & Auto Rejection BEI

Diverifikasi di [situs BEI](https://www.idx.co.id/id/produk-layanan/jam-dan-mekanisme-perdagangan/) pada **21 Oktober 2026**, mengacu Peraturan II-A (Kep-00158/BEI/10-2026).

**Fraksi harga saham:**

| Rentang harga | Fraksi | Jenjang maksimum perubahan* |
|---|---|---|
| < Rp200 | Rp1 | Rp10 |
| Rp200 – < Rp500 | Rp2 | Rp20 |
| Rp500 – < Rp2.000 | Rp5 | Rp50 |
| Rp2.000 – < Rp5.000 | Rp10 | Rp100 |
| ≥ Rp5.000 | Rp25 | Rp250 |

*Jenjang maksimum berlaku sepanjang tidak melampaui batas auto rejection.

**Auto rejection saham Papan Utama, Pengembangan, dan Ekonomi Baru (20 Okt – 31 Des 2026):**

| Harga acuan | ARA | ARB |
|---|---|---|
| Rp1 – Rp10 | Rp1 | Rp1 |
| Rp11 – Rp14 | 35% | Rp1 |
| Rp15 – Rp200 | 35% | 7% |
| > Rp200 – Rp5.000 | 25% | 7% |
| > Rp5.000 | 20% | 7% |

Saham Papan Akselerasi dan Pemantauan Khusus memakai Rp1 untuk harga Rp1–Rp10 dan 10%/10% untuk harga di atas Rp10 (preset `--aturan akselerasi`).

Mengapa ada batas Rp1 untuk Rp11–Rp14? Secara matematis, 7% dari Rp14 hanya Rp0,98, kurang dari satu fraksi, sehingga tanpa batas nominal harga di rentang itu tidak bisa turun sama sekali.

**Riwayat perubahan auto rejection** (ringkasan dari pemberitaan, lihat sumber di bawah):

| Periode | ARA | ARB |
|---|---|---|
| Awal 2017 – Mar 2020 | 35/25/20% | 35/25/20% |
| Mar 2020 – 4 Jun 2023 | 35/25/20% | 7% |
| 5 Jun – 3 Sep 2023 | 35/25/20% | 15% |
| 4 Sep 2023 – 7 Apr 2025 | 35/25/20% | 35/25/20% |
| 8 Apr 2025 – 27 Sep 2026 | 35/25/20% | 15% |
| 28 Sep – 18 Okt 2026 | Rp1 (≤Rp10); 35/25/20% | Rp1 (≤Rp10); 15% |
| 19 Okt 2026 | sama | Rp1 (≤Rp10); 7% |
| 20 Okt – 31 Des 2026 | sama | Rp1 (≤Rp14); 7% |

Bersama Kep-00136/BEI/09-2026, BEI mengumumkan rencana ARB simetris mulai 1 Januari 2027. Keputusan itu lalu diganti Kep-00157 dan Kep-00158, dan BEI menyatakan aturan akan dievaluasi, sehingga kami **belum bisa memastikan** rencana 2027 tetap berlaku. Preset `simetris` disediakan sebagai asumsi, dan persentase selalu bisa diganti lewat `--ara`/`--arb`.

## Risiko Average Down

Average down **tidak** membuat saham lebih mungkin naik. Yang berubah hanya angka rata-rata di aplikasi Anda. Beberapa risiko yang wajib dipahami:

- **Menambah posisi yang sedang rugi.** Bila harga terus turun, kerugian bertambah lebih cepat karena jumlah lembar Anda lebih banyak.
- **Harga bisa turun sangat dalam.** Sejak 28 September 2026, harga minimum saham di BEI turun dari Rp50 menjadi Rp1, jadi "lantai" Rp50 tidak ada lagi.
- **Fundamental bisa memburuk.** Penurunan harga kadang mencerminkan masalah nyata seperti rugi berulang, utang menumpuk, atau suspensi.
- **Konsentrasi dan biaya peluang.** Dana yang terkunci di satu saham tidak bisa dipakai untuk peluang lain.

Gunakan kalkulator average down saham ini untuk **mengukur** konsekuensi keputusan (dana yang dibutuhkan dan harga impasnya), bukan sebagai alasan untuk membeli.

## Tips & Kesalahan Umum

- **Lupa fee.** Average tanpa fee terlihat lebih rendah daripada modal sebenarnya, jadi pakai angka "Harga impas" sebagai harga jual minimal.
- **Salah satuan.** Input `--beli` memakai **lot** (1 lot = 100 lembar), bukan lembar.
- **Mengabaikan fraksi.** Harga Rp953,81 tidak bisa diantrekan, karena harga valid terdekat adalah Rp955.
- **Return compounding terlalu optimistis.** Coba beberapa skenario, misalnya 5%, 8%, dan 12%, lalu bandingkan dengan return nol.
- **Lupa dana tebus right issue.** Menebus HMETD butuh dana tunai tambahan sebelum batas waktu pelaksanaan.

## FAQ

**Bagaimana cara memakai kalkulator average saham untuk lebih dari dua pembelian?**
Tulis semua pembelian setelah `--beli`, misalnya `--beli 1200:5 1000:10 850:15`. Hasilnya average Rp958,33 dan harga impas Rp965.

**Apakah kalkulator avg saham ini memperhitungkan fee?**
Ya. Average ditampilkan tanpa fee dan dengan fee beli, sedangkan harga impas memperhitungkan fee beli dan fee jual.

**Kenapa kalkulator average down saham bilang target saya mustahil?**
Average baru selalu berada di antara average lama dan harga beli baru. Target di luar rentang itu tidak akan tercapai, berapa pun lot yang dibeli.

**Apa beda compounding bulanan dan tahunan di kalkulator compounding ini?**
Bulanan menambahkan imbal hasil r/12 tiap bulan, sedangkan tahunan menambahkan r sekali setahun. Untuk return positif yang sama, compounding bulanan menghasilkan nilai sedikit lebih besar.

**Apakah kalkulator bunga majemuk ini cocok untuk deposito atau reksa dana?**
Rumusnya umum, tetapi deposito dikenai pajak bunga dan reksa dana punya biaya serta return yang tidak tetap. Masukkan return bersih sebagai asumsi.

**Apakah hasil kalkulator ARA selalu sama dengan aplikasi sekuritas?**
Tool mengikuti tabel resmi BEI, tetapi belum kami bandingkan dengan setiap aplikasi sekuritas. Perbedaan paling mungkin muncul di dekat batas rentang fraksi atau saat BEI mengubah aturan, karena itu persentase bisa diubah lewat parameter.

**Apakah kalkulator average down saham ini memberi sinyal beli atau jual?**
Tidak. Ini kalkulator investasi saham untuk berhitung, bukan penasihat investasi.

## Metodologi, Pengujian & Sumber

Seluruh logika diuji dengan **17 unit test** (`python3 -m unittest discover -s tests -v`), dan semuanya lulus. Yang diuji antara lain:

- **Kalkulator average down:** contoh manual 10 lot @1.000 + 10 lot @900 (average Rp950, impas Rp955), target pas (5 lot), target dibulatkan ke atas (3,08 menjadi 4 lot, dan 3 lot terbukti belum cukup), average up, serta empat kasus mustahil.
- **Kalkulator compounding:** empat skenario dibandingkan dengan rumus tertutup, nilai buku teks 10 juta × 1,1¹⁰ = 25.937.424,60, dan return 0%.
- **Fraksi dan ARA/ARB:** batas tiap rentang (199/200, 499/500, 1.995/2.000, 4.990/5.000) dan 14 harga acuan dari Rp1 sampai Rp5.025.
- **Contoh nyata:** ARA DFAM Rp50 ke Rp67, TERP SMGR Rp6.731,272 ke Rp6.725, dan TERP VKTR Rp672,872 ke Rp675 (dilusi 25,53%).

Hitungan uang memakai pecahan eksak (`fractions.Fraction`), jadi bebas galat pembulatan float.

**Sumber:**

1. Bursa Efek Indonesia — [Jam dan Mekanisme Perdagangan](https://www.idx.co.id/id/produk-layanan/jam-dan-mekanisme-perdagangan/) (fraksi dan auto rejection, Kep-00158/BEI/10-2026), diakses 21 Oktober 2026.
2. Bareksa (20 Okt 2026) — [BEI Ubah Lagi Aturan ARB Mulai 20 Oktober](https://www.bareksa.com/berita/saham/2026-10-20/bei-ubah-lagi-aturan-arb-mulai-20-oktober-saham-rp11rp14-dibatasi-turun-rp1).
3. Fortune IDN (19 Okt 2026) — [BEI Pangkas ARB Jadi 7 Persen](https://www.fortuneidn.com/market/resmi-bei-pangkas-arb-jadi-7-persen-d7w02-00-fykp7-n4fph0).
4. Katadata (21 Sep 2026) — [BEI Ubah Aturan Auto Rejection](https://katadata.co.id/finansial/bursa/6ab10d458e4d5/bei-ubah-aturan-auto-rejection-batas-arb-makin-lebar-jadi-35-mulai-2027) (Kep-00136/BEI/09-2026, harga minimum Rp1).
5. Kontan Momsmoney (8 Apr 2025) — [ARB 15% dan trading halt 8%](https://momsmoney.kontan.co.id/news/bei-tetapkan-auto-rejection-bawah-arb-hanya-15-dan-mengubah-batas-trading-halt-8).
6. Bisnis.com (31 Agu 2023) — [Aturan ARB-ARA Simetris Berlaku 4 September](https://market.bisnis.com/read/20230831/7/1690211/aturan-arb-ara-simetris-dari-bei-terbaru-berlaku-4-september) (riwayat 2017, 2020, dan 2023).
7. Bisnis.com (13 Des 2022) — [Harga teoretis SMGR](https://market.bisnis.com/read/20221213/192/1607988/semen-indonesia-smgr-pakai-harga-baru-rp6725-setelah-rights-issue).
8. IDXChannel via RCTI+ (7 Okt 2026) — [Harga teoretis VKTR](https://www.rctiplus.com/news/detail/idxchannel/5488321/rights-issue-rp3-triliun--segini-harga-teoritis-saham-vktr).
9. Investortrust (4 Jan 2024) — [DFAM ARA ke Rp67](https://investortrust.id/market/19809/saat-ihsg-ukir-ath-saham-apex-dan-dfam-terbang-hingga-ara).
10. [PP Nomor 14 Tahun 1997](https://perpajakan.ddtc.co.id/sumber-hukum/peraturan-pusat/peraturan-pemerintah-14-tahun-1997) tentang perubahan PP 41/1994 (PPh 0,1% penjualan saham di bursa).

## Tentang Pembuat

Proyek ini adalah karya [JoinBareng](https://joinbareng.com) dan dikelola oleh [@redyopa2929](https://github.com/redyopa2929). JoinBareng adalah platform patungan langganan premium (Netflix, Spotify, YouTube Premium, ChatGPT, dll.) plus marketplace akun digital yang aman dan transparan.

## Disclaimer

**Tool ini bukan rekomendasi, ajakan, atau saran untuk membeli maupun menjual efek apa pun.** Semua angka adalah hasil hitungan matematis berdasarkan input dan asumsi Anda. Investasi saham mengandung risiko, termasuk kehilangan sebagian atau seluruh modal, dan kinerja masa lalu tidak menjamin hasil di masa depan. Aturan bursa (fraksi, auto rejection, harga minimum) dan fee sekuritas dapat berubah sewaktu-waktu. Selalu cek sumber resmi BEI dan aplikasi sekuritas Anda, dan lakukan riset sendiri (DYOR). Pembuat tidak bertanggung jawab atas kerugian akibat penggunaan tool ini.

## Kontribusi

Menemukan angka yang tidak cocok dengan aplikasi sekuritas atau aturan BEI berubah? Buka isu di [github.com/redyopa2929/kalkulator-saham/issues](https://github.com/redyopa2929/kalkulator-saham/issues) dengan contoh input, hasil yang diharapkan, dan sumbernya. Pull request untuk fitur baru juga sangat diterima.

## Lisensi

Dirilis di bawah [Lisensi MIT](LICENSE) © 2026 redyopa2929.

## Dukung Proyek Ini

Jika kalkulator average down saham dan kalkulator compounding ini bermanfaat, beri ⭐ star pada repositori ini agar lebih mudah ditemukan investor lain. Ingin sisa dana bulanan lebih banyak untuk diinvestasikan? Hemat biaya langganan aplikasi premium dengan patungan di [JoinBareng](https://joinbareng.com).

## Tools Lainnya dari Seri Ini

- [Kalkulator Jadian](https://github.com/redyopa2929/kalkulator-jadian) — hitung lama hari jadian & anniversary
- [Kalkulator Jasmani Polri](https://github.com/redyopa2929/kalkulator-jasmani-polri) — hitung nilai kesamaptaan jasmani
- [Hitung WR ML](https://github.com/redyopa2929/hitung-wr-ml) — hitung win rate Mobile Legends
- [Tasbih Online](https://github.com/redyopa2929/tasbih-online) — tasbih digital penghitung dzikir
- [Kalkulator Selamatan](https://github.com/redyopa2929/kalkulator-selamatan) — hitung selamatan orang meninggal adat Jawa
- [Terbilang Online](https://github.com/redyopa2929/terbilang-online) — ubah angka ke huruf / terbilang rupiah
- [Kalkulator Bangunan](https://github.com/redyopa2929/kalkulator-bangunan) — keramik, hebel, kubikasi, besi
- [Konversi Koordinat](https://github.com/redyopa2929/konversi-koordinat) — DMS, desimal, UTM
- [Cek Weton](https://github.com/redyopa2929/cek-weton) — cek weton & neptu dari tanggal lahir

---

Terakhir diperbarui: 21 Oktober 2026
