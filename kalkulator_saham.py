#!/usr/bin/env python3
"""Kalkulator saham BEI: average down/up, compounding, batas ARA/ARB, dan right issue.

Hanya memakai standard library Python 3.8+. Hasil hitungan bersifat edukasi,
bukan rekomendasi jual/beli. Fee dan aturan bursa bisa diubah lewat parameter.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

LEMBAR_PER_LOT = 100
FEE_BELI_DEFAULT = 0.15  # persen; contoh saja, tiap sekuritas berbeda
FEE_JUAL_DEFAULT = 0.25  # persen; contoh saja, tiap sekuritas berbeda
INF = float("inf")

# Fraksi harga saham BEI per Kep-00158/BEI/10-2026 (diverifikasi di idx.co.id, 21 Okt 2026):
# (batas atas eksklusif, fraksi). Harga < Rp200 -> Rp1, Rp200-<500 -> Rp2, dst.
FRAKSI_HARGA: Tuple[Tuple[float, int], ...] = ((200, 1), (500, 2), (2000, 5), (5000, 10), (INF, 25))

# Batas auto rejection: (batas atas inklusif harga acuan, persen). Rentang Rp1 s.d.
# "*_rp1_sampai" memakai batas nominal Rp1, bukan persen.
ATURAN_AR: Dict[str, dict] = {
    "terkini": {
        "label": "Kep-00158/BEI/10-2026, berlaku 20 Okt-31 Des 2026 "
                 "(Papan Utama, Pengembangan, Ekonomi Baru)",
        "ara": ((200, 35), (5000, 25), (INF, 20)),
        "arb": ((INF, 7),),
        "ara_rp1_sampai": 10,
        "arb_rp1_sampai": 14,
    },
    "simetris": {
        "label": "Simetris 35/25/20% (pernah berlaku 4 Sep 2023-7 Apr 2025; "
                 "rencana BEI mulai 1 Jan 2027 - bisa berubah)",
        "ara": ((200, 35), (5000, 25), (INF, 20)),
        "arb": ((200, 35), (5000, 25), (INF, 20)),
        "ara_rp1_sampai": 10,
        "arb_rp1_sampai": 10,
    },
    "akselerasi": {
        "label": "Papan Akselerasi & Pemantauan Khusus (idx.co.id, 21 Okt 2026)",
        "ara": ((INF, 10),),
        "arb": ((INF, 10),),
        "ara_rp1_sampai": 10,
        "arb_rp1_sampai": 10,
    },
}


class SahamError(ValueError):
    """Kesalahan input kalkulator (pesan berbahasa Indonesia)."""


# --- Utilitas angka -------------------------------------------------------------
def parse_angka(teks: str) -> Fraction:
    """Teks angka -> Fraction. Menerima '1.250.000', '1250000', '0,15', '0.15', '1.250'."""
    s = str(teks).strip().replace(" ", "").replace("Rp", "").replace("rp", "").rstrip("%")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1 or re.fullmatch(r"-?[1-9]\d{0,2}\.\d{3}", s):
        s = s.replace(".", "")  # titik ribuan, mis. 1.250 = seribu dua ratus lima puluh
    try:
        return Fraction(s)
    except (ValueError, ZeroDivisionError):
        raise SahamError(f"'{teks}' bukan angka yang valid.") from None


def fmt_angka(x: float, desimal: int = 0) -> str:
    """1234567.5 -> '1.234.567,50' (format Indonesia, pembulatan setengah ke atas)."""
    if isinstance(x, Fraction):
        with localcontext() as ctx:
            ctx.prec = 50
            d = Decimal(x.numerator) / Decimal(x.denominator)
    else:
        d = Decimal(str(x))
    d = d.quantize(Decimal(1).scaleb(-desimal), rounding=ROUND_HALF_UP)
    s = f"{d:,.{desimal}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def fmt_rp(x: float, desimal: int = 0) -> str:
    return ("-Rp" if x < 0 else "Rp") + fmt_angka(abs(x), desimal)


def fmt_persen(x: float, desimal: int = 2) -> str:
    return fmt_angka(x, desimal) + "%"


def fraksi_harga(harga: float) -> int:
    """Fraksi (tick size) untuk sebuah harga saham."""
    if harga <= 0:
        raise SahamError("Harga harus lebih dari 0.")
    for batas, fraksi in FRAKSI_HARGA:
        if harga < batas:
            return fraksi
    return FRAKSI_HARGA[-1][1]


def bulatkan_fraksi(harga: Fraction, arah: str = "terdekat", fraksi: Optional[int] = None) -> int:
    """Bulatkan harga ke kelipatan fraksi: 'bawah', 'atas', atau 'terdekat'."""
    f = fraksi or fraksi_harga(harga)
    q = Fraction(harga) / f
    if arah == "bawah":
        n = math.floor(q)
    elif arah == "atas":
        n = math.ceil(q)
    else:
        n = math.floor(q + Fraction(1, 2))
    return int(n * f)


# --- Average down / up ------------------------------------------------------------
class HasilAverage(NamedTuple):
    total_lot: int
    total_lembar: int
    nilai_beli: Fraction      # tanpa fee
    fee_beli: Fraction
    modal: Fraction           # nilai beli + fee beli
    rata_rata: Fraction       # tanpa fee
    rata_rata_fee: Fraction   # termasuk fee beli
    harga_impas: Fraction     # termasuk fee beli & fee jual
    harga_impas_fraksi: int   # dibulatkan ke atas sesuai fraksi


def hitung_average(pembelian: Sequence[Tuple[float, int]], fee_beli: float = FEE_BELI_DEFAULT,
                   fee_jual: float = FEE_JUAL_DEFAULT) -> HasilAverage:
    """Hitung harga rata-rata dari beberapa pembelian (harga per lembar, jumlah lot)."""
    if not pembelian:
        raise SahamError("Masukkan minimal satu pembelian.")
    fb, fj = Fraction(str(fee_beli)), Fraction(str(fee_jual))
    if not (0 <= fb < 100 and 0 <= fj < 100):
        raise SahamError("Fee harus di antara 0% dan 100%.")
    total_lot, nilai = 0, Fraction(0)
    for harga, lot in pembelian:
        harga = Fraction(str(harga)) if not isinstance(harga, Fraction) else harga
        if harga <= 0:
            raise SahamError("Harga beli harus lebih dari 0.")
        if int(lot) != lot or lot <= 0:
            raise SahamError("Jumlah lot harus bilangan bulat positif (1 lot = 100 lembar).")
        total_lot += int(lot)
        nilai += harga * int(lot) * LEMBAR_PER_LOT
    lembar = total_lot * LEMBAR_PER_LOT
    fee = nilai * fb / 100
    modal = nilai + fee
    impas = modal / (lembar * (1 - fj / 100))
    return HasilAverage(total_lot, lembar, nilai, fee, modal, nilai / lembar, modal / lembar,
                        impas, bulatkan_fraksi(impas, "atas"))


def lot_untuk_target(rata_rata: float, lot_sekarang: int, harga_beli: float,
                     target: float) -> int:
    """Lot minimal yang harus dibeli di harga_beli agar average mencapai target.

    Rumus: L = L0 x (P0 - T) / (T - P), dibulatkan ke atas.
    """
    p0, p, t = (Fraction(str(x)) if not isinstance(x, Fraction) else x
                for x in (rata_rata, harga_beli, target))
    if lot_sekarang <= 0 or min(p0, p, t) <= 0:
        raise SahamError("Average, lot, harga beli, dan target harus lebih dari 0.")
    if t == p0:
        return 0
    if t == p:
        raise SahamError("Mustahil: target sama dengan harga beli baru; average hanya "
                         "mendekati target tetapi tidak pernah tepat mencapainya.")
    if not min(p, p0) < t < max(p, p0):
        if p < p0:
            raise SahamError(f"Mustahil: membeli di {fmt_rp(p)} hanya bisa menurunkan average "
                             f"ke antara {fmt_rp(p)} dan {fmt_rp(p0, 2)}. Target harus di rentang itu.")
        raise SahamError(f"Mustahil: membeli di {fmt_rp(p)} hanya bisa menggeser average "
                         f"ke antara {fmt_rp(p0, 2)} dan {fmt_rp(p)}.")
    return math.ceil(lot_sekarang * (p0 - t) / (t - p))


# --- Compounding ------------------------------------------------------------------
class BarisTahun(NamedTuple):
    tahun: int
    total_setoran: float   # modal awal + setoran rutin kumulatif
    imbal_hasil: float     # saldo - total setoran
    saldo: float


def hitung_compounding(modal: float, setoran_bulanan: float, return_tahunan: float,
                       tahun: int, frekuensi: str = "bulanan") -> List[BarisTahun]:
    """Simulasi bunga majemuk; setoran rutin di akhir tiap bulan.

    frekuensi 'bulanan': imbal hasil r/12 dikreditkan tiap bulan.
    frekuensi 'tahunan': imbal hasil r dikreditkan di akhir tahun; setoran
    tahun berjalan baru ikut berbunga mulai tahun berikutnya.
    """
    if modal < 0 or setoran_bulanan < 0:
        raise SahamError("Modal dan setoran tidak boleh negatif.")
    if return_tahunan <= -100:
        raise SahamError("Return per tahun harus lebih besar dari -100%.")
    if int(tahun) != tahun or not 1 <= tahun <= 100:
        raise SahamError("Durasi harus bilangan bulat 1 sampai 100 tahun.")
    if frekuensi not in ("bulanan", "tahunan"):
        raise SahamError("Frekuensi harus 'bulanan' atau 'tahunan'.")
    r = return_tahunan / 100
    saldo, setor, hasil = float(modal), float(modal), []
    for th in range(1, int(tahun) + 1):
        if frekuensi == "bulanan":
            for _ in range(12):
                saldo = saldo * (1 + r / 12) + setoran_bulanan
        else:
            saldo = saldo * (1 + r) + 12 * setoran_bulanan
        setor += 12 * setoran_bulanan
        hasil.append(BarisTahun(th, setor, saldo - setor, saldo))
    return hasil


def nilai_akhir_rumus(modal: float, setoran_bulanan: float, return_tahunan: float,
                      tahun: int, frekuensi: str = "bulanan") -> float:
    """Rumus tertutup FV = M(1+i)^n + S x ((1+i)^n - 1) / i (setoran akhir periode)."""
    r = return_tahunan / 100
    if frekuensi == "bulanan":
        i, n, s = r / 12, tahun * 12, setoran_bulanan
    else:
        i, n, s = r, tahun, 12 * setoran_bulanan
    anuitas = s * n if i == 0 else s * ((1 + i) ** n - 1) / i
    return modal * (1 + i) ** n + anuitas


# --- ARA / ARB ------------------------------------------------------------------------
class HasilAR(NamedTuple):
    acuan: int
    fraksi: int
    ara: int
    arb: int
    persen_ara: Optional[Fraction]  # None = batas nominal Rp1
    persen_arb: Optional[Fraction]


def _persen_rentang(harga: int, tabel: Sequence[Tuple[float, float]]) -> Fraction:
    for batas, persen in tabel:
        if harga <= batas:
            return Fraction(str(persen))
    return Fraction(str(tabel[-1][1]))


def batas_ara_arb(acuan: int, aturan: str = "terkini", ara: Optional[float] = None,
                  arb: Optional[float] = None, fraksi_dari: str = "acuan") -> HasilAR:
    """Batas ARA/ARB untuk satu hari bursa berdasarkan harga acuan.

    ARA dibulatkan ke BAWAH dan ARB ke ATAS ke kelipatan fraksi, agar tidak
    melampaui persentase. Fraksi default mengikuti rentang harga acuan.
    """
    if aturan not in ATURAN_AR:
        raise SahamError(f"Aturan '{aturan}' tidak dikenal. Pilih: {', '.join(ATURAN_AR)}.")
    if int(acuan) != acuan or acuan < 1:
        raise SahamError("Harga acuan harus bilangan bulat minimal Rp1.")
    for nama, nilai in (("ARA", ara), ("ARB", arb)):
        if nilai is not None and not 0 < nilai < 100:
            raise SahamError(f"Persentase {nama} harus di antara 0 dan 100.")
    acuan, cfg = int(acuan), ATURAN_AR[aturan]
    fraksi = fraksi_harga(acuan)

    def tick(harga: Fraction) -> int:
        return fraksi if fraksi_dari == "acuan" else fraksi_harga(harga)

    if acuan <= cfg["ara_rp1_sampai"]:
        harga_ara, p_ara = acuan + 1, None
    else:
        p_ara = Fraction(str(ara)) if ara is not None else _persen_rentang(acuan, cfg["ara"])
        mentah = acuan * (100 + p_ara) / 100
        harga_ara = bulatkan_fraksi(mentah, "bawah", tick(mentah))
    batas_rp1 = cfg["arb_rp1_sampai"] if arb is None else 10
    if acuan <= batas_rp1:
        harga_arb, p_arb = max(1, acuan - 1), None
    else:
        p_arb = Fraction(str(arb)) if arb is not None else _persen_rentang(acuan, cfg["arb"])
        mentah = acuan * (100 - p_arb) / 100
        harga_arb = max(1, bulatkan_fraksi(mentah, "atas", tick(mentah)))
    return HasilAR(acuan, fraksi, harga_ara, harga_arb, p_ara, p_arb)


def ara_arb_beruntun(acuan: int, hari: int, **opsi) -> List[HasilAR]:
    """Simulasi ARA (atau ARB) beruntun: acuan hari berikutnya = batas hari ini."""
    if not 1 <= hari <= 30:
        raise SahamError("Jumlah hari harus 1 sampai 30.")
    hasil, a, b = [], acuan, acuan
    for _ in range(hari):
        ra, rb = batas_ara_arb(a, **opsi), batas_ara_arb(b, **opsi)
        hasil.append(HasilAR(a, ra.fraksi, ra.ara, rb.arb, ra.persen_ara, rb.persen_arb))
        a, b = ra.ara, rb.arb
    return hasil


# --- Right issue ----------------------------------------------------------------------
def parse_rasio(teks: str) -> Tuple[int, int]:
    """'5:2' -> (5, 2): tiap 5 saham lama mendapat 2 HMETD (1 HMETD = 1 saham baru)."""
    m = re.fullmatch(r"\s*([\d.]+)\s*[:/]\s*([\d.]+)\s*", str(teks))
    if not m:
        raise SahamError(f"Rasio '{teks}' tidak valid. Contoh: 5:2 atau 35:12.")
    lama, baru = (int(x.replace(".", "")) for x in m.groups())
    if lama <= 0 or baru <= 0:
        raise SahamError("Angka rasio harus lebih dari 0.")
    return lama, baru


def harga_teoretis(harga_cum: float, harga_tebus: float, lama: int, baru: int) -> Fraction:
    """TERP = (P x N + Pe x R) / (N + R)."""
    p, pe = Fraction(str(harga_cum)), Fraction(str(harga_tebus))
    if p <= 0 or pe <= 0:
        raise SahamError("Harga pasar dan harga tebus harus lebih dari 0.")
    return (p * lama + pe * baru) / (lama + baru)


def dampak_right_issue(harga_cum: float, harga_tebus: float, lama: int, baru: int,
                       lot: int = 0, rata_rata: Optional[float] = None) -> Dict[str, Fraction]:
    """Hitung TERP, nilai teoretis HMETD, dan dampak ke portofolio (tebus vs tidak)."""
    terp = harga_teoretis(harga_cum, harga_tebus, lama, baru)
    p, pe = Fraction(str(harga_cum)), Fraction(str(harga_tebus))
    hasil: Dict[str, Fraction] = {
        "terp": terp, "terp_fraksi": Fraction(bulatkan_fraksi(terp, "terdekat")),
        "nilai_hmetd": max(Fraction(0), terp - pe), "dilusi_persen": Fraction(100 * baru, lama + baru),
    }
    if lot:
        if lot < 0 or int(lot) != lot:
            raise SahamError("Lot harus bilangan bulat positif.")
        avg = Fraction(str(rata_rata)) if rata_rata is not None else p
        lembar = int(lot) * LEMBAR_PER_LOT
        hak = lembar * baru // lama  # pecahan HMETD dibulatkan ke bawah (asumsi)
        hasil.update({
            "lembar": Fraction(lembar), "hmetd": Fraction(hak), "dana_tebus": hak * pe,
            "avg_lama": avg, "avg_tebus": (avg * lembar + pe * hak) / (lembar + hak),
            "nilai_awal": lembar * p, "nilai_tebus": (lembar + hak) * terp,
            "nilai_tidak_tebus": lembar * terp, "jual_hmetd": hak * max(Fraction(0), terp - pe),
        })
    return hasil


# --- Tampilan teks ---------------------------------------------------------------------
def teks_average(pembelian: List[Tuple[Fraction, int]], fee_beli: float, fee_jual: float,
                 target: Optional[float] = None, harga_target: Optional[float] = None) -> str:
    h = hitung_average(pembelian, fee_beli, fee_jual)
    out = ["Rincian pembelian:"]
    for i, (harga, lot) in enumerate(pembelian, 1):
        out.append(f"  {i}. {lot} lot @ {fmt_rp(harga)} = {fmt_rp(harga * lot * LEMBAR_PER_LOT)}")
    out += [
        f"Total                : {fmt_angka(h.total_lot)} lot ({fmt_angka(h.total_lembar)} lembar)",
        f"Nilai pembelian      : {fmt_rp(h.nilai_beli)}",
        f"{'Fee beli (' + fmt_persen(fee_beli) + ')':<21}: {fmt_rp(h.fee_beli, 2)}",
        f"Total modal          : {fmt_rp(h.modal, 2)}",
        f"Harga rata-rata      : {fmt_rp(h.rata_rata, 2)} per lembar (tanpa fee)",
        f"Rata-rata + fee beli : {fmt_rp(h.rata_rata_fee, 2)} per lembar",
        f"Harga impas (BEP)    : {fmt_rp(h.harga_impas, 2)} -> jual minimal {fmt_rp(h.harga_impas_fraksi)}"
        f" (fraksi Rp{fraksi_harga(h.harga_impas_fraksi)}, fee jual {fmt_persen(fee_jual)})",
    ]
    if target is not None and harga_target is not None:
        lot = lot_untuk_target(h.rata_rata, h.total_lot, harga_target, target)
        p = Fraction(str(harga_target))
        baru = (h.nilai_beli + p * lot * LEMBAR_PER_LOT) / (h.total_lembar + lot * LEMBAR_PER_LOT)
        dana = p * lot * LEMBAR_PER_LOT
        out += ["", f"Target average {fmt_rp(target)} dengan membeli di {fmt_rp(harga_target)}:",
                f"  Beli minimal       : {fmt_angka(lot)} lot ({fmt_angka(lot * LEMBAR_PER_LOT)} lembar)",
                f"  Dana tambahan      : {fmt_rp(dana)} + fee beli {fmt_rp(dana * Fraction(str(fee_beli)) / 100, 2)}",
                f"  Average baru       : {fmt_rp(baru, 2)} (total {fmt_angka(h.total_lot + lot)} lot)"]
    return "\n".join(out)


def teks_compounding(modal: float, setoran: float, r: float, tahun: int, frek: str) -> str:
    tabel = hitung_compounding(modal, setoran, r, tahun, frek)
    akhir = tabel[-1]
    out = [f"Modal awal {fmt_rp(modal)}, setoran {fmt_rp(setoran)}/bulan, return "
           f"{fmt_persen(r)}/tahun, compounding {frek}, {tahun} tahun", "",
           f"{'Tahun':>5} | {'Total setoran':>18} | {'Imbal hasil':>18} | {'Saldo akhir':>18}",
           "-" * 68]
    for b in tabel:
        out.append(f"{b.tahun:>5} | {fmt_rp(b.total_setoran):>18} | {fmt_rp(b.imbal_hasil):>18} "
                   f"| {fmt_rp(b.saldo):>18}")
    out += ["", f"Nilai akhir          : {fmt_rp(akhir.saldo)}",
            f"Total setoran        : {fmt_rp(akhir.total_setoran)}",
            f"Total imbal hasil    : {fmt_rp(akhir.imbal_hasil)}"]
    if akhir.total_setoran > 0:
        out.append(f"Kelipatan setoran    : {fmt_angka(akhir.saldo / akhir.total_setoran, 2)}x")
    return "\n".join(out)


def _ket_persen(p: Optional[Fraction]) -> str:
    return "Rp1 (nominal)" if p is None else fmt_persen(p, 0 if p.denominator == 1 else 2)


def teks_ara_arb(acuan: int, aturan: str, ara: Optional[float], arb: Optional[float],
                 hari: int, fraksi_dari: str) -> str:
    opsi = dict(aturan=aturan, ara=ara, arb=arb, fraksi_dari=fraksi_dari)
    r = batas_ara_arb(acuan, **opsi)
    label = ATURAN_AR[aturan]["label"] + (" + persen kustom" if ara or arb else "")
    out = [f"Aturan       : {label}",
           f"Harga acuan  : {fmt_rp(acuan)} (fraksi Rp{r.fraksi})",
           f"Batas ARA    : {fmt_rp(r.ara)} (batas {_ket_persen(r.persen_ara)}; naik "
           f"{fmt_rp(r.ara - acuan)} = {fmt_persen((r.ara - acuan) * 100 / acuan)})",
           f"Batas ARB    : {fmt_rp(r.arb)} (batas {_ket_persen(r.persen_arb)}; turun "
           f"{fmt_rp(acuan - r.arb)} = {fmt_persen((acuan - r.arb) * 100 / acuan)})"]
    if r.arb == acuan:
        out.append("Catatan      : ARB sama dengan harga acuan -> harga tidak bisa turun hari itu.")
    if hari > 1:
        out += ["", f"Simulasi {hari} hari beruntun (acuan berikutnya = batas hari ini):",
                f"{'Hari':>4} | {'ARA':>10} | {'ARB':>10}"]
        for i, b in enumerate(ara_arb_beruntun(acuan, hari, **opsi), 1):
            out.append(f"{i:>4} | {fmt_rp(b.ara):>10} | {fmt_rp(b.arb):>10}")
    return "\n".join(out)


def teks_right_issue(harga: float, tebus: float, rasio: str, lot: int, avg: Optional[float]) -> str:
    lama, baru = parse_rasio(rasio)
    d = dampak_right_issue(harga, tebus, lama, baru, lot, avg)
    out = [f"Rasio {lama}:{baru} -> tiap {lama} saham lama mendapat {baru} HMETD @ {fmt_rp(tebus)}",
           f"Harga teoretis (TERP): {fmt_rp(d['terp'], 3)} -> sesuai fraksi {fmt_rp(d['terp_fraksi'])}",
           f"Nilai teoretis HMETD : {fmt_rp(d['nilai_hmetd'], 2)} per hak",
           f"Dilusi maksimal      : {fmt_persen(d['dilusi_persen'])} kepemilikan (bila tidak menebus)"]
    if "lembar" in d:
        out += ["", f"Posisi Anda: {fmt_angka(lot)} lot ({fmt_angka(d['lembar'])} lembar), "
                    f"average {fmt_rp(d['avg_lama'], 2)}, dapat {fmt_angka(d['hmetd'])} HMETD",
                "", "A. Jika menebus semua HMETD:",
                f"   Dana tebus        : {fmt_rp(d['dana_tebus'])}",
                f"   Jumlah saham      : {fmt_angka(d['lembar'] + d['hmetd'])} lembar",
                f"   Average baru      : {fmt_rp(d['avg_tebus'], 2)}",
                f"   Nilai pasar (TERP): {fmt_rp(d['nilai_tebus'])}",
                "", "B. Jika tidak menebus:",
                f"   Average tetap     : {fmt_rp(d['avg_lama'], 2)}",
                f"   Nilai pasar (TERP): {fmt_rp(d['nilai_tidak_tebus'])} (sebelumnya {fmt_rp(d['nilai_awal'])})",
                f"   Turun teoretis    : {fmt_rp(d['nilai_awal'] - d['nilai_tidak_tebus'])}",
                f"   Bila HMETD dijual di nilai teoretis: +{fmt_rp(d['jual_hmetd'])}"]
    return "\n".join(out)


# --- CLI ----------------------------------------------------------------------------------
def parse_pembelian(teks: str) -> Tuple[Fraction, int]:
    """'1000:10' atau '1000x10' -> (harga, lot)."""
    m = re.fullmatch(r"\s*([\d.,]+)\s*[:xX@]\s*(\d+)\s*", teks)
    if not m:
        raise SahamError(f"Format pembelian '{teks}' salah. Contoh: 1000:10 (harga:lot).")
    return parse_angka(m.group(1)), int(m.group(2))


def _tipe(fungsi):
    """Bungkus parser agar galatnya tampil apa adanya lewat argparse."""
    def bungkus(teks: str):
        try:
            return fungsi(teks)
        except SahamError as e:
            raise argparse.ArgumentTypeError(str(e)) from None
    bungkus.__name__ = fungsi.__name__
    return bungkus


class ParserID(argparse.ArgumentParser):
    """ArgumentParser dengan pesan galat berbahasa Indonesia."""

    _TERJEMAHAN = (("the following arguments are required", "argumen wajib belum diisi"),
                   ("unrecognized arguments", "argumen tidak dikenal"),
                   ("invalid choice", "pilihan tidak valid"),
                   ("choose from", "pilih dari"),
                   ("expected one argument", "butuh satu nilai"),
                   ("expected at least one argument", "butuh minimal satu nilai"),
                   ("invalid int value", "bukan bilangan bulat"),
                   ("argument ", "argumen "))

    def error(self, message: str) -> None:  # type: ignore[override]
        for en, idn in self._TERJEMAHAN:
            message = message.replace(en, idn)
        print(f"Galat: {message}\nKetik '{self.prog} --help' untuk bantuan.", file=sys.stderr)
        sys.exit(2)


def buat_parser() -> argparse.ArgumentParser:
    p = ParserID(prog="kalkulator_saham.py",
                                description="Kalkulator saham BEI. Tanpa argumen = mode interaktif.")
    sub = p.add_subparsers(dest="perintah", metavar="PERINTAH")
    s = sub.add_parser("average", help="harga rata-rata, BEP, dan target average down")
    s.add_argument("--beli", nargs="+", action="extend", required=True, type=_tipe(parse_pembelian),
                   metavar="HARGA:LOT", help="satu atau beberapa pembelian, mis. 1000:10 900:5")
    s.add_argument("--fee-beli", type=_tipe(parse_angka), default=Fraction(str(FEE_BELI_DEFAULT)))
    s.add_argument("--fee-jual", type=_tipe(parse_angka), default=Fraction(str(FEE_JUAL_DEFAULT)))
    s.add_argument("--target-avg", type=_tipe(parse_angka), help="target harga rata-rata")
    s.add_argument("--harga-beli", type=_tipe(parse_angka), help="harga beli berikutnya untuk target")
    s = sub.add_parser("compounding", help="bunga majemuk + setoran rutin")
    s.add_argument("--modal", type=_tipe(parse_angka), required=True)
    s.add_argument("--setoran", type=_tipe(parse_angka), default=Fraction(0), help="setoran per bulan")
    s.add_argument("--return", dest="ret", type=_tipe(parse_angka), required=True, help="persen per tahun")
    s.add_argument("--tahun", type=int, required=True)
    s.add_argument("--frekuensi", choices=("bulanan", "tahunan"), default="bulanan")
    s = sub.add_parser("ara-arb", help="batas auto rejection hari berikutnya")
    s.add_argument("acuan", type=_tipe(parse_angka), help="harga acuan (penutupan sebelumnya)")
    s.add_argument("--aturan", choices=tuple(ATURAN_AR), default="terkini")
    s.add_argument("--ara", type=_tipe(parse_angka), help="ganti persen ARA (untuk harga > Rp10)")
    s.add_argument("--arb", type=_tipe(parse_angka), help="ganti persen ARB (untuk harga > Rp10)")
    s.add_argument("--hari", type=int, default=1, help="simulasi ARA/ARB beruntun N hari")
    s.add_argument("--fraksi-dari", choices=("acuan", "hasil"), default="acuan",
                   help="fraksi mengikuti rentang harga acuan (default) atau harga hasil")
    s = sub.add_parser("right-issue", help="harga teoretis & dampak right issue")
    s.add_argument("--harga", type=_tipe(parse_angka), required=True, help="harga pasar saat cum")
    s.add_argument("--tebus", type=_tipe(parse_angka), required=True, help="harga pelaksanaan/tebus")
    s.add_argument("--rasio", required=True, help="saham lama:HMETD, mis. 5:2")
    s.add_argument("--lot", type=int, default=0, help="jumlah lot yang Anda miliki")
    s.add_argument("--avg", type=_tipe(parse_angka), help="harga rata-rata Anda")
    return p


def _opsional(x: Optional[Fraction]) -> Optional[float]:
    return None if x is None else float(x)


def jalankan(args: argparse.Namespace) -> str:
    if args.perintah == "average":
        if (args.target_avg is None) != (args.harga_beli is None):
            raise SahamError("--target-avg dan --harga-beli harus diisi bersamaan.")
        return teks_average(args.beli, args.fee_beli, args.fee_jual, args.target_avg, args.harga_beli)
    if args.perintah == "compounding":
        return teks_compounding(float(args.modal), float(args.setoran), float(args.ret),
                                args.tahun, args.frekuensi)
    if args.perintah == "ara-arb":
        return teks_ara_arb(args.acuan, args.aturan, _opsional(args.ara), _opsional(args.arb),
                            args.hari, args.fraksi_dari)
    return teks_right_issue(args.harga, args.tebus, args.rasio, args.lot, args.avg)


def _tanya(prompt: str, default: Optional[str] = None) -> str:
    teks = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return teks or (default or "")


def mode_interaktif() -> None:
    print("=== Kalkulator Saham: Average Down, Compounding, ARA/ARB, Right Issue ===")
    print("Edukasi saja, bukan rekomendasi jual/beli. Fee & aturan bisa berbeda.")
    while True:
        print("\n1. Average down / up\n2. Compounding (bunga majemuk)\n3. Batas ARA/ARB\n"
              "4. Right issue\n0. Keluar")
        pilihan = input("Pilih menu: ").strip()
        try:
            if pilihan == "0":
                print("Sampai jumpa! Ingat: selalu DYOR.")
                return
            if pilihan == "1":
                beli = []
                while True:
                    t = _tanya(f"Pembelian ke-{len(beli) + 1} (harga:lot, kosongkan bila selesai)", "")
                    if not t:
                        break
                    beli.append(parse_pembelian(t))
                fb = parse_angka(_tanya("Fee beli %", "0,15"))
                fj = parse_angka(_tanya("Fee jual %", "0,25"))
                tgt = _tanya("Target average (kosongkan bila tidak perlu)", "")
                hb = parse_angka(_tanya("Harga beli berikutnya")) if tgt else None
                print("\n" + teks_average(beli, fb, fj, parse_angka(tgt) if tgt else None, hb))
            elif pilihan == "2":
                print("\n" + teks_compounding(
                    float(parse_angka(_tanya("Modal awal (Rp)"))),
                    float(parse_angka(_tanya("Setoran per bulan (Rp)", "0"))),
                    float(parse_angka(_tanya("Return per tahun (%)"))),
                    int(parse_angka(_tanya("Durasi (tahun)"))),
                    _tanya("Frekuensi compounding (bulanan/tahunan)", "bulanan").lower()))
            elif pilihan == "3":
                acuan = parse_angka(_tanya("Harga acuan / penutupan kemarin (Rp)"))
                aturan = _tanya(f"Aturan ({'/'.join(ATURAN_AR)})", "terkini").lower()
                hari = int(_tanya("Simulasi berapa hari beruntun", "1"))
                print("\n" + teks_ara_arb(acuan, aturan, None, None, hari, "acuan"))
            elif pilihan == "4":
                harga = parse_angka(_tanya("Harga pasar saat cum (Rp)"))
                tebus = parse_angka(_tanya("Harga tebus / pelaksanaan (Rp)"))
                rasio = _tanya("Rasio saham lama:HMETD (mis. 5:2)")
                lot = int(_tanya("Lot yang Anda miliki (0 bila tidak ada)", "0"))
                avg = parse_angka(_tanya("Harga rata-rata Anda (Rp)")) if lot else None
                print("\n" + teks_right_issue(harga, tebus, rasio, lot, avg))
            else:
                print("Pilihan tidak dikenal.")
        except (SahamError, ValueError) as e:
            print(f"\nGalat: {e}")


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        if not argv:
            mode_interaktif()
            return 0
        args = buat_parser().parse_args(argv)
        if not args.perintah:
            buat_parser().print_help()
            return 2
        print(jalankan(args))
        return 0
    except SahamError as e:
        print(f"Galat: {e}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nDibatalkan.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
