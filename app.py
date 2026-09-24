from datetime import datetime
from flask import Flask, abort, flash, redirect, render_template_string, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "super-secret-key-change-this"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///oneshop.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# --- DATABASE MODELS ---


class User(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(150), unique=True, nullable=False)
  email = db.Column(db.String(150), unique=True, nullable=False)
  password = db.Column(db.String(150), nullable=False)
  is_admin = db.Column(db.Boolean, default=False)
  is_pro = db.Column(db.Boolean, default=False)
  products = db.relationship(
      "Product", backref="seller", lazy=True, cascade="all, delete-orphan"
  )


class Product(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(150), nullable=False)
  description = db.Column(db.Text, nullable=False)
  price = db.Column(db.Float, nullable=False)
  category = db.Column(db.String(50), nullable=False, default="Այլ")
  image_url = db.Column(db.String(500), nullable=True)
  is_vip = db.Column(db.Boolean, default=False)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Favorite(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
  product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)


class Message(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
  receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
  product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=True)
  content = db.Column(db.Text, nullable=False)
  timestamp = db.Column(db.DateTime, default=datetime.utcnow)

  sender = db.relationship("User", foreign_keys=[sender_id])
  receiver = db.relationship("User", foreign_keys=[receiver_id])
  product = db.relationship("Product")


@login_manager.user_loader
def v_user(user_id):  # կամ def load_user(user_id):
  return User.query.get(int(user_id))


# --- HTML TEMPLATE (DESIGN + NEW FEATURES) ---
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="hy">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>One-Shop - Հայկական Օնլայն Շուկա</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .navbar { background-color: #1a1a1a; }
        .navbar-brand { color: #ffc107 !important; font-weight: bold; font-size: 1.5rem; }
        .footer { background-color: #1a1a1a; color: #aaa; padding: 20px 0; margin-top: 40px; text-align: center; }
        .card { border: none; transition: 0.3s; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .card:hover { transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); }
        .vip-badge { background: linear-gradient(45deg, #f12711, #f5af19); color: white; font-weight: bold; }
        .pro-badge { background: linear-gradient(45deg, #11998e, #38ef7d); color: white; font-weight: bold; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark px-3">
        <a class="navbar-brand" href="/"><i class="fa-solid fa-store me-2"></i>One-Shop</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse justify-content-end" id="navbarNav">
            <ul class="navbar-nav align-items-center">
                <li class="nav-item"><a class="nav-link" href="/"><i class="fa-solid fa-house me-1"></i>Գլխավոր</a></li>
                {% if current_user.is_authenticated %}
                    <li class="nav-item"><a class="nav-link" href="/add"><i class="fa-solid fa-plus me-1"></i>Ավելացնել</a></li>
                    <li class="nav-item"><a class="nav-link" href="/favorites"><i class="fa-solid fa-heart text-danger me-1"></i>Հավանածներ</a></li>
                    <li class="nav-item"><a class="nav-link" href="/messages"><i class="fa-solid fa-envelope me-1"></i>Նամակներ</a></li>
                    <li class="nav-item"><a class="nav-link" href="/profile"><i class="fa-solid fa-user me-1"></i>Պրոֆիլ</a></li>
                    {% if current_user.is_admin %}
                        <li class="nav-item"><a class="nav-link text-warning" href="/admin"><i class="fa-solid fa-shield me-1"></i>Ադմին</a></li>
                    {% endif %}
                    <li class="nav-item"><a class="btn btn-outline-light btn-sm ms-2" href="/logout">Ելք</a></li>
                {% else %}
                    <li class="nav-item"><a class="nav-link" href="/login">Մուտք</a></li>
                    <li class="nav-item"><a class="btn btn-warning btn-sm ms-2 text-dark fw-bold" href="/register">Գրանցվել</a></li>
                {% endif %}
            </ul>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'success' if category == 'success' else 'danger' }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <div class="footer">
        <p>&copy; 2026 One-Shop - Բոլոր իրավունքները պաշտպանված են։ Մասիս, Հայաստան 🇦🇲</p>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# --- ROUTES ---


@app.route("/")
def index():
  search_query = request.args.get("q", "")
  category_filter = request.args.get("category", "")

  query = Product.query
  if search_query:
    query = query.filter(
        Product.title.ilike(f"%{search_query}%")
        | Product.description.ilike(f"%{search_query}%")
    )
  if category_filter and category_filter != "Բոլորը":
    query = query.filter(Product.category == category_filter)

  # VIP-ները միշտ առաջինն են
  products = query.order_by(Product.is_vip.desc(), Product.id.desc()).all()
  categories = [
      "Բոլորը",
      "Էլեկտրոնիկա",
      "Հագուստ",
      "Տուն և Ագարակ",
      "Խաղեր",
      "Այլ",
  ]

  html = (
      BASE_TEMPLATE
      + """
    {% block content %}
    <div class="p-4 mb-4 bg-dark text-white rounded shadow-sm text-center">
        <h1 class="display-5 fw-bold">Բարի գալուստ One-Shop 🛒</h1>
        <p class="lead">Գտեք կամ վաճառեք ցանկացած ապրանք արագ և հարմարավետ:</p>
        
        <!-- Որոնման և ֆիլտրի ձևանմուշ -->
        <form method="GET" action="/" class="row g-2 justify-content-center mt-3">
            <div class="col-md-5">
                <input type="text" name="q" class="form-control" placeholder="Որոնել ապրանք..." value="{{ search_query }}">
            </div>
            <div class="col-md-3">
                <select name="category" class="form-select">
                    {% for cat in categories %}
                        <option value="{{ cat }}" {{ 'selected' if category_filter == cat else '' }}>{{ cat }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-md-2">
                <button type="submit" class="btn btn-warning w-100 fw-bold"><i class="fa-solid fa-search me-1"></i>Որոնել</button>
            </div>
        </form>
    </div>

    <h3 class="mb-3">Ակտիվ Ապրանքներ</h3>
    <div class="row">
        {% if products %}
            {% for p in products %}
                <div class="col-md-4 mb-4">
                    <div class="card h-100 position-relative">
                        {% if p.is_vip %}
                            <span class="position-absolute top-0 start-0 badge vip-badge m-2 px-2 py-1">VIP</span>
                        {% endif %}
                        {% if p.image_url %}
                            <img src="{{ p.image_url }}" class="card-img-top" style="height: 200px; object-fit: cover;" alt="Product">
                        {% else %}
                            <div class="bg-secondary text-white d-flex align-items-center justify-content-center" style="height: 200px;">
                                <i class="fa-solid fa-image fa-2x"></i>
                            </div>
                        {% endif %}
                        <div class="card-body d-flex flex-column">
                            <h5 class="card-title fw-bold">{{ p.title }}</h5>
                            <p class="card-text text-muted flex-grow-1">{{ p.description[:80] }}...</p>
                            <div class="d-flex justify-content-between align-items-center mt-3">
                                <span class="text-success fw-bold fs-5">{{ p.price }} ֏</span>
                                <div>
                                    {% if current_user.is_authenticated %}
                                        <a href="/favorite/{{ p.id }}" class="btn btn-outline-danger btn-sm me-1" title="Հավանել">
                                            <i class="fa-solid fa-heart"></i>
                                        </a>
                                    {% endif %}
                                    <a href="/product/{{ p.id }}" class="btn btn-dark btn-sm">Դիտել</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            {% endfor %}
        {% else %}
            <div class="col-12 text-center py-5">
                <h5 class="text-muted">Ապրանքներ չեն գտնվել...</h5>
            </div>
        {% endif %}
    </div>
    {% endblock %}
    """
  )
  return render_template_string(
      html, products=products, categories=categories, search_query=search_query
  )


@app.route("/product/<int:id>")
def product_detail(id):
  product = Product.query.get_or_404(id)
  html = (
      BASE_TEMPLATE
      + """
    {% block content %}
    <div class="row bg-white p-4 rounded shadow-sm">
        <div class="col-md-6">
            {% if product.image_url %}
                <img src="{{ product.image_url }}" class="img-fluid rounded" alt="Product">
            {% else %}
                <div class="bg-secondary text-white d-flex align-items-center justify-content-center rounded" style="height: 350px;">
                    <i class="fa-solid fa-image fa-3x"></i>
                </div>
            {% endif %}
        </div>
        <div class="col-md-6 d-flex flex-column justify-content-between">
            <div>
                <h2>{{ product.title }}</h2>
                <span class="badge bg-secondary mb-2">{{ product.category }}</span>
                <h3 class="text-success fw-bold my-3">{{ product.price }} ֏</h3>
                <p class="text-muted"><strong>Նկարագրություն:</strong><br>{{ product.description }}</p>
                <hr>
                <p><strong>Վաճառող:</strong> {{ product.seller.username }}</p>
                <p class="text-muted small">Տեղադրված է՝ {{ product.created_at.strftime('%Y-%m-%d %H:%M') }}</p>
            </div>
            
            {% if current_user.is_authenticated and current_user.id != product.user_id %}
                <div class="mt-3">
                    <a href="/chat/{{ product.user_id }}/{{ product.id }}" class="btn btn-warning w-100 fw-bold text-dark">
                        <i class="fa-solid fa-comment-dots me-2"></i>Գրել վաճառողին
                    </a>
                </div>
            {% endif %}
        </div>
    </div>
    <div class="mt-3">
        <a href="/" class="btn btn-outline-secondary"><i class="fa-solid fa-arrow-left me-1"></i>Հետ դեպի գլխավոր</a>
    </div>
    {% endblock %}
    """
  )
  return render_template_string(html, product=product)


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_product():
  if request.method == "POST":
    title = request.form.get("title")
    description = request.form.get("description")
    price = float(request.form.get("price"))
    category = request.form.get("category")
    image_url = request.form.get("image_url")

    # Ստուգում ենք PRO սահմանափակումը (եթե PRO չէ և ադմին չէ, կարող է դնել մինչև 3 ապրանք)
    if not current_user.is_admin and not current_user.is_pro:
      user_count = Product.query.filter_by(user_id=current_user.id).count()
      if user_count >= 3:
        flash(
            "Անվճար օգտատերերը կարող են տեղադրել առավելագույնը 3 ապրանք։"
            " Ավելացնելու համար անցեք PRO կարգավիճակի!",
            "danger",
        )
        return redirect("/profile")

    new_prod = Product(
        title=title,
        description=description,
        price=price,
        category=category,
        image_url=image_url,
        user_id=current_user.id,
    )
    db.session.add(new_prod)
    db.session.commit()
    flash("Ապրանքը հաջողությամբ ավելացվեց!", "success")
    return redirect("/")

  categories = ["Էլեկտրոնիկա", "Հագուստ", "Տուն և Ագարակ", "Խաղեր", "Այլ"]
  html = (
      BASE_TEMPLATE
      + """
    {% block content %}
    <div class="row justify-content-center">
        <div class="col-md-6 bg-white p-4 rounded shadow-sm">
            <h3 class="mb-4 text-center">Ավելացնել նոր ապրանք</h3>
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">Ապրանքի վերնագիր</label>
                    <input type="text" name="title" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Կատեգորիա</label>
                    <select name="category" class="form-select">
                        {% for cat in categories %}
                            <option value="{{ cat }}">{{ cat }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Գինը (֏)</label>
                    <input type="number" step="any" name="price" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Նկարի հղում (URL)</label>
                    <input type="text" name="image_url" class="form-control" placeholder="https://example.com/image.jpg">
                </div>
                <div class="mb-3">
                    <label class="form-label">Նկարագրություն</label>
                    <textarea name="description" class="form-control" rows="4" required></textarea>
                </div>
                <button type="submit" class="btn btn-warning w-100 fw-bold">Տեղադրել ապրանքը</button>
            </form>
        </div>
    </div>
    {% endblock %}
    """
  )
  return render_template_string(html, categories=categories)


@app.route("/favorite/<int:product_id>")
@login_required
def toggle_favorite(product_id):
  existing = Favorite.query.filter_by(
      user_id=current_user.id, product_id=product_id
  ).first()
  if existing:
    db.session.delete(existing)
    db.session.commit()
    flash("Ապրանքը հեռացվեց հավանածներից։", "success")
  else:
    fav = Favorite(user_id=current_user.id, product_id=product_id)
    db.session.add(fav)
    db.session.commit()
    flash("Ապրանքն ավելացվեց հավանածներին!", "success")
  return redirect(request.referrer or "/")


@app.route("/favorites")
@login_required
def favorites():
  favs = Favorite.query.filter_by(user_id=current_user.id).all()
  products = [Product.query.get(f.product_id) for f in favs]
  html = (
      BASE_TEMPLATE
      + """
    {% block content %}
    <h3 class="mb-3"><i class="fa-solid fa-heart text-danger me-2"></i>Իմ Հավանած Ապրանքները</h3>
    <div class="row">
        {% if products %}
            {% for p in products %}
                <div class="col-md-4 mb-4">
                    <div class="card h-100">
                        {% if p.image_url %}
                            <img src="{{ p.image_url }}" class="card-img-top" style="height: 200px; object-fit: cover;">
                        {% endif %}
                        <div class="card-body d-flex flex-column">
                            <h5 class="card-title fw-bold">{{ p.title }}</h5>
                            <p class="card-text text-success fw-bold">{{ p.price }} ֏</p>
                            <a href="/product/{{ p.id }}" class="btn btn-dark btn-sm mt-auto">Դիտել</a>
                        </div>
                    </div>
                </div>
            {% endfor %}
        {% else %}
            <div class="col-12 text-center py-5">
                <h5 class="text-muted">Դուք դեռ չունեք հավանած ապրանքներ։</h5>
            </div>
        {% endif %}
    </div>
    {% endblock %}
    """
  )
  return render_template_string(html, products=products)


@app.route("/chat/<int:receiver_id>/<int:product_id>")
@login_required
def start_chat(receiver_id, product_id):
  # Ուղղորդում է դեպի նամակների էջ կոնկրետ օգտատիրոջ հետ
  return redirect(f"/messages?with={receiver_id}&product={product_id}")


@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages():
  other_user_id = request.args.get("with", type=int)
  product_id = request.args.get("product", type=int)

  if request.method == "POST":
    receiver_id = request.form.get("receiver_id", type=int)
    content = request.form.get("content")
    p_id = request.form.get("product_id", type=int)
    if content:
      msg = Message(
          sender_id=current_user.id,
          receiver_id=receiver_id,
          product_id=p_id if p_id else None,
          content=content,
      )
      db.session.add(msg)
      db.session.commit()
    return redirect(f"/messages?with={receiver_id}")

  # Բոլոր այն օգտատերերը, որոնց հետ կան նամակներ կամ որոշակի զրույց
  active_with = None
  chat_messages = []
  if other_user_id:
    active_with = User.query.get_or_404(other_user_id)
    chat_messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == other_user_id))
        | ((Message.sender_id == other_user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()

  # Գտնենք բոլոր զրուցակիցներին
  sent_to = [m.receiver_id for m in Message.query.filter_by(sender_id=current_user.id).all()]
  received_from = [m.sender_id for m in Message.query.filter_by(receiver_id=current_user.id).all()]
  contact_ids = list(set(sent_to + received_from))
  contacts = User.query.filter(User.id.in_(contact_ids)).all() if contact_ids else []

  html = (
      BASE_TEMPLATE
      + """
    {% block content %}
    <div class="row bg-white rounded shadow-sm p-3" style="min-height: 500px;">
        <div class="col-md-4 border-end">
            <h5>Զրույցներ</h5>
            <div class="list-group mt-3">
                {% if contacts %}
                    {% for c in contacts %}
                        <a href="/messages?with={{ c.id }}" class="list-group-item list-group-item-action {{ 'active' if active_with and active_with.id == c.id else '' }}">
                            <i class="fa-solid fa-user-circle me-2"></i>{{ c.username }}
                        </a>
                    {% endfor %}
                {% else %}
                    <p class="text-muted small">Դեռևս նամակներ չկան։ Կարող եք գրել վաճառողներին ապրանքի էջից։</p>
                {% endif %}
            </div>
        </div>
        <div class="col-md-8 d-flex flex-column justify-content-between">
            {% if active_with %}
                <div>
                    <h5 class="border-bottom pb-2">Զրույց {{ active_with.username }}-ի հետ</h5>
                    <div class="p-3 mb-3" style="height: 350px; overflow-y: auto; background: #f9f9f9; border-radius: 8px;">
                        {% for msg in chat_messages %}
                            <div class="mb-2 text-{{ 'end' if msg.sender_id == current_user.id else 'start' }}">
                                <div class="d-inline-block p-2 rounded {{ 'bg-warning text-dark' if msg.sender_id == current_user.id else 'bg-white border' }}" style="max-width: 75%;">
                                    <small class="d-block text-muted" style="font-size: 10px;">{{ msg.timestamp.strftime('%H:%M') }}</small>
                                    {{ msg.content }}
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                </div>
                <form method="POST">
                    <input type="hidden" name="receiver_id" value="{{ active_with.id }}">
                    <div class="input-group">
                        <input type="text" name="content" class="form-control" placeholder="Գրեք հաղորդագրություն..." required>
                        <button type="submit" class="btn btn-warning fw-bold">Ուղարկել</button>
                    </div>
                </form>
            {% else %}
                <div class="text-center my-auto">
                    <h5 class="text-muted">Ընտրեք զրույց ձախ կողմից կամ գրեք ապրանքի վաճառողին։</h5>
                </div>
            {% endif %}
        </div>
    </div>
    {% endblock %}
    """
  )
  return render_template_string(
      html, contacts=contacts, active_with=active_with, chat_messages=chat_messages
  )


@app.route("/profile")
@login_required
def profile():
  user_products = Product.query.filter_by(user_id=current_user.id).all()
  html = (
      BASE_TEMPLATE
      + """
    {% block content %}
    <div class="row bg-white p-4 rounded shadow-sm">
        <div class="col-md-4 text-center border-end">
            <i class="fa-solid fa-user-circle fa-5x text-secondary mb-3"></i>
            <h4>{{ current_user.username }}</h4>
            <p class="text-muted">{{ current_user.email }}</p>
            
            {% if current_user.is_admin %}
                <span class="badge bg-danger mb-2">Ադմինիստրատոր</span>
            {% elif current_user.is_pro %}
                <span class="badge pro-badge mb-2">PRO Օգտատեր</span>
            {% else %}
                <span class="badge bg-secondary mb-2">Սովորական օգտատեր</span>
                <div class="card bg-light p-3 mt-3 text-start">
                    <h6 class="fw-bold text-dark">Ցանկանո՞ւմ եք անսահմանափակ ապրանքներ։</h6>
                    <p class="small text-muted mb-2">Ձեռք բերեք PRO կարգավիճակ ընդամենը 1000 դրամով։ Գրեք ադմինին՝ haykazaryan3@gmail.com</p>
                </div>
            {% endif %}
        </div>
        
        <div class="col-md-8">
            <h4 class="mb-3">Իմ Ապրանքները</h4>
            <div class="row">
                {% if user_products %}
                    {% for p in user_products %}
                        <div class="col-md-6 mb-3">
                            <div class="card h-100">
                                <div class="card-body">
                                    <h5 class="card-title">{{ p.title }}</h5>
                                    <p class="text-success fw-bold">{{ p.price }} ֏</p>
                                    <a href="/product/{{ p.id }}" class="btn btn-dark btn-sm">Դիտել</a>
                                    <a href="/delete/{{ p.id }}" class="btn btn-outline-danger btn-sm">Ջնջել</a>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <p class="text-muted">Դուք դեռ ապրանքներ չեք տեղադրել։</p>
                {% endif %}
            </div>
        </div>
    </div>
    {% endblock %}
    """
  )
  return render_template_string(html, user_products=user_products)


@app.route("/delete/<int:id>")
@login_required
def delete_product(id):
  product = Product.query.get_or_404(id)
  if product.user_id == current_user.id or current_user.is_admin:
    db.session.delete(product)
    db.session.commit()
    flash("Ապրանքը ջնջվեց։", "success")
  else:
    flash("Դուք իրավունք չունեք ջնջելու այս ապրանքը։", "danger")
  return redirect("/profile")


@app.route("/admin")
@login_required
def admin():
  if not current_user.is_admin:
    abort(403)
  users = User.query.all()
  products = Product.query.all()
  html = (
      BASE_TEMPLATE
      + """
    {% block content %}
    <h2 class="mb-4 text-danger"><i class="fa-solid fa-shield-halved me-2"></i>Ադմինիստրատորի Վահանակ</h2>
    
    <h4 class="mt-4">Օգտատերեր</h4>
    <div class="table-responsive bg-white p-3 rounded shadow-sm">
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Անուն</th>
                    <th>Email</th>
                    <th>Կարգավիճակ</th>
                    <th>Գործողություն</th>
                </tr>
            </thead>
            <tbody>
                {% for u in users %}
                <tr>
                    <td>{{ u.id }}</td>
                    <td>{{ u.username }}</td>
                    <td>{{ u.email }}</td>
                    <td>
                        {% if u.is_admin %} Ադմին
                        {% elif u.is_pro %} PRO
                        {% else %} Սովորական
                        {% endif %}
                    </td>
                    <td>
                        {% if not u.is_admin %}
                            <a href="/admin/make-pro/{{ u.id }}" class="btn btn-success btn-sm">PRO դարձնել</a>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endblock %}
    """
  )
  return render_template_string(html, users=users, products=products)


@app.route("/admin/make-pro/<int:user_id>")
@login_required
def make_pro(user_id):
  if not current_user.is_admin:
    abort(403)
  u = User.query.get_or_404(user_id)
  u.is_pro = True
  db.session.commit()
  flash(f"{u.username} օգտատերը հաջողությամբ դարձավ PRO!", "success")
  return redirect("/admin")


@app.route("/login", methods=["GET", "POST"])
def login():
  if request.method == "POST":
    email = request.form.get("email")
    password = request.form.get("password")
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
      login_user(user)
      flash("Բարի գալուստ!", "success")
      return redirect("/")
    flash("Սխալ էլ. փոստ կամ գաղտնաբառ։", "danger")

  html = (
      BASE_TEMPLATE
      + """
    {% block content %}
    <div class="row justify-content-center">
        <div class="col-md-5 bg-white p-4 rounded shadow-sm">
            <h3 class="mb-4 text-center">Մուտք</h3>
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">Էլ. փոստ</label>
                    <input type="email" name="email" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Գաղտնաբառ</label>
                    <input type="password" name="password" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-warning w-100 fw-bold">Մուտք գործել</button>
            </form>
        </div>
    </div>
    {% endblock %}
    """
  )
  return render_template_string(html)


@app.route("/register", methods=["GET", "POST"])
def register():
  if request.method == "POST":
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")

    if User.query.filter_by(email=email).first():
      flash("Այս էլ. փոստն արդեն զբաղված է։", "danger")
      return redirect("/register")

    hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
    is_admin_val = True if email == "haykazaryan3@gmail.com" else False

    new_user = User(
        username=username,
        email=email,
        password=hashed_pw,
        is_admin=is_admin_val,
    )
    db.session.add(new_user)
    db.session.commit()
    flash("Գրանցումը հաջողված է։ Խնդրում ենք մուտք գործել։", "success")
    return redirect("/login")

  html = (
      BASE_TEMPLATE
      + """
    {% block content %}
    <div class="row justify-content-center">
        <div class="col-md-5 bg-white p-4 rounded shadow-sm">
            <h3 class="mb-4 text-center">Գրանցում</h3>
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">Անուն</label>
                    <input type="text" name="username" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Էլ. փոստ</label>
                    <input type="email" name="email" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Գաղտնաբառ</label>
                    <input type="password" name="password" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-warning w-100 fw-bold">Գրանցվել</button>
            </form>
        </div>
    </div>
    {% endblock %}
    """
  )
  return render_template_string(html)


@app.route("/logout")
@login_required
def logout():
  logout_user()
  flash("Դուրս եկաք հաշվից։", "success")
  return redirect("/")


if __name__ == "__main__":
  with app.app_context():
    db.create_all()
  app.run(debug=True)
