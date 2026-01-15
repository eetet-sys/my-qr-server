import sqlite3
from flask import Flask, redirect, request, render_template_string, send_file
import qrcode
import io
import uuid

app = Flask(__name__)
DB_FILE = 'qrcode.db'

# 0. 데이터베이스 초기화 함수 (앱 시작 시 자동 실행)
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 테이블이 없으면 생성 (id: 단축ID, url: 이동할주소)
    c.execute('''CREATE TABLE IF NOT EXISTS urls 
                 (id TEXT PRIMARY KEY, url TEXT)''')
    conn.commit()
    conn.close()

# 앱 실행 시 DB 준비
init_db()

# 1. 관리자 페이지
@app.route('/', methods=['GET', 'POST'])
def admin_panel():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if request.method == 'POST':
        original_url = request.form.get('url')
        if original_url:
            if not original_url.startswith(('http://', 'https://')):
                original_url = 'https://' + original_url
            
            short_id = str(uuid.uuid4())[:6]
            # DB에 저장 (INSERT)
            c.execute("INSERT INTO urls (id, url) VALUES (?, ?)", (short_id, original_url))
            conn.commit()
            
    # 저장된 목록 가져오기 (SELECT)
    c.execute("SELECT id, url FROM urls")
    rows = c.fetchall() # [(id1, url1), (id2, url2)...] 형태
    conn.close()

    html = """
    <!doctype html>
    <html>
    <head>
        <title>영구 QR 관리자 (DB버전)</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 20px auto; padding: 20px; }
            .card { border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 8px; }
            input[type=text] { width: 300px; padding: 5px; }
            button { padding: 5px 10px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>💾 영구 QR 관리자 (SQLite)</h1>
        <div class="card" style="background: #f0f8ff;">
            <h3>새로운 QR 만들기</h3>
            <form method="POST">
                <input type="text" name="url" placeholder="연결할 주소" required>
                <button type="submit">생성</button>
            </form>
        </div>
        <hr>
        <h3>생성된 목록</h3>
        {% for row in rows %}
        <div class="card">
            <p><strong>ID:</strong> {{ row[0] }}</p>
            <p><strong>URL:</strong> <a href="{{ row[1] }}" target="_blank">{{ row[1] }}</a></p>
            <img src="/qr_img/{{ row[0] }}" width="100" style="border:1px solid #ccc"><br><br>
            <form action="/update/{{ row[0] }}" method="POST">
                <input type="text" name="new_url" placeholder="새 주소 입력">
                <button type="submit">수정</button>
            </form>
            <p><small>테스트: <a href="/go/{{ row[0] }}">이동하기</a></small></p>
        </div>
        {% endfor %}
    </body>
    </html>
    """
    return render_template_string(html, rows=rows)

# 2. 주소 수정
@app.route('/update/<short_id>', methods=['POST'])
def update_url(short_id):
    new_url = request.form.get('new_url')
    if new_url:
        if not new_url.startswith(('http://', 'https://')):
            new_url = 'https://' + new_url
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE urls SET url = ? WHERE id = ?", (new_url, short_id))
        conn.commit()
        conn.close()
    return redirect('/')

# 3. 리다이렉트
@app.route('/go/<short_id>')
def redirect_to_url(short_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT url FROM urls WHERE id = ?", (short_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return redirect(row[0], code=302)
    else:
        return "존재하지 않는 QR입니다.", 404

# 4. QR 이미지
@app.route('/qr_img/<short_id>')
def generate_qr_image(short_id):
    # 실제 배포시에는 이 주소를 '내 도메인'으로 변경해야 합니다.
    link = f"http://localhost:5000/go/{short_id}"
    
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True, port=5000)