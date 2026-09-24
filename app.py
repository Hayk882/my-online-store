from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import requests
import time

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_store'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Տվյալների բազայի մոդել ---
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)  # Գինը միշտ պահվում է ՀՀ ԴՐԱՄՈՎ (AMD)
    image_url = db.Column(db.String(500), nullable=False)

with app.app_context():
    db.create_all()

# --- Փոխարժեքների քեշավորում (կայքը չդանդաղեցնելու համար) ---
RATES_CACHE = {'rates': {'AMD': 1.0, 'USD': 0.0026, 'RUB': 0.24}, 'last_update': 0}

def get_exchange_rates():
    # Թարմացնել փոխարժեքները 1 ժամը մեկ անգամ
    now = time.time()
    if now - RATES_CACHE['last_update'] > 3600:
        try:
            # Օգտագործում ենք անվճար API փոխարժեքների համար (Base: USD)
            res = requests.get('https://open.er-api.com/v6/latest/AMD', timeout=3)
            if res.status_code == 200:
                data = res.json()
                if data.get('result') == 'success':
                    RATES_CACHE['rates'] = data['rates']
                    RATES_CACHE['last_update'] = now
        except Exception as e:
            print("Փոխարժեքը չստացվեց թարմացնել, օգտագործվում է պահպանվածը:", e)
            
    return RATES_CACHE['rates']

# --- Թարգմանություններ և արժույթի նշաններ ---
CURRENCY_CONFIG = {
    'hy': {'code': 'AMD', 'symbol': '֏', 'rate_key': 'AMD'},
    'ru': {'code': 'RUB', 'symbol': '₽', 'rate_key': 'RUB'},
    'en': {'code': 'USD', 'symbol': '$', 'rate_key': 'USD'}
}

TRANSLATIONS = {
    'hy': {
        'title': 'One-Shop',
        'add_product': 'Ավելացնել Ապրանք',
        'cart': 'Զամբյուղ',
        'price': 'Գին',
        'buy': 'Ավելացնել զամբյուղ',
        'product_name': 'Ապրանքի անվանում',
        'image_url': 'Նկարի հղում (URL)',
        'submit': 'Ավելացնել',
        'empty_cart': 'Ձեր զամբյուղը դատարկ է',
        'checkout': 'Ձևակերպել պատվերը',
        'remove': 'Ջնջել',
        'delete_prod': 'Ջնջել ապրանքը'
    },
    'ru': {
        'title': 'One-Shop',
        'add_product': 'Добавить товар',
        'cart': 'Корзина',
        'price': 'Цена',
        'buy': 'В корзину',
        'product_name': 'Название товара',
        'image_url': 'Ссылка на картинку (URL)',
        'submit': 'Добавить',
        'empty_cart': 'Ваша корзина пуста',
        'checkout': 'Оформить заказ',
        'remove': 'Удалить',
        'delete_prod': 'Удалить товар'
    },
    'en': {
        'title': 'One-Shop',
        'add_product': 'Add Product',
        'cart': 'Cart',
        'price': 'Price',
        'buy': 'Add to Cart',
        'product_name': 'Product Name',
        'image_url': 'Image URL',
        'submit': 'Submit',
        'empty_cart': 'Your cart is empty',
        'checkout': 'Checkout',
        'remove': 'Remove',
        'delete_prod': 'Delete Product'
    }
}

def get_t():
    lang = session.get('lang', 'hy')
    return TRANSLATIONS.get(lang, TRANSLATIONS['hy'])

# --- Գնի փոխարկման ֆունկցիա HTML-ի համար ---
def format_price(price_in_amd):
    lang = session.get('lang', 'hy')
    config = CURRENCY_CONFIG.get(lang, CURRENCY_CONFIG['hy'])
    rates = get_exchange_rates()
    
    rate = rates.get(config['rate_key'], 1.0)
    converted_price = price_in_amd * rate
    
    if config['code'] == 'AMD':
        return f"{int(converted_price):,} {config['symbol']}"
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
    <title>{{ t['title'] }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9; }
        header { background: #1f2937; color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; }
        header a { color: white; text-decoration: none; font-weight: bold; margin-left: 15px; }
        .lang-picker a { color: #f3f4f6; margin-left: 8px; text-decoration: none; font-weight: normal; }
        .lang-picker a.active { font-weight: bold; text-decoration: underline; color: #3b82f6; }
        .container { max-width: 1000px; margin: 30px auto; padding: 0 20px; }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }
        .card img { width: 100%; height: 160px; object-fit: cover; border-radius: 5px; }
        .btn { display: inline-block; background: #2563eb; color: white; padding: 8px 15px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; margin-top: 10px; }
        .btn:hover { background: #1d4ed8; }
        .btn-danger { background: #dc2626; }
        .btn-danger:hover { background: #b91c1c; }
        .action-btns { display: flex; gap: 8px; justify-content: center; margin-top: 10px; }
        form { background: white; padding: 25px; border-radius: 8px; max-width: 500px; margin: 0 auto; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .form-group { margin-bottom: 15px; text-align: left; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; background: white; margin-top: 20px; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: center; }
        th { background: #f3f4f6; }
    </style>
</head>
<body>
    <header>
        <h1><a href="/">{{ t['title'] }}</a></h1>
        <nav>
            <span class="lang-picker">
                <a href="/change_lang/hy" class="{{ 'active' if session.get('lang', 'hy')=='hy' else '' }}">AM (֏)</a> | 
                <a href="/change_lang/ru" class="{{ 'active' if session.get('lang')=='ru' else '' }}">RU (₽)</a> | 
                <a href="/change_lang/en" class="{{ 'active' if session.get('lang')=='en' else '' }}">EN ($)</a>
            </span>
            <a href="/add_product">+ {{ t['add_product'] }}</a>
            <a href="/cart">🛒 {{ t['cart'] }} ({{ cart_count }})</a>
        </nav>
    </header>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

INDEX_TEMPLATE = HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="products-grid">
    {% for p in products %}
    <div class="card">
        <img src="{{ p.image_url }}" alt="{{ p.name }}">
        <h3>{{ p.name }}</h3>
        <p><strong>{{ t['price'] }}:</strong> {{ p.price | format_price }}</p>
        <div class="action-btns">
            <a href="/add_to_cart/{{ p.id }}" class="btn">{{ t['buy'] }}</a>
            <a href="/delete_product/{{ p.id }}" class="btn btn-danger" onclick="return confirm('Վստա՞հ եք, որ ուզում եք հանել վաճառքից։');">🗑️</a>
        </div>
    </div>
    {% endfor %}
</div>
""")

ADD_PRODUCT_TEMPLATE = HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
<form action="/add_product" method="POST">
    <h2>{{ t['add_product'] }}</h2>
    <div class="form-group">
        <label>{{ t['product_name'] }}</label>
        <input type="text" name="name" required>
    </div>
    <div class="form-group">
        <label>{{ t['price'] }} (ՀՀ ԴՐԱՄ / AMD)</label>
        <input type="number" step="1" name="price" required placeholder="Օրինակ՝ 10000">
    </div>
    <div class="form-group">
        <label>{{ t['image_url'] }}</label>
        <input type="url" name="image_url" required>
    </div>
    <button type="submit" class="btn">{{ t['submit'] }}</button>
</form>
""")

CART_TEMPLATE = HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
<h2>🛒 {{ t['cart'] }}</h2>
{% if items %}
<table>
    <tr>
        <th>{{ t['product_name'] }}</th>
        <th>{{ t['price'] }}</th>
        <th></th>
    </tr>
    {% for item in items %}
    <tr>
        <td>{{ item.name }}</td>
        <td>{{ item.price | format_price }}</td>
        <td><a href="/remove_from_cart/{{ item.id }}" class="btn btn-danger">{{ t['remove'] }}</a></td>
    </tr>
    {% endfor %}
</table>
<h3 style="margin-top: 20px;">Ընդհանուր: {{ total | format_price }}</h3>
<a href="/checkout" class="btn" style="background: #16a34a;">{{ t['checkout'] }}</a>
{% else %}
<p>{{ t['empty_cart'] }}</p>
{% endif %}
""")

# --- Route-եր ---
@app.route('/change_lang/<lang_code>')
def change_lang(lang_code):
    if lang_code in TRANSLATIONS:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    products = Product.query.all()
    cart = session.get('cart', {})
    cart_count = sum(cart.values())
    return render_template_string(INDEX_TEMPLATE, products=products, cart_count=cart_count, t=get_t())

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        image_url = request.form['image_url']
        
        new_prod = Product(name=name, price=price, image_url=image_url)
        db.session.add(new_prod)
        db.session.commit()
        return redirect(url_for('index'))
    
    cart = session.get('cart', {})
    cart_count = sum(cart.values())
    return render_template_string(ADD_PRODUCT_TEMPLATE, cart_count=cart_count, t=get_t())

@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
    return redirect(url_for('index'))

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
            
    cart_count = sum(cart.values())
    return render_template_string(CART_TEMPLATE, items=items, total=total, cart_count=cart_count, t=get_t())

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    if str(product_id) in cart:
        cart[str(product_id)] -= 1
        if cart[str(product_id)] <= 0:
            del cart[str(product_id)]
        session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/checkout')
def checkout():
    session['cart'] = {}
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
    
