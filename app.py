from datetime import date, datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_bareskrim_2026'

# 📊 DATA RESMI BARESKRIM (Sudah terintegrasi dengan Jenis, Status, dan Relasi Sub-Surat)
data_surat = [
    {
        "id": 1, "tanggal": "18-09-2026", "no": "498", 
        "nomor_tanggal_surat": "B/ND-796/IX/DIK.5./2026/Bagrenopsnal (17 September 2026)",
        "terima_dari": "Kabagrenopsnal Robinopsnal Bareskrim Polri", 
        "perihal": "Penyampaian hasil tindak lanjut rekomendasi Tim Komisi Percepatan Reformasi Polri tentang draft SOP",
        "lampiran": "1 berkas", "kepada": "Karobinops", "kualifikasi": "Surat Asli",
        "bagian_menangani": "Bagrenopsnal", "disposisi": "Yth Kabagrenops: Simulasikan ke pers robinopsnal kang hadi. Tks. 18/9/26",
        "jenis_surat": "Masuk", "status": "Baru", "parent_id": None
    },
    {
        "id": 2, "tanggal": "18-09-2026", "no": "497", 
        "nomor_tanggal_surat": "B/ND-11/I/IX/RES.1.18./2026/Dittipidum (18 September 2026)",
        "terima_dari": "Dirtipidum Bareskrim Polri", 
        "perihal": "Pelimpahan laporan polisi dugaan kasus penipuan online",
        "lampiran": "1 berkas", "kepada": "Karobinopsnal", "kualifikasi": "Surat Asli",
        "bagian_menangani": "Baganev", "disposisi": "Yth Kabaganev: Buat ND ke dittipidsiber untuk back-up tracking. Tks. 18/9/26",
        "jenis_surat": "Masuk", "status": "Diproses", "parent_id": None
    },
    {
        "id": 3, "tanggal": "19-09-2026", "no": "496", 
        "nomor_tanggal_surat": "B/ST-2105/IX/HUM.1.1./2026/Divhumas (19 September 2026)",
        "terima_dari": "Kadiv Humas Polri", 
        "perihal": "Permintaan data anev mingguan gangguan kamtibmas untuk rilis media",
        "lampiran": "-", "kepada": "Karobinops", "kualifikasi": "Surat Asli",
        "bagian_menangani": "Bagyanmas", "disposisi": "Yth Kabagyanmas: Siapkan bahan anev komparatif jajaran kordinasikan dengan urtu. Tks.",
        "jenis_surat": "Masuk", "status": "Diproses", "parent_id": None
    },
    {
        "id": 4, "tanggal": "20-09-2026", "no": "495", 
        "nomor_tanggal_surat": "B/ND-552/IX/KERMA/2026/Bagkerma (20 September 2026)",
        "terima_dari": "Kabagkerma Robinopsnal Bareskrim", 
        "perihal": "Rencana rapat koordinasi pembahasan draf MoU kerja sama penanganan kejahatan lintas negara",
        "lampiran": "2 lembar", "kepada": "Karobinops", "kualifikasi": "Surat Tembusan",
        "bagian_menangani": "Bagkerma", "disposisi": "Yth Kabagkerma: Jadwalkan hari selasa ini di ruang rapat utama. Tks.",
        "jenis_surat": "Keluar", "status": "Selesai", "parent_id": None
    }
]


def _parse_tanggal_surat(value):
    for date_format in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, date_format).date()
        except (TypeError, ValueError):
            continue
    return None


def _build_analytics(period):
    parsed_dates = [
        (surat, _parse_tanggal_surat(surat.get("tanggal")))
        for surat in data_surat
    ]
    valid_dates = [tanggal for _, tanggal in parsed_dates if tanggal]
    anchor = max(valid_dates) if valid_dates else date.today()

    if period == "bulanan":
        anchor_month = anchor.replace(day=1)
        nama_bulan = (
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember",
        )
        buckets = []
        for offset in range(5, -1, -1):
            month_index = anchor_month.year * 12 + anchor_month.month - 1 - offset
            year, month_index = divmod(month_index, 12)
            month = month_index + 1
            bucket_date = date(year, month, 1)
            buckets.append({
                "key": bucket_date.strftime("%Y-%m"),
                "label": f"{nama_bulan[month - 1][:3]} {year}",
                "title": f"{nama_bulan[month - 1]} {year}",
            })
    else:
        period = "mingguan"
        buckets = [
            {
                "key": (anchor - timedelta(days=offset)).isoformat(),
                "label": (anchor - timedelta(days=offset)).strftime("%d/%m"),
                "title": (anchor - timedelta(days=offset)).strftime("%d-%m-%Y"),
            }
            for offset in range(6, -1, -1)
        ]

    bucket_by_key = {}
    for bucket in buckets:
        bucket.update({"baru": 0, "diproses": 0, "selesai": 0, "total": 0})
        bucket_by_key[bucket["key"]] = bucket

    for surat, tanggal in parsed_dates:
        if not tanggal:
            continue
        key = tanggal.strftime("%Y-%m") if period == "bulanan" else tanggal.isoformat()
        bucket = bucket_by_key.get(key)
        if not bucket:
            continue
        status = (surat.get("status") or "").strip().lower()
        status_key = status if status in ("baru", "diproses", "selesai") else "baru"
        bucket[status_key] += 1
        bucket["total"] += 1

    max_total = max((bucket["total"] for bucket in buckets), default=0)
    for bucket in buckets:
        for status in ("baru", "diproses", "selesai"):
            bucket[f"{status}_height"] = (
                bucket[status] / max_total * 100 if max_total else 0
            )

    totals = {
        status: sum(bucket[status] for bucket in buckets)
        for status in ("baru", "diproses", "selesai")
    }
    totals["total"] = sum(bucket["total"] for bucket in buckets)
    return buckets, totals, anchor, period


@app.route('/login', methods=['GET', 'POST'])
def login():
    pesan_error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'urtu.bareskrim' and password == 'urtu123':
            session['is_logged_in'] = True
            session['username'] = username
            session['role'] = 'operator'
            return redirect(url_for('index'))
        elif username == 'karo.opsnal' and password == 'karo123':
            session['is_logged_in'] = True
            session['username'] = username
            session['role'] = 'pimpinan'
            return redirect(url_for('index'))
        else:
            pesan_error = "Username atau Password salah! Akses ditolak."
    return render_template('login.html', error=pesan_error)

@app.route('/')
def index():
    if not session.get('is_logged_in'):
        return redirect(url_for('login'))
        
    kata_kunci = request.args.get('q', '').strip().lower()
    filter_bagian = request.args.get('bagian', '').strip()
    filter_kualifikasi = request.args.get('kualifikasi', '').strip()
    periode_analitik = request.args.get('periode', 'mingguan').strip().lower()
    if periode_analitik not in ('mingguan', 'bulanan'):
        periode_analitik = 'mingguan'
    analytics_visible = request.args.get('analitik') == '1'
    grafik, ringkasan_analitik, tanggal_terbaru, periode_analitik = _build_analytics(periode_analitik)
    
    # Kelompokkan anak surat di bawah induknya masing-masing
    surat_induk = [s for s in data_surat if s.get('parent_id') is None]
    surat_anak = [s for s in data_surat if s.get('parent_id') is not None]
    
    data_terstruktur = []
    for induk in surat_induk:
        data_terstruktur.append(induk.copy())
        for anak in surat_anak:
            if anak.get('parent_id') == induk['id']:
                data_terstruktur.append(anak.copy())
                
    for anak in surat_anak:
        if anak not in data_terstruktur:
            data_terstruktur.append(anak)

    data_disaring = data_terstruktur.copy()
    
    if filter_bagian:
        data_disaring = [s for s in data_disaring if s['bagian_menangani'].lower() == filter_bagian.lower()]
        
    if filter_kualifikasi:
        data_disaring = [s for s in data_disaring if s['kualifikasi'].lower() == filter_kualifikasi.lower()]
        
    if kata_kunci:
        data_disaring = [s for s in data_disaring if (
            kata_kunci in s['nomor_tanggal_surat'].lower() or 
            kata_kunci in s['perihal'].lower() or 
            kata_kunci in s['terima_dari'].lower() or
            kata_kunci in s['no'].lower()
        )]
        
    return render_template(
        'index.html', 
        data_list=data_disaring, 
        pencarian=kata_kunci, 
        bagian_aktif=filter_bagian,
        kualifikasi_aktif=filter_kualifikasi,
        role=session.get('role'),
        grafik=grafik,
        ringkasan_analitik=ringkasan_analitik,
        tanggal_terbaru=tanggal_terbaru,
        periode_analitik=periode_analitik,
        analytics_visible=analytics_visible
    )

@app.route('/tambah', methods=['GET', 'POST'])
def tambah():
    if not session.get('is_logged_in'):
        return redirect(url_for('login'))
    if session.get('role') != 'operator':
        return "<h3>Akses Ditolak!</h3><br><a href='/'>Kembali</a>"
        
    if request.method == 'POST':
        p_id = request.form.get('parent_id')
        p_id = int(p_id) if p_id else None
        
        data_baru = {
            "id": len(data_surat) + 1,
            "tanggal": request.form.get('tanggal'),
            "no": request.form.get('no'),
            "nomor_tanggal_surat": request.form.get('nomor_tanggal_surat'),
            "terima_dari": request.form.get('terima_dari'),
            "perihal": request.form.get('perihal'),
            "lampiran": request.form.get('lampiran'),
            "kepada": request.form.get('kepada'),
            "kualifikasi": request.form.get('kualifikasi'),
            "bagian_menangani": request.form.get('bagian_menangani'),
            "disposisi": request.form.get('disposisi'),
            "jenis_surat": request.form.get('jenis_surat'),
            "status": request.form.get('status'),
            "parent_id": p_id
        }
        data_surat.insert(0, data_baru)
        return redirect(url_for('index'))
        
    return render_template('tambah.html', semua_surat=data_surat)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
