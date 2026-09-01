from datetime import datetime
import io
import json
import os
import sys

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import qrcode

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from models.db_manager import (
    add_general_expense,
    add_product,
    add_raw_expense,
    add_raw_material_db,
    add_shop,
    authenticate_user,
    create_tables,
    delete_general_expense,
    delete_product,
    delete_raw_material_db,
    delete_shop,
    get_active_shift,
    get_all_products,
    get_all_raw_materials,
    get_all_shops,
    get_connection,
    get_custom_report,
    get_daily_sales,
    get_daily_shop_invoices,
    get_general_expenses_by_date,
    get_raw_expenses_by_date,
    get_truck_inventory_data,
    load_truck_inventory,
    process_store_sale_db,
    return_truck_to_warehouse,
    seed_data,
    start_new_shift,
    end_active_shift,
    update_full_product,
    update_raw_material_db,
    update_raw_stock_db,
    update_stock_after_sale,
)

app = Flask(__name__)
# استخدام مفتاح سحري آمن أو من متغيرات البيئة مع قيمة افتراضية صلبة
app.secret_key = os.environ.get("SECRET_KEY", "your_secure_random_production_key_here")

# إعداد حماية الـ Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

TRUCKS_LIST = [
    {"id": "truck_1", "name": "عربية سوزوكي", "driver_name": "فكتور"},
    {"id": "truck_2", "name": "عربية لادا", "driver_name": "اشرف"},
]

with app.app_context():
  create_tables()
  seed_data()


# --- Decorator للتحقق من تسجيل الدخول العام ---
def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    if "username" not in session:
      if request.is_json:
        return jsonify({"success": False, "error": "يجب تسجيل الدخول أولاً"}), 401
      return redirect(url_for("login"))
    return f(*args, **kwargs)
  return decorated_function


def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "username" not in session:
            return jsonify({"success": False, "error": "يجب تسجيل الدخول أولاً"}), 401

        user_role = session.get("user_role")

        if user_role != "admin":
            return (
                jsonify({
                    "success": False,
                    "error": "غير مسموح! هذه العملية خاصة بالمدير فقط.",
                }),
                403,
            )

        return f(*args, **kwargs)

    return decorated_function


# --- Decorator للتحقق من الصلاحيات المخصصة ---
def permission_required(permission_name):
  def decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
      if "username" not in session:
        if request.is_json:
          return jsonify({"success": False, "error": "يجب تسجيل الدخول أولاً"}), 401
        return redirect(url_for("login"))

      user_role = session.get("user_role")
      user_permissions = session.get("permissions", "")

      # المدير لديه كافة الصلاحيات دائماً
      if user_role == "admin":
        return f(*args, **kwargs)

      # التحقق إذا كانت الصلاحية المطلوبة موجودة ضمن صلاحيات المستخدم
      if user_permissions == "all" or permission_name in [p.strip() for p in user_permissions.split(",")]:
        return f(*args, **kwargs)

      return (
          jsonify({
              "success": False,
              "error": "غير مسموح! لا تملك الصلاحية اللازمة لتنفيذ هذه العملية.",
          }),
          403,
      )
    return decorated_function
  return decorator


# --- مسار توليد الـ QR Code تلقائياً ---
@app.route("/generate_qr")
def generate_qr():
  try:
    menu_url = "http://192.168.1.18:5000/menu"

    img = qrcode.make(menu_url)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")
  except Exception as e:
    return str(e)


# --- مسار تسجيل الدخول ---
@app.route("/login", methods=["GET", "POST"])
def login():
  if request.method == "POST":
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user = authenticate_user(username, password)
    if user:
      session["username"] = user["username"]
      session["user_role"] = user["role"]
      session["permissions"] = user.get("permissions", "")
      return jsonify({"success": True, "role": user["role"], "permissions": user.get("permissions", "")})
    else:
      return jsonify(
          {"success": False, "error": "اسم المستخدم أو كلمة المرور غير صحيحة"}
      )

  return render_template("login.html")


@app.route("/logout")
def logout():
  session.clear()
  return redirect(url_for("login"))


# --- الصفحات الرئيسية المحمية ---
@app.route("/")
@login_required
def pos_screen():
  raw_products = get_all_products()
  products = []
  for p in raw_products:
    products.append({
        "name": p[0],
        "price": p[1],
        "wholesale_price": p[2] if len(p) > 2 else 0.0,
        "stock": p[3] if len(p) > 3 else p[2],
        "unit": p[4] if len(p) > 4 else "piece",
        "image_path": p[5] if len(p) > 5 else "default.png",
        "category": p[6] if len(p) > 6 else "bread",
    })
  return render_template("pos.html", products=products)


@app.route("/driver")
@permission_required("driver")
def driver_screen():
  stores = get_all_shops()
  warehouse_products = []
  for p in get_all_products():
    warehouse_products.append({
        "id": p[0],
        "name": p[0],
        "price": p[1],
        "wholesale_price": p[2],
        "stock": p[3],
        "unit": p[4] if len(p) > 4 else "قطعة",
    })
  return render_template(
      "driver.html",
      trucks=TRUCKS_LIST,
      stores=stores,
      warehouse_products=warehouse_products,
  )


# --- صفحة المنيو لعرض الأسعار (عامة للعملاء) ---
@app.route("/menu")
def online_menu():
  raw_products = get_all_products()
  products = []
  for p in raw_products:
    products.append({
        "name": p[0],
        "price": p[1],
        "wholesale_price": p[2] if len(p) > 2 else 0.0,
        "stock": p[3] if len(p) > 3 else p[2],
        "unit": p[4] if len(p) > 4 else "piece",
        "image_path": p[5] if len(p) > 5 else "default.png",
        "category": p[6] if len(p) > 6 else "bread",
    })
  return render_template("menu.html", products=products)


# --- الصفحات المحمية بالصلاحيات ---
@app.route("/reports")
@permission_required("reports")
def reports_screen():
  return render_template("reports.html")


# --- مسار لوحة التحليلات الجديد (Analysis) ---
@app.route("/analysis")
@permission_required("reports")
def analysis_screen():
  return render_template("analysis.html")


@app.route("/expenses")
@permission_required("expenses")
def expenses_screen():
  return render_template("expenses.html")


@app.route("/products_manage")
@permission_required("products")
def products_manage_screen():
  raw_products = get_all_products()
  products = []
  for p in raw_products:
    products.append({
        "name": p[0],
        "price": p[1],
        "wholesale_price": p[2] if len(p) > 2 else 0.0,
        "stock": p[3] if len(p) > 3 else p[2],
        "unit": p[4] if len(p) > 4 else "piece",
        "image_path": p[5] if len(p) > 5 else "default.png",
        "category": p[6] if len(p) > 6 else "bread",
    })
  return render_template("products_manage.html", products=products)


@app.route("/raw_inventory")
@permission_required("raw_inventory")
def raw_inventory():
  raw_materials_db = get_all_raw_materials()
  return render_template("raw_inventory.html", raw_materials=raw_materials_db)


# --- مسارات إدارة المستخدمين (للمدير فقط) ---
@app.route("/users_manage", methods=["GET", "POST"])
@admin_required
def users_manage():
  conn = get_connection()
  cursor = conn.cursor()

  if request.method == "POST":
    username = request.form.get("username")
    password = request.form.get("password")
    role = request.form.get("role")
    
    permissions_list = request.form.getlist("permissions")
    permissions_str = ",".join(permissions_list) if permissions_list else ""

    if username and password and role:
      try:
        cursor.execute(
            "INSERT INTO users (username, password, role, permissions) VALUES (?, ?, ?, ?)",
            (username, password, role, permissions_str),
        )
        conn.commit()
      except Exception as e:
        print("Error adding user:", e)
    conn.close()
    return redirect(url_for("users_manage"))

  cursor.execute("SELECT id, username, role, permissions FROM users")
  users = cursor.fetchall()
  conn.close()

  return render_template("users_manage.html", users=users)


@app.route("/user_delete/<int:id>", methods=["POST"])
@admin_required
def user_delete(id):
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("DELETE FROM users WHERE id = ?", (id,))
  conn.commit()
  conn.close()
  return redirect(url_for("users_manage"))


# --- الـ APIs وعمليات المخزن والخامات والمبيعات ---
@app.route("/add_raw_material", methods=["POST"])
@permission_required("raw_inventory")
def add_raw_material():
  try:
    name = request.form.get("name")
    quantity = float(request.form.get("quantity", 0))
    unit = request.form.get("unit")
    cost_price = float(request.form.get("cost_price", 0))
    min_limit = float(request.form.get("min_limit", 10))

    if quantity < 0:
      return "الكمية لا يمكن أن تكون سالبة", 400

    if name:
      add_raw_material_db(name, quantity, unit, cost_price, min_limit)

      total_cost = quantity * cost_price
      if total_cost > 0:
        today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        add_raw_expense(name, total_cost, today_str)

    return redirect(url_for("raw_inventory"))
  except Exception as e:
    return str(e)


@app.route("/update_raw_stock", methods=["POST"])
@permission_required("raw_inventory")
def update_raw_stock():
  try:
    data = request.json
    item_id = data.get("id")
    amount = float(data.get("amount", 0))

    success, message, item_name, cost_price = update_raw_stock_db(item_id, amount)
    
    if success and amount != 0:
      cost_to_record = abs(amount) * cost_price
      today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      add_raw_expense(
          f"{item_name} ({'إضافة' if amount > 0 else 'استهلاك/سحب'})",
          cost_to_record,
          today_str,
      )

    return jsonify({"success": success, "error": message if not success else None})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/update_raw_material", methods=["POST"])
@permission_required("raw_inventory")
def update_raw_material():
  try:
    item_id = request.form.get("id")
    name = request.form.get("name")
    unit = request.form.get("unit")
    cost_price = float(request.form.get("cost_price", 0))
    min_limit = float(request.form.get("min_limit", 10))

    update_raw_material_db(item_id, name, unit, cost_price, min_limit)
    return redirect(url_for("raw_inventory"))
  except Exception as e:
    return str(e)


@app.route("/delete_raw_material", methods=["POST"])
@permission_required("raw_inventory")
def delete_raw_material():
  try:
    data = request.json
    item_id = data.get("id")
    delete_raw_material_db(item_id)
    return jsonify({"success": True})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/get_raw_expenses", methods=["GET"])
@permission_required("reports")
def api_get_raw_expenses():
  try:
    selected_date = request.args.get("date")
    total_raw_cost = get_raw_expenses_by_date(selected_date)
    return jsonify({"success": True, "total_raw_expenses": total_raw_cost})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/add_general_expense", methods=["POST"])
@permission_required("expenses")
def api_add_general_expense():
  try:
    data = request.json
    expense_type = data.get("expense_type")
    amount = data.get("amount")
    notes = data.get("notes", "")
    expense_date = data.get("date")

    if not expense_type or amount is None:
      return jsonify({"success": False, "error": "نوع المصروف والمبلغ مطلوبان"})
    
    if float(amount) <= 0:
      return jsonify({"success": False, "error": "المبلغ يجب أن يكون أكبر من الصفر"})

    add_general_expense(expense_type, float(amount), notes, expense_date)
    return jsonify({"success": True, "message": "تم تسجيل المصروف العام بنجاح"})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/get_general_expenses", methods=["GET"])
@permission_required("expenses")
def api_get_general_expenses():
  try:
    selected_date = request.args.get("date")
    result = get_general_expenses_by_date(selected_date)
    return jsonify(
        {"success": True, "expenses": result["expenses"], "total": result["total"]}
    )
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/delete_general_expense", methods=["POST"])
@permission_required("expenses")
def api_delete_general_expense():
  try:
    data = request.json
    expense_id = data.get("id")
    if not expense_id:
      return jsonify({"success": False, "error": "معرف المصروف مطلوب"})

    delete_general_expense(expense_id)
    return jsonify({"success": True, "message": "تم حذف المصروف بنجاح"})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/api/shift/start", methods=["POST"])
@login_required
def api_start_shift():
  try:
    data = request.json
    cashier_name = data.get("cashier_name")
    starting_cash = float(data.get("starting_cash", 0.0))

    if starting_cash < 0:
      return jsonify({"success": False, "error": "النقدية الابتدائية لا يمكن أن تكون سالبة"})

    if not cashier_name:
      return jsonify({"success": False, "error": "اسم الكاشير مطلوب"})

    success, message = start_new_shift(cashier_name, starting_cash)
    if success:
      return jsonify({"success": True, "message": message})
    else:
      return jsonify({"success": False, "error": message})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/api/shift/active", methods=["GET"])
@login_required
def api_get_active_shift():
  try:
    shift = get_active_shift()
    return jsonify({"success": True, "shift": shift})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/api/shift/end", methods=["POST"])
@login_required
def api_end_shift():
  try:
    data = request.json
    actual_cash = data.get("actual_cash")

    if actual_cash is None:
      return jsonify({"success": False, "error": "النقد الفعلي في الدرج مطلوب"})

    if float(actual_cash) < 0:
      return jsonify({"success": False, "error": "النقد الفعلي لا يمكن أن يكون بالسالب"})

    success, result = end_active_shift(float(actual_cash))
    if success:
      return jsonify({"success": True, "summary": result})
    else:
      return jsonify({"success": False, "error": result})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/custom_report", methods=["GET"])
@permission_required("reports")
def api_custom_report():
  try:
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
      return jsonify(
          {"success": False, "error": "يجب تحديد تاريخ البداية والنهاية"}
      )

    report_data = get_custom_report(start_date, end_date)
    trucks_map = {t["id"]: t["name"] for t in TRUCKS_LIST}

    if "trucks_invoices" in report_data:
      for inv in report_data["trucks_invoices"]:
        t_id = inv.get("truck_id")
        inv["truck_name"] = trucks_map.get(
            t_id, t_id if t_id else "غير محددة"
        )

    return jsonify({"success": True, "report": report_data})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/get_products_json", methods=["GET"])
@login_required
def api_get_products_json():
  try:
    raw_products = get_all_products()
    list_data = []
    for p in raw_products:
      list_data.append({
          "name": p[0],
          "price": p[1],
          "wholesale_price": p[2] if len(p) > 2 else 0.0,
          "stock": p[3] if len(p) > 3 else p[2],
          "unit": p[4] if len(p) > 4 else "piece",
          "image_path": p[5] if len(p) > 5 else "default.png",
          "category": p[6] if len(p) > 6 else "bread",
      })
    return jsonify({"success": True, "products": list_data})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/add_product", methods=["POST"])
@permission_required("products")
def api_add_product():
  data = request.json
  name = data.get("name")
  price = data.get("price")
  wholesale_price = data.get("wholesale_price", 0)
  stock = data.get("stock", 100)
  unit = data.get("unit", "piece")
  image_path = data.get("image_path", "fino.png")

  if name and price is not None:
    try:
      if float(price) < 0 or float(stock) < 0:
        return jsonify({"success": False, "error": "السعر أو المخزون لا يمكن أن يكون سالباً"})

      add_product(
          name,
          float(price),
          float(wholesale_price),
          int(stock),
          unit,
          image_path,
      )
      return jsonify({"success": True})
    except Exception as e:
      return jsonify({"success": False, "error": str(e)})
  return jsonify({"success": False, "error": "بيانات غير مكتملة"})


@app.route("/delete_product", methods=["POST"])
@permission_required("products")
def api_delete_product():
  data = request.json
  name = data.get("name")
  if name:
    try:
      delete_product(name)
      return jsonify({"success": True})
    except Exception as e:
      return jsonify({"success": False, "error": str(e)})
  return jsonify({"success": False, "error": "اسم المنتج مطلوب"})


@app.route("/update_product", methods=["POST"])
@permission_required("products")
def api_update_product():
  data = request.json
  old_name = data.get("old_name")
  new_name = data.get("new_name")
  price = data.get("price")
  wholesale_price = data.get("wholesale_price", 0)
  stock = data.get("stock")
  unit = data.get("unit", "piece")

  if old_name and new_name and price is not None and stock is not None:
    try:
      if float(price) < 0 or float(stock) < 0:
        return jsonify({"success": False, "error": "السعر أو المخزون لا يمكن أن يكون سالباً"})

      update_full_product(
          old_name, new_name, price, wholesale_price, stock, unit
      )
      return jsonify({"success": True})
    except Exception as e:
      return jsonify({"success": False, "error": str(e)})
  return jsonify({"success": False, "error": "بيانات غير مكتملة"})


@app.route("/checkout", methods=["POST"])
@login_required
def api_checkout():
  data = request.json
  cart = data.get("cart", {})

  if not cart:
    return jsonify({"success": False, "error": "الفاتورة فارغة"})

  try:
    products = {p[0]: p[3] for p in get_all_products()}

    for name, item in cart.items():
      required_qty = float(item.get("qty", 0))
      
      if required_qty <= 0:
        return jsonify({"success": False, "error": f"كمية البيع للمنتج ({name}) غير صالحة أو بالسالب"})

      available_stock = products.get(name, 0)

      if required_qty > available_stock:
        return jsonify({
            "success": False,
            "error": (
                f"الكمية المطلوبة من ({name}) تتجاوز المتاح في المخزن! المتاح:"
                f" {available_stock}"
            ),
        })

    update_stock_after_sale(cart)
    return jsonify({
        "success": True,
        "message": "تم الدفع وخصم المخزن وتسجيل المبيعات بنجاح",
    })

  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/daily_report", methods=["GET"])
@permission_required("reports")
def api_daily_report():
  try:
    selected_date = request.args.get("date")
    report_data = get_daily_sales(selected_date)

    sales_dict = {}
    for item in report_data.get("items", []):
      sales_dict[item["name"]] = {"qty": item["qty"], "total": item["total"]}

    return jsonify({
        "success": True,
        "sales": sales_dict,
        "grand_total": report_data.get("grand_total", 0.0),
        "date": report_data.get("date"),
    })
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/add_shop", methods=["POST"])
@login_required
def api_add_shop():
  data = request.json
  name = data.get("name")
  phone = data.get("phone", "")
  address = data.get("address", "")

  if name:
    try:
      add_shop(name, phone, address)
      return jsonify({"success": True})
    except Exception as e:
      return jsonify({"success": False, "error": str(e)})
  return jsonify({"success": False, "error": "اسم المحل مطلوب"})


@app.route("/delete_shop", methods=["POST"])
@admin_required
def api_delete_shop():
  data = request.json
  shop_id = data.get("id")
  if shop_id:
    try:
      delete_shop(shop_id)
      return jsonify({"success": True})
    except Exception as e:
      return jsonify({"success": False, "error": str(e)})
  return jsonify({"success": False, "error": "معرف المحل مطلوب"})


@app.route("/load_truck", methods=["POST"])
@permission_required("driver")
def api_load_truck():
  data = request.json
  truck_id = data.get("truck_id")
  product_name = data.get("product_id")
  qty = float(data.get("qty", 0))

  if not truck_id or not product_name or qty <= 0:
    return jsonify({"success": False, "error": "بيانات التحميل غير مكتملة أو الكمية سالبة"})

  try:
    success, message = load_truck_inventory(truck_id, product_name, qty)
    if success:
      return jsonify({"success": True, "message": message})
    else:
      return jsonify({"success": False, "error": message})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/get_truck_inventory/<truck_id>", methods=["GET"])
@permission_required("driver")
def api_get_truck_inventory(truck_id):
  try:
    inventory = get_truck_inventory_data(truck_id)
    return jsonify({"success": True, "inventory": inventory})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/return_to_warehouse", methods=["POST"])
@permission_required("driver")
def api_return_to_warehouse():
  data = request.json
  truck_id = data.get("truck_id")
  product_name = data.get("product_name")
  qty = float(data.get("qty", 0))

  if not truck_id or not product_name or qty <= 0:
    return jsonify({"success": False, "error": "بيانات الإرجاع غير مكتملة أو الكمية سالبة"})

  try:
    success, message = return_truck_to_warehouse(truck_id, product_name, qty)
    if success:
      return jsonify({"success": True, "message": message})
    else:
      return jsonify({"success": False, "error": message})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)})


@app.route("/process_store_sale", methods=["POST"])
@permission_required("driver")
def api_process_store_sale():
  data = request.json
  truck_id = data.get("truck_id")
  store_id = data.get("store_id")
  store_name = data.get("store_name")
  items = data.get("items", {})

  if not truck_id or not store_id or not items:
    return jsonify({"success": False, "error": "بيانات الفاتورة غير مكتملة"})

  for item_name, item_info in items.items():
    qty = float(item_info.get("qty", 0))
    if qty <= 0:
      return jsonify({"success": False, "error": f"كمية البيع للمنتج ({item_name}) لا يمكن أن تكون سالبة أو صفر"})

  try:
    success, message = process_store_sale_db(
        truck_id, store_id, store_name, items
    )
    if success:
      return jsonify({"success": True, "message": message})
    else:
      return jsonify({"success": False, "error": message})
  except Exception as e:
    template_error = str(e)
    return jsonify({"success": False, "error": template_error})


@app.route("/get_daily_shop_invoices", methods=["GET"])
@permission_required("driver")
def api_get_daily_shop_invoices():
  try:
    selected_date = request.args.get("date")
    invoices = get_daily_shop_invoices(selected_date)
    trucks_map = {t["id"]: t["name"] for t in TRUCKS_LIST}

    for inv in invoices:
      t_id = inv.get("truckid")
      inv["truck_name"] = trucks_map.get(t_id, t_id if t_id else "غير محددة")

    return jsonify({"success": True, "invoices": invoices})
  except Exception as data_error:
    backend_error = str(data_error)
    return jsonify({"success": False, "error": backend_error})


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port, debug=False)
  