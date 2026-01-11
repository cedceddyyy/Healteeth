import sqlite3
import datetime
import os

def setup_database():
    db_path = os.environ.get('DB_PATH', 'healteeth.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # CUSTOMER Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CUSTOMER (
        CUST_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        CUST_FNAME TEXT NOT NULL,
        CUST_MNAME TEXT NOT NULL,
        CUST_LNAME TEXT NOT NULL,
        CUST_GENDER TEXT,
        CUST_ADDRESS TEXT NOT NULL,
        CUST_PHONE TEXT NOT NULL,
        CUST_EMAIL TEXT NOT NULL,
        CUST_BDATE TEXT NOT NULL
    );
    """)

    # SERVICE Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS SERVICE (
        SERVICE_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        SERVICE_NAME TEXT NOT NULL,
        SERVICE_DESC TEXT NOT NULL,
        SERVICE_PRICE REAL NOT NULL,
        ImagePath TEXT NOT NULL
    );
    """)

    # BRANCH Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS BRANCH (
        BRANCH_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        BRANCH_LOC TEXT NOT NULL
    );
    """)

    # SERVICE_BRANCH Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS SERVICE_BRANCH (
        SERVICE_ID INTEGER NOT NULL,
        BRANCH_ID INTEGER NOT NULL,
        FOREIGN KEY (SERVICE_ID) REFERENCES SERVICE(SERVICE_ID),
        FOREIGN KEY (BRANCH_ID) REFERENCES BRANCH(BRANCH_ID)
    );
    """)

    # SCHEDULE Table
    # Added STATUS column as inferred from usage
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS SCHEDULE (
        SCHED_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        SCHED_SLOTNUM INTEGER NOT NULL,
        SCHED_DATETIME TEXT NOT NULL,
        BRANCH_ID INTEGER NOT NULL,
        STATUS TEXT DEFAULT 'Active',
        FOREIGN KEY (BRANCH_ID) REFERENCES BRANCH(BRANCH_ID),
        UNIQUE(BRANCH_ID, SCHED_SLOTNUM)
    );
    """)

    # DENTIST Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS DENTIST (
        DENTIST_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        DENTIST_FULLNAME TEXT NOT NULL,
        DENTIST_EMAIL TEXT NOT NULL,
        BRANCH_ID INTEGER NOT NULL,
        FOREIGN KEY (BRANCH_ID) REFERENCES BRANCH(BRANCH_ID)
    );
    """)

    # USER_PROFILE Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS USER_PROFILE (
        USER_PROFILE_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        USER_FNAME TEXT NOT NULL,
        USER_LNAME TEXT NOT NULL,
        USER_TYPE TEXT NOT NULL
    );
    """)

    # USER Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS USER (
        USER_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        USER_USERNAME TEXT NOT NULL,
        USER_PASSWORD TEXT NOT NULL,
        USER_PROFILE_ID INTEGER NOT NULL,
        DENTIST_ID INTEGER,
        FOREIGN KEY (USER_PROFILE_ID) REFERENCES USER_PROFILE(USER_PROFILE_ID)
    );
    """)

    # APPOINTMENT Table
    # Added APPROVAL_STATUS as inferred from usage
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS APPOINTMENT (
        APPOINT_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        SERVICE_ID INTEGER NOT NULL,
        BRANCH_ID INTEGER NOT NULL,
        SCHED_ID INTEGER NOT NULL,
        CUST_ID INTEGER NOT NULL,
        USER_ID INTEGER,
        NUMTEETH_TO_EXTRACT INTEGER,
        TOTAL_PRICE REAL NOT NULL,
        APPOINT_DATE TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL,
        APPROVAL_STATUS TEXT DEFAULT 'Pending',
        FOREIGN KEY (SERVICE_ID) REFERENCES SERVICE(SERVICE_ID),
        FOREIGN KEY (BRANCH_ID) REFERENCES BRANCH(BRANCH_ID),
        FOREIGN KEY (SCHED_ID) REFERENCES SCHEDULE(SCHED_ID),
        FOREIGN KEY (CUST_ID) REFERENCES CUSTOMER(CUST_ID),
        FOREIGN KEY (USER_ID) REFERENCES USER(USER_ID)
    );
    """)

    # SEED DATA
    # Services
    services = [
        ('Cleaning', 'Teeth cleaning service', 500.00, 'images/cleaning.jfif'),
        ('Braces', 'Orthodontic braces', 25000.00, 'images/braces.jfif'),
        ('Extraction', 'Tooth extraction', 1000.00, 'images/extraction.jfif')
    ]
    cursor.executemany("INSERT OR IGNORE INTO SERVICE (SERVICE_NAME, SERVICE_DESC, SERVICE_PRICE, ImagePath) VALUES (?, ?, ?, ?)", services)

    # Branches
    branches = [
        ('Main Branch',),
        ('Santo Nino',),
        ('Ayala Center',)
    ]
    cursor.executemany("INSERT OR IGNORE INTO BRANCH (BRANCH_LOC) VALUES (?)", branches)

    # Schedules
    schedules = [
        (1, '2024-12-01 09:00:00', 1, 'Active'),
        (2, '2024-12-01 10:00:00', 2, 'Active'),
        (3, '2024-12-02 14:00:00', 3, 'Active')
    ]
    cursor.executemany("INSERT OR IGNORE INTO SCHEDULE (SCHED_SLOTNUM, SCHED_DATETIME, BRANCH_ID, STATUS) VALUES (?, ?, ?, ?)", schedules)

    # Dentists
    dentists = [
        ('Dr. Alice Johnson', 'alice.johnson@example.com', 1),
        ('Dr. Bob Brown', 'bob.brown@example.com', 2),
        ('Dr. Charlie Davis', 'charlie.davis@example.com', 3)
    ]
    cursor.executemany("INSERT OR IGNORE INTO DENTIST (DENTIST_FULLNAME, DENTIST_EMAIL, BRANCH_ID) VALUES (?, ?, ?)", dentists)

    # User Profiles
    profiles = [
        ('CEDRIC', 'CORNELIO', 'DOCTOR'),
        ('MARIANNE', 'CALDERON', 'ADMIN'),
        ('ADMIN', 'USER', 'ADMIN')
    ]
    cursor.executemany("INSERT OR IGNORE INTO USER_PROFILE (USER_FNAME, USER_LNAME, USER_TYPE) VALUES (?, ?, ?)", profiles)

    # Users
    # Note: Using hardcoded USER_PROFILE_ID here based on insertion order. 
    # In a robust script we'd look them up, but for initial seed on fresh DB this is fine.
    # CEDRIC (1), MARIANNE (2), ADMIN (3)
    users = [
        ('admin', 'admin123', 3, None), 
        ('staff01', 'staffpwd', 2, None), # Assuming staff maps to Marianne? original SQL had mapped to 'Staff Member'
        ('dentist01', 'dentistpwd', 1, 1) # Assuming dentist maps to Cedric (Doctor)? 
    ]
    
    # Actually, let's just insert the explicit ADMIN USER from line 130 of HEALTEETH.sql which is the only one mentioned explicitly at the end
    # "INSERT INTO [USER] (USER_USERNAME, USER_PASSWORD, USER_PROFILE_ID) VALUES ('ADMIN','USER', 3)"
    # But wait, lines 119-123 insert admin, staff01, dentist01.
    # HEALTEETH.sql has two sets of INSERTs for USER_PROFILE. 
    # Set 1: Admin User, Staff Member, Dentist Jones.
    # Set 2: CEDRIC, MARIANNE, ADMIN USER.
    # I should probably include all or just enough to make login work.
    # The 'login' function uses get_user.
    
    # Let's seed the first set of profiles too to be safe/consistent with users.
    extra_profiles = [
        ('Admin', 'User', 'Admin'),      # ID 4 if sequential after previous insert, logic depends if DB is fresh.
        ('Staff', 'Member', 'Staff'),
        ('Dentist', 'Jones', 'Dentist')
    ]
    # To avoid ID confusion, I'll clear tables first? No, "INSERT OR IGNORE" is better but IDs might drift.
    # I'll just insert everything afresh if tables are empty.
    
    # Actually, simplest is to just INSERT the users referenced in HEALTEETH.sql
    # REFERENCES:
    # ('admin', 'admin123', 1, 3) -> Profile 1 (Admin User?), Dentist 3 (Dr. Charlie Davis)
    # ('staff01', 'staffpwd', 2, 2) -> Profile 2 (Staff Member?), Dentist 2 (Dr. Bob Brown)
    # ('dentist01', 'dentistpwd', 3, 1) -> Profile 3 (Dentist Jones?), Dentist 1 (Dr. Alice Johnson)
    
    # So I need the first set of profiles.
    cursor.execute("DELETE FROM USER_PROFILE") 
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='USER_PROFILE'")
    
    profiles_ordered = [
        ('Admin', 'User', 'Admin'),         # 1
        ('Staff', 'Member', 'Staff'),       # 2
        ('Dentist', 'Jones', 'Dentist'),    # 3
        ('CEDRIC', 'CORNELIO', 'DOCTOR'),   # 4
        ('MARIANNE', 'CALDERON', 'ADMIN'),  # 5
        ('ADMIN', 'USER', 'ADMIN')          # 6
    ]
    cursor.executemany("INSERT INTO USER_PROFILE (USER_FNAME, USER_LNAME, USER_TYPE) VALUES (?, ?, ?)", profiles_ordered)

    cursor.execute("DELETE FROM USER")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='USER'")
    
    users_data = [
        ('admin', 'admin123', 1, 3),
        ('staff01', 'staffpwd', 2, 2),
        ('dentist01', 'dentistpwd', 3, 1),
        ('ADMIN', 'USER', 6, None)
    ]
    cursor.executemany("INSERT INTO USER (USER_USERNAME, USER_PASSWORD, USER_PROFILE_ID, DENTIST_ID) VALUES (?, ?, ?, ?)", users_data)


    conn.commit()
    conn.close()
    print("Database setup complete.")

if __name__ == "__main__":
    setup_database()
