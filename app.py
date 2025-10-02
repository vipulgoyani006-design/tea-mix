from flask import Flask, render_template, request, jsonify
import sqlite3
from itertools import chain, combinations

app = Flask(__name__)
DB_PATH = "database/tea.db"

ingredients_list = ["sugar", "milk", "honey", "lemon", "ginger", "mint", "spices"]

# --- Utilities ---
def powerset_limited(iterable, max_size=3):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(1, min(len(s), max_size)+1))

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS ingredients (id INTEGER PRIMARY KEY, name TEXT UNIQUE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS tea_variants (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS tea_ingredients (tea_id INTEGER, ingredient_id INTEGER)")
    for ing in ingredients_list:
        cursor.execute("INSERT OR IGNORE INTO ingredients (name) VALUES (?)", (ing,))
    conn.commit()
    conn.close()

def create_tea_variant(selected_ingredients):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    name = "Plain tea" if not selected_ingredients else "Tea with " + ", ".join(selected_ingredients)
    cursor.execute("SELECT id FROM tea_variants WHERE name = ?", (name,))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("INSERT INTO tea_variants (name) VALUES (?)", (name,))
    tea_id = cursor.lastrowid
    for ing in selected_ingredients:
        cursor.execute("SELECT id FROM ingredients WHERE name = ?", (ing,))
        ing_id = cursor.fetchone()[0]
        cursor.execute("INSERT INTO tea_ingredients (tea_id, ingredient_id) VALUES (?, ?)", (tea_id, ing_id))
    conn.commit()
    conn.close()
    return True

def create_all_combinations(selected_ingredients, max_size=3):
    created_count = 0
    create_tea_variant([])  # Include plain tea
    for combo in powerset_limited(selected_ingredients, max_size=max_size):
        if create_tea_variant(list(combo)):
            created_count += 1
    return created_count

def get_all_tea_variants():
    conn = sqlite3.connect(DB_PATH)
    df = conn.execute("""
        SELECT tv.name, group_concat(i.name, ', ') AS ingredients
        FROM tea_variants tv
        LEFT JOIN tea_ingredients ti ON tv.id = ti.tea_id
        LEFT JOIN ingredients i ON ti.ingredient_id = i.id
        GROUP BY tv.id
    """).fetchall()
    conn.close()
    return [{"name": row[0], "ingredients": row[1]} for row in df]

# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html", ingredients=ingredients_list)

@app.route("/create", methods=["POST"])
def create():
    data = request.json
    selected = data.get("ingredients", [])
    count = create_all_combinations(selected)
    return jsonify({"created": count, "variants": get_all_tea_variants()})

@app.route("/variants")
def variants():
    return jsonify(get_all_tea_variants())

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
