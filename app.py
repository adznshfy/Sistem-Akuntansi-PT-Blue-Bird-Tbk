from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import json
from datetime import date
import math

app = Flask(__name__)
app.secret_key = 'bluebird_rahasia'

# Konfigurasi Database
DB_CONFIG = {'host': 'localhost', 'user': 'root', 'password': '', 'database': 'akuntansi_bluebird'}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

# --- DASHBOARD (LOGIKA BARU) ---
@app.route('/dashboard')
def dashboard():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    # 1. Total Statistik (Kartu Atas)
    cur.execute("SELECT SUM(debit) as d, SUM(kredit) as k FROM jurnal WHERE status = 'Active'")
    res = cur.fetchone()
    t_debit = res['d'] or 0
    t_kredit = res['k'] or 0

    cur.execute("SELECT COUNT(*) as total FROM coa")
    t_akun = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM jurnal WHERE status = 'Active'")
    t_transaksi = cur.fetchone()['total']
    
    # 2. DATA BAR CHART: Pendapatan vs Beban
    # Hitung Total Pendapatan (Kredit - Debit)
    cur.execute("""
        SELECT SUM(j.kredit - j.debit) as val 
        FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun 
        WHERE c.kategori='Pendapatan' AND j.status='Active'
    """)
    res_pdpt = cur.fetchone()
    val_pdpt = res_pdpt['val'] if res_pdpt and res_pdpt['val'] else 0
    
    # Hitung Total Beban (Debit - Kredit)
    cur.execute("""
        SELECT SUM(j.debit - j.kredit) as val 
        FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun 
        WHERE c.kategori='Beban' AND j.status='Active'
    """)
    res_beban = cur.fetchone()
    val_beban = res_beban['val'] if res_beban and res_beban['val'] else 0
    
    # 3. DATA PIE CHART: Komposisi ASET (Kas, Bank, Kendaraan, dll)
    # Kita ambil akun Aset yang saldonya > 0
    cur.execute("""
        SELECT c.nama_akun, SUM(j.debit - j.kredit) as val 
        FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun 
        WHERE c.kategori='Aset' AND j.status='Active' 
        GROUP BY c.nama_akun
        HAVING val > 0
    """)
    pie_aset_data = cur.fetchall()
    
    # 4. DATA LINE CHART: Tren Arus Kas (Akun 1100)
    cur.execute("""
        SELECT tanggal, SUM(debit - kredit) as flow 
        FROM jurnal 
        WHERE kode_akun='1100' AND status='Active' 
        GROUP BY tanggal 
        ORDER BY tanggal LIMIT 7
    """)
    line_data = cur.fetchall()
    
    conn.close()
    
    # Kirim data ke HTML (Konversi ke JSON untuk Chart.js)
    return render_template('dashboard.html', 
                           t_debit=t_debit, t_kredit=t_kredit,
                           t_akun=t_akun, t_transaksi=t_transaksi,
                           # Bar Chart Data
                           bar_label=json.dumps(['Pendapatan', 'Beban']),
                           bar_data=json.dumps([float(val_pdpt), float(val_beban)]),
                           # Pie Chart Data (ASET)
                           pie_labels=json.dumps([r['nama_akun'] for r in pie_aset_data]), 
                           pie_values=json.dumps([float(r['val']) for r in pie_aset_data]),
                           # Line Chart Data
                           line_labels=json.dumps([str(r['tanggal']) for r in line_data]), 
                           line_values=json.dumps([float(r['flow']) for r in line_data]))

from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import json
from datetime import date

app = Flask(__name__)
app.secret_key = 'bluebird_rahasia'

# Konfigurasi Database
DB_CONFIG = {'host': 'localhost', 'user': 'root', 'password': '', 'database': 'akuntansi_bluebird'}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

# --- DASHBOARD (LOGIKA EXECUTIVE: LABA BERSIH & SALDO KAS) ---
@app.route('/dashboard')
def dashboard():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    # 1. Total Statistik (Kartu 1 & 2)
    cur.execute("SELECT SUM(debit) as d, SUM(kredit) as k FROM jurnal WHERE status = 'Active'")
    res = cur.fetchone()
    t_debit = res['d'] or 0
    t_kredit = res['k'] or 0
    
    # 2. DATA BAR CHART & LABA BERSIH (Kartu 3)
    # Hitung Pendapatan
    cur.execute("""
        SELECT SUM(j.kredit - j.debit) as val 
        FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun 
        WHERE c.kategori='Pendapatan' AND j.status='Active'
    """)
    res_pdpt = cur.fetchone()
    val_pdpt = res_pdpt['val'] if res_pdpt and res_pdpt['val'] else 0
    
    # Hitung Beban
    cur.execute("""
        SELECT SUM(j.debit - j.kredit) as val 
        FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun 
        WHERE c.kategori='Beban' AND j.status='Active'
    """)
    res_beban = cur.fetchone()
    val_beban = res_beban['val'] if res_beban and res_beban['val'] else 0
    
    # [LOGIKA BARU] Hitung Laba Bersih untuk Kartu ke-3
    laba_bersih = val_pdpt - val_beban

    # [LOGIKA BARU] Hitung Saldo Kas & Bank untuk Kartu ke-4
    # Mengambil akun 1100 (Kas) dan 1101 (Bank)
    cur.execute("""
        SELECT SUM(debit - kredit) as val 
        FROM jurnal 
        WHERE kode_akun IN ('1100', '1101') AND status = 'Active'
    """)
    res_kas = cur.fetchone()
    saldo_kas = res_kas['val'] if res_kas and res_kas['val'] else 0
    
    # 3. DATA PIE CHART: Komposisi ASET
    cur.execute("""
        SELECT c.nama_akun, SUM(j.debit - j.kredit) as val 
        FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun 
        WHERE c.kategori='Aset' AND j.status='Active' 
        GROUP BY c.nama_akun
        HAVING val > 0
    """)
    pie_aset_data = cur.fetchall()
    
    # 4. DATA LINE CHART: Tren Arus Kas (Akun 1100)
    cur.execute("""
        SELECT DATE_FORMAT(tanggal, '%d %b') as tgl_formatted, SUM(debit - kredit) as flow 
        FROM jurnal 
        WHERE kode_akun='1101' AND status='Active' 
        GROUP BY tanggal 
        ORDER BY tanggal ASC
    """)
    line_data = cur.fetchall()
    
    line_labels_list = [x['tgl_formatted'] for x in line_data] if line_data else []
    line_values_list = [float(x['flow']) for x in line_data] if line_data else []
    
    line_labels = json.dumps(line_labels_list)
    line_values = json.dumps(line_values_list)
    
    conn.close()
    
    return render_template('dashboard.html', 
                           t_debit=t_debit, t_kredit=t_kredit,
                           laba_bersih=laba_bersih, # Dikirim ke Kartu 3
                           saldo_kas=saldo_kas,     # Dikirim ke Kartu 4
                           
                           # Data Chart
                           bar_label=json.dumps(['Pendapatan', 'Beban']),
                           bar_data=json.dumps([float(val_pdpt), float(val_beban)]),
                           pie_labels=json.dumps([r['nama_akun'] for r in pie_aset_data]), 
                           pie_values=json.dumps([float(r['val']) for r in pie_aset_data]),
                           line_labels=line_labels, 
                           line_values=line_values)

# --- JURNAL UMUM (DENGAN PAGINATION) ---
@app.route('/jurnal_umum')
def jurnal_umum():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    # 1. Setup Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20  # 20 Baris = Estimasi 10 Transaksi
    offset = (page - 1) * per_page
    
    # 2. Ambil Filter
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # --- QUERY 1: HITUNG TOTAL DATA (Untuk tahu jumlah halaman) ---
    count_query = "SELECT COUNT(*) as total FROM jurnal j WHERE 1=1"
    params = []
    
    if start_date and end_date:
        count_query += " AND j.tanggal BETWEEN %s AND %s"
        params.extend([start_date, end_date])
        
    cur.execute(count_query, tuple(params))
    total_rows = cur.fetchone()['total']
    total_pages = math.ceil(total_rows / per_page)
    
    # --- QUERY 2: AMBIL DATA (Dengan Limit & Offset) ---
    query = """
        SELECT j.id, j.tanggal, j.deskripsi, j.kode_akun, c.nama_akun, j.debit, j.kredit, j.status 
        FROM jurnal j JOIN coa c ON j.kode_akun = c.kode_akun 
        WHERE 1=1 
    """
    
    # Gunakan params baru untuk query data karena params lama sudah dipakai execute
    data_params = []
    if start_date and end_date:
        query += " AND j.tanggal BETWEEN %s AND %s"
        data_params.extend([start_date, end_date])
    
    # Sorting & Pagination
    query += " ORDER BY j.tanggal DESC, j.id ASC LIMIT %s OFFSET %s"
    data_params.extend([per_page, offset])
    
    cur.execute(query, tuple(data_params))
    data = cur.fetchall()
    conn.close()
    
    return render_template('jurnal_umum.html', 
                           data_jurnal=data, 
                           start_date=start_date, 
                           end_date=end_date,
                           page=page, 
                           total_pages=total_pages,
                           total_rows=total_rows)

# --- MASTER COA ---
@app.route('/coa')
def coa():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    # Query mengambil saldo akhir
    query = """
        SELECT c.*, 
        COALESCE(SUM(j.debit), 0) as mutasi_debit,
        COALESCE(SUM(j.kredit), 0) as mutasi_kredit
        FROM coa c
        LEFT JOIN jurnal j ON c.kode_akun = j.kode_akun AND j.status = 'Active'
        GROUP BY c.kode_akun
        ORDER BY c.kode_akun ASC
    """
    cur.execute(query)
    accounts = cur.fetchall()
    
    coa_list = []
    total_akun = len(accounts)
    
    for acc in accounts:
        if acc['saldo_normal'] == 'Debit':
            saldo_akhir = acc['mutasi_debit'] - acc['mutasi_kredit']
        else:
            saldo_akhir = acc['mutasi_kredit'] - acc['mutasi_debit']
        acc['saldo_akhir'] = saldo_akhir
        coa_list.append(acc)
        
    conn.close()
    return render_template('coa.html', coa_list=coa_list, total_akun=total_akun)

# --- TAMBAH AKUN BARU (DENGAN SUB KATEGORI) ---
@app.route('/tambah_akun', methods=['POST'])
def tambah_akun():
    conn = get_db()
    cur = conn.cursor()
    try:
        kode = request.form['kode_akun']
        nama = request.form['nama_akun']
        kategori = request.form['kategori']
        saldo_normal = request.form['saldo_normal']
        # Tangkap sub kategori agar otomatis terfilter di laporan
        sub_kategori = request.form.get('sub_kategori', None) 

        cur.execute("SELECT * FROM coa WHERE kode_akun = %s", (kode,))
        if cur.fetchone():
            flash(f"Error: Kode Akun {kode} sudah ada!", "danger")
        else:
            cur.execute("""
                INSERT INTO coa (kode_akun, nama_akun, kategori, saldo_normal, sub_kategori) 
                VALUES (%s, %s, %s, %s, %s)
            """, (kode, nama, kategori, saldo_normal, sub_kategori))
            conn.commit()
            flash("Akun berhasil ditambahkan!", "success")
            
    except Exception as e:
        flash(f"Terjadi kesalahan: {e}", "danger")
    finally:
        conn.close()
    
    return redirect(url_for('coa'))

# --- UPDATE AKUN (EDIT) ---
@app.route('/edit_akun', methods=['POST'])
def edit_akun():
    conn = get_db()
    cur = conn.cursor()
    try:
        kode_lama = request.form['kode_akun_lama'] # Key untuk mencari
        nama = request.form['nama_akun']
        kategori = request.form['kategori']
        saldo_normal = request.form['saldo_normal']
        sub_kategori = request.form['sub_kategori']

        query = """
            UPDATE coa 
            SET nama_akun=%s, kategori=%s, saldo_normal=%s, sub_kategori=%s
            WHERE kode_akun=%s
        """
        cur.execute(query, (nama, kategori, saldo_normal, sub_kategori, kode_lama))
        conn.commit()
        flash(f"Akun {kode_lama} berhasil diperbarui!", "success")
    except Exception as e:
        flash(f"Gagal update: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('coa'))

# --- HAPUS AKUN (DELETE) ---
@app.route('/hapus_akun/<kode>', methods=['POST'])
def hapus_akun(kode):
    conn = get_db()
    cur = conn.cursor()
    try:
        # Cek dulu apakah akun ini pernah dipakai transaksi?
        cur.execute("SELECT COUNT(*) FROM jurnal WHERE kode_akun = %s", (kode,))
        jumlah_transaksi = cur.fetchone()[0]

        if jumlah_transaksi > 0:
            flash(f"Gagal! Akun {kode} tidak bisa dihapus karena sudah ada {jumlah_transaksi} transaksi terkait.", "danger")
        else:
            cur.execute("DELETE FROM coa WHERE kode_akun = %s", (kode,))
            conn.commit()
            flash(f"Akun {kode} berhasil dihapus permanen.", "success")
    except Exception as e:
        flash(f"Terjadi kesalahan: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('coa'))

# --- INPUT JURNAL (VALIDASI Q3 & DEFAULT TANGGAL FIXED) ---
@app.route('/jurnal', methods=['GET', 'POST'])
def input_jurnal():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        try:
            tgl = request.form['tanggal']
            desc = request.form['deskripsi']
            akun_list = request.form.getlist('kode_akun[]')
            debit_list = request.form.getlist('debit[]')
            kredit_list = request.form.getlist('kredit[]')
            
            # 1. Validasi Tanggal (Wajib Q3)
            start_date = '2025-07-01'
            end_date = '2025-09-30'
            if tgl < start_date or tgl > end_date:
                flash(f'Gagal: Tanggal harus dalam periode Q3 (1 Juli - 30 September 2025)!', 'danger')
                return redirect(url_for('input_jurnal'))

            total_d = sum(float(x) for x in debit_list)
            total_k = sum(float(x) for x in kredit_list)
            
            # 2. Validasi Balance & Nol
            if abs(total_d - total_k) > 1.0:
                flash(f'Gagal: Tidak Balance! Selisih: {total_d - total_k}', 'danger')
            elif total_d == 0:
                flash('Gagal: Nominal nol!', 'danger')
            else:
                # 3. Validasi Saldo Kas (Cegah Minus)
                kredit_kas_baru = 0
                for i in range(len(akun_list)):
                    if akun_list[i] == '1100': # Kode 1100 = KAS
                        kredit_kas_baru += float(kredit_list[i])
                
                saldo_cukup = True
                if kredit_kas_baru > 0:
                    cur.execute("SELECT SUM(debit - kredit) as saldo FROM jurnal WHERE kode_akun = '1100' AND status = 'Active'")
                    res_saldo = cur.fetchone()
                    saldo_kas = res_saldo['saldo'] if res_saldo['saldo'] else 0
                    if (saldo_kas - kredit_kas_baru) < 0:
                        flash(f'Gagal: Saldo Kas Tidak Cukup! Sisa: {saldo_kas:,.0f}', 'danger')
                        saldo_cukup = False
                
                # Simpan jika aman
                if saldo_cukup:
                    for i in range(len(akun_list)):
                        kode = akun_list[i]
                        d = float(debit_list[i])
                        k = float(kredit_list[i])
                        if d > 0 or k > 0:
                            query = "INSERT INTO jurnal (tanggal, deskripsi, kode_akun, debit, kredit, status) VALUES (%s, %s, %s, %s, %s, 'Active')"
                            cur.execute(query, (tgl, desc, kode, d, k))
                    conn.commit()
                    flash('Jurnal berhasil disimpan!', 'success')
                    
        except Exception as e:
            conn.rollback()
            flash(f"Error Database: {e}", 'danger')
            
        return redirect(url_for('input_jurnal'))
        
    cur.execute("SELECT * FROM coa ORDER BY kode_akun")
    akun_list = cur.fetchall()
    conn.close()
    
    # REVISI: Set Default Tanggal ke Akhir Q3 (2025-09-30) agar user tidak repot
    return render_template('jurnal.html', akun_list=akun_list, today='2025-09-30')

# --- VOID JURNAL ---
@app.route('/void_jurnal/<int:id_jurnal>', methods=['POST'])
def void_jurnal(id_jurnal):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE jurnal SET status = 'Void', deskripsi = CONCAT(deskripsi, ' [DIBATALKAN]') WHERE id = %s", (id_jurnal,))
        conn.commit()
        flash('Transaksi dibatalkan (Void)!', 'success')
    except Exception as e:
        flash(f'Gagal: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('jurnal_umum'))

# --- BUKU BESAR ---
@app.route('/bukubesar')
def bukubesar():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    selected_akun = request.args.get('akun')
    transaksi = []
    info_akun = None
    
    cur.execute("SELECT * FROM coa ORDER BY kode_akun")
    akun_list = cur.fetchall()

    if selected_akun:
        cur.execute("SELECT * FROM coa WHERE kode_akun = %s", (selected_akun,))
        info_akun = cur.fetchone()
        
        cur.execute("SELECT * FROM jurnal WHERE kode_akun = %s AND status = 'Active' ORDER BY tanggal, id", (selected_akun,))
        raw_transaksi = cur.fetchall()

        current_saldo = 0
        for t in raw_transaksi:
            if info_akun['saldo_normal'] == 'Debit':
                current_saldo += (t['debit'] - t['kredit'])
            else:
                current_saldo += (t['kredit'] - t['debit'])
            t['saldo_posisi'] = current_saldo
            transaksi.append(t)
            
    conn.close()
    return render_template('bukubesar.html', akun_list=akun_list, transaksi=transaksi, selected=selected_akun, info_akun=info_akun)

# --- LAPORAN KEUANGAN BLUE BIRD ---
@app.route('/laporan')
def laporan_default():
    return redirect(url_for('laporan_view', jenis='labarugi'))

@app.route('/laporan/<jenis>')
def laporan_view(jenis):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    # Init vars
    data = {}
    aset = []; liabilitas = []; ekuitas = []
    t_aset = 0; t_pasiva = 0; arus_kas = []; kas_akhir = 0
    laba_bersih = 0
    
    # 1. HITUNG LABA RUGI DULU (Karena dipakai di Neraca & Ekuitas)
    cur.execute("""
        SELECT c.kode_akun, c.nama_akun, c.sub_kategori,
        CASE 
            WHEN c.saldo_normal = 'Kredit' THEN SUM(j.kredit - j.debit)
            ELSE SUM(j.debit - j.kredit)
        END as nominal
        FROM coa c 
        LEFT JOIN jurnal j ON c.kode_akun = j.kode_akun AND j.status = 'Active'
        WHERE c.kategori IN ('Pendapatan', 'Beban')
        GROUP BY c.kode_akun
        HAVING nominal != 0
    """)
    raw_lr = cur.fetchall()
    
    # FILTER LIST (LOGIKA BLUE BIRD)
    list_pendapatan = [x for x in raw_lr if x['sub_kategori'] == 'Pendapatan Usaha']
    list_beban_pokok = [x for x in raw_lr if x['sub_kategori'] == 'Beban Langsung']
    list_beban_ops = [x for x in raw_lr if x['sub_kategori'] == 'Beban Operasional']
    list_lain_lain = [x for x in raw_lr if x['sub_kategori'] in ['Pendapatan Lain-lain', 'Beban Lain-lain']]
    list_pajak = [x for x in raw_lr if x['sub_kategori'] == 'Beban Pajak']

    # HITUNG SUBTOTAL
    total_pendapatan = sum(x['nominal'] for x in list_pendapatan)
    total_beban_pokok = sum(x['nominal'] for x in list_beban_pokok)
    laba_kotor = total_pendapatan - total_beban_pokok
    
    total_beban_ops = sum(x['nominal'] for x in list_beban_ops)
    laba_usaha = laba_kotor - total_beban_ops
    
    # Hitung Lain-lain (Net)
    total_lain_lain = 0
    for x in list_lain_lain:
        if 'Beban' in x['nama_akun'] or 'Rugi' in x['nama_akun']:
            total_lain_lain -= x['nominal'] 
            x['nominal'] = -abs(x['nominal']) # Tanda minus visual
        else:
            total_lain_lain += x['nominal']

    laba_sebelum_pajak = laba_usaha + total_lain_lain
    beban_pajak = sum(x['nominal'] for x in list_pajak)
    laba_bersih = laba_sebelum_pajak - beban_pajak

    # --- Routing View ---
    if jenis == 'labarugi':
        data = {
            'list_pendapatan': list_pendapatan, 'total_pendapatan': total_pendapatan,
            'list_beban_pokok': list_beban_pokok, 'total_beban_pokok': total_beban_pokok,
            'laba_kotor': laba_kotor,
            'list_beban_ops': list_beban_ops, 'total_beban_ops': total_beban_ops,
            'laba_usaha': laba_usaha,
            'list_lain_lain': list_lain_lain,
            'laba_sebelum_pajak': laba_sebelum_pajak,
            'beban_pajak': beban_pajak,
            'laba_bersih': laba_bersih
        }

    elif jenis == 'neraca':
        # --- PERBAIKAN QUERY NERACA (MENGAMBIL SUB_KATEGORI) ---
        
        # 1. Asset (Debit - Kredit)
        cur.execute("""
            SELECT c.kode_akun, c.nama_akun, c.sub_kategori, 
            SUM(j.debit - j.kredit) as val 
            FROM coa c 
            LEFT JOIN jurnal j ON c.kode_akun = j.kode_akun AND j.status = 'Active'
            WHERE c.kategori = 'Aset'
            GROUP BY c.kode_akun 
            HAVING val != 0
        """)
        aset = cur.fetchall()
        t_aset = sum(x['val'] for x in aset)
        
        # 2. Liabilitas (Kredit - Debit)
        cur.execute("""
            SELECT c.kode_akun, c.nama_akun, c.sub_kategori, 
            SUM(j.kredit - j.debit) as val 
            FROM coa c 
            LEFT JOIN jurnal j ON c.kode_akun = j.kode_akun AND j.status = 'Active'
            WHERE c.kategori = 'Liabilitas'
            GROUP BY c.kode_akun 
            HAVING val != 0
        """)
        liabilitas = cur.fetchall()
        
        # 3. Ekuitas (Kredit - Debit) - Tanpa Laba Tahun Berjalan
        cur.execute("""
            SELECT c.kode_akun, c.nama_akun, c.sub_kategori, 
            SUM(j.kredit - j.debit) as val 
            FROM coa c 
            LEFT JOIN jurnal j ON c.kode_akun = j.kode_akun AND j.status = 'Active'
            WHERE c.kategori = 'Ekuitas'
            GROUP BY c.kode_akun 
            HAVING val != 0
        """)
        ekuitas = cur.fetchall()
        
        t_pasiva = sum(x['val'] for x in liabilitas) + sum(x['val'] for x in ekuitas) + laba_bersih

    elif jenis == 'ekuitas':
         cur.execute("""
            SELECT c.nama_akun, SUM(kredit-debit) as val FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun 
            WHERE c.kategori='Ekuitas' AND j.status='Active' 
            GROUP BY c.nama_akun HAVING val!=0
        """)
         ekuitas = cur.fetchall()

    elif jenis == 'aruskas':
        # --- PERBAIKAN 1: DEFINISIKAN TANGGAL DULU ---
        # Ambil dari parameter URL (misal: ?start_date=2025-07-01)
        # Atau gunakan default jika tidak ada input
        from flask import request 
        start_date = request.args.get('start_date', '2025-07-01') 
        end_date = request.args.get('end_date', '2025-09-30')

        # --- PERBAIKAN 2: INDENTASI (Semua kode di bawah ini menjorok ke dalam) ---
        
        # LANGKAH 1: HITUNG SALDO AWAL (REAL)
        # Menggunakan akun 1101 sesuai gambar Master COA Anda
        query_awal = """
            SELECT COALESCE(SUM(debit - kredit), 0) as saldo_awal
            FROM jurnal 
            WHERE kode_akun = '1101' 
            AND status = 'Active' 
            AND (tanggal < %s OR (tanggal = %s AND deskripsi LIKE '%%Saldo Awal%%'))
        """
        cur.execute(query_awal, (start_date, start_date))
        result_awal = cur.fetchone()
        kas_awal = result_awal['saldo_awal'] if result_awal else 0
        
        # LANGKAH 2: AMBIL TRANSAKSI PERIODE BERJALAN
        query_aktivitas = """
            SELECT tanggal, deskripsi, (debit - kredit) as aliran 
            FROM jurnal 
            WHERE kode_akun = '1101' 
            AND status = 'Active' 
            AND tanggal BETWEEN %s AND %s
            AND deskripsi NOT LIKE '%%Saldo Awal%%'
            ORDER BY tanggal ASC
        """
        cur.execute(query_aktivitas, (start_date, end_date))
        raw_cash = cur.fetchall()
        
        arus_operasi = []
        arus_investasi = []
        arus_pendanaan = []
        
        # LANGKAH 3: KLASIFIKASI OTOMATIS
        for row in raw_cash:
            desc = row['deskripsi'].lower()
            keyword_pendanaan = ['modal', 'saham', 'investor', 'dividen', 'pinjaman bank', 'prive']
            keyword_investasi = ['beli aset', 'jual aset', 'beli kendaraan', 'peralatan', 'investasi']
            
            if any(x in desc for x in keyword_pendanaan):
                arus_pendanaan.append(row)
            elif any(x in desc for x in keyword_investasi):
                arus_investasi.append(row)
            else:
                arus_operasi.append(row)

        total_operasi = sum(x['aliran'] for x in arus_operasi)
        total_investasi = sum(x['aliran'] for x in arus_investasi)
        total_pendanaan = sum(x['aliran'] for x in arus_pendanaan)
        
        kenaikan_bersih = total_operasi + total_investasi + total_pendanaan
        kas_akhir = kas_awal + kenaikan_bersih
        
        arus_kas = {
            'operasi': arus_operasi, 'total_operasi': total_operasi,
            'investasi': arus_investasi, 'total_investasi': total_investasi,
            'pendanaan': arus_pendanaan, 'total_pendanaan': total_pendanaan,
            'kenaikan_bersih': kenaikan_bersih,
            'kas_awal': kas_awal,
            'kas_akhir': kas_akhir,
            'periode_awal': start_date, 
            'periode_akhir': end_date
        }
    
    conn.close()
    
    return render_template('laporan.html', 
                           jenis=jenis, 
                           data=data, 
                           laba=laba_bersih,
                           aset=aset, t_aset=t_aset, 
                           liabilitas=liabilitas, ekuitas=ekuitas, t_pasiva=t_pasiva, 
                           arus_kas=arus_kas, kas_akhir=kas_akhir,
                           today=date.today().strftime('%d %B %Y'))

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)