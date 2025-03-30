from flask import Flask, render_template, request, jsonify
import os
import PIL.Image
from werkzeug.utils import secure_filename
import google.genai as genai
import json
from collections import defaultdict
from functions import clean_json

app = Flask(__name__)

# Replace MySQL with JSON file handling
INVENTORY_FILE = "data/inventory.json"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Create inventory file if it doesn't exist
if not os.path.exists(INVENTORY_FILE):
    with open(INVENTORY_FILE, "w") as f:
        json.dump({"items": []}, f)


def get_inventory_data():
    with open(INVENTORY_FILE, "r") as f:
        return json.load(f)


def save_inventory_data(data):
    with open(INVENTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)


model = genai.Client(api_key="").models
# model = genai.Client(model_name="gemini-1.5-flash")

UPLOAD_FOLDER = "static/invoices"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_inventory", methods=["GET"])
def get_inventory():
    inventory = get_inventory_data()
    return jsonify(inventory["items"])


@app.route("/add_item", methods=["POST"])
def add_item():
    data = request.json
    try:
        inventory = get_inventory_data()
        new_item = {
            "item_code": data["code"],
            "item_name": data["name"],
            "item_quantity": data["quantity"],
            "cost_per_item": data["cost"],
            "profit_percentage": data["profit"],
        }
        inventory["items"].append(new_item)
        save_inventory_data(inventory)
        return jsonify({"message": "Item added successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/remove_item", methods=["POST"])
def remove_item():
    data = request.json
    try:
        inventory = get_inventory_data()
        items = inventory["items"]
        item_name = data["name"]
        remove_quantity = int(data["quantity"])

        for item in items:
            if item["item_name"] == item_name:
                if remove_quantity >= item["item_quantity"]:
                    items.remove(item)
                    message = f"Item '{item_name}' removed from inventory."
                else:
                    item["item_quantity"] -= remove_quantity
                    message = f"Removed {remove_quantity} of '{item_name}'. New stock: {item['item_quantity']}"

                save_inventory_data(inventory)
                return jsonify({"message": message}), 200

        return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/edit_item", methods=["POST"])
def edit_item():
    data = request.json
    try:
        inventory = get_inventory_data()
        items = inventory["items"]
        item_code = data["item_code"]

        for item in items:
            if item["item_code"] == item_code:
                item["item_name"] = data["name"]
                item["item_quantity"] = int(data["quantity"])
                item["cost_per_item"] = float(data["cost"])
                item["profit_percentage"] = float(data["profit"])

                save_inventory_data(inventory)
                return jsonify({"message": f"Item updated successfully"}), 200

        return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/delete_item", methods=["POST"])
def delete_item():
    data = request.json
    try:
        inventory = get_inventory_data()
        items = inventory["items"]
        item_code = data["item_code"]

        for item in items:
            if item["item_code"] == item_code:
                items.remove(item)
                save_inventory_data(inventory)
                return (
                    jsonify(
                        {"message": f"Item with code {item_code} deleted successfully"}
                    ),
                    200,
                )

        return jsonify({"error": "Item not found"}), 404
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
        contents=[
            'Extract the data from this image and structure it in the following JSON dictionary: {"data" : [{"name" : <STRING>, "quantity" : <INTEGER>, "price" : <FLOAT>}]}',
            img_file,
        ],
        model="gemini-2.0-flash",
        config={"temperature": 0},
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
        inventory = get_inventory_data()
        existing_items = {item["item_code"]: item for item in inventory["items"]}

        for item in items:
            if item["item_code"] in existing_items:
                # Update existing item
                existing_item = existing_items[item["item_code"]]
                existing_item["item_quantity"] += item["quantity"]
                existing_item["cost_per_item"] = item["price"]
                existing_item["profit_percentage"] = item["profit_percentage"]
            else:
                # Add new item
                inventory["items"].append(
                    {
                        "item_code": item["item_code"],
                        "item_name": item["name"],
                        "item_quantity": item["quantity"],
                        "cost_per_item": item["price"],
                        "profit_percentage": item["profit_percentage"],
                    }
                )

        save_inventory_data(inventory)

        # Log successfully imported items
        with open("log.txt", "a") as log:
            log.write(str(items) + "\n")

        return jsonify({"message": "Inventory updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
