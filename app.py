from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import json
from datetime import date

app = Flask(__name__)
app.secret_key = 'bluebird_rahasia'

DB_CONFIG = {'host': 'localhost', 'user': 'root', 'password': '', 'database': 'akuntansi_bluebird'}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

# --- DASHBOARD ---
@app.route('/dashboard')
def dashboard():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    cur.execute("SELECT SUM(debit) as d, SUM(kredit) as k FROM jurnal")
    res = cur.fetchone()
    total_debit = res['d'] or 0
    total_kredit = res['k'] or 0
    
    # Data Grafik
    cur.execute("SELECT c.kategori, SUM(j.kredit - j.debit) as val FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun WHERE c.kategori='Pendapatan' GROUP BY c.kategori")
    pdpt = cur.fetchone()
    val_pdpt = pdpt['val'] if pdpt else 0
    
    cur.execute("SELECT c.kategori, SUM(j.debit - j.kredit) as val FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun WHERE c.kategori='Beban' GROUP BY c.kategori")
    beban = cur.fetchone()
    val_beban = beban['val'] if beban else 0
    
    # Pie Chart
    cur.execute("SELECT c.nama_akun, SUM(j.debit - j.kredit) as val FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun WHERE c.kategori='Beban' GROUP BY c.nama_akun")
    pie_data = cur.fetchall()
    
    # Line Chart
    cur.execute("SELECT tanggal, SUM(debit - kredit) as flow FROM jurnal WHERE kode_akun='1100' GROUP BY tanggal ORDER BY tanggal LIMIT 7")
    line_data = cur.fetchall()
    
    conn.close()
    return render_template('dashboard.html', 
                           t_debit=total_debit, t_kredit=total_kredit,
                           bar_data=[float(val_pdpt), float(val_beban)],
                           pie_labels=json.dumps([r['nama_akun'] for r in pie_data]), 
                           pie_values=json.dumps([float(r['val']) for r in pie_data]),
                           line_labels=json.dumps([str(r['tanggal']) for r in line_data]), 
                           line_values=json.dumps([float(r['flow']) for r in line_data]))

# --- JURNAL UMUM (MENU BARU) ---
@app.route('/jurnal_umum')
def jurnal_umum():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    # Ambil semua jurnal urut tanggal terbaru
    query = """
        SELECT j.tanggal, j.deskripsi, j.kode_akun, c.nama_akun, j.debit, j.kredit 
        FROM jurnal j 
        JOIN coa c ON j.kode_akun = c.kode_akun 
        ORDER BY j.tanggal DESC, j.id DESC
    """
    cur.execute(query)
    data_jurnal = cur.fetchall()
    conn.close()
    return render_template('jurnal_umum.html', data_jurnal=data_jurnal)

# --- COA ---
@app.route('/coa')
def coa():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM coa ORDER BY kode_akun")
    accounts = cur.fetchall()
    coa_list = []
    for acc in accounts:
        if acc['saldo_normal'] == 'Debit':
            q = "SELECT SUM(debit - kredit) as sal FROM jurnal WHERE kode_akun = %s"
        else:
            q = "SELECT SUM(kredit - debit) as sal FROM jurnal WHERE kode_akun = %s"
        cur.execute(q, (acc['kode_akun'],))
        acc['saldo_akhir'] = cur.fetchone()['sal'] or 0
        coa_list.append(acc)
    conn.close()
    return render_template('coa.html', coa_list=coa_list)

# --- INPUT JURNAL ---
@app.route('/jurnal', methods=['GET', 'POST'])
def input_jurnal():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    if request.method == 'POST':
        try:
            tgl = request.form['tanggal']
            desc = request.form['deskripsi']
            ad = request.form['akun_debit']
            ak = request.form['akun_kredit']
            nom = request.form['nominal']
            
            if ad == ak:
                flash('ERROR: Akun Debit dan Kredit tidak boleh sama!', 'danger')
            else:
                cur.execute("INSERT INTO jurnal (tanggal, deskripsi, kode_akun, debit, kredit) VALUES (%s, %s, %s, %s, 0)", (tgl, desc, ad, nom))
                cur.execute("INSERT INTO jurnal (tanggal, deskripsi, kode_akun, debit, kredit) VALUES (%s, %s, %s, 0, %s)", (tgl, desc, ak, nom))
                conn.commit()
                flash('Jurnal berhasil disimpan!', 'success')
        except Exception as e:
            flash(f"Terjadi kesalahan: {e}", 'danger')
        return redirect(url_for('input_jurnal'))
        
    cur.execute("SELECT * FROM coa ORDER BY kode_akun")
    return render_template('jurnal.html', akun_list=cur.fetchall(), today=date.today())

# --- BUKU BESAR ---
@app.route('/bukubesar')
def bukubesar():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    selected = request.args.get('akun')
    transaksi = []
    if selected:
        cur.execute("SELECT * FROM jurnal WHERE kode_akun = %s ORDER BY tanggal", (selected,))
        transaksi = cur.fetchall()
    cur.execute("SELECT * FROM coa")
    akun_list = cur.fetchall()
    conn.close()
    return render_template('bukubesar.html', akun_list=akun_list, transaksi=transaksi, selected=selected)

# --- LAPORAN KEUANGAN ---
@app.route('/laporan')
def laporan():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    # 1. Laba Rugi
    cur.execute("SELECT SUM(kredit-debit) as v FROM jurnal j JOIN coa c ON j.kode_akun=c.kode_akun WHERE c.kategori='Pendapatan'")
    pdpt = cur.fetchone()['v'] or 0
    cur.execute("SELECT SUM(debit-kredit) as v FROM jurnal j JOIN coa c ON j.kode_akun=c.kode_akun WHERE c.kategori='Beban'")
    beban = cur.fetchone()['v'] or 0
    laba = pdpt - beban
    
    # 2. Neraca
    cur.execute("SELECT c.nama_akun, SUM(debit-kredit) as val FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun WHERE c.kategori='Aset' GROUP BY c.nama_akun HAVING val!=0")
    aset = cur.fetchall()
    t_aset = sum(x['val'] for x in aset)
    
    cur.execute("SELECT c.nama_akun, SUM(kredit-debit) as val FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun WHERE c.kategori='Liabilitas' GROUP BY c.nama_akun HAVING val!=0")
    liabilitas = cur.fetchall()
    
    cur.execute("SELECT c.nama_akun, SUM(kredit-debit) as val FROM coa c JOIN jurnal j ON c.kode_akun=j.kode_akun WHERE c.kategori='Ekuitas' GROUP BY c.nama_akun HAVING val!=0")
    ekuitas = cur.fetchall()
    
    # 3. Arus Kas
    cur.execute("SELECT tanggal, deskripsi, (debit-kredit) as aliran FROM jurnal WHERE kode_akun='1100' ORDER BY tanggal")
    arus_kas = cur.fetchall()
    kas_akhir = sum(x['aliran'] for x in arus_kas)
    
    conn.close()
    return render_template('laporan.html', pdpt=pdpt, beban=beban, laba=laba, aset=aset, t_aset=t_aset, liabilitas=liabilitas, ekuitas=ekuitas, arus_kas=arus_kas, kas_akhir=kas_akhir)

if __name__ == '__main__':
    app.run(debug=True)