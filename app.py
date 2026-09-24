from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_store'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Տվյալների բազայի մոդել (Ապրանքներ) ---
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)

with app.app_context():
    db.create_all()

# --- HTML Շաբլոններ (HTML + CSS) ---
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="hy">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Առցանց Մարկետպլեյս</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9; }
        header { background: #1f2937; color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; }
        header a { color: white; text-decoration: none; font-weight: bold; margin-left: 15px; }
        .container { max-width: 1000px; margin: 30px auto; padding: 0 20px; }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }
        .card img { width: 100%; height: 160px; object-fit: cover; border-radius: 5px; }
        .btn { display: inline-block; background: #2563eb; color: white; padding: 8px 15px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; margin-top: 10px; }
        .btn:hover { background: #1d4ed8; }
        .btn-add { background: #16a34a; }
        .btn-add:hover { background: #15803d; }
        .btn-danger { background: #dc2626; }
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
        <h1><a href="/">Online Store</a></h1>
        <nav>
            <a href="/">Գլխավոր</a>
            <a href="/add_product" class="btn btn-add" style="margin-top:0;">+ Վաճառել ապրանք</a>
            <a href="/cart">Զամբյուղ ({{ cart_count }})</a>
        </nav>
    </header>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

HOME_TEMPLATE = HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
<h2>Ապրանքների Ցանկ</h2>
{% if products %}
<div class="products-grid">
    {% for product in products %}
    <div class="card">
        <img src="{{ product.image_url }}" alt="{{ product.name }}">
        <h3>{{ product.name }}</h3>
        <p><b>{{ product.price }} ֏</b></p>
        <a href="/add_to_cart/{{ product.id }}" class="btn">Ավելացնել զամբյուղ</a>
    </div>
    {% endfor %}
</div>
{% else %}
<p>Դեռևս ապրանքներ չկան: Եղիր առաջինը և ավելացրու ապրանք «+ Վաճառել ապրանք» կոճակով:</p>
{% endif %}
""")

ADD_PRODUCT_TEMPLATE = HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
<h2>Ավելացնել Նոր Ապրանք Վաճառքի Համար</h2>
<form action="/add_product" method="POST">
    <div class="form-group">
        <label>Ապրանքի անվանումը:</label>
        <input type="text" name="name" required placeholder="Օրինակ՝ iPhone 13 Pro">
    </div>
    <div class="form-group">
        <label>Գինը (֏):</label>
        <input type="number" step="0.01" name="price" required placeholder="Օրինակ՝ 280000">
    </div>
    <div class="form-group">
        <label>Նկարի հղումը (URL):</label>
        <input type="url" name="image_url" required placeholder="https://example.com/image.jpg">
    </div>
    <button type="submit" class="btn btn-add" style="width: 100%;">Հրապարակել Ապրանքը</button>
</form>
""")

CART_TEMPLATE = HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
<h2>Քո Զամբյուղը</h2>
{% if items %}
<table>
    <tr>
        <th>Ապրանք</th>
        <th>Գին</th>
        <th>Քանակ</th>
        <th>Ընդամենը</th>
        <th>Գործողություն</th>
    </tr>
    {% for item in items %}
    <tr>
        <td>{{ item.name }}</td>
        <td>{{ item.price }} ֏</td>
        <td>{{ item.quantity }}</td>
        <td>{{ item.price * item.quantity }} ֏</td>
        <td><a href="/remove_from_cart/{{ item.id }}" class="btn btn-danger">Ջնջել</a></td>
    </tr>
    {% endfor %}
</table>
<h3>Ընդհանուր Գումար: {{ total }} ֏</h3>
<a href="/checkout" class="btn" style="background: #16a34a;">Ձևակերպել Պատվերը</a>
{% else %}
<p>Զամբյուղը դատարկ է:</p>
<a href="/" class="btn">Վերադառնալ Խանութ</a>
{% endif %}
""")

CHECKOUT_TEMPLATE = HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
<h2>Պատվերը Հաջողությամբ Ձևակերպվեց:</h2>
<p>Շնորհակալություն գնումների համար։</p>
<a href="/" class="btn">Վերադառնալ Գլխավոր Էջ</a>
""")

# --- Երթուղիներ (Routes) ---

@app.route('/')
def home():
    products = Product.query.all()
    cart = session.get('cart', {})
    cart_count = sum(cart.values())
    return render_template_string(HOME_TEMPLATE, products=products, cart_count=cart_count)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        image_url = request.form.get('image_url')
        
        new_product = Product(name=name, price=price, image_url=image_url)
        db.session.add(new_product)
        db.session.commit()
        
        return redirect(url_for('home'))
        
    cart = session.get('cart', {})
    cart_count = sum(cart.values())
    return render_template_string(ADD_PRODUCT_TEMPLATE, cart_count=cart_count)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    cart = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    return redirect(url_for('home'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    cart_count = sum(cart.values())
    items = []
    total = 0
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            items.append({
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'quantity': quantity
            })
            total += product.price * quantity
    return render_template_string(CART_TEMPLATE, items=items, total=total, cart_count=cart_count)

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
        session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/checkout')
def checkout():
    session['cart'] = {}
    return render_template_string(CHECKOUT_TEMPLATE, cart_count=0)

if __name__ == '__main__':
    app.run(debug=True)
    