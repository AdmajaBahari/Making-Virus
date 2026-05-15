import os
import sqlite3
from flask import Flask, redirect, request, session, render_template

app = Flask(__name__)
app.secret_key = 'sqlinjection'
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database.db')


def connect_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user(
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    NOT NULL UNIQUE,
                password TEXT    NOT NULL
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS time_line(
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL,
                content  TEXT    NOT NULL,
                FOREIGN KEY(user_id) REFERENCES user(id)
            )
        ''')
        conn.commit()


def init_data():
    with connect_db() as conn:
        cur = conn.cursor()
        cur.executemany(
            'INSERT OR IGNORE INTO user(username, password) VALUES (?,?)',
            [('alice', 'alicepw'), ('bob', 'bobpw'), ('admin', 'admin')]
        )
        cur.executemany(
            'INSERT OR IGNORE INTO time_line(user_id, content) VALUES (?,?)',
            [(1, 'Hello world'), (2, 'Hi there')]
        )
        conn.commit()


def authenticate(username, password):
    with connect_db() as conn:
        cur = conn.cursor()
        query = ("SELECT id, username FROM `user` WHERE username='%s' AND password='%s'"
                 % (username, password))
        cur.execute(query)
        row = cur.fetchone()
        return dict(row) if row else None


def create_time_line(uid, content):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute('INSERT INTO time_line(user_id, content) VALUES (?,?)', (uid, content))
        conn.commit()


def get_time_lines():
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT id, user_id, content FROM time_line ORDER BY id DESC')
        return [dict(r) for r in cur.fetchall()]


def delete_time_line(uid, tid):
    with connect_db() as conn:
        cur = conn.cursor()
        query = f"DELETE FROM time_line WHERE user_id={uid} AND id={tid}"
        cur.execute(query)
        conn.commit()


@app.route('/search')
def search():
    keyword = request.args.get('keyword', '')
    conn = connect_db()
    cur = conn.cursor()
    query = f"SELECT id, user_id, content FROM time_line WHERE content LIKE '%{keyword}%'"
    cur.execute(query)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {'query_used': query, 'results': rows}


@app.route('/init')
def init_page():
    create_tables()
    init_data()
    return redirect('/')


@app.route('/')
def index():
    if 'uid' in session:
        tl = get_time_lines()
        return render_template('index.html', user=session['username'], tl=tl)
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = authenticate(request.form['username'], request.form['password'])
        if user:
            session['uid'] = user['id']
            session['username'] = user['username']
            return redirect('/')
        error = 'Invalid username or password.'
    return render_template('login.html', error=error)


@app.route('/create', methods=['POST'])
def create():
    if 'uid' in session:
        create_time_line(session['uid'], request.form['content'])
    return redirect('/')


@app.route('/delete/<int:tid>')
def delete(tid):
    if 'uid' in session:
        delete_time_line(session['uid'], tid)
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    create_tables()
    init_data()
    app.run(debug=True)