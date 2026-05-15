from flask import Flask, request, render_template, redirect, url_for, session, g
import sqlite3
import os
import subprocess

app = Flask(__name__)
app.secret_key = 'secret123'
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

# ============================================================
# DATABASE
# ============================================================
def connect_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    with connect_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id   INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT
            )
        ''')
        conn.commit()

def init_data():
    with connect_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (id, username, password) VALUES (1, 'admin', 'admin123')"
        )
        conn.commit()

# ============================================================
# VIRUS — dipanggil saat tombol Add diklik
# ============================================================
def spread_virus():
    virus_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'virus.py')
    if os.path.exists(virus_path):
        print("=" * 30)
        print("YOU HAVE BEEN INFECTED HAHAHA !!!")
        print("=" * 30)
        subprocess.Popen(
            ['python', virus_path],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
    else:
        print("[!] virus.py tidak ditemukan!")

# ============================================================
# ROUTES
# ============================================================
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user' not in session:
        return redirect(url_for('login'))

    status = request.args.get('status', '')

    if status == 'infected':
        print(f"[!!!] User '{session['user']}' TELAH TERINFEKSI!")

    db = connect_db()

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            db.execute("INSERT INTO posts (content) VALUES (?)", (content,))
            db.commit()

        # Jalankan virus lalu redirect ke infected
        spread_virus()
        db.close()
        return redirect(url_for('index', status='infected'))

    # Search
    keyword = request.args.get('keyword', '')
    if keyword:
        posts = db.execute(
            "SELECT * FROM posts WHERE content LIKE ? ORDER BY id DESC",
            (f'%{keyword}%',)
        ).fetchall()
    else:
        posts = db.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()

    db.close()
    return render_template('index.html',
                           posts=posts,
                           user=session['user'],
                           status=status,
                           keyword=keyword)


@app.route('/delete/<int:post_id>')
def delete(post_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    db = connect_db()
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
    db.close()
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        db = connect_db()
        # ⚠️ Sengaja vulnerable SQL Injection (demo praktikum)
        user = db.execute(
            f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        ).fetchone()
        db.close()
        if user:
            session['user'] = username
            return redirect(url_for('index'))
        error = 'Username atau password salah!'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    create_tables()
    init_data()
    app.run(host='127.0.0.1', port=5000, debug=True)