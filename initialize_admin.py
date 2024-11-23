import hashlib
import mysql.connector

# Connect to your database
connection = mysql.connector.connect(
    user='root',
    password='sql_my1country',
    host='localhost',
    database='sample'
)
cursor = connection.cursor()

# Check if admin user already exists
cursor.execute("SELECT id FROM users WHERE username = 'admin'")
admin_exists = cursor.fetchone()

if not admin_exists:
    # Hash the password
    hashed_password = hashlib.sha256('admin_password'.encode()).hexdigest()

    # Insert the admin user
    cursor.execute("""
        INSERT INTO users (username, password, email, is_admin) 
        VALUES ('admin', %s, 'admin@example.com', TRUE)
    """, (hashed_password,))
    connection.commit()
    print("Admin user created successfully.")
else:
    print("Admin user already exists.")

cursor.close()
connection.close()
