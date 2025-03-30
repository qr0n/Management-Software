from flask import Flask, render_template, request, jsonify
import os
import PIL.Image
from werkzeug.utils import secure_filename
import mysql.connector
import google.generativeai as genai
import json
from collections import defaultdict

app = Flask(__name__)

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "iron",
    "database": "inventory",
}

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

genai.configure(api_key="AIzaSyDvIVXJdduW2QI6X9N1cojkDSfKECMSq1k")
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

UPLOAD_FOLDER = "static/invoices"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def clean_json(nasty_json: str):
    """
    Description:
    This function cleans the potentially dirty json by removing the markdown

    Arguments:
    nasty_json : str

    Returns:
    nasty_json : dict
    """
    print("type nasty", type(nasty_json))
    if nasty_json.startswith("```json") and nasty_json.endswith("```"):
        return json.loads(nasty_json[7:-3])
    else:
        return json.loads(nasty_json)  # Assumed to be clean.. lol


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_inventory", methods=["GET"])
def get_inventory():
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM stock ORDER BY id")
        items = cursor.fetchall()
    return jsonify(items)


@app.route("/add_item", methods=["POST"])
def add_item():
    data = request.json
    try:
        sql = """
            INSERT INTO stock (item_code, item_name, item_quantity, cost_per_item, profit_percentage)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (
            data["code"],
            data["name"],
            data["quantity"],
            data["cost"],
            data["profit"],
        )

        with conn.cursor() as cursor:
            cursor.execute(sql, values)
            conn.commit()

        return jsonify({"message": "Item added successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/remove_item", methods=["POST"])
def remove_item():
    data = request.json
    try:
        item_name = data["name"]
        remove_quantity = int(data["quantity"])

        with conn.cursor() as cursor:
            # Check current stock
            cursor.execute(
                "SELECT item_quantity FROM stock WHERE item_name = %s", (item_name,)
            )
            result = cursor.fetchone()

            if result:
                current_stock = result[0]

                if remove_quantity >= current_stock:
                    # If removing more than or equal to stock, delete the item
                    cursor.execute(
                        "DELETE FROM stock WHERE item_name = %s", (item_name,)
                    )
                    message = f"Item '{item_name}' removed from inventory."
                else:
                    # Otherwise, subtract from the stock
                    cursor.execute(
                        "UPDATE stock SET item_quantity = item_quantity - %s WHERE item_name = %s",
                        (remove_quantity, item_name),
                    )
                    message = f"Removed {remove_quantity} of '{item_name}'. New stock: {current_stock - remove_quantity}"

                conn.commit()
                return jsonify({"message": message}), 200
            else:
                return jsonify({"error": "Item not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/edit_item", methods=["POST"])
def edit_item():
    data = request.json
    try:
        item_code = data["item_code"]  # Use item_code instead of item_name
        new_name = data["name"]
        new_quantity = int(data["quantity"])
        new_cost = float(data["cost"])
        new_profit = float(data["profit"])

        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE stock 
                SET item_name = %s, item_quantity = %s, cost_per_item = %s, profit_percentage = %s
                WHERE item_code = %s
                """,
                (new_name, new_quantity, new_cost, new_profit, item_code),
            )
            conn.commit()

        return jsonify({"message": f"Item '{new_name}' updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/delete_item", methods=["POST"])
def delete_item():
    data = request.json
    try:
        item_code = data["item_code"]  # Identify item by code

        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM stock WHERE item_code = %s", (item_code,))
            conn.commit()

        return (
            jsonify({"message": f"Item with code {item_code} deleted successfully"}),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/import_invoice", methods=["POST"])
def import_invoice():
    if "invoice" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["invoice"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    # Send image to Gemini for text extraction
    img_file = PIL.Image.open(file_path)
    response = model.generate_content(
        [
            'Extract the data from this image and structure it in the following JSON dictionary: {"data" : [{"name" : <STRING>, "quantity" : <INTEGER>, "price" : <FLOAT>}]}',
            img_file,
        ],
        generation_config={"temperature": 0},
    )

    # Aggregate items by name
    aggregated_data = defaultdict(lambda: {"quantity": 0, "price": 0.0})

    for item in clean_json(response.text)["data"]:
        name = item["name"]
        aggregated_data[name]["quantity"] += item["quantity"]
        aggregated_data[name]["price"] = item["price"]  # Keep last seen price

    # Convert aggregated data to a list
    processed_data = [
        {"name": name, "quantity": details["quantity"], "price": details["price"]}
        for name, details in aggregated_data.items()
    ]

    return jsonify({"data": processed_data}), 200


@app.route("/confirm_import", methods=["POST"])
def confirm_import():
    data = request.json
    items = data.get("items", [])

    if not items:
        return jsonify({"error": "No items to import"}), 400

    try:
        with conn.cursor() as cursor:
            for item in items:
                cursor.execute(
                    """
                    INSERT INTO stock (item_code, item_name, item_quantity, cost_per_item, profit_percentage)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (
                        item["item_code"],  # Fixed: Correct key
                        item["name"],
                        item["quantity"],
                        item["price"],
                        item["profit_percentage"],  # Fixed: Insert correct value
                    ),
                )

        conn.commit()

        # Log successfully imported items
        with open("log.txt", "a") as log:  # Use "a" to append instead of overwrite
            log.write(str(items) + "\n")

        return jsonify({"message": "Inventory updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
