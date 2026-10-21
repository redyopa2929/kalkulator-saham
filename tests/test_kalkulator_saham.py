"""Unit test kalkulator_saham. Jalankan: python3 -m unittest discover -s tests -v"""

import io
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from fractions import Fraction

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import kalkulator_saham as ks  # noqa: E402


class TestAverage(unittest.TestCase):
    def test_contoh_manual_dua_pembelian(self):
        # 10 lot @1.000 + 10 lot @900 = Rp1.900.000 / 2.000 lembar = Rp950
        h = ks.hitung_average([(1000, 10), (900, 10)], fee_beli=0.15, fee_jual=0.25)
        self.assertEqual(h.total_lembar, 2000)
        self.assertEqual(h.nilai_beli, 1900000)
        self.assertEqual(h.rata_rata, 950)
        self.assertEqual(h.fee_beli, 2850)
        self.assertEqual(h.modal, 1902850)
        self.assertEqual(h.rata_rata_fee, Fraction("951.425"))
        # BEP = 1.902.850 / (2.000 x 0,9975) = 953,81 -> naik ke fraksi Rp5 = 955
        self.assertAlmostEqual(float(h.harga_impas), 953.8095238, places=6)
        self.assertEqual(h.harga_impas_fraksi, 955)

    def test_tiga_pembelian_tanpa_fee(self):
        h = ks.hitung_average([(1200, 5), (1000, 10), (850, 15)], 0, 0)
        self.assertEqual(h.nilai_beli, 2875000)
        self.assertEqual(h.rata_rata, Fraction(2875000, 3000))
        self.assertEqual(h.harga_impas, h.rata_rata)
        self.assertEqual(h.harga_impas_fraksi, 960)  # 958,33 -> fraksi Rp5 ke atas

    def test_target_average_down(self):
        self.assertEqual(ks.lot_untuk_target(950, 20, 800, 920), 5)   # 20x30/120 = 5 tepat
        self.assertEqual(ks.lot_untuk_target(950, 20, 800, 900), 10)  # 20x50/100 = 10
        lot = ks.lot_untuk_target(950, 20, 800, 930)                  # 20x20/130 = 3,08 -> 4
        self.assertEqual(lot, 4)
        avg = lambda n: (950 * 2000 + 800 * n * 100) / (2000 + n * 100)  # noqa: E731
        self.assertLessEqual(avg(lot), 930)
        self.assertGreater(avg(lot - 1), 930)

    def test_target_average_up_dan_nol(self):
        self.assertEqual(ks.lot_untuk_target(1000, 10, 1500, 1200), 7)  # 6,67 -> 7
        self.assertEqual(ks.lot_untuk_target(950, 20, 800, 950), 0)

    def test_target_mustahil(self):
        for target in (800, 700, 960, 1000):
            with self.subTest(target), self.assertRaises(ks.SahamError):
                ks.lot_untuk_target(950, 20, 800, target)
        with self.assertRaises(ks.SahamError):
            ks.hitung_average([(1000, 0)])
        with self.assertRaises(ks.SahamError):
            ks.hitung_average([(1000, 1.5)])


class TestCompounding(unittest.TestCase):
    def test_cocok_dengan_rumus_tertutup(self):
        for modal, setor, r, th, frek in ((10e6, 1e6, 10, 10, "bulanan"), (10e6, 1e6, 10, 10, "tahunan"),
                                          (0, 500000, 7.5, 25, "bulanan"), (5e6, 0, -5, 3, "tahunan")):
            with self.subTest((modal, setor, r, th, frek)):
                tabel = ks.hitung_compounding(modal, setor, r, th, frek)
                self.assertEqual(len(tabel), th)
                self.assertAlmostEqual(tabel[-1].saldo, ks.nilai_akhir_rumus(modal, setor, r, th, frek),
                                       delta=1e-6 * max(1, tabel[-1].saldo))
                self.assertAlmostEqual(tabel[-1].total_setoran, modal + 12 * setor * th)

    def test_nilai_buku_teks(self):
        # Rp10 juta, 10%/tahun, 10 tahun: 10.000.000 x 1,1^10 = 25.937.424,60
        tahunan = ks.hitung_compounding(10_000_000, 0, 10, 10, "tahunan")[-1]
        self.assertAlmostEqual(tahunan.saldo, 25937424.601, places=2)
        bulanan = ks.hitung_compounding(10_000_000, 0, 10, 10, "bulanan")[-1]
        self.assertAlmostEqual(bulanan.saldo, 10_000_000 * (1 + 0.1 / 12) ** 120, places=4)
        self.assertGreater(bulanan.saldo, tahunan.saldo)
        nol = ks.hitung_compounding(1_000_000, 100_000, 0, 2)[-1]
        self.assertAlmostEqual(nol.saldo, 3_400_000)
        self.assertAlmostEqual(nol.imbal_hasil, 0)

    def test_validasi_compounding(self):
        for args in ((-1, 0, 5, 1), (1, 0, -100, 1), (1, 0, 5, 0), (1, 0, 5, 2.5)):
            with self.subTest(args), self.assertRaises(ks.SahamError):
                ks.hitung_compounding(*args)


class TestFraksiDanARA(unittest.TestCase):
    def test_fraksi_di_tiap_batas_rentang(self):
        pasangan = {1: 1, 199: 1, 200: 2, 499: 2, 500: 5, 1995: 5, 2000: 10,
                    4990: 10, 5000: 25, 50000: 25}
        for harga, fraksi in pasangan.items():
            with self.subTest(harga):
                self.assertEqual(ks.fraksi_harga(harga), fraksi)
        self.assertEqual(ks.bulatkan_fraksi(Fraction("623.75"), "bawah"), 620)  # fraksi harga itu (Rp5)
        self.assertEqual(ks.bulatkan_fraksi(Fraction("623.75"), "bawah", fraksi=2), 622)
        self.assertEqual(ks.bulatkan_fraksi(Fraction("953.81"), "atas"), 955)
        self.assertEqual(ks.bulatkan_fraksi(Fraction("6731.272"), "terdekat"), 6725)
        self.assertEqual(ks.bulatkan_fraksi(Fraction("672.872"), "terdekat"), 675)

    def test_ara_arb_aturan_terkini_tiap_rentang(self):
        # acuan: (ARA, ARB) menurut Kep-00158/BEI/10-2026
        harapan = {
            1: (2, 1), 10: (11, 9),          # Rp1-Rp10: batas nominal Rp1
            11: (14, 10), 14: (18, 13),      # Rp11-Rp14: ARA 35%, ARB Rp1
            15: (20, 14), 50: (67, 47),      # Rp15-Rp200: 35% / 7%
            200: (270, 186), 201: (250, 188),  # 200 masih 35%; >200 pakai 25%
            499: (622, 466), 500: (625, 465),
            5000: (6250, 4650), 5025: (6025, 4675),  # >Rp5.000: 20% / 7%
        }
        for acuan, (ara, arb) in harapan.items():
            with self.subTest(acuan):
                r = ks.batas_ara_arb(acuan)
                self.assertEqual((r.ara, r.arb), (ara, arb))

    def test_ara_contoh_nyata_dfam(self):
        # DFAM, 4 Jan 2024: ARA dari Rp50 naik Rp17 (34%) ke Rp67 (investortrust.id)
        self.assertEqual(ks.batas_ara_arb(50, "simetris").ara, 67)

    def test_ara_arb_aturan_lain_dan_kustom(self):
        self.assertEqual(ks.batas_ara_arb(1000, "simetris")[2:4], (1250, 750))
        self.assertEqual(ks.batas_ara_arb(50, "simetris").arb, 33)
        self.assertEqual(ks.batas_ara_arb(100, "akselerasi")[2:4], (110, 90))
        self.assertEqual(ks.batas_ara_arb(1000, ara=20, arb=10)[2:4], (1200, 900))
        self.assertEqual(ks.batas_ara_arb(499, fraksi_dari="hasil").ara, 620)
        with self.assertRaises(ks.SahamError):
            ks.batas_ara_arb(0)
        with self.assertRaises(ks.SahamError):
            ks.batas_ara_arb(1000, ara=150)

    def test_ara_beruntun(self):
        hari = ks.ara_arb_beruntun(100, 5)
        self.assertEqual([h.ara for h in hari], [135, 182, 245, 306, 382])
        self.assertEqual([h.arb for h in hari], [93, 87, 81, 76, 71])


class TestRightIssue(unittest.TestCase):
    def test_terp_contoh_nyata_bei(self):
        # SMGR Des 2022: (6.750 x 100.000.000 + 6.600 x 14.266.416) / 114.266.416 = 6.731,272 -> 6.725
        terp = ks.harga_teoretis(6750, 6600, 100_000_000, 14_266_416)
        self.assertAlmostEqual(float(terp), 6731.272, places=3)
        self.assertEqual(ks.bulatkan_fraksi(terp), 6725)
        # VKTR Okt 2026: cum Rp835, tebus Rp200, rasio 35:12 -> 672,872 -> 675
        d = ks.dampak_right_issue(835, 200, 35, 12)
        self.assertAlmostEqual(float(d["terp"]), 672.872, places=3)
        self.assertEqual(d["terp_fraksi"], 675)
        self.assertAlmostEqual(float(d["dilusi_persen"]), 25.53, places=2)

    def test_dampak_ke_average(self):
        # 10 lot avg Rp1.000, harga Rp1.000, tebus Rp600, rasio 5:2 -> 400 HMETD
        d = ks.dampak_right_issue(1000, 600, 5, 2, lot=10, rata_rata=1000)
        self.assertEqual(d["terp"], Fraction(6200, 7))  # 885,714...
        self.assertEqual(d["hmetd"], 400)
        self.assertEqual(d["dana_tebus"], 240000)
        self.assertEqual(d["avg_tebus"], Fraction(1240000, 1400))
        # Teori: nilai turun saat tidak menebus = nilai jual HMETD di harga teoretis
        self.assertEqual(d["nilai_awal"] - d["nilai_tidak_tebus"], d["jual_hmetd"])

    def test_parse_rasio_dan_angka(self):
        self.assertEqual(ks.parse_rasio("5:2"), (5, 2))
        self.assertEqual(ks.parse_rasio("100.000.000:14.266.416"), (100000000, 14266416))
        with self.assertRaises(ks.SahamError):
            ks.parse_rasio("5-2")
        self.assertEqual(ks.parse_angka("1.250"), 1250)
        self.assertEqual(ks.parse_angka("Rp1.000.000"), 1000000)
        self.assertEqual(ks.parse_angka("0,15"), Fraction("0.15"))
        self.assertEqual(ks.parse_angka("2.5"), Fraction("2.5"))
        self.assertEqual(ks.fmt_rp(Fraction("951.425"), 2), "Rp951,43")


class TestCLI(unittest.TestCase):
    def jalankan(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                kode = ks.main(list(argv))
            except SystemExit as e:  # galat argparse
                kode = e.code
        return kode, out.getvalue(), err.getvalue()

    def test_cli_sukses_dan_galat(self):
        kode, out, _ = self.jalankan("average", "--beli", "1000:10", "900:10",
                                     "--target-avg", "920", "--harga-beli", "800")
        self.assertEqual(kode, 0)
        self.assertIn("5 lot", out)
        kode, out, _ = self.jalankan("ara-arb", "1000")
        self.assertEqual(kode, 0)
        self.assertIn("Rp1.250", out)
        kode, _, err = self.jalankan("average", "--beli", "1000:10", "--target-avg", "1100",
                                     "--harga-beli", "800")
        self.assertEqual(kode, 1)
        self.assertIn("Mustahil", err)
        kode, _, err = self.jalankan("right-issue", "--harga", "1000", "--tebus", "600", "--rasio", "x")
        self.assertEqual(kode, 1)
        kode, _, err = self.jalankan("compounding", "--modal", "abc", "--return", "5", "--tahun", "1")
        self.assertNotEqual(kode, 0)


if __name__ == "__main__":
    unittest.main()
