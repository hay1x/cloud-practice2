import os
import sqlite3
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

DB_PATH = "catalog.db"
API_KEY = os.environ.get("API_KEY", "devkey")

app = Flask(__name__)
CORS(app)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


def check_key():
    # Revisa que la peticion traiga la llave correcta en el encabezado X-API-KEY
    return request.headers.get("X-API-KEY") == API_KEY


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


# CREATE: registrar un producto
@app.route("/products", methods=["POST"])
def create_product():
    if not check_key():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    name = data.get("name")
    price = data.get("price")
    stock = data.get("stock", 0)

    if not name or price is None:
        return jsonify({"error": "name y price son obligatorios"}), 400

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
        (name, float(price), int(stock)),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return jsonify({"id": new_id, "name": name, "price": float(price), "stock": int(stock)}), 201


# READ: consultar todos los productos
@app.route("/products", methods=["GET"])
def list_products():
    if not check_key():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# READ: consultar un solo producto por su id
@app.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    if not check_key():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


# UPDATE: modificar un producto
@app.route("/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    if not check_key():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}

    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "not found"}), 404

    name = data.get("name", row["name"])
    price = float(data.get("price", row["price"]))
    stock = int(data.get("stock", row["stock"]))

    conn.execute(
        "UPDATE products SET name = ?, price = ?, stock = ? WHERE id = ?",
        (name, price, stock, product_id),
    )
    conn.commit()
    conn.close()

    return jsonify({"id": product_id, "name": name, "price": price, "stock": stock})


# DELETE: eliminar un producto
@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    if not check_key():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_db()
    cur = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": product_id})


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
