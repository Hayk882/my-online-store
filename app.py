from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_store_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Flask-Login Կարգավորումներ ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Տվյալների Բազայի Մոդելներ ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    address = db.Column(db.String(200), nullable=False, default="Երևան")
    seller_phone = db.Column(db.String(30), nullable=False, default="")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])
    product = db.relationship('Product')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# --- Փոխարժեքների Քեշավորում ---
RATES_CACHE = {
    'rates': {'AMD': 1.0, 'USD': 0.0026, 'RUB': 0.24},
    'last_update': 0
}

def get_exchange_rates():
    now = time.time()
    if now - RATES_CACHE['last_update'] > 3600:
        try:
            res = requests.get('https://open.er-api.com/v6/latest/AMD', timeout=3)
            if res.status_code == 200:
                data = res.json()
                if data.get('result') == 'success' and 'rates' in data:
                    RATES_CACHE['rates']['USD'] = data['rates'].get('USD', 0.0026)
                    RATES_CACHE['rates']['RUB'] = data['rates'].get('RUB', 0.24)
                    RATES_CACHE['last_update'] = now
        except Exception as e:
            print("Փոխարժեքի API սխալ:", e)
    return RATES_CACHE['rates']

CURRENCY_CONFIG = {
    'hy': {'code': 'AMD', 'symbol': '֏', 'rate_key': 'AMD'},
    'ru': {'code': 'RUB', 'symbol': '₽', 'rate_key': 'RUB'},
    'en': {'code': 'USD', 'symbol': '$', 'rate_key': 'USD'}
}

def get_current_lang():
    return session.get('lang', 'hy')

def format_price(price_in_amd):
    try:
        price_in_amd = float(price_in_amd)
    except (ValueError, TypeError):
        return "0 ֏"

    lang = get_current_lang()
    config = CURRENCY_CONFIG.get(lang, CURRENCY_CONFIG['hy'])
    rates = get_exchange_rates()
    rate = rates.get(config['rate_key'], 1.0)
    converted_price = price_in_amd * rate
    
    if config['code'] == 'AMD':
        return f"{int(converted_price):,} {config['symbol']}"
    elif config['code'] == 'RUB':
        return f"{converted_price:.2f} {config['symbol']}"
    else:
        return f"{config['symbol']}{converted_price:.2f}"

app.jinja_env.filters['format_price'] = format_price

# --- HTML Շաբլոն ---
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="hy">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>One-Shop</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9; }
        header { background: #1f2937; color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        header a { color: white; text-decoration: none; font-weight: bold; margin-left: 12px; }
        .lang-picker a { color: #f3f4f6; margin-left: 5px; text-decoration: none; }
        .lang-picker a.active { font-weight: bold; text-decoration: underline; color: #3b82f6; }
        .container { max-width: 1000px; margin: 30px auto; padding: 0 20px; }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; }
        .card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }
        .card img { width: 100%; height: 160px; object-fit: cover; border-radius: 5px; }
        .btn { display: inline-block; background: #2563eb; color: white; padding: 8px 12px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; margin-top: 5px; font-size: 14px; }
        .btn:hover { background: #1d4ed8; }
        .btn-success { background: #16a34a; }
        .btn-danger { background: #dc2626; }
        .btn-info { background: #0284c7; }
        .action-btns { display: flex; flex-wrap: wrap; gap: 5px; justify-content: center; margin-top: 10px; }
        form { background: white; padding: 25px; border-radius: 8px; max-width: 450px; margin: 0 auto; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .form-group { margin-bottom: 15px; text-align: left; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input, .form-group textarea { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        .chat-box { background: white; padding: 15px; border-radius: 8px; height: 300px; overflow-y: scroll; border: 1px solid #ccc; margin-bottom: 15px; }
        .message { margin-bottom: 10px; padding: 8px; border-radius: 5px; }
        .my-msg { background: #dcf8c6; text-align: right; }
        .other-msg { background: #e2e8f0; text-align: left; }
    </style>
</head>
<body>
    <header>
        <h1><a href="/">One-Shop</a></h1>
        <nav>
            <span class="lang-picker">
                <a href="/change_lang/hy" class="{{ 'active' if current_lang=='hy' else '' }}">AM (֏)</a> | 
                <a href="/change_lang/ru" class="{{ 'active' if current_lang=='ru' else '' }}">RU (₽)</a> | 
                <a href="/change_lang/en" class="{{ 'active' if current_lang=='en' else '' }}">EN ($)</a>
            </span>
            {% if current_user.is_authenticated %}
                <span>👤 {{ current_user.username }}</span>
                <a href="/add_product">+ Ապրանք</a>
                <a href="/messages">💬 Նամակներ</a>
                <a href="/logout">Դուրս գալ</a>
            {% else %}
                <a href="/login">Մուտք</a>
                <a href="/register">Գրանցվել</a>
            {% endif %}
            <a href="/cart">🛒 ({{ cart_count }})</a>
        </nav>
    </header>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# --- Route-եր ---
@app.route('/change_lang/<lang_code>')
def change_lang(lang_code):
    if lang_code in CURRENCY_CONFIG:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    products = Product.query.all()
    cart = session.get('cart', {})
    cart_count = sum(cart.values())
    return render_template_string(
        HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
        <div class="products-grid">
            {% for p in products %}
            <div class="card">
                <img src="{{ p.image_url }}" alt="{{ p.name }}">
                <h3>{{ p.name }}</h3>
                <p><strong>Գին:</strong> {{ p.price | format_price }}</p>
                <p>📍 <strong>Հասցե:</strong> {{ p.address }}</p>
                <div class="action-btns">
                    {% if p.seller_phone %}
                        <a href="tel:{{ p.seller_phone }}" class="btn btn-success">📞 Զանգել</a>
                    {% endif %}
                    {% if current_user.is_authenticated and p.user_id and p.user_id != current_user.id %}
                        <a href="/chat/{{ p.user_id }}?product_id={{ p.id }}" class="btn btn-info">💬 Գրել</a>
                    {% endif %}
                    <a href="/add_to_cart/{{ p.id }}" class="btn">🛒 Զամբյուղ</a>
                </div>
            </div>
            {% endfor %}
        </div>
        """),
        products=products, cart_count=cart_count, current_lang=get_current_lang()
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        phone = request.form['phone']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            return "Այս օգտանունը արդեն զբաղված է:"

        user = User(username=username, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))

    return render_template_string(
        HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
        <form method="POST">
            <h2>Գրանցում</h2>
            <div class="form-group">
                <label>Օգտանուն (Username)</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Հեռախոսահամար</label>
                <input type="text" name="phone" placeholder="+374 99 123456" required>
            </div>
            <div class="form-group">
                <label>Գաղտնաբառ</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn">Գրանցվել</button>
        </form>
        """),
        cart_count=0, current_lang=get_current_lang()
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        return "Սխալ օգտանուն կամ գաղտնաբառ:"

    return render_template_string(
        HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
        <form method="POST">
            <h2>Մուտք</h2>
            <div class="form-group">
                <label>Օգտանուն</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Գաղտնաբառ</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn">Մուտք գործել</button>
        </form>
        """),
        cart_count=0, current_lang=get_current_lang()
    )

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        image_url = request.form['image_url']
        address = request.form['address']
        seller_phone = current_user.phone

        product = Product(
            name=name, price=price, image_url=image_url,
            address=address, seller_phone=seller_phone, user_id=current_user.id
        )
        db.session.add(product)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template_string(
        HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
        <form method="POST">
            <h2>Ավելացնել Ապրանք</h2>
            <div class="form-group">
                <label>Անվանում</label>
                <input type="text" name="name" required>
            </div>
            <div class="form-group">
                <label>Գին (AMD)</label>
                <input type="number" step="1" name="price" required>
            </div>
            <div class="form-group">
                <label>Նկարի հղում (URL)</label>
                <input type="url" name="image_url" required>
            </div>
            <div class="form-group">
                <label>Որտեղի՞ց վերցնել ապրանքը (Հասցե)</label>
                <input type="text" name="address" placeholder="օր․ Երևան, Կենտրոն, Մաշտոցի 10" required>
            </div>
            <button type="submit" class="btn">Ավելացնել</button>
        </form>
        """),
        cart_count=0, current_lang=get_current_lang()
    )

@app.route('/chat/<int:receiver_id>', methods=['GET', 'POST'])
@login_required
def chat(receiver_id):
    receiver = User.query.get_or_404(receiver_id)
    product_id = request.args.get('product_id')

    if request.method == 'POST':
        content = request.form['content']
        if content.strip():
            msg = Message(
                sender_id=current_user.id,
                receiver_id=receiver_id,
                product_id=product_id,
                content=content
            )
            db.session.add(msg)
            db.session.commit()
            return redirect(url_for('chat', receiver_id=receiver_id, product_id=product_id))

    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == receiver_id)) |
        ((Message.sender_id == receiver_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()

    return render_template_string(
        HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
        <h2>💬 Չաթ: {{ receiver.username }}</h2>
        <p>📱 Հեռախոս: <a href="tel:{{ receiver.phone }}">{{ receiver.phone }}</a></p>
        <div class="chat-box">
            {% for msg in messages %}
                <div class="message {{ 'my-msg' if msg.sender_id == current_user.id else 'other-msg' }}">
                    <strong>{{ msg.sender.username }}:</strong> {{ msg.content }}
                </div>
            {% endfor %}
        </div>
        <form method="POST" style="max-width: 100%;">
            <div class="form-group">
                <input type="text" name="content" placeholder="Գրեք նամակ..." required>
            </div>
            <button type="submit" class="btn btn-success">Ուղարկել</button>
        </form>
        """),
        messages=messages, receiver=receiver, cart_count=0, current_lang=get_current_lang()
    )

@app.route('/messages')
@login_required
def messages():
    sent = Message.query.filter_by(sender_id=current_user.id).all()
    received = Message.query.filter_by(receiver_id=current_user.id).all()
    user_ids = set([m.receiver_id for m in sent] + [m.sender_id for m in received])
    users = User.query.filter(User.id.in_(user_ids)).all()

    return render_template_string(
        HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
        <h2>Իմ նամակագրությունները</h2>
        {% if users %}
            <ul>
            {% for u in users %}
                <li><a href="/chat/{{ u.id }}" class="btn btn-info" style="margin-bottom: 10px;">💬 {{ u.username }} ({{ u.phone }})</a></li>
            {% endfor %}
            </ul>
        {% else %}
            <p>Դեռ ոչ մի նամակ չունեք:</p>
        {% endif %}
        """),
        users=users, cart_count=0, current_lang=get_current_lang()
    )

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    cart = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    return redirect(url_for('index'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    items = []
    total = 0
    for p_id, qty in cart.items():
        product = Product.query.get(int(p_id))
        if product:
            for _ in range(qty):
                items.append(product)
            total += product.price * qty
    return render_template_string(
        HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
        <h2>🛒 Զամբյուղ</h2>
        {% if items %}
            <ul>
            {% for item in items %}
                <li>{{ item.name }} - {{ item.price | format_price }} (📍 {{ item.address }})</li>
            {% endfor %}
            </ul>
            <h3>Ընդհանուր: {{ total | format_price }}</h3>
        {% else %}
            <p>Զամբյուղը դատարկ է:</p>
        {% endif %}
        """),
        items=items, total=total, cart_count=sum(cart.values()), current_lang=get_current_lang()
    )

if __name__ == '__main__':
    app.run(debug=True)
