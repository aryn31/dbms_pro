import streamlit as st
import mysql.connector
import pandas as pd
import hashlib
from datetime import datetime

def connect_to_database():
    try:
        connection = mysql.connector.connect(
            user='root',
            password='sql_my1country',
            host='localhost',
            database='sample'
        )
        cursor = connection.cursor()
        # Create users table with is_admin field
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        cursor.close()
        return connection
    except mysql.connector.Error as e:
        st.error(f"Error connecting to MySQL database: {e}")
        return None

def get_all_tables(mydb):
    try:
        with mydb.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall() if table[0] != 'users']
        return tables 
    
    except mysql.connector.Error as e:
        st.error(f"Error fetching tables: {e}")
        return []

def get_table_data(mydb,tablename):
    try:
        query=f"SELECT * FROM {tablename}"
        df=pd.read_sql(query,mydb)
        return df
    except mysql.connector.Error as e:
        st.error(f"Error fetching data from table {tablename}: {e}")
        return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(connection, username, password):
    try:
        cursor = connection.cursor()
        hashed_password = hash_password(password)
        cursor.execute("SELECT id, username, is_admin FROM users WHERE username = %s AND password = %s", 
                      (username, hashed_password))
        user = cursor.fetchone()
        cursor.close()
        if user:
            return {'id': user[0], 'username': user[1], 'is_admin': user[2]}
        return None
    except mysql.connector.Error as e:
        st.error(f"Authentication error: {e}")
        return None

def create_user(connection, username, password, email, is_admin=False):
    try:
        cursor = connection.cursor()
        hashed_password = hash_password(password)
        cursor.execute("INSERT INTO users (username, password, email, is_admin) VALUES (%s, %s, %s, %s)", 
                      (username, hashed_password, email, is_admin))
        connection.commit()
        cursor.close()
        return True
    except mysql.connector.Error as e:
        if e.errno == 1062:
            st.error("Username or email already exists!")
        else:
            st.error(f"Error creating user: {e}")
        return False

def manage_user(connection):
            # View non-admin users and allow updates
        st.header("Manage Users")
        

        # Fetch all non-admin users
        cursor = connection.cursor()
        cursor.execute("SELECT id, username, email, is_admin FROM users WHERE is_admin = FALSE")
        users = cursor.fetchall()
        cursor.close()
        
        # Display list of non-admin users
        if users:
            selected_user_id = st.selectbox("Select a User to Edit", [user[1] for user in users])
            if selected_user_id:
                # Get the user details based on the selection
                selected_user = next(user for user in users if user[1] == selected_user_id)
                user_id, username, email, is_admin = selected_user
                
                # Display current details
                st.write(f"Username: {username}")
                st.write(f"Email: {email}")
                
                # Edit user details
                new_username = st.text_input("New Username", value=username)
                new_email = st.text_input("New Email", value=email)
                new_password = st.text_input("New Password", type="password")
                new_is_admin = st.checkbox("Grant Admin Privileges", value=is_admin)
                
                if st.button("Update User Details"):
                    try:
                        cursor = connection.cursor()
                        
                        # If a new password is provided, hash it
                        if new_password:
                            hashed_password = hash_password(new_password)
                            cursor.execute("""
                                UPDATE users
                                SET username = %s, email = %s, is_admin = %s, password = %s
                                WHERE id = %s
                            """, (new_username, new_email, new_is_admin, hashed_password, user_id))
                        else:
                            # If no password change, just update the other fields
                            cursor.execute("""
                                UPDATE users
                                SET username = %s, email = %s, is_admin = %s
                                WHERE id = %s
                            """, (new_username, new_email, new_is_admin, user_id))
                        
                        connection.commit()
                        cursor.close()
                        st.success("User details updated successfully!")
                    except mysql.connector.Error as e:
                        st.error(f"Error updating user details: {e}")
        else:
            st.write("No non-admin users found.")

def table_operations(connection):
    # Add other admin operations like table operations
        st.header("Table Operations")
        
        tables = get_all_tables(connection)
        selected_table = st.selectbox("Select Table", tables)
        
        if selected_table:
            operation = st.radio("Select Operation", ["View", "Insert", "Update", "Delete"])
            
            if operation == "View":
                df = get_table_data(connection, selected_table)
                if df is not None:
                    st.dataframe(df)
            
            elif operation == "Insert":
                # Get column names and types
                cursor = connection.cursor()
                cursor.execute(f"DESCRIBE {selected_table}")
                columns = cursor.fetchall()
                cursor.close()
                
                st.subheader(f"Insert into {selected_table}")
                # Create input fields for each column
                values = {}
                for col in columns:
                    col_name = col[0]
                    col_type = col[1]
                    if col_name not in ['id', 'created_at']:  # Skip auto-generated columns
                        if 'int' in col_type:
                            values[col_name] = st.number_input(f"Enter {col_name}", step=1)
                        elif 'float' in col_type or 'double' in col_type:
                            values[col_name] = st.number_input(f"Enter {col_name}", step=0.01)
                        else:
                            values[col_name] = st.text_input(f"Enter {col_name}")
                
                if st.button("Insert Record"):
                    try:
                        cursor = connection.cursor()
                        cols = ', '.join(values.keys())
                        vals = ', '.join(['%s'] * len(values))
                        query = f"INSERT INTO {selected_table} ({cols}) VALUES ({vals})"
                        cursor.execute(query, list(values.values()))
                        connection.commit()
                        cursor.close()
                        st.success("Record inserted successfully!")
                    except mysql.connector.Error as e:
                        st.error(f"Error inserting record: {e}")
            
            elif operation == "Update":
                df = get_table_data(connection, selected_table)
                if df is not None:
                    st.dataframe(df)
                    
                    # Get primary key for the table
                    cursor = connection.cursor()
                    cursor.execute(f"SHOW KEYS FROM {selected_table} WHERE Key_name = 'PRIMARY'")
                    primary_key = cursor.fetchone()[4]  # Column name of primary key
                    
                    # Select record to update
                    record_id = st.number_input(f"Enter {primary_key} of record to update", min_value=1)
                    
                    # Get column names and types
                    cursor.execute(f"DESCRIBE {selected_table}")
                    columns = cursor.fetchall()
                    cursor.close()
                    
                    # Create input fields for each column
                    values = {}
                    for col in columns:
                        col_name = col[0]
                        col_type = col[1]
                        if col_name not in ['id', 'created_at', primary_key]:  # Skip primary key and auto-generated columns
                            if 'int' in col_type:
                                values[col_name] = st.number_input(f"New value for {col_name}", step=1)
                            elif 'float' in col_type or 'double' in col_type:
                                values[col_name] = st.number_input(f"New value for {col_name}", step=0.01)
                            else:
                                values[col_name] = st.text_input(f"New value for {col_name}")
                    
                    if st.button("Update Record"):
                        try:
                            cursor = connection.cursor()
                            set_clause = ', '.join([f"{k} = %s" for k in values.keys()])
                            query = f"UPDATE {selected_table} SET {set_clause} WHERE {primary_key} = %s"
                            cursor.execute(query, list(values.values()) + [record_id])
                            connection.commit()
                            cursor.close()
                            st.success("Record updated successfully!")
                        except mysql.connector.Error as e:
                            st.error(f"Error updating record: {e}")
            
            elif operation == "Delete":
                df = get_table_data(connection, selected_table)
                if df is not None:
                    st.dataframe(df)
                    
                    # Get primary key for the table
                    cursor = connection.cursor()
                    cursor.execute(f"SHOW KEYS FROM {selected_table} WHERE Key_name = 'PRIMARY'")
                    primary_key = cursor.fetchone()[4]
                    cursor.close()
                    
                    # Select record to delete
                    record_id = st.number_input(f"Enter {primary_key} of record to delete", min_value=1)
                    
                    if st.button("Delete Record"):
                        try:
                            cursor = connection.cursor()
                            cursor.execute(f"DELETE FROM {selected_table} WHERE {primary_key} = %s", (record_id,))
                            connection.commit()
                            cursor.close()
                            st.success("Record deleted successfully!")
                        except mysql.connector.Error as e:
                            st.error(f"Error deleting record: {e}")

def admin_panel(connection):
    st.title("Admin Panel")

    menu = ["Manage Users", "Manage Tables"]
    choice = st.sidebar.selectbox("What do you want to do today?", menu)
    
    if(choice == "Manage Users"):
        manage_user(connection)
    else:
        table_operations(connection)

def login_page():
    st.subheader("Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        connection = connect_to_database()
        if connection:
            user = authenticate_user(connection, username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.is_admin = user['is_admin']  # Save admin status in session state
                st.success("Logged in successfully!")
                st.rerun()  # Reload the app to refresh the UI with admin options
            else:
                st.error("Invalid username or password")
            connection.close()

def signup_page():
    st.subheader("Create New Account")
    username = st.text_input("Username", key="signup_username")
    password = st.text_input("Password", type="password", key="signup_password")
    email = st.text_input("Email")
    
    # Admin option checkbox
    is_admin = st.checkbox("Grant Admin Privileges")

    if st.button("Sign Up"):
        if username and password and email:
            mydb = connect_to_database()
            if mydb:
                if create_user(mydb, username, password, email, is_admin):
                    st.success("Account created successfully! Please login.")
                    st.session_state.signup_success = True
                    st.rerun()  # Reload the page to show login option
                mydb.close()
        else:
            st.warning("Please fill all fields!")

def user_view():
    mydb = connect_to_database()
    if mydb:
        tables = get_all_tables(mydb)
        # ... (rest of your existing view data code)
        if tables:
            selected_table = st.selectbox("Select a table to view:", tables)
            if selected_table:
                df = get_table_data(mydb, selected_table)
                if df is not None:
                    st.subheader(f"Data from table: {selected_table}")
                    st.dataframe(df)
                    
                    # Add download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download table as CSV",
                        data=csv,
                        file_name=f"{selected_table}.csv",
                        mime="text/csv"
                    )
                    
                    # Display table information
                    st.subheader("Table Information")
                    st.write(f"Number of Rows: {len(df)}")
                    st.write(f"Number of columns: {len(df.columns)}")
                    st.write("Column names:", ", ".join(df.columns))
        mydb.close()

def main():
    st.title("MySQL Database Explorer")
    
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    
    ##Sidebar for navigation
    if not st.session_state.logged_in:
        menu = ["Login", "Sign Up"]
        choice = st.sidebar.selectbox("Menu", menu)
        
        if choice == "Login":
            login_page()
        else:
            signup_page()
    
    # Main application
    else:
        st.sidebar.success(f"Welcome {st.session_state.username}")
        if st.session_state.is_admin:
            # Admin navigation
            menu = ["View Data", "Admin Panel"]
            choice = st.sidebar.selectbox("Menu", menu)
            
            if choice == "Admin Panel":
                mydb = connect_to_database()
                if mydb:
                    admin_panel(mydb)
                    mydb.close()
            else:
                # Regular data viewing functionality
                user_view()
        else:
            user_view()
        
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.is_admin = False
            st.rerun()

if __name__ == "__main__":
    main()