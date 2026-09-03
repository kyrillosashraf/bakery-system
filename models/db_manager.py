from datetime import datetime
import json
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash


def get_connection():
  return sqlite3.connect("database.db")


def create_tables():
  conn = get_connection()
  cursor = conn.cursor()

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            wholesale_price REAL DEFAULT 0.0,
            stock INTEGER NOT NULL,
            unit TEXT DEFAULT 'piece',
            image_path TEXT DEFAULT 'default.png',
            category TEXT DEFAULT 'bread'
        )
    """)

  try:
    cursor.execute(
        "ALTER TABLE products ADD COLUMN wholesale_price REAL DEFAULT 0.0;"
    )
  except sqlite3.OperationalError:
    pass

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount REAL NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            total_price REAL NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS driver_loads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_name TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS truck_inventory (
            truck_id TEXT,
            product_name TEXT,
            qty REAL NOT NULL,
            price REAL NOT NULL,
            unit TEXT,
            PRIMARY KEY(truck_id, product_name)
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS driver_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_name TEXT NOT NULL,
            shop_name TEXT NOT NULL,
            product_name TEXT NOT NULL,
            qty_sent REAL NOT NULL,
            wholesale_price REAL NOT NULL,
            qty_returned REAL DEFAULT 0,
            status TEXT DEFAULT 'pending',
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER,
            store_name TEXT NOT NULL,
            truck_id TEXT NOT NULL,
            items_details TEXT NOT NULL,
            total_amount REAL NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT NOT NULL,
            cost REAL NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS general_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_type TEXT NOT NULL,
            amount REAL NOT NULL,
            notes TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cashier_name TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            starting_cash REAL DEFAULT 0.0,
            expected_sales REAL DEFAULT 0.0,
            actual_cash REAL,
            status TEXT DEFAULT 'open'
        )
    """)

  # جدول الخامات الدائم في قاعدة البيانات
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            quantity REAL NOT NULL DEFAULT 0.0,
            unit TEXT DEFAULT 'كيلو (Kg)',
            cost_price REAL NOT NULL DEFAULT 0.0,
            min_limit REAL DEFAULT 10.0
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'cashier',
            permissions TEXT DEFAULT ''
        )
    """)

  try:
    cursor.execute("ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT '';")
  except sqlite3.OperationalError:
    pass

  conn.commit()
  conn.close()


def seed_data():
  conn = get_connection()
  cursor = conn.cursor()

  cursor.execute("SELECT count(*) FROM products")
  if cursor.fetchone()[0] == 0:
    products = [
        ("فينو", 2.0, 1.75, 1000, "piece", "fino.png", "bread"),
        ("عيش بالرده", 2, 1.75, 1000, "piece", "عيش مدور.png", "bread"),
        ("عيش حبه كامله", 2, 1.75, 1000, "piece", "عيش حبه.png", "bread"),
        ("كيس باجيت", 9, 10, 1000, "piece", "كيس_باجيت.png", "bread"),
        ("كيزر", 9.0, 8.0, 1000, "piece", "kaizer.png", "bread"),
        ("بقسماط", 80.0, 70.0, 1000, "kg", "baqsamat.png", "nawashef"),
        ("توست اسمر", 80.0, 70.0, 1000, "piece", "توست_اسمر.png", "bread"),
        ("توست", 80.0, 70.0, 1000, "piece", "toast.png", "bread"),
        ("كروسون", 10.0, 8.5, 1000, "piece", "croissant.png", "pastries"),
        ("فطير", 10.0, 8.5, 1000, "piece", "fطير.png", "pastries"),
        ("حلويات شرقيه", 120.0, 105.0, 1000, "kg", "حلويات.png", "pastries"),
        ("مقرمشات", 120.0, 105.0, 1000, "kg", "مقرمشات.png", "nawashef"),
        ("طبق ", 15.0, 13, 1000, "piece", "طبق.png", "pastries"),
        ("حجازية ", 100.0, 90.0, 1000, "kg", "حجازيه.png", "pastries"),
        ("هريسه ", 100.0, 90.0, 1000, "kg", "هريسه.png", "pastries"),
        ("معموله ", 100.0, 90.0, 1000, "kg", "معموله.png", "nawashef"),
        ("مانيه عجوه وملبن ", 100.0, 90.0, 1000, "kg", "مانيه عجوه وملبن .png", "nawashef"),
        ("قطعه ب5 ", 5, 5, 1000, "piece", "5.png", "nawashef"),
        ("علبه حلويات", 120.0, 105.0, 1000, "kg", "علبه حلويات.png.png", "pastries"),

    ]
    cursor.executemany(
        "INSERT INTO products (name, price, wholesale_price, stock, unit,"
        " image_path, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
        products,
    )
    conn.commit()

  cursor.execute("SELECT count(*) FROM raw_materials")
  if cursor.fetchone()[0] == 0:
    initial_raws = [
        ("دقيق ابودنقل", 40.0, "شكارة (Bag)", 450.0, 30.0),
        ("سكر أبيض مطحون", 80.0, "كيلو (Kg)", 35.0, 15.0),
        ("زيت خليط", 45.0, "لتر (Liter)", 65.0, 10.0),
        ("خميرة فوريّة", 12.0, "كيلو (Kg)", 120.0, 5.0),
        ("سكر خرز", 100.0, "كيلو (Kg)", 30.0, 20.0),
        ("زبدة", 100.0, "كيلو (Kg)", 150.0, 20.0),
    ]
    cursor.executemany(
        "INSERT INTO raw_materials (name, quantity, unit, cost_price,"
        " min_limit) VALUES (?, ?, ?, ?, ?)",
        initial_raws,
    )
    conn.commit()

  cursor.execute("SELECT count(*) FROM users")
  if cursor.fetchone()[0] == 0:
    default_users = [
        ("admin", generate_password_hash("1234"), "admin", "all"),
        ("cashier", generate_password_hash("1234"), "cashier", ""),
    ]
    cursor.executemany(
        "INSERT INTO users (username, password, role, permissions) VALUES (?, ?,"
        " ?, ?)",
        default_users,
    )
    conn.commit()

  conn.close()


def authenticate_user(username, password):
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT username, password, role, permissions FROM users WHERE username = ?",
      (username,),
  )
  user = cursor.fetchone()
  conn.close()

  if user and check_password_hash(user[1], password):
    return {"username": user[0], "role": user[2], "permissions": user[3]}
  return None


def get_all_products():
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT name, price, wholesale_price, stock, unit, image_path, category"
      " FROM products"
  )
  products = cursor.fetchall()
  conn.close()
  return products


def add_product(
    name,
    price,
    wholesale_price=0.0,
    stock=100,
    unit="piece",
    image_path="fino.png",
    category="bread",
):
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO products (name, price, wholesale_price, stock, unit,"
      " image_path, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
      (
          name,
          float(price),
          float(wholesale_price),
          int(stock),
          unit,
          image_path,
          category,
      ),
  )
  conn.commit()
  conn.close()


def delete_product(name):
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("DELETE FROM products WHERE name = ?", (name,))
  conn.commit()
  conn.close()


def update_full_product(
    old_name, new_name, price, wholesale_price, stock, unit
):
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute(
      "UPDATE products SET name = ?, price = ?, wholesale_price = ?, stock = ?,"
      " unit = ? WHERE name = ?",
      (
          new_name,
          float(price),
          float(wholesale_price),
          int(stock),
          unit,
          old_name,
      ),
  )
  conn.commit()
  conn.close()


def update_stock_after_sale(cart_items):
  conn = get_connection()
  cursor = conn.cursor()
  sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  for name, item in cart_items.items():
    qty_sold = item["qty"]
    price = item["price"]
    total_price = qty_sold * price

    cursor.execute(
        "UPDATE products SET stock = stock - ? WHERE name = ?",
        (qty_sold, name),
    )
    cursor.execute(
        "INSERT INTO invoice_items (product_name, quantity, total_price,"
        " sale_date) VALUES (?, ?, ?, ?)",
        (name, qty_sold, total_price, sale_date),
    )

  conn.commit()
  conn.close()


def get_daily_sales(target_date=None):
  conn = get_connection()
  cursor = conn.cursor()

  query_date = (
      target_date if target_date else datetime.now().strftime("%Y-%m-%d")
  )

  cursor.execute(
      """
        SELECT product_name, SUM(quantity), SUM(total_price) 
        FROM invoice_items 
        WHERE DATE(sale_date) = ? 
        GROUP BY product_name
    """,
      (query_date,),
  )
  rows = cursor.fetchall()

  cursor.execute(
      """
        SELECT SUM(total_price) 
        FROM invoice_items 
        WHERE DATE(sale_date) = ?
    """,
      (query_date,),
  )
  grand_total_res = cursor.fetchone()[0]
  grand_total = grand_total_res if grand_total_res else 0.0

  conn.close()

  items = [{"name": r[0], "qty": r[1], "total": r[2]} for r in rows]
  return {"items": items, "grand_total": grand_total, "date": query_date}


def get_custom_report(start_date, end_date):
  conn = get_connection()
  cursor = conn.cursor()

  cursor.execute(
      """
        SELECT product_name, SUM(quantity), SUM(total_price) 
        FROM invoice_items 
        WHERE DATE(sale_date) BETWEEN ? AND ? 
        GROUP BY product_name
    """,
      (start_date, end_date),
  )
  retail_rows = cursor.fetchall()

  cursor.execute(
      """
        SELECT SUM(total_price) 
        FROM invoice_items 
        WHERE DATE(sale_date) BETWEEN ? AND ?
    """,
      (start_date, end_date),
  )
  retail_total = cursor.fetchone()[0] or 0.0

  cursor.execute(
      """
        SELECT id, store_name, truck_id, items_details, total_amount, sale_date 
        FROM shop_invoices 
        WHERE DATE(sale_date) BETWEEN ? AND ?
    """,
      (start_date, end_date),
  )
  truck_rows = cursor.fetchall()

  trucks_invoices = []
  trucks_total = 0.0
  for r in truck_rows:
    inv_total = r[4]
    trucks_total += inv_total
    trucks_invoices.append({
        "id": r[0],
        "store_name": r[1],
        "truck_id": r[2],
        "items": json.loads(r[3]),
        "total_amount": inv_total,
        "date": r[5],
    })

  # --- تعديل استعلام تفاصيل وإجمالي مصروفات المواد الخام بالفترة ---
  cursor.execute(
      """
        SELECT material_name, SUM(cost) 
        FROM raw_expenses 
        WHERE DATE(date) BETWEEN ? AND ? 
        GROUP BY material_name 
        ORDER BY SUM(cost) DESC
    """,
      (start_date, end_date),
  )
  raw_expense_rows = cursor.fetchall()

  raw_expenses = [
      {"material_name": r[0], "cost": r[1]} for r in raw_expense_rows
  ]

  cursor.execute(
      """
        SELECT SUM(cost) 
        FROM raw_expenses 
        WHERE DATE(date) BETWEEN ? AND ?
    """,
      (start_date, end_date),
  )
  raw_expenses_total = cursor.fetchone()[0] or 0.0
  # -------------------------------------------------------------

  cursor.execute(
      """
        SELECT SUM(amount) 
        FROM general_expenses 
        WHERE DATE(date) BETWEEN ? AND ?
    """,
      (start_date, end_date),
  )
  general_expenses_total = cursor.fetchone()[0] or 0.0

  conn.close()

  retail_items = [{"name": r[0], "qty": r[1], "total": r[2]} for r in retail_rows]

  return {
      "retail_items": retail_items,
      "retail_total": retail_total,
      "trucks_total": trucks_total,
      "trucks_invoices": trucks_invoices,
      "raw_expenses": raw_expenses,  # أضفنا قائمة التفاصيل هنا
      "raw_expenses_total": raw_expenses_total,
      "general_expenses_total": general_expenses_total,
      "net_profit": (retail_total + trucks_total)
      - (raw_expenses_total + general_expenses_total),
  }


def add_shop(name, phone, address):
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO shops (name, phone, address) VALUES (?, ?, ?)",
      (name, phone or "", address or ""),
  )
  conn.commit()
  conn.close()


def get_all_shops():
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, phone, address FROM shops")
  shops = cursor.fetchall()
  conn.close()
  return shops


def delete_shop(shop_id):
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("DELETE FROM shops WHERE id = ?", (shop_id,))
  conn.commit()
  conn.close()


def load_truck_inventory(truck_id, product_name, qty):
  conn = get_connection()
  cursor = conn.cursor()

  cursor.execute(
      "SELECT stock, wholesale_price, unit FROM products WHERE name = ?",
      (product_name,),
  )
  prod = cursor.fetchone()

  if not prod:
    conn.close()
    return False, "المنتج غير موجود في المخزن الرئيسي"

  current_stock, wholesale_price, unit = prod[0], prod[1], prod[2]

  if current_stock < qty:
    conn.close()
    return False, f"الكمية المتاحة بالمخزن ({current_stock}) لا تكفي!"

  new_stock = current_stock - qty
  cursor.execute(
      "UPDATE products SET stock = ? WHERE name = ?", (new_stock, product_name)
  )

  cursor.execute(
      "SELECT qty FROM truck_inventory WHERE truck_id = ? AND product_name ="
      " ?",
      (truck_id, product_name),
  )
  existing = cursor.fetchone()

  if existing:
    new_qty = existing[0] + qty
    cursor.execute(
        "UPDATE truck_inventory SET qty = ? WHERE truck_id = ? AND"
        " product_name = ?",
        (new_qty, truck_id, product_name),
    )
  else:
    cursor.execute(
        "INSERT INTO truck_inventory (truck_id, product_name, qty, price, unit)"
        " VALUES (?, ?, ?, ?, ?)",
        (truck_id, product_name, qty, wholesale_price, unit),
    )

  conn.commit()
  conn.close()
  return True, "تم التحميل بنجاح بسعر الجملة"


def get_truck_inventory_data(truck_id):
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT product_name, qty, price, unit FROM truck_inventory WHERE"
      " truck_id = ?",
      (truck_id,),
  )
  rows = cursor.fetchall()
  conn.close()

  inventory = {}
  for r in rows:
    inventory[r[0]] = {"qty": r[1], "price": r[2], "unit": r[3]}
  return inventory


def return_truck_to_warehouse(truck_id, product_name, qty):
  conn = get_connection()
  cursor = conn.cursor()

  try:
    cursor.execute(
        "SELECT qty FROM truck_inventory WHERE truck_id = ? AND product_name ="
        " ?",
        (truck_id, product_name),
    )
    row = cursor.fetchone()

    if not row or row[0] < qty:
      conn.close()
      return False, "الكمية المطلوبة إرجاعها غير موجودة في عهدة العربية!"

    current_truck_qty = row[0]
    new_truck_qty = current_truck_qty - qty

    if new_truck_qty == 0:
      cursor.execute(
          "DELETE FROM truck_inventory WHERE truck_id = ? AND product_name = ?",
          (truck_id, product_name),
      )
    else:
      cursor.execute(
          "UPDATE truck_inventory SET qty = ? WHERE truck_id = ? AND"
          " product_name = ?",
          (new_truck_qty, truck_id, product_name),
      )

    cursor.execute(
        "UPDATE products SET stock = stock + ? WHERE name = ?",
        (qty, product_name),
    )

    conn.commit()
    conn.close()
    return True, "تم إرجاع البضاعة بنجاح إلى مخزن الفرن الرئيسي"
  except Exception as e:
    conn.rollback()
    conn.close()
    return False, str(e)


def process_store_sale_db(truck_id, store_id, store_name, items):
  conn = get_connection()
  cursor = conn.cursor()

  try:
    today_date = datetime.now().strftime("%Y-%m-%d")
    sale_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
            SELECT id, items_details, total_amount FROM shop_invoices 
            WHERE store_id = ? AND truck_id = ? AND DATE(sale_date) = ?
        """,
        (store_id, truck_id, today_date),
    )
    existing_invoice = cursor.fetchone()

    for product_name, details in items.items():
      qty_sold = float(details["qty"])
      if qty_sold <= 0:
        continue

      cursor.execute(
          "SELECT qty FROM truck_inventory WHERE truck_id = ? AND product_name"
          " = ?",
          (truck_id, product_name),
      )
      row = cursor.fetchone()

      if not row or row[0] < qty_sold:
        conn.close()
        return (
            False,
            f"الكمية المتاحة من ({product_name}) في عهدة العربية لا تكفي!",
        )

      current_qty = row[0]
      new_qty = current_qty - qty_sold

      if new_qty == 0:
        cursor.execute(
            "DELETE FROM truck_inventory WHERE truck_id = ? AND product_name ="
            " ?",
            (truck_id, product_name),
        )
      else:
        cursor.execute(
            "UPDATE truck_inventory SET qty = ? WHERE truck_id = ? AND"
            " product_name = ?",
            (new_qty, truck_id, product_name),
        )

    if existing_invoice:
      inv_id, old_items_json, old_total = existing_invoice
      old_items = json.loads(old_items_json)

      for product_name, details in items.items():
        qty_sold = float(details["qty"])
        price = float(details["price"])
        if qty_sold <= 0:
          continue

        if product_name in old_items:
          old_items[product_name]["qty"] += qty_sold
        else:
          old_items[product_name] = {
              "qty": qty_sold,
              "price": price,
              "unit": details.get("unit", "piece"),
          }

      new_total_amount = sum(
          float(item["qty"]) * float(item["price"])
          for item in old_items.values()
      )
      updated_items_json = json.dumps(old_items, ensure_ascii=False)

      cursor.execute(
          """
                UPDATE shop_invoices 
                SET items_details = ?, total_amount = ? 
                WHERE id = ?
            """,
          (updated_items_json, new_total_amount, inv_id),
      )

    else:
      total_invoice_amount = sum(
          float(details["qty"]) * float(details["price"])
          for details in items.values()
          if float(details["qty"]) > 0
      )
      items_json = json.dumps(items, ensure_ascii=False)
      cursor.execute(
          """
                INSERT INTO shop_invoices (store_id, store_name, truck_id, items_details, total_amount, sale_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
          (
              store_id,
              store_name,
              truck_id,
              items_json,
              total_invoice_amount,
              sale_timestamp,
          ),
      )

    conn.commit()
    conn.close()
    return True, "تم تسجيل الفاتورة بسعر الجملة بنجاح وخصمها من عهدة العربية"
  except Exception as e:
    conn.rollback()
    conn.close()
    return False, str(e)


def get_daily_shop_invoices(target_date=None):
  conn = get_connection()
  cursor = conn.cursor()

  query_date = (
      target_date if target_date else datetime.now().strftime("%Y-%m-%d")
  )

  cursor.execute(
      """
        SELECT id, store_name, truck_id, items_details, total_amount, sale_date 
        FROM shop_invoices 
        WHERE DATE(sale_date) = ?
    """,
      (query_date,),
  )
  rows = cursor.fetchall()
  conn.close()

  invoices = []
  for r in rows:
    invoices.append({
        "id": r[0],
        "store_name": r[1],
        "truck_id": r[2],
        "items": json.loads(r[3]),
        "total_amount": r[4],
        "date": r[5],
    })
  return invoices


def get_all_raw_materials():
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, name, quantity, unit, cost_price, min_limit FROM"
      " raw_materials"
  )
  rows = cursor.fetchall()
  conn.close()

  materials = []
  for r in rows:
    materials.append({
        "id": str(r[0]),
        "name": r[1],
        "quantity": r[2],
        "unit": r[3],
        "cost_price": r[4],
        "min_limit": r[5],
    })
  return materials


def add_raw_material_db(name, quantity, unit, cost_price, min_limit):
  conn = get_connection()
  cursor = conn.cursor()
  try:
    cursor.execute(
        """
            INSERT INTO raw_materials (name, quantity, unit, cost_price, min_limit)
            VALUES (?, ?, ?, ?, ?)
        """,
        (
            name,
            float(quantity),
            unit,
            float(cost_price),
            float(min_limit),
        ),
    )
    conn.commit()
    return True, "تم إضافة الخامة بنجاح"
  except Exception as e:
    return False, str(e)
  finally:
    conn.close()


def update_raw_stock_db(item_id, amount):
  conn = get_connection()
  cursor = conn.cursor()
  try:
    cursor.execute(
        "SELECT name, quantity, cost_price FROM raw_materials WHERE id = ?",
        (item_id,),
    )
    item = cursor.fetchone()
    if not item:
      conn.close()
      return False, "الخامة غير موجودة", "", 0.0

    name, current_qty, cost_price = item[0], item[1], item[2]
    new_qty = current_qty + amount
    if new_qty < 0:
      new_qty = 0.0

    cursor.execute(
        "UPDATE raw_materials SET quantity = ? WHERE id = ?", (new_qty, item_id)
    )
    conn.commit()
    conn.close()
    return True, "Success", name, cost_price
  except Exception as e:
    conn.close()
    return False, str(e), "", 0.0


def update_raw_material_db(item_id, name, unit, cost_price, min_limit):
  conn = get_connection()
  cursor = conn.cursor()
  try:
    cursor.execute(
        """
            UPDATE raw_materials 
            SET name = ?, unit = ?, cost_price = ?, min_limit = ? 
            WHERE id = ?
        """,
        (name, unit, float(cost_price), float(min_limit), item_id),
    )
    conn.commit()
    return True
  except Exception as e:
    return False
  finally:
    conn.close()


def delete_raw_material_db(item_id):
  conn = get_connection()
  cursor = conn.cursor()
  try:
    cursor.execute("DELETE FROM raw_materials WHERE id = ?", (item_id,))
    conn.commit()
    return True
  except Exception as e:
    return False
  finally:
    conn.close()


def add_raw_expense(material_name, cost, expense_date=None):
  conn = get_connection()
  cursor = conn.cursor()
  exp_date = (
      expense_date
      if expense_date
      else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  )
  cursor.execute(
      "INSERT INTO raw_expenses (material_name, cost, date) VALUES (?, ?, ?)",
      (material_name, float(cost), exp_date),
  )
  conn.commit()
  conn.close()


def get_raw_expenses_by_date(target_date=None):
  conn = get_connection()
  cursor = conn.cursor()
  query_date = (
      target_date if target_date else datetime.now().strftime("%Y-%m-%d")
  )

  cursor.execute(
      """
        SELECT SUM(cost) 
        FROM raw_expenses 
        WHERE DATE(date) = ?
    """,
      (query_date,),
  )

  res = cursor.fetchone()[0]
  total = res if res else 0.0
  conn.close()
  return total


def add_general_expense(expense_type, amount, notes="", expense_date=None):
  conn = get_connection()
  cursor = conn.cursor()
  exp_date = (
      expense_date
      if expense_date
      else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  )
  cursor.execute(
      "INSERT INTO general_expenses (expense_type, amount, notes, date) VALUES"
      " (?, ?, ?, ?)",
      (expense_type, float(amount), notes, exp_date),
  )
  conn.commit()
  conn.close()


def get_general_expenses_by_date(target_date=None):
  conn = get_connection()
  cursor = conn.cursor()
  query_date = (
      target_date if target_date else datetime.now().strftime("%Y-%m-%d")
  )

  cursor.execute(
      """
        SELECT id, expense_type, amount, notes, date 
        FROM general_expenses 
        WHERE DATE(date) = ?
    """,
      (query_date,),
  )
  rows = cursor.fetchall()

  cursor.execute(
      """
        SELECT SUM(amount) 
        FROM general_expenses 
        WHERE DATE(date) = ?
    """,
      (query_date,),
  )
  total_res = cursor.fetchone()[0]
  total = total_res if total_res else 0.0

  conn.close()
  expenses = [{
      "id": r[0],
      "expense_type": r[1],
      "amount": r[2],
      "notes": r[3],
      "date": r[4],
  } for r in rows]
  return {"expenses": expenses, "total": total}


def delete_general_expense(expense_id):
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("DELETE FROM general_expenses WHERE id = ?", (expense_id,))
  conn.commit()
  conn.close()


def start_new_shift(cashier_name, starting_cash):
  conn = get_connection()
  cursor = conn.cursor()

  cursor.execute("SELECT id FROM shifts WHERE status = 'open'")
  if cursor.fetchone():
    conn.close()
    return False, "توجد وردية مفتوحة بالفعل! يجب إغلاقها أولاً."

  start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  cursor.execute(
      """
        INSERT INTO shifts (cashier_name, start_time, starting_cash, status) 
        VALUES (?, ?, ?, 'open')
    """,
      (cashier_name, start_time, float(starting_cash)),
  )

  conn.commit()
  conn.close()
  return True, "تم فتح الوردية بنجاح"


def get_active_shift():
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, cashier_name, start_time, starting_cash FROM shifts WHERE"
      " status = 'open'"
  )
  row = cursor.fetchone()
  conn.close()

  if row:
    return {
        "id": row[0],
        "cashier_name": row[1],
        "start_time": row[2],
        "starting_cash": row[3],
    }
  return None


def end_active_shift(actual_cash):
  conn = get_connection()
  cursor = conn.cursor()

  cursor.execute(
      "SELECT id, start_time, starting_cash FROM shifts WHERE status = 'open'"
  )
  row = cursor.fetchone()

  if not row:
    conn.close()
    return False, "لا توجد وردية مفتوحة حالياً!"

  shift_id, start_time, starting_cash = row[0], row[1], row[2]

  cursor.execute(
      """
        SELECT SUM(total_price) 
        FROM invoice_items 
        WHERE sale_date >= ?
    """,
      (start_time,),
  )
  res = cursor.fetchone()[0]
  expected_sales = res if res else 0.0

  end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  cursor.execute(
      """
        UPDATE shifts 
        SET end_time = ?, expected_sales = ?, actual_cash = ?, status = 'closed' 
        WHERE id = ?
    """,
      (end_time, expected_sales, float(actual_cash), shift_id),
  )

  conn.commit()
  conn.close()

  difference = float(actual_cash) - (starting_cash + expected_sales)
  return True, {
      "expected_sales": expected_sales,
      "starting_cash": starting_cash,
      "actual_cash": actual_cash,
      "difference": difference,
  }
