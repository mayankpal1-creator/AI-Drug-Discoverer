import os, sqlite3, json
from flask import Flask, render_template, request, redirect, session, g, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import ensure_models, generate_candidates

app = Flask(__name__)
app.secret_key = 'replace-with-a-secure-key'
DB_PATH = os.path.join('instance', 'app.db')

def init_db_and_admin():
    os.makedirs('instance', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, smiles1 TEXT, smiles2 TEXT, result_smiles TEXT, properties TEXT, adme REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    # create default admin if not exists
    cur.execute('SELECT id FROM users WHERE email=?', ('admin@example.com',))
    if not cur.fetchone():
        cur.execute('INSERT INTO users (email, password) VALUES (?,?)', ('admin@example.com', generate_password_hash('admin123')))
    conn.commit()
    conn.close()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        os.makedirs('instance', exist_ok=True)
        db = g._database = sqlite3.connect(DB_PATH)
    return db

@app.teardown_appcontext
def close_conn(exc):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/home')
    return redirect('/login')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        pwd = request.form['password']
        db = get_db()
        try:
            db.execute('INSERT INTO users (email, password) VALUES (?,?)', (email, generate_password_hash(pwd)))
            db.commit()
            return redirect('/login')
        except Exception as e:
            return render_template('signup.html', error='User exists or invalid')
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email = request.form['email'].strip().lower()
        pwd = request.form['password']
        db = get_db()
        cur = db.execute('SELECT id, password FROM users WHERE email=?', (email,))
        row = cur.fetchone()
        if row and check_password_hash(row[1], pwd):
            session['user_id'] = row[0]
            session['email'] = email
            return redirect('/home')
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/home', methods=['GET'])
def home():
    return render_template('home.html')

@app.route('/generate', methods=['POST'])
def generate():
    if 'user_id' not in session:
        return redirect('/login')
    data = request.form
    s1 = data.get('smiles1','').strip()
    s2 = data.get('smiles2','').strip()
    if not s1 or not s2:
        return render_template('home.html', error='Provide two SMILES')
    try:
        ensure_models()
        candidates = generate_candidates(s1, s2, topk=1)
        if not candidates:
            return render_template('home.html', error='No candidates found')
        c = candidates[0]
        props = c['properties']
        adme = c['adme_score']
        db = get_db()
        db.execute('INSERT INTO history (user_id, smiles1, smiles2, result_smiles, properties, adme) VALUES (?,?,?,?,?,?)',
                   (session['user_id'], s1, s2, c['SMILES'], json.dumps(props), float(adme)))
        db.commit()
        return render_template('home.html', result=c)
    except Exception as e:
        return render_template('home.html', error=str(e))

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login')
    db = get_db()
    cur = db.execute('SELECT id, smiles1, smiles2, result_smiles, properties, adme, timestamp FROM history WHERE user_id=? ORDER BY id DESC', (session['user_id'],))
    rows = cur.fetchall()
    hist = []
    for r in rows:
        hist.append({'id':r[0],'smiles1':r[1],'smiles2':r[2],'result':r[3],'properties':json.loads(r[4]),'adme':r[5],'timestamp':r[6]})
    return render_template('history.html', history=hist)

if __name__ == '__main__':
    init_db_and_admin()
    ensure_models()
    app.run(debug=True)
