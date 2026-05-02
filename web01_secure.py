import os
import sqlite3
import secrets  # FIX 4: secret key yang aman

from flask import Flask, redirect, request, session
from jinja2 import Template
from markupsafe import escape  # FIX 5: XSS prevention

app = Flask(__name__)

# FIX 4: Jangan hardcode secret key — gunakan secrets.token_hex
# Di production: app.secret_key = os.environ.get('SECRET_KEY')
app.secret_key = secrets.token_hex(32)

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database.db')


def connect_db():
    return sqlite3.connect(DATABASE_PATH)


def create_tables():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute('''
            CREATE TABLE IF NOT EXISTS user(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(32),
            password VARCHAR(64)
            )''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS time_line(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        FOREIGN KEY (`user_id`) REFERENCES `user`(`id`)
        )''')
    conn.commit()
    conn.close()


def init_data():
    # CATATAN: Di production, password harus di-hash dengan bcrypt/werkzeug
    # Contoh: from werkzeug.security import generate_password_hash
    #         password_hash = generate_password_hash('123456')
    users = [
        ('user1', '123456'),
        ('user2', '123456')
    ]
    lines = [
        (1, 'Hello'),
        (1, 'World'),
        (2, 'Im 2'),
        (2, 'Hello 2')
    ]
    conn = connect_db()
    cur = conn.cursor()
    cur.executemany('INSERT INTO `user` VALUES(NULL,?,?)', users)
    cur.executemany('INSERT INTO `time_line` VALUES(NULL,?,?)', lines)
    conn.commit()
    conn.close()


def init():
    create_tables()
    init_data()


# FIX 1: MENCEGAH TAUTOLOGY ATTACK
# SEBELUM (RENTAN):
#   cur.execute(
#       "SELECT id, username FROM user WHERE username='%s' AND password='%s'"
#       % (username, password)
#   )
#   → Payload: username = "user1' OR '1'='1"
#   → SQL: WHERE username='user1' OR '1'='1' AND password='...'
#   → Selalu TRUE, login berhasil tanpa password!
#
# SESUDAH (AMAN): Parameterized Query dengan placeholder ?
#   Driver SQLite yang mengurus escaping secara otomatis.
#   Input pernah ada tanda kutip, OR, --, dsb. diperlakukan sebagai string literal.
def get_user_from_username_and_password(username, password):
    conn = connect_db()
    cur = conn.cursor()

    # AMAN: Parameterized query — ? adalah placeholder, bukan substitusi string
    cur.execute(
        'SELECT id, username FROM `user` WHERE username=? AND password=?',
        (username, password)  # driver yang mengurus escaping
    )
    # Payload "user1' OR '1'='1" sekarang dicari PERSIS sebagai username,
    # bukan sebagai bagian dari struktur SQL

    row = cur.fetchone()
    conn.commit()
    conn.close()
    return {'id': row[0], 'username': row[1]} if row is not None else None


def get_user_from_id(uid):
    conn = connect_db()
    cur = conn.cursor()
    # AMAN: gunakan parameterized query + pastikan uid adalah integer
    cur.execute('SELECT id, username FROM `user` WHERE id=?', (int(uid),))
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return {'id': row[0], 'username': row[1]} if row else None


# FIX 2: MENCEGAH PIGGYBACK ATTACK
# SEBELUM (RENTAN):
#   cur.executescript(
#       "INSERT INTO time_line VALUES (NULL, %d, '%s')" % (uid, content)
#   )
#   → executescript() mengizinkan BEBERAPA statement SQL sekaligus (dipisah ;)
#   → Payload: content = "x'); DELETE FROM time_line WHERE (content='"
#   → SQL: INSERT ... VALUES (NULL,1,'x'); DELETE FROM time_line WHERE (content='')
#   → Dua perintah dieksekusi: INSERT + DELETE → seluruh data hilang!
#
# SESUDAH (AMAN):
#   1. Ganti executescript() → execute() (hanya satu statement)
#   2. Gunakan parameterized query
def create_time_line(uid, content):
    conn = connect_db()
    cur = conn.cursor()

    # AMAN: execute() (bukan executescript) + parameterized query
    # execute() hanya menjalankan SATU statement — piggyback ; tidak bisa
    cur.execute(
        'INSERT INTO `time_line` VALUES (NULL, ?, ?)',
        (int(uid), content)  # content berbahaya jadi string literal biasa
    )

    conn.commit()
    conn.close()


def get_time_lines():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, content FROM `time_line` ORDER BY id DESC')
    rows = cur.fetchall()
    conn.commit()
    conn.close()
    return map(lambda row: {'id': row[0], 'user_id': row[1], 'content': row[2]}, rows)


# FIX 3: DELETE — validasi tipe data integer untuk tid
# SEBELUM (RENTAN):
#   cur.execute('DELETE FROM time_line WHERE user_id=%s AND id=%s' % (uid, tid))
#   → String format langsung ke SQL
#
# SESUDAH (AMAN): Parameterized query + validasi int
def user_delete_time_line_of_id(uid, tid):
    try:
        uid = int(uid)  # validasi: pastikan integer
        tid = int(tid)  # validasi: pastikan integer
    except (ValueError, TypeError):
        return  # tolak jika bukan angka

    conn = connect_db()
    cur = conn.cursor()
    # AMAN: Parameterized query
    cur.execute(
        'DELETE FROM `time_line` WHERE user_id=? AND id=?',
        (uid, tid)
    )
    conn.commit()
    conn.close()


def render_login_page(error=False):
    return '''
<form method="POST" style="margin: 60px auto; width: 200px;">
    <p><input name="username" type="text" placeholder="Username" /></p>
    <p><input name="password" type="password" placeholder="Password" /></p>
    ''' + ('<p style="color:red;font-size:13px;">Username/password salah.</p>' if error else '') + '''
    <p><input value="Login" type="submit" /></p>
</form>
    '''


def render_home_page(uid):
    user = get_user_from_id(uid)
    if not user:
        return redirect('/logout')
    time_lines = get_time_lines()

    # Jinja2 auto-escape aktif untuk {{ }} — mencegah XSS
    template = Template('''
<div style="width: 400px; margin: 80px auto;">
    <h4>I am: {{ user['username'] }}</h4>
    <form method="POST" action="/create_time_line">
        Add time line:
        <input type="text" name="content" />
        <input type="submit" value="Submit" />
    </form>
    <ul style="border-top: 1px solid #ccc;">
        {% for line in time_lines %}
        <li style="border-top: 1px solid #efefef;">
            <p>{{ line['content'] }}</p>
            {% if line['user_id'] == user['id'] %}
            <a href="/delete/time_line/{{ line['id'] }}">Delete</a>
            {% endif %}
        </li>
        {% endfor %}
    </ul>
    <a href="/logout">Logout</a>
</div>
    ''')
    return template.render(user=user, time_lines=time_lines)


@app.route('/init')
def init_page():
    init()
    return redirect('/')


@app.route('/')
def index():
    if 'uid' in session:
        return render_home_page(session['uid'])
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_login_page()
    elif request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # Validasi input kosong
        if not username or not password:
            return render_login_page(error=True)

        user = get_user_from_username_and_password(username, password)
        if user is not None:
            session['uid'] = user['id']
            return redirect('/')
        else:
            return render_login_page(error=True)  # pesan error, bukan redirect


@app.route('/create_time_line', methods=['POST'])
def time_line():
    if 'uid' in session:
        uid = session['uid']
        content = request.form.get('content', '').strip()
        if content:  # jangan simpan konten kosong
            create_time_line(uid, content)
    return redirect('/')


@app.route('/delete/time_line/<tid>')
def delete_time_line(tid):
    if 'uid' in session:
        try:
            tid = int(tid)  # FIX: validasi tid adalah integer
        except ValueError:
            return redirect('/')  # abaikan jika bukan angka
        user_delete_time_line_of_id(session['uid'], tid)
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()  # hapus semua session, bukan hanya 'uid'
    return redirect('/login')


if __name__ == '__main__':
    # debug=False di production!
    app.run(debug=False)