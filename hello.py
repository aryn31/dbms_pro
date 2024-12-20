import streamlit as st
import mysql.connector
import pandas as pd
import hashlib
import re
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE,
                user_type VARCHAR(50) NOT NULL DEFAULT 'regular'
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
    cursor = connection.cursor(dictionary=True)  # Results as a dictionary
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    query = """
    SELECT id,username, password, is_admin, user_type  -- Include user_type in query
    FROM users
    WHERE username = %s
    """
    cursor.execute(query, (username,))
    user = cursor.fetchone()  # Fetch user data as a dictionary
    cursor.close()

    # Validate password
    if user and user["password"] == hashed_password:
        return user
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
                if st.button("Delete User"):
                    try:
                        cursor = connection.cursor()
                        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                        connection.commit()
                        cursor.close()
                        st.success(f"User '{username}' deleted successfully!")
                    except mysql.connector.Error as e:
                        st.error(f"Error deleting user: {e}")
        else:
            st.write("No non-admin users found.")

def table_operations(connection):
    st.header("Table Operations")
    
    # Fetch all table names
    tables = get_all_tables(connection)
    selected_table = st.selectbox("Select Table", tables)
    
    if selected_table:
        operation = st.radio("Select Operation", ["View", "Insert", "Update", "Delete"])
        
        if operation == "View":
            df = get_table_data(connection, selected_table)
            if df is not None:
                st.dataframe(df)
        
        elif operation == "Insert":
            st.subheader(f"Insert into {selected_table}")
            
            if selected_table == "Flights":
                # Input fields for Flights
                flight_id = st.text_input("Enter Flight ID")
                aircraft_id = st.number_input("Enter Aircraft ID", step=1)
                flight_number = st.text_input("Enter Flight Number")
                departure_airport = st.text_input("Enter Departure Airport")
                arrival_airport = st.text_input("Enter Arrival Airport")
                departure_time = st.text_input("Enter Departure Time (Format: YYYY-MM-DD HH:MM:SS)")
                arrival_time = st.text_input("Enter Arrival Time (Format: YYYY-MM-DD HH:MM:SS)")
                
                if st.button("Insert Record"):
                    try:
                        # Prepare flight data
                        flight_data = {
                            'FlightID': flight_id,
                            'AircraftID': aircraft_id,
                            'FlightNumber': flight_number,
                            'DepartureAirport': departure_airport,
                            'ArrivalAirport': arrival_airport,
                            'DepartureTime': departure_time,
                            'ArrivalTime': arrival_time
                        }
                        
                        # Schedule flight and assign crew
                        schedule_flight_and_manage_crew(connection,flight_data)
                    except mysql.connector.Error as e:
                        if "Duplicate entry" in str(e):
                            st.error("Same flight is going somewhere else at the entered time.")
                        else:
                            st.error(f"Error inserting record: {e}")
            else:
                # Generic Insert for other tables
                cursor = connection.cursor()
                cursor.execute(f"DESCRIBE {selected_table}")
                columns = cursor.fetchall()
                cursor.close()
                
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
            if selected_table == "Flights":
                # Input field for FlightID (as only this is required for deletion)
                flight_id = st.text_input("Enter Flight ID to Delete")
                
                if st.button("Delete Record"):
                    try:
                        # Prepare flight data for deletion
                        if not flight_id:
                            st.error("Please enter a Flight ID.")
                            return

                        # Call the delete operation
                        flight_data = {'FlightID': flight_id}
                        schedule_flight_and_manage_crew(connection, flight_data, action="delete")
                        
                    except mysql.connector.Error as e:
                        st.error(f"Error during deletion: {e}")
                        
            if df is not None:
                st.dataframe(df)

def schedule_flight_and_manage_crew(connection, flight_data=None, action="insert"):
    try:
        cursor = connection.cursor()

        if action == "insert":
            # Step 1: Insert the flight
            st.write("Inserting flight record...")
            cursor.execute('''
                INSERT INTO Flights (FlightID, AircraftID, FlightNumber, DepartureAirport, ArrivalAirport, DepartureTime, ArrivalTime)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            ''', (
                flight_data['FlightID'], 
                flight_data['AircraftID'], 
                flight_data['FlightNumber'], 
                flight_data['DepartureAirport'], 
                flight_data['ArrivalAirport'], 
                flight_data['DepartureTime'], 
                flight_data['ArrivalTime']
            ))
            st.write("Flight record inserted!")

            # Step 2: Find and assign available crew members
            roles = ['Pilot', 'Co-Pilot', 'Flight Attendant']
            assigned_crew = {}

            for role in roles:
                st.write(f"Assigning crew for role: {role}")
                cursor.execute('''
                    SELECT c.CrewID
                    FROM Crew c
                    WHERE c.Role = %s
                      AND NOT EXISTS (
                          SELECT 1
                          FROM CrewAssignment ca
                          JOIN Flights f ON ca.FlightID = f.FlightID
                          WHERE ca.CrewID = c.CrewID
                            AND (
                                %s < f.ArrivalTime AND %s > f.DepartureTime
                            )
                      )
                    LIMIT 1;
                ''', (role, flight_data['DepartureTime'], flight_data['ArrivalTime']))

                result = cursor.fetchone()
                if result:
                    assigned_crew[role] = result[0]
                else:
                    raise Exception(f"No available crew member found for role: {role}")

            # Step 3: Assign crew to the flight
            for role, crew_id in assigned_crew.items():
                st.write(f"Assigning {role} with CrewID {crew_id} to FlightID {flight_data['FlightID']}")
                cursor.execute('''
                    INSERT INTO CrewAssignment (CrewID, FlightID, AssignedAircraftID)
                    VALUES (%s, %s, %s);
                ''', (crew_id, flight_data['FlightID'], flight_data['AircraftID']))

            connection.commit()
            st.success("Flight scheduled and crew assigned successfully!")

        elif action == "update":
            # Update flight details
            st.write("Updating flight record...")
            cursor.execute('''
                UPDATE Flights
                SET AircraftID = %s, FlightNumber = %s, DepartureAirport = %s, ArrivalAirport = %s,
                    DepartureTime = %s, ArrivalTime = %s
                WHERE FlightID = %s;
            ''', (
                flight_data['AircraftID'], 
                flight_data['FlightNumber'], 
                flight_data['DepartureAirport'], 
                flight_data['ArrivalAirport'], 
                flight_data['DepartureTime'], 
                flight_data['ArrivalTime'],
                flight_data['FlightID']
            ))
            st.write("Flight record updated!")

            # Optional: Update crew assignment (if needed)
            st.info("You may need to reassign crew members if flight timings are changed.")
            # Logic for reassigning can be similar to the insert section

            connection.commit()
            st.success("Flight updated successfully!")

        elif action == "delete":
            # Step 1: Delete associated crew assignments
            st.write(f"Deleting crew assignments for FlightID {flight_data['FlightID']}...")
            cursor.execute('''
                DELETE FROM CrewAssignment
                WHERE FlightID = %s;
            ''', (flight_data['FlightID'],))
            st.write("Crew assignments deleted!")

            # Step 2: Delete the flight record
            st.write(f"Deleting flight record for FlightID {flight_data['FlightID']}...")
            cursor.execute('''
                DELETE FROM Flights
                WHERE FlightID = %s;
            ''', (flight_data['FlightID'],))
            st.write("Flight record deleted!")

            connection.commit()
            st.success("Flight and associated crew assignments deleted successfully!")

    except Exception as e:
        # Roll back the transaction in case of failure
        connection.rollback()
        st.error(f"Error during {action}: {str(e)}")

    finally:
        cursor.close()

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

    # Ask for user type
    user_type = st.radio("Select User Type", ("Admin", "Regular", "Manufacturer"))

    # Username and password fields
    username = st.text_input(f"👤 Username for {user_type}")
    password = st.text_input(f"🔑 Password for {user_type}", type="password")

    if st.button("Login"):
        connection = connect_to_database()
        if connection:
            user = authenticate_user(connection, username, password)
            if user:
                # Validate user type matches
                if user["user_type"] == user_type:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_id = user['id']
                    st.session_state.is_admin = user["is_admin"]  # Save admin status
                    st.session_state.user_type = user["user_type"]  # Save user type
                    st.success("Logged in successfully!")
                    st.rerun()  # Reload the app to refresh the UI
                else:
                    st.error(f"Invalid user type for {username}.")
            else:
                st.error("Invalid username or password")
            connection.close()
            
def signup_page():

    st.subheader("Create New Account")
    
    # Input fields for username, password, and email
    username = st.text_input("Username", key="signup_username")
    password = st.text_input("Password", type="password", key="signup_password")
    email = st.text_input("Email")

    # Dropdown for user type selection
    user_type = st.selectbox("Select User Type", ["Admin", "Regular", "Manufacturer"])

    # Email validation regex: (something)(number)@gmail.com
    email_pattern = r"^[a-zA-Z]+[0-9]+@gmail\.com$"

    # Function to check if username already exists
    def username_exists(mydb, username):
        cursor = mydb.cursor()
        query = "SELECT COUNT(*) FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        count = cursor.fetchone()[0]
        cursor.close()
        return count > 0

    # Display a success message if the account was just created
    if st.session_state.get("signup_success", False):
        st.success("Account created successfully! Please login.")
        if st.button("Sign Up Another Account"):  # Option to show signup again
            st.session_state.signup_success = False
            st.rerun()
            
    elif st.button("Sign Up"):
        if username and password and email:
            # Validate email format
            if not re.match(email_pattern, email):
                st.error("Invalid email format! Use 'something(number)@gmail.com'.")
            else:
                mydb = connect_to_database()
                if mydb:
                    # Check if username already exists
                    if username_exists(mydb, username):
                        st.error("This username is already taken. Please choose another one.")
                    else:
                        # Automatically set `is_admin` based on user type
                        is_admin = user_type == "Admin"
                        
                        # Create the user with the selected user type
                        if create_user(mydb, username, password, email, is_admin, user_type):
                            # Set a flag for success
                            st.session_state.signup_success = True
                            st.rerun()  # Reload page to show the success message
                        else:
                            st.error("Error creating account. Username or email may already exist.")
                    mydb.close()
        else:
            st.warning("Please fill all fields!")

def create_user(mydb, username, password, email, is_admin, user_type):
    """Create a new user in the database."""
    cursor = mydb.cursor()

    # Hash the password for secure storage
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    # Insert user into the database
    query = """
    INSERT INTO users (username, password, email, is_admin, user_type)
    VALUES (%s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (username, hashed_password, email, is_admin, user_type))
        mydb.commit()
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False
    finally:
        cursor.close()

def get_airport_names(mydb):
    """
    Fetches a list of unique airport names (Departure and Arrival airports) from the Flights table.
    Joins with the Airports table to fetch full airport names.
    """
    try:
        cursor = mydb.cursor()
        query = """
        SELECT DISTINCT a.AirportName
        FROM Airports a
        JOIN Flights f ON f.DepartureAirport = a.IATACode
        UNION
        SELECT DISTINCT a.AirportName
        FROM Airports a
        JOIN Flights f ON f.ArrivalAirport = a.IATACode
        """
        cursor.execute(query)
        airports = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return sorted(airports)  # Sort alphabetically for better UX
    except Exception as e:
        st.error(f"Error fetching airport names: {e}")
        return []

def flight_search_view():
    # Connect to the database
    mydb = connect_to_database()

    if mydb:
        st.title("Flight Search")

        # Fetch unique airport names
        airports = get_airport_names(mydb)

        if airports:
            # Input fields for filtering
            departure_airport = st.selectbox("Select Departure Airport (optional)", [""] + airports)
            arrival_airport = st.selectbox("Select Arrival Airport (optional)", [""] + airports)
        else:
            st.warning("No airports found in the database.")
            departure_airport, arrival_airport = None, None

        departure_date = st.date_input("Departure Date (optional)")
        arrival_date = st.date_input("Arrival Date (optional)")

        # Convert dates to strings
        departure_date = str(departure_date) if departure_date else None
        arrival_date = str(arrival_date) if arrival_date else None

        # Search button
        if st.button("Search Flights"):
            with st.spinner("Fetching flight data..."):
                df = filter_flights(
                    mydb,
                    departure_airport=departure_airport if departure_airport else None,
                    arrival_airport=arrival_airport if arrival_airport else None,
                    departure_date=departure_date,
                    arrival_date=arrival_date
                )

            if df is not None and not df.empty:
                st.success("Flights fetched successfully!")
                st.dataframe(df)

                # Download button for filtered data
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download results as CSV",
                    data=csv,
                    file_name="filtered_flights.csv",
                    mime="text/csv"
                )
            elif df is not None:
                st.warning("No flights match the given criteria.")

        mydb.close()

def filter_flights(mydb, departure_airport=None, arrival_airport=None, departure_date=None, arrival_date=None):
    """
    Fetches flights from the Flights table based on the provided filters.
    Uses airport names for filtering.
    """
    try:
        cursor = mydb.cursor(dictionary=True)

        query = """
        SELECT f.FlightNumber, f.DepartureAirport, f.ArrivalAirport, f.DepartureTime, f.ArrivalTime
        FROM Flights f
        JOIN Airports a1 ON f.DepartureAirport = a1.IATACode
        JOIN Airports a2 ON f.ArrivalAirport = a2.IATACode
        WHERE 1 = 1
        """
        params = []

        if departure_airport:
            query += " AND a1.AirportName = %s"
            params.append(departure_airport)

        if arrival_airport:
            query += " AND a2.AirportName = %s"
            params.append(arrival_airport)

        if departure_date:
            query += " AND DATE(f.DepartureTime) = %s"
            params.append(departure_date)

        if arrival_date:
            query += " AND DATE(f.ArrivalTime) = %s"
            params.append(arrival_date)

        cursor.execute(query, params)
        flights = cursor.fetchall()
        cursor.close()

        # Convert to DataFrame for better handling
        import pandas as pd
        return pd.DataFrame(flights)
    except Exception as e:
        st.error(f"Error filtering flights: {e}")
        return None

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

def manufacturer_dashboard():
    st.subheader("Manufacturer Dashboard")
    st.write(f"Welcome, {st.session_state.username}!")

    # Dropdown menu for different options
    options = [
        "Flight Details",
        "Flight Crew",
        "Incidents",
        "Aircraft Status",
        "Maintenance Info",
    ]
    selected_option = st.selectbox("Select an option to view details:", options)

    # Establish database connection
    mydb = connect_to_database()
    if mydb:
        cursor = mydb.cursor(dictionary=True)

        # Handle each option
        if selected_option == "Flight Details":
            query = """
                SELECT 
                    a.AircraftID, 
                    a.Model, 
                    a.Capacity, 
                    a.FlightRange, 
                    f.FlightNumber, 
                    f.DepartureAirport, 
                    f.ArrivalAirport, 
                    f.DepartureTime, 
                    f.ArrivalTime
                FROM Aircraft a
                JOIN Flights f ON a.AircraftID = f.AircraftID
                WHERE a.Manufacturer = %s
            """
            cursor.execute(query, (st.session_state.username,))
            data = cursor.fetchall()

        elif selected_option == "Flight Crew":
            query = """
                SELECT 
                    c.AssignedAircraftID AS AircraftID, 
                    c.CrewID, 
                    cr.Name, 
                    cr.Role
                FROM CrewAssignment c
                JOIN Crew cr ON c.CrewID = cr.CrewID
                JOIN Aircraft a ON c.AssignedAircraftID = a.AircraftID
                WHERE a.Manufacturer = %s
            """
            cursor.execute(query, (st.session_state.username,))
            data = cursor.fetchall()

        elif selected_option == "Incidents":
            query = """
                SELECT 
                    i.AircraftID, 
                    i.IncidentID, 
                    d.Description, 
                    i.Severity
                FROM IncidentInfo i
                JOIN IncidentDetails d ON i.IncidentID = d.IncidentID
                JOIN Aircraft a ON i.AircraftID = a.AircraftID
                WHERE a.Manufacturer = %s
            """
            cursor.execute(query, (st.session_state.username,))
            data = cursor.fetchall()

        elif selected_option == "Aircraft Status":
            query = """
                SELECT 
                    s.AircraftID, 
                    s.StatusID, 
                    s.Status, 
                    s.StatusDate
                FROM AircraftStatus s
                JOIN Aircraft a ON s.AircraftID = a.AircraftID
                WHERE a.Manufacturer = %s
            """
            cursor.execute(query, (st.session_state.username,))
            data = cursor.fetchall()

        elif selected_option == "Maintenance Info":
            query = """
                SELECT 
                    m.AircraftID, 
                    m.MaintenanceID, 
                    m.MaintenanceType, 
                    m.StartDate, 
                    m.EndDate, 
                    t.TeamName
                FROM MaintenanceInfo m
                JOIN MaintenanceAssignment ma ON m.MaintenanceID = ma.MaintenanceID
                JOIN MaintenanceTeam t ON ma.TeamID = t.TeamID
                JOIN Aircraft a ON m.AircraftID = a.AircraftID
                WHERE a.Manufacturer = %s
            """
            cursor.execute(query, (st.session_state.username,))
            data = cursor.fetchall()

        else:
            data = None

        # Display results
        if data:
            st.dataframe(data)
            csv = pd.DataFrame(data).to_csv(index=False)
            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name=f"{selected_option.replace(' ', '_').lower()}_data.csv",
                mime="text/csv"
            )
        else:
            st.warning(f"No data found for {selected_option}.")

        # Close database connection
        cursor.close()
        mydb.close()
    else:
        st.error("Failed to connect to the database.")

def filter_flights_with_prices_and_duration(mydb, departure_airport=None, arrival_airport=None, departure_date=None, arrival_date=None):
    """
    Fetches flights from the Flights table along with their prices and durations.
    Uses airport names and dates for filtering.
    """
    try:
        cursor = mydb.cursor(dictionary=True)

        query = """
        SELECT 
            f.FlightID,
            f.FlightNumber,
            f.DepartureAirport,
            f.ArrivalAirport,
            f.DepartureTime,
            f.ArrivalTime,
            TIMEDIFF(f.ArrivalTime, f.DepartureTime) AS Duration,
            fp.SeatClass,
            fp.Price
        FROM 
            Flights f
        LEFT JOIN 
            FlightPrices fp ON f.FlightID = fp.FlightID
        JOIN 
            Airports a1 ON f.DepartureAirport = a1.IATACode
        JOIN 
            Airports a2 ON f.ArrivalAirport = a2.IATACode
        WHERE 1 = 1
        """
        
        # List to hold parameters for SQL query
        params = []

        # Add filters based on user input
        if departure_airport:
            query += " AND a1.AirportName = %s"
            params.append(departure_airport)

        if arrival_airport:
            query += " AND a2.AirportName = %s"
            params.append(arrival_airport)

        if departure_date:
            query += " AND DATE(f.DepartureTime) = %s"
            params.append(departure_date)

        if arrival_date:
            query += " AND DATE(f.ArrivalTime) = %s"
            params.append(arrival_date)

        # Execute the query
        cursor.execute(query, params)
        flights = cursor.fetchall()
        cursor.close()

        # Convert the result to a DataFrame
        import pandas as pd
        return pd.DataFrame(flights)
    
    except Exception as e:
        st.error(f"Error filtering flights: {e}")
        return None

def flight_booking_view():
    # Connect to the database
    mydb = connect_to_database()

    if mydb:
        st.title("Flight Booking")

        # Check for user ID and username in session state
        if 'user_id' not in st.session_state or 'username' not in st.session_state:
            st.error("User details are not set in session state.")
            return

        # Display user information for debugging
        st.write(f"User ID: {st.session_state.user_id}")
        st.write(f"User Name: {st.session_state.username}")

        # Fetch unique airport names
        if 'airports' not in st.session_state:
            st.session_state.airports = get_airport_names(mydb)

        airports = st.session_state.airports

        if airports:
            # Input fields for filtering
            departure_airport = st.selectbox("Select Departure Airport (optional)", [""] + airports)
            arrival_airport = st.selectbox("Select Arrival Airport (optional)", [""] + airports)
        else:
            st.warning("No airports found in the database.")
            departure_airport, arrival_airport = None, None

        departure_date = st.date_input("Departure Date (optional)")
        arrival_date = st.date_input("Arrival Date (optional)")

        # Convert dates to strings
        departure_date = str(departure_date) if departure_date else None
        arrival_date = str(arrival_date) if arrival_date else None

        # Search flights
        if st.button("Search Flights for Booking"):
            with st.spinner("Fetching flight data..."):
                df = filter_flights_with_prices_and_duration(
                    mydb,
                    departure_airport=departure_airport if departure_airport else None,
                    arrival_airport=arrival_airport if arrival_airport else None,
                    departure_date=departure_date,
                    arrival_date=arrival_date
                )
                st.session_state.search_results = df  # Save results to session state

        # Fetch results from session state
        if 'search_results' in st.session_state:
            df = st.session_state.search_results

            if df is not None and not df.empty:
                st.success("Flights fetched successfully!")

                # Show flight results
                for index, row in df.iterrows():
                    st.write(f"### Flight: {row['FlightNumber']}")
                    st.write(f"Departure: {row['DepartureAirport']} at {row['DepartureTime']}")
                    st.write(f"Arrival: {row['ArrivalAirport']} at {row['ArrivalTime']}")
                    st.write(f"Duration: {row['Duration']}")
                    st.write(f"Class: {row['SeatClass']}")
                    st.write(f"Price: ₹{row['Price']}")

                    # Book button
                    if st.button(f"Book Flight {row['FlightNumber']} ({row['SeatClass']})", key=f"book_{index}"):
                        with st.spinner("Booking flight..."):
                            success = book_flight(
                                mydb,
                                user_id=st.session_state.user_id,
                                user_name=st.session_state.username,
                                flight_id=row['FlightID'],
                                seat_class=row['SeatClass']
                            )
                        if success:
                            st.success("Flight booked successfully!")
                        else:
                            st.error("Booking failed. Please try again.")

                # Download button for filtered data
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download results as CSV",
                    data=csv,
                    file_name="available_flights.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No flights match the given criteria.")
        else:
            st.info("Search for flights to view available options.")

        mydb.close()

def book_flight(mydb, user_id, user_name, flight_id, seat_class):
    cursor = mydb.cursor(dictionary=True)
    st.write(f"chacha function me ghus gaya")
    # Fetch the price for the given flight_id and seat_class
    cursor.execute("""
        SELECT Price 
        FROM FlightPrices 
        WHERE FlightID = %s AND SeatClass = %s
    """, (flight_id, seat_class))
    flight_price = cursor.fetchone()

    if not flight_price:
        st.error("Flight not available for the selected seat class.")
        return False

    price = flight_price['Price']
    st.write(f"Booking Flight: FlightID = {flight_id}, SeatClass = {seat_class}, Price = ₹{price}")  # Debug line

    # Insert a new booking into the Bookings table
    try:
        cursor.execute("""
            INSERT INTO Bookings (UserID, FlightID, SeatClass, Price, Status, UserName)
            VALUES (%s, %s, %s, %s, 'Confirmed', %s)
        """, (user_id, flight_id, seat_class, price, user_name))
        mydb.commit()  # Commit the transaction

        # Debug line to confirm SQL execution
        st.write("Booking SQL executed successfully.")

        st.success("Booking confirmed!")
        return True
    except mysql.connector.Error as e:
        st.error(f"Error booking flight: {e}")
        mydb.rollback()  # Rollback in case of error
        return False
    finally:
        cursor.close()

def view_booking_history(mydb, user_id):
    """
    Fetches and displays the booking history for the given user with an option to cancel active bookings.
    """
    try:
        cursor = mydb.cursor(dictionary=True)
        
        query = """
        SELECT 
            b.BookingID,
            b.UserName,
            f.FlightNumber,
            b.SeatClass,
            b.Price,
            b.BookingDate,
            b.Status,
            f.DepartureAirport,
            f.ArrivalAirport,
            f.DepartureTime,
            f.ArrivalTime
        FROM Bookings b
        JOIN Flights f ON b.FlightID = f.FlightID
        WHERE b.UserID = %s
        ORDER BY b.BookingDate DESC
        """
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()
        cursor.close()

        if results:
            st.title("Your Booking History")

            # Display bookings
            for booking in results:
                st.write(f"### Booking ID: {booking['BookingID']}")
                st.write(f"Flight Number: {booking['FlightNumber']}")
                st.write(f"Seat Class: {booking['SeatClass']}")
                st.write(f"Price: ₹{booking['Price']}")
                st.write(f"Booking Date: {booking['BookingDate']}")
                st.write(f"Departure: {booking['DepartureAirport']} at {booking['DepartureTime']}")
                st.write(f"Arrival: {booking['ArrivalAirport']} at {booking['ArrivalTime']}")
                st.write(f"Status: {booking['Status']}")

                if booking['Status'] == 'Confirmed':  # Assuming 'Confirmed' means active
                    # Cancel button
                    if st.button(f"Cancel Booking {booking['BookingID']}", key=f"cancel_{booking['BookingID']}"):
                        with st.spinner("Canceling booking..."):
                            success = cancel_booking(mydb, booking['BookingID'])
                        if success:
                            st.success(f"Booking ID {booking['BookingID']} canceled successfully!")
                        else:
                            st.error(f"Failed to cancel Booking ID {booking['BookingID']}. Please try again.")
        else:
            st.info("No bookings found.")
    except Exception as e:
        st.error(f"Error fetching booking history: {e}")

def booking_history_view():
    """
    Displays the user's booking history and allows cancellation of active bookings.
    """
    mydb = connect_to_database()

    if mydb:
        st.title("Booking History")

        if "user_id" in st.session_state:
            user_id = st.session_state.user_id
            view_booking_history(mydb, user_id)
        else:
            st.warning("Please log in to view your booking history.")
        
        mydb.close()

def cancel_booking(mydb, booking_id):
    """
    Cancels a booking by updating its status to 'Canceled'.
    """
    try:
        cursor = mydb.cursor()
        query = "UPDATE Bookings SET Status = 'Canceled' WHERE BookingID = %s AND Status = 'Confirmed'"
        cursor.execute(query, (booking_id,))
        mydb.commit()
        cursor.close()

        if cursor.rowcount > 0:
            return True  # Cancellation successful
        else:
            return False  # Booking not found or already canceled
    except Exception as e:
        st.error(f"Error canceling booking: {e}")
        return False

def main():
    # Display logo and company name side by side
    col1, col2 = st.columns([1, 6])  # Adjust column widths as needed
    with col1:
        st.image("logo.png", use_container_width=True)  # Display logo in the first column
    with col2:
        st.title("FlyingMotors Ltd.")  # Display company name in the second column

    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'user_type' not in st.session_state:
        st.session_state.user_type = None

    # User is not logged in
    if not st.session_state.logged_in:
        menu = ["Login", "Sign Up"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Login":
            login_page()
        else:
            signup_page()
    else:
        # Show welcome message in the sidebar
        st.sidebar.success(f"Welcome {st.session_state.username}")

        # Debugging: Show role
        st.write(f"Logged in as: {st.session_state.username} ({st.session_state.user_type})")

        # Role-based menu options
        if st.session_state.is_admin:
            menu = ["View Data", "Admin Panel"]
        elif st.session_state.user_type == "Manufacturer":
            menu = ["Manufacturer Dashboard"]
        else:
            # Regular user menu
            menu = ["Flight Search", "Flight Booking", "Booking History"]

        choice = st.sidebar.selectbox("Menu", menu)

        # Admin view
        if choice == "Admin Panel" and st.session_state.is_admin:
            mydb = connect_to_database()
            if mydb:
                admin_panel(mydb)
                mydb.close()

        # Manufacturer view
        elif choice == "Manufacturer Dashboard" and st.session_state.user_type == "Manufacturer":
            manufacturer_dashboard()

        # Regular user views
        elif choice == "Flight Search" and st.session_state.user_type == "Regular":
            flight_search_view()
        elif choice == "Flight Booking" and st.session_state.user_type == "Regular":
            flight_booking_view()
        elif choice == "Booking History" and st.session_state.user_type == "Regular":
            mydb = connect_to_database()
            if mydb:
                view_booking_history(mydb, st.session_state.user_id)  # Show booking history
                mydb.close()

        # Default user view
        else:
            user_view()

        # Logout option in the sidebar
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.is_admin = False
            st.session_state.user_type = None
            st.session_state.username = None
            st.session_state.user_id = None
            st.rerun()

if __name__ == "__main__":
    main()