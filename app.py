from datetime import datetime, timedelta
from pathlib import Path
import json
import sqlite3
import uuid

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"

app = Flask(__name__)
app.secret_key = "parts360secret"

VEHICLES = {
    "Maruti": ["Swift", "Baleno", "Brezza", "Fronx", "Ertiga"],
    "Hyundai": ["Creta", "i20", "Venue", "Verna", "Alcazar"],
    "Honda": ["City", "Amaze", "Elevate", "Jazz"],
    "Tata": ["Nexon", "Harrier", "Safari", "Punch", "Altroz"],
    "Mahindra": ["Thar", "Scorpio", "XUV700", "Bolero", "XUV300"],
    "Toyota": ["Innova", "Fortuner", "Glanza", "Urban Cruiser"],
    "Kia": ["Seltos", "Sonet", "Carens"],
    "Skoda": ["Slavia", "Kushaq", "Octavia"],
    "Renault": ["Kiger", "Triber", "Kwid"],
    "Nissan": ["Magnite", "Sunny", "Kicks"],
}

YEARS = [2026, 2025, 2024, 2023, 2022, 2021, 2020]

PART_TYPES = [
    {"category": "Engine", "name": "Oil Filter Kit", "maker": "Bosch", "price": 799, "image": "oil-filter.svg", "warranty": "12 months"},
    {"category": "Engine", "name": "Spark Plug Set", "maker": "NGK", "price": 1299, "image": "spark-plugs.svg", "warranty": "12 months"},
    {"category": "Engine", "name": "Timing Belt Assembly", "maker": "Gates", "price": 3499, "image": "timing-belt.svg", "warranty": "18 months"},
    {"category": "Brakes", "name": "Ceramic Brake Pads", "maker": "Brembo", "price": 2499, "image": "brake-pads.svg", "warranty": "12 months"},
    {"category": "Brakes", "name": "Front Disc Rotor Pair", "maker": "TVS Girling", "price": 4599, "image": "disc-rotor.svg", "warranty": "18 months"},
    {"category": "Suspension", "name": "Shock Absorber Set", "maker": "Monroe", "price": 5999, "image": "shock-absorber.svg", "warranty": "24 months"},
    {"category": "Suspension", "name": "Lower Control Arm", "maker": "Mando", "price": 3199, "image": "control-arm.svg", "warranty": "18 months"},
    {"category": "Filters", "name": "Cabin AC Filter", "maker": "Mann Filter", "price": 699, "image": "cabin-filter.svg", "warranty": "6 months"},
    {"category": "Filters", "name": "Performance Air Filter", "maker": "K&N", "price": 2299, "image": "air-filter.svg", "warranty": "12 months"},
    {"category": "Electrical", "name": "DIN Battery", "maker": "Amaron", "price": 6499, "image": "battery.svg", "warranty": "36 months"},
    {"category": "Electrical", "name": "Alternator Assembly", "maker": "Denso", "price": 8499, "image": "alternator.svg", "warranty": "12 months"},
    {"category": "Lighting", "name": "LED Headlamp Unit", "maker": "Philips", "price": 5499, "image": "headlamp.svg", "warranty": "24 months"},
    {"category": "Lighting", "name": "Fog Lamp Pair", "maker": "Hella", "price": 2899, "image": "fog-lamp.svg", "warranty": "12 months"},
    {"category": "Body Parts", "name": "Front Bumper", "maker": "Uno Minda", "price": 7999, "image": "bumper.svg", "warranty": "6 months"},
    {"category": "Body Parts", "name": "ORVM Mirror Assembly", "maker": "Mobis", "price": 2399, "image": "mirror.svg", "warranty": "12 months"},
    {"category": "Accessories", "name": "3D Floor Mat Set", "maker": "Autoform", "price": 2199, "image": "floor-mats.svg", "warranty": "12 months"},
    {"category": "Accessories", "name": "Android Infotainment System", "maker": "Sony", "price": 18499, "image": "infotainment.svg", "warranty": "24 months"},
]

CATEGORY_IMAGES = {
    "Engine": "engine.png",
    "Brakes": "brakes.png",
    "Suspension": "suspension.png",
    "Filters": "filters.png",
    "Electrical": "electrical.png",
    "Lighting": "lighting.png",
    "Body Parts": "bodyparts.png",
    "Accessories": "accessories.png",
}


def build_catalog():
    catalog = []
    product_id = 1
    for brand_index, (brand, models) in enumerate(VEHICLES.items()):
        for model_index, model in enumerate(models):
            for year in YEARS:
                offset = (brand_index + model_index + year) % len(PART_TYPES)
                selected_parts = [PART_TYPES[(offset + i) % len(PART_TYPES)] for i in range(10)]
                for part_index, part in enumerate(selected_parts):
                    price = part["price"] + max(0, year - 2020) * 85 + (model_index + 1) * 140
                    discount = int(price * (0.88 if part_index % 3 == 0 else 0.94))
                    catalog.append({
                        "id": product_id,
                        "name": f"{brand} {model} {part['name']} ({year})",
                        "short_name": part["name"],
                        "category": part["category"],
                        "brand": brand,
                        "model": model,
                        "year": year,
                        "maker": part["maker"],
                        "price": price,
                        "discount_price": discount,
                        "image": part["image"],
                        "gallery": [part["image"], CATEGORY_IMAGES[part["category"]], "logo_page.png"],
                        "stock": 4 + ((product_id * 7) % 45),
                        "rating": round(4.1 + ((product_id % 9) / 10), 1),
                        "reviews": 18 + (product_id * 3) % 240,
                        "warranty": part["warranty"],
                        "delivery_days": 2 + (product_id % 5),
                        "description": f"Genuine-fit {part['name'].lower()} for {brand} {model} {year}. Built for reliable daily use, correct mounting points, and long service life.",
                        "specs": [
                            f"Compatible with {brand} {model} {year}",
                            f"Part category: {part['category']}",
                            f"Manufacturer: {part['maker']}",
                            "Quality checked before dispatch",
                            "Returnable within 7 days if unused and in original packaging",
                        ],
                    })
                    product_id += 1
    return catalog


CATALOG = build_catalog()
PRODUCTS = {item["id"]: item for item in CATALOG}
CATEGORIES = sorted({item["category"] for item in CATALOG})


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        password TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT UNIQUE,
        username TEXT,
        customer_name TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        payment_method TEXT,
        total INTEGER,
        items TEXT,
        created_at TEXT,
        delivery_date TEXT
    )
    """)
    conn.commit()
    conn.close()


def find_products(brand="", model="", year="", category="", query="", sort=""):
    results = CATALOG
    if brand:
        results = [p for p in results if p["brand"] == brand]
    if model:
        results = [p for p in results if p["model"] == model]
    if year:
        results = [p for p in results if str(p["year"]) == str(year)]
    if category:
        results = [p for p in results if p["category"] == category]
    if query:
        q = query.lower()
        results = [p for p in results if q in p["name"].lower() or q in p["category"].lower() or q in p["maker"].lower()]
    if sort == "price-low":
        results = sorted(results, key=lambda p: p["discount_price"])
    elif sort == "price-high":
        results = sorted(results, key=lambda p: p["discount_price"], reverse=True)
    elif sort == "rating":
        results = sorted(results, key=lambda p: p["rating"], reverse=True)
    return results


def cart_details():
    cart = session.get("cart", {})
    products = []
    subtotal = 0
    for product_id, qty in cart.items():
        product = PRODUCTS.get(int(product_id))
        if not product:
            continue
        qty = int(qty)
        line_total = product["discount_price"] * qty
        subtotal += line_total
        products.append({"product": product, "qty": qty, "line_total": line_total})
    coupon = session.get("coupon", "")
    discount = int(subtotal * 0.10) if coupon.upper() == "PARTS10" else 0
    shipping = 0 if subtotal >= 5000 or subtotal == 0 else 99
    tax = int((subtotal - discount) * 0.18)
    total = max(0, subtotal - discount + shipping + tax)
    return {"items": products, "subtotal": subtotal, "discount": discount, "shipping": shipping, "tax": tax, "total": total, "coupon": coupon}


@app.context_processor
def inject_globals():
    return {"cart_count": sum(int(qty) for qty in session.get("cart", {}).values()), "username": session.get("username")}


@app.route("/")
def home():
    featured_parts = [CATALOG[i] for i in [0, 8, 34, 88, 148, 228, 318, 468] if i < len(CATALOG)]
    return render_template("index.html", vehicles=VEHICLES, years=YEARS, categories=CATEGORIES, featured_parts=featured_parts)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE name=?", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template("register.html", error="Username already exists")
        cursor.execute("INSERT INTO users (name, password) VALUES (?, ?)", (username, generate_password_hash(password)))
        conn.commit()
        conn.close()
        return render_template("login.html", message="Account created successfully. Please login to continue.")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE name=?", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["username"] = username
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    message = "Message sent successfully. Our parts advisor will contact you soon." if request.method == "POST" else None
    return render_template("contact.html", message=message)


@app.route("/vehicle")
def vehicle():
    brand = request.args.get("brand", "")
    model = request.args.get("model", "")
    year = request.args.get("year", "")
    category = request.args.get("category", "")
    sort = request.args.get("sort", "")
    query = request.args.get("query", "")
    parts = find_products(brand, model, year, category, query, sort)
    return render_template("vehicle.html", parts=parts, vehicles=VEHICLES, years=YEARS, categories=CATEGORIES, brand=brand, model=model, year=year, category=category, sort=sort, query=query)


@app.route("/product/<int:id>")
def product(id):
    item = PRODUCTS.get(id)
    if not item:
        return redirect(url_for("home"))
    related = [p for p in CATALOG if p["brand"] == item["brand"] and p["model"] == item["model"] and p["id"] != item["id"]][:4]
    return render_template("product.html", product=item, related=related)


@app.route("/search")
def search():
    query = request.args.get("query", "")
    parts = find_products(query=query, sort=request.args.get("sort", ""))
    return render_template("search.html", parts=parts, query=query, categories=CATEGORIES)


@app.route("/add_to_cart/<int:product_id>", methods=["GET", "POST"])
def add_to_cart(product_id):
    if product_id not in PRODUCTS:
        return redirect(url_for("home"))
    cart = session.get("cart", {})
    qty = int(request.form.get("qty", 1)) if request.method == "POST" else 1
    cart[str(product_id)] = int(cart.get(str(product_id), 0)) + max(1, qty)
    session["cart"] = cart
    session.modified = True
    return redirect(request.form.get("next") or request.referrer or url_for("cart"))


@app.route("/update_cart", methods=["POST"])
def update_cart():
    product_id = request.form.get("product_id")
    action = request.form.get("action")
    cart = session.get("cart", {})
    if product_id in cart:
        current = int(cart[product_id])
        if action == "increase":
            cart[product_id] = current + 1
        elif action == "decrease":
            cart.pop(product_id) if current <= 1 else cart.update({product_id: current - 1})
        elif action == "remove":
            cart.pop(product_id)
    session["cart"] = cart
    session.modified = True
    return redirect(url_for("cart"))


@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    cart.pop(str(product_id), None)
    session["cart"] = cart
    session.modified = True
    return redirect(url_for("cart"))


@app.route("/apply_coupon", methods=["POST"])
def apply_coupon():
    session["coupon"] = request.form.get("coupon", "").strip().upper()
    return redirect(url_for("cart"))


@app.route("/cart")
def cart():
    return render_template("cart.html", cart=cart_details())


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart = cart_details()
    if not cart["items"]:
        return redirect(url_for("cart"))
    if request.method == "POST":
        order_id = "P360-" + uuid.uuid4().hex[:8].upper()
        delivery_date = (datetime.now() + timedelta(days=5)).strftime("%d %b %Y")
        order = {
            "order_id": order_id,
            "customer_name": request.form["customer_name"],
            "phone": request.form["phone"],
            "email": request.form["email"],
            "address": request.form["address"],
            "payment_method": request.form["payment_method"],
            "delivery_date": delivery_date,
            "cart": cart,
        }
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders (order_id, username, customer_name, phone, email, address, payment_method, total, items, created_at, delivery_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id, session.get("username", "Guest"), order["customer_name"], order["phone"], order["email"],
            order["address"], order["payment_method"], cart["total"],
            json.dumps([{"id": row["product"]["id"], "name": row["product"]["name"], "qty": row["qty"], "line_total": row["line_total"]} for row in cart["items"]]),
            datetime.now().isoformat(timespec="seconds"), delivery_date,
        ))
        conn.commit()
        conn.close()
        session["last_order"] = order
        session.pop("cart", None)
        session.pop("coupon", None)
        return redirect(url_for("order_confirmation", order_id=order_id))
    return render_template("checkout.html", cart=cart)


@app.route("/order/<order_id>")
def order_confirmation(order_id):
    order = session.get("last_order")
    if not order or order.get("order_id") != order_id:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE order_id=?", (order_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return redirect(url_for("home"))
        order = dict(row)
        order["items"] = json.loads(order["items"])
    return render_template("order_confirmation.html", order=order)


init_db()

if __name__ == "__main__":
    app.run(debug=True)
