import json
import mysql.connector
from flask import jsonify

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "iron",
    "database": "inventory",
}

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()


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
        return json.loads(nasty_json)


class Inventory:

    class Display:
        def get_inventory():
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT * FROM stock ORDER BY id")
                items = cursor.fetchall()
            return jsonify(items)

    class Management:
        def add_item(data):
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

        def remove_item(data):
            try:
                item_name = data["name"]
                remove_quantity = int(data["quantity"])

                with conn.cursor() as cursor:
                    # Check current stock
                    cursor.execute(
                        "SELECT item_quantity FROM stock WHERE item_name = %s",
                        (item_name,),
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

        def edit_item(data):
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

                return (
                    jsonify({"message": f"Item '{new_name}' updated successfully"}),
                    200,
                )

            except Exception as e:
                return jsonify({"error": str(e)}), 500
