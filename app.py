from flask import Flask, render_template, request, jsonify
import os
import PIL.Image
from werkzeug.utils import secure_filename
import mysql.connector
import google.generativeai as genai
import json
from collections import defaultdict
from functions import Inventory, clean_json

app = Flask(__name__)

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "iron",
    "database": "inventory",
}

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

genai.configure(api_key="")
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

UPLOAD_FOLDER = "static/invoices"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_inventory", methods=["GET"])
def get_inventory():
    return Inventory.Display.get_inventory()


@app.route("/add_item", methods=["POST"])
def add_item():
    data = request.json
    return Inventory.Management.add_item(data=data)


@app.route("/remove_item", methods=["POST"])
def remove_item():
    data = request.json
    return Inventory.Management.remove_item(data=data)


@app.route("/edit_item", methods=["POST"])
def edit_item():
    data = request.json
    return Inventory.Management.edit_item(data=data)


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
                # Check if the item already exists in the inventory
                cursor.execute(
                    "SELECT item_quantity FROM stock WHERE item_code = %s",
                    (item["item_code"],),
                )
                result = cursor.fetchone()

                if result:
                    # If the item exists, update its quantity
                    current_quantity = result[0]
                    new_quantity = current_quantity + item["quantity"]
                    cursor.execute(
                        """
                        UPDATE stock 
                        SET item_quantity = %s, cost_per_item = %s, profit_percentage = %s
                        WHERE item_code = %s
                        """,
                        (
                            new_quantity,
                            item["price"],
                            item["profit_percentage"],
                            item["item_code"],
                        ),
                    )
                else:
                    # If the item does not exist, insert it as a new item
                    cursor.execute(
                        """
                        INSERT INTO stock (item_code, item_name, item_quantity, cost_per_item, profit_percentage)
                        VALUES (%s, %s, %s, %s, %s);
                        """,
                        (
                            item["item_code"],
                            item["name"],
                            item["quantity"],
                            item["price"],
                            item["profit_percentage"],
                        ),
                    )

        conn.commit()

        # Log successfully imported items
        with open("log.txt", "a") as log:
            log.write(str(items) + "\n")

        return jsonify({"message": "Inventory updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
