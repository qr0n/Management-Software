import mysql.connector

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",  # Replace with your username
    password="iron",  # Replace with your password
)

cursor = db.cursor()

# Create Database if it doesn't exist
cursor.execute("CREATE DATABASE IF NOT EXISTS inventory")

# Reconnect to the MySQL server, this time specifying the database
db.database = "inventory"

cursor.execute(
    """
DROP TABLE IF EXISTS stock;
    """
)

# Create 'stock' Table
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS stock (
        id INT AUTO_INCREMENT PRIMARY KEY,
        item_code VARCHAR(50),
        item_name VARCHAR(255),
        item_quantity INTEGER,
        cost_per_item DOUBLE,
        profit_percentage FLOAT
    )
    """
)

# Create 'restock_list' Table
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS restock_list (
        id INT AUTO_INCREMENT PRIMARY KEY,
        item_name TEXT NOT NULL,
        item_quantity INTEGER NOT NULL,
        cost_per_item FLOAT NOT NULL
    )
    """
)

# Close the cursor and connection
cursor.close()
db.close()
