import sqlite3
from datetime import datetime

import os

DATABASE_NAME = os.environ.get('DB_PATH', 'healteeth.db')

def get_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(query, params=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
    finally:
        conn.close()

def fetch_one(query, params=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def fetch_all(query, params=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_user(username, password):
    query = """
    SELECT u.*, up.USER_FNAME, up.USER_LNAME, up.USER_TYPE
    FROM USER u
    JOIN USER_PROFILE up ON u.USER_PROFILE_ID = up.USER_PROFILE_ID
    WHERE u.USER_USERNAME = ? AND u.USER_PASSWORD = ?
    """
    return fetch_one(query, (username, password))

def get_all_services():
    query = "SELECT SERVICE_ID, SERVICE_NAME, SERVICE_DESC, SERVICE_PRICE, ImagePath FROM SERVICE"
    return fetch_all(query)

def get_all_branches():
    query = "SELECT BRANCH_ID, BRANCH_LOC FROM BRANCH"
    return fetch_all(query)

def get_schedules_by_branch(branch_id):
    # Assuming this returns active schedules based on typical app logic
    query = """
    SELECT SCHED_ID, SCHED_SLOTNUM, SCHED_DATETIME, BRANCH_ID 
    FROM SCHEDULE 
    WHERE BRANCH_ID = ? AND STATUS = 'Active'
    ORDER BY SCHED_DATETIME
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (branch_id,))
        schedules = cursor.fetchall()
        formatted_schedules = []

        for schedule in schedules:
            sched_datetime_str = schedule['SCHED_DATETIME']
            # Parse the datetime string from SQLite
            try:
                if 'T' in sched_datetime_str:
                     sched_datetime = datetime.strptime(sched_datetime_str, "%Y-%m-%dT%H:%M:%S")
                else:
                     sched_datetime = datetime.strptime(sched_datetime_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Fallback or try other formats if seeded differently
                try: 
                    sched_datetime = datetime.strptime(sched_datetime_str, "%Y-%m-%d %H:%M") 
                except:
                     sched_datetime = datetime.now() # Error fallback

            formatted_date = sched_datetime.strftime("%B %d, %Y")
            formatted_time = sched_datetime.strftime("%I:%M %p")

            formatted_schedules.append({
                "SCHED_ID": schedule['SCHED_ID'],
                "SCHED_SLOTNUM": schedule['SCHED_SLOTNUM'],
                "SCHEDULE_DATE": formatted_date,
                "SCHEDULE_TIME": formatted_time,
                "BRANCH_ID": schedule['BRANCH_ID']
            })

        return formatted_schedules
    finally:
        conn.close()

def get_customer_by_name(first_name, last_name):
    query = """
    SELECT * FROM CUSTOMER 
    WHERE CUST_FNAME = ? AND CUST_LNAME = ?
    """
    return fetch_one(query, (first_name, last_name))

def insert_new_customer(first_name, middle_name, last_name, gender, address, phone, email, birthdate):
    # Upsert logic: Check if exists/Update or Insert. 
    # But function name says insert_new_customer.
    # The original SP was SP_POPULATEORUPDATE_CUSTOMER. 
    # Current call site in app.py checks get_customer_by_name first.
    # If not found, it calls insert_new_customer.
    # So we can just INSERT.
    query = """
    INSERT INTO CUSTOMER (CUST_FNAME, CUST_MNAME, CUST_LNAME, CUST_GENDER, CUST_ADDRESS, CUST_PHONE, CUST_EMAIL, CUST_BDATE)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    execute_query(query, (first_name, middle_name, last_name, gender, address, phone, email, birthdate))

def update_customer_in_db(customer_data):
    # This corresponds to atomic update of existing customer
    query = """
    UPDATE CUSTOMER
    SET CUST_FNAME = ?, 
        CUST_MNAME = ?, 
        CUST_LNAME = ?, 
        CUST_GENDER = ?, 
        CUST_ADDRESS = ?, 
        CUST_PHONE = ?, 
        CUST_EMAIL = ?, 
        CUST_BDATE = ?
    WHERE CUST_ID = ?
    """
    execute_query(query, (
        customer_data['CUST_FNAME'],
        customer_data['CUST_MNAME'],
        customer_data['CUST_LNAME'],
        customer_data['CUST_GENDER'],
        customer_data['CUST_ADDRESS'],
        customer_data['CUST_PHONE'],
        customer_data['CUST_EMAIL'],
        customer_data['CUST_BDATE'],
        customer_data['CUST_ID']
    ))

def get_appointments_by_branch(branch_id):
    # Status default Pending from original code behavior
    return get_appointments_by_status(branch_id, 'Pending')

def get_all_dentists():
    # FN_GETDENTISTDETAILS joined DENTIST and BRANCH
    query = """
    SELECT d.DENTIST_FULLNAME, d.DENTIST_EMAIL, b.BRANCH_LOC
    FROM DENTIST d
    JOIN BRANCH b ON d.BRANCH_ID = b.BRANCH_ID
    """
    return fetch_all(query)

def insert_service(service_name, service_desc, service_price, service_image):
    # Upsert logic
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT SERVICE_ID FROM SERVICE WHERE SERVICE_NAME = ?", (service_name,))
        row = cursor.fetchone()
        if row:
            cursor.execute("""
                UPDATE SERVICE SET SERVICE_DESC=?, SERVICE_PRICE=?, ImagePath=? WHERE SERVICE_NAME=?
            """, (service_desc, service_price, service_image, service_name))
        else:
            cursor.execute("""
                INSERT INTO SERVICE (SERVICE_NAME, SERVICE_DESC, SERVICE_PRICE, ImagePath) VALUES (?, ?, ?, ?)
            """, (service_name, service_desc, service_price, service_image))
        conn.commit()
    finally:
        conn.close()

def insert_schedule(branch_id, schedule_date, schedule_slot):
    # Handle datetime conversion
    if isinstance(schedule_date, str):
        # The app might send "YYYY-MM-DDTHH:MM" (HTML datetime-local input)
         try:
             sched_datetime = datetime.strptime(schedule_date, "%Y-%m-%dT%H:%M")
         except ValueError:
              # Try fallback if it's just date
             sched_datetime = datetime.strptime(schedule_date, "%Y-%m-%d") # unlikely but possible
    else:
        sched_datetime = schedule_date

    sched_datetime_str = sched_datetime.strftime("%Y-%m-%d %H:%M:%S")

    # Upsert logic based on SLOT and BRANCH? 
    # Original SP: IF EXISTS (SELECT 1 FROM SCHEDULE WHERE SCHED_DATETIME = @SCHED_DATETIME AND BRANCH_ID = @BRANCH_ID)
    # Actually SP logic was updating slotnum based on datetime+branch.
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT SCHED_ID FROM SCHEDULE WHERE SCHED_DATETIME = ? AND BRANCH_ID = ?", (sched_datetime_str, branch_id))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE SCHEDULE SET SCHED_SLOTNUM = ?, STATUS='Active' WHERE SCHED_DATETIME = ? AND BRANCH_ID = ?", (schedule_slot, sched_datetime_str, branch_id))
        else:
            cursor.execute("INSERT INTO SCHEDULE (SCHED_SLOTNUM, SCHED_DATETIME, BRANCH_ID, STATUS) VALUES (?, ?, ?, 'Active')", (schedule_slot, sched_datetime_str, branch_id))
        conn.commit()
    finally:
        conn.close()

def _calculate_total_price(conn, service_id, numteeth):
    cursor = conn.cursor()
    cursor.execute("SELECT SERVICE_PRICE, SERVICE_NAME FROM SERVICE WHERE SERVICE_ID = ?", (service_id,))
    row = cursor.fetchone()
    if not row:
        return 0.0
    
    price = row['SERVICE_PRICE']
    name = row['SERVICE_NAME']
    
    if name and 'extraction' in name.lower():
        return float(price) * int(numteeth)
    return float(price)

def insert_appointment(service_id, branch_id, sched_id, cust_id, numteeth_to_extract):
    conn = get_connection()
    try:
        total_price = _calculate_total_price(conn, service_id, numteeth_to_extract)
        
        cursor = conn.cursor()
        # Upsert logic: SP checked service+branch+sched+cust... if exists update.
        cursor.execute("""
            SELECT APPOINT_ID FROM APPOINTMENT 
            WHERE SERVICE_ID=? AND BRANCH_ID=? AND SCHED_ID=? AND CUST_ID=?
        """, (service_id, branch_id, sched_id, cust_id))
        row = cursor.fetchone()
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if row:
            cursor.execute("""
                UPDATE APPOINTMENT 
                SET NUMTEETH_TO_EXTRACT=?, TOTAL_PRICE=?, APPOINT_DATE=?
                WHERE APPOINT_ID=?
            """, (numteeth_to_extract, total_price, current_time, row['APPOINT_ID']))
            conn.commit()
            return row['APPOINT_ID']
        else:
            cursor.execute("""
                INSERT INTO APPOINTMENT (SERVICE_ID, BRANCH_ID, SCHED_ID, CUST_ID, NUMTEETH_TO_EXTRACT, TOTAL_PRICE, APPOINT_DATE, APPROVAL_STATUS)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
            """, (service_id, branch_id, sched_id, cust_id, numteeth_to_extract, total_price, current_time))
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()

def get_schedule_details_by_id(sched_id):
    query = "SELECT * FROM SCHEDULE WHERE SCHED_ID = ?"
    return fetch_one(query, (sched_id,))

def get_appointment_total_price(appointment_id):
    query = "SELECT TOTAL_PRICE FROM APPOINTMENT WHERE APPOINT_ID = ?"
    row = fetch_one(query, (appointment_id,))
    return float(row['TOTAL_PRICE']) if row else 0.0

def update_service_in_db(service_name, service_desc, service_price, service_image):
    insert_service(service_name, service_desc, service_price, service_image)

def delete_service_in_db(service_name):
    query = "DELETE FROM SERVICE WHERE SERVICE_NAME = ?"
    execute_query(query, (service_name,))

def update_schedule_in_db(schedule_id, schedule_date, schedule_slot):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT BRANCH_ID FROM SCHEDULE WHERE SCHED_ID = ?", (schedule_id,))
        row = cursor.fetchone()
        if row:
            branch_id = row['BRANCH_ID']
            # Re-use insert logic for update/upsert usually, but here we update specific ID?
            # SP updated by datetime/branch. Python wrapper passed ID but SP ignored ID and used params to find by datetime/branch?
            # Wait, `update_schedule_in_db` in original dbhelper passed ID... but `SP_POPULATEORUPDATE_SCHEDULE` didn't take ID!
            # It took slot, datetime, branch.
            # Original code:
            # executed "SELECT BRANCH_ID FROM SCHEDULE WHERE SCHED_ID = ?"
            # then "EXEC SP_POPULATEORUPDATE_SCHEDULE ..." using new DATE, SLOT, and found BRANCH.
            # So it actually CHANGED the schedule at that NEW date/slot/branch? 
            # Or if it existed, updated slot?
            # This logic is weird in original.
            # I will trust the logic: It tries to insert/update a schedule slot at the specified date.
            
            insert_schedule(branch_id, schedule_date, schedule_slot)
            
            # Note: The original code didn't delete the old schedule ID if the date changed to a new slot that created a NEW row.
            # If the user intended to "Move" a schedule, `SP_` would only update if target exists, else insert new.
            # The old ID would remain at old date.
            # Usually update schedule means move. 
            # Given `SP` limitation, maybe I should just update the row by ID.
            # But I should stick to original behavior replication if possible. 
            # The original code called `SP_POPULATEORUPDATE_SCHEDULE`.
            
    finally:
        conn.close()

def delete_schedule_in_db(schedule_id):
    query = "DELETE FROM SCHEDULE WHERE SCHED_ID = ?"
    execute_query(query, (schedule_id,))

def update_schedule_status_to_inactive(sched_id):
    # SP_DEACTIVATE_SCHEDULE
    query = "UPDATE SCHEDULE SET STATUS = 'Inactive' WHERE SCHED_ID = ?"
    execute_query(query, (sched_id,))

def update_appointment_with_user(appoint_id, user_id):
    query = "UPDATE APPOINTMENT SET USER_ID = ? WHERE APPOINT_ID = ?"
    execute_query(query, (user_id, appoint_id))

def get_appointment_by_id(appointment_id):
    # SP_GETAPPOINTMENTBYID
    # Needs to return appointment details.
    # The original SP likely did joins to get Service Name, Branch Loc, etc?
    # Let's assume basic select or join.
    # The app usages usually imply detailed info.
    query = """
    SELECT a.*, s.SERVICE_NAME, s.SERVICE_PRICE, b.BRANCH_LOC, sch.SCHED_DATETIME, 
           c.CUST_FNAME, c.CUST_LNAME, c.CUST_PHONE
    FROM APPOINTMENT a
    JOIN SERVICE s ON a.SERVICE_ID = s.SERVICE_ID
    JOIN BRANCH b ON a.BRANCH_ID = b.BRANCH_ID
    JOIN SCHEDULE sch ON a.SCHED_ID = sch.SCHED_ID
    JOIN CUSTOMER c ON a.CUST_ID = c.CUST_ID
    WHERE a.APPOINT_ID = ?
    """
    return fetch_one(query, (appointment_id,))

def update_appointment_approval_status(appoint_id, approval_status):
    query = "UPDATE APPOINTMENT SET APPROVAL_STATUS = ? WHERE APPOINT_ID = ?"
    execute_query(query, (approval_status, appoint_id))

def get_appointments_by_status(branch_id, status):
    # Joined detailed view
    query = """
    SELECT a.APPOINT_ID, a.SERVICE_ID, a.BRANCH_ID, a.SCHED_ID, a.CUST_ID, a.USER_ID, 
           a.NUMTEETH_TO_EXTRACT, a.TOTAL_PRICE, a.APPOINT_DATE, a.APPROVAL_STATUS,
           s.SERVICE_NAME, b.BRANCH_LOC, sch.SCHED_DATETIME,
           c.CUST_FNAME, c.CUST_LNAME
    FROM APPOINTMENT a
    JOIN SERVICE s ON a.SERVICE_ID = s.SERVICE_ID
    JOIN BRANCH b ON a.BRANCH_ID = b.BRANCH_ID
    JOIN SCHEDULE sch ON a.SCHED_ID = sch.SCHED_ID
    JOIN CUSTOMER c ON a.CUST_ID = c.CUST_ID
    WHERE a.BRANCH_ID = ? AND a.APPROVAL_STATUS = ?
    """
    return fetch_all(query, (branch_id, status))

def get_inactive_schedules_by_branch(branch_id):
    query = """
    SELECT SCHED_ID, SCHED_SLOTNUM, SCHED_DATETIME, BRANCH_ID, STATUS
    FROM SCHEDULE
    WHERE BRANCH_ID = ? AND STATUS = 'Inactive'
    ORDER BY SCHED_DATETIME
    """
    # Need formatting like get_schedules_by_branch
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (branch_id,))
        schedules = cursor.fetchall()
        formatted_schedules = []

        # Get Branch Location for display
        cursor.execute("SELECT BRANCH_LOC FROM BRANCH WHERE BRANCH_ID = ?", (branch_id,))
        b_row = cursor.fetchone()
        branch_loc = b_row['BRANCH_LOC'] if b_row else ""

        for schedule in schedules:
            sched_datetime_str = schedule['SCHED_DATETIME']
            # Parse datetime
            try:
                if 'T' in sched_datetime_str:
                     sched_datetime = datetime.strptime(sched_datetime_str, "%Y-%m-%dT%H:%M:%S")
                else:
                     sched_datetime = datetime.strptime(sched_datetime_str, "%Y-%m-%d %H:%M:%S")
            except:
                 try:
                     sched_datetime = datetime.strptime(sched_datetime_str, "%Y-%m-%d %H:%M")
                 except:
                     sched_datetime = datetime.now()

            formatted_date = sched_datetime.strftime("%B %d, %Y")
            formatted_time = sched_datetime.strftime("%I:%M %p")

            formatted_schedules.append({
                "SCHED_ID": schedule['SCHED_ID'],
                "SCHED_SLOTNUM": schedule['SCHED_SLOTNUM'],
                "SCHEDULE_DATE": formatted_date,
                "SCHEDULE_TIME": formatted_time,
                "BRANCH_LOC": branch_loc,
                "STATUS": schedule['STATUS']
            })
        return formatted_schedules
    finally:
        conn.close()

def insert_service_branch(service_id, branch_id):
    query = "INSERT INTO SERVICE_BRANCH (SERVICE_ID, BRANCH_ID) VALUES (?, ?)"
    # Handle unique constraint if needed? Table schema PK? 
    # Current helper script didn't make composite PK.
    # To be safe, ignore if exists
    try:
        execute_query(query, (service_id, branch_id))
    except sqlite3.IntegrityError:
        pass

def delete_service_branch(service_id, branch_id):
    query = "DELETE FROM SERVICE_BRANCH WHERE SERVICE_ID = ? AND BRANCH_ID = ?"
    execute_query(query, (service_id, branch_id))

def get_branches_by_service(service_id):
    query = """
    SELECT b.BRANCH_ID, b.BRANCH_LOC
    FROM BRANCH b
    JOIN SERVICE_BRANCH sb ON b.BRANCH_ID = sb.BRANCH_ID
    WHERE sb.SERVICE_ID = ?
    """
    return fetch_all(query, (service_id,))

def get_services_by_branch(branch_id):
    query = """
    SELECT s.*
    FROM SERVICE s
    JOIN SERVICE_BRANCH sb ON s.SERVICE_ID = sb.SERVICE_ID
    WHERE sb.BRANCH_ID = ?
    """
    return fetch_all(query, (branch_id,))


def get_available_branches_for_service(service_id):
    # Same as get_branches_by_service
    return get_branches_by_service(service_id)

def get_dashboard_stats():
    conn = get_connection()
    stats = {}
    
    try:
        # 1. Appointment Counts by Status
        query_status = """
            SELECT APPROVAL_STATUS, COUNT(*) as count 
            FROM APPOINTMENT 
            GROUP BY APPROVAL_STATUS
        """
        status_counts = fetch_all(query_status)
        stats['status_counts'] = {row['APPROVAL_STATUS']: row['count'] for row in status_counts}
        
        # Ensure all keys exist
        for status in ['Pending', 'Approved', 'Disapproved']:
            if status not in stats['status_counts']:
                stats['status_counts'][status] = 0

        # 2. Total Revenue (Approved appointments only)
        query_revenue = """
            SELECT SUM(TOTAL_PRICE) as total_revenue
            FROM APPOINTMENT
            WHERE APPROVAL_STATUS = 'Approved'
        """
        revenue_result = fetch_one(query_revenue)
        stats['total_revenue'] = revenue_result['total_revenue'] if revenue_result and revenue_result['total_revenue'] else 0

        # 3. Monthly Revenue (Current Year)
        current_year = datetime.now().year
        query_monthly = """
            SELECT strftime('%m', SCHEDULE.SCHED_DATETIME) as month, SUM(APPOINTMENT.TOTAL_PRICE) as revenue
            FROM APPOINTMENT
            JOIN SCHEDULE ON APPOINTMENT.SCHED_ID = SCHEDULE.SCHED_ID
            WHERE APPOINTMENT.APPROVAL_STATUS = 'Approved' 
            AND strftime('%Y', SCHEDULE.SCHED_DATETIME) = ?
            GROUP BY month
            ORDER BY month
        """
        monthly_revenue = fetch_all(query_monthly, (str(current_year),))
        stats['monthly_revenue'] = {int(row['month']): row['revenue'] for row in monthly_revenue}
        
        # Fill missing months
        for m in range(1, 13):
            if m not in stats['monthly_revenue']:
                stats['monthly_revenue'][m] = 0

        # 4. Service Distribution (Top 5 popular services)
        query_services = """
            SELECT SERVICE.SERVICE_NAME, COUNT(APPOINTMENT.APPOINT_ID) as count
            FROM APPOINTMENT
            JOIN SERVICE ON APPOINTMENT.SERVICE_ID = SERVICE.SERVICE_ID
            GROUP BY SERVICE.SERVICE_NAME
            ORDER BY count DESC
            LIMIT 5
        """
        service_stats = fetch_all(query_services)
        stats['top_services'] = {row['SERVICE_NAME']: row['count'] for row in service_stats}

    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        stats = {
            'status_counts': {'Pending': 0, 'Approved': 0, 'Disapproved': 0},
            'total_revenue': 0,
            'monthly_revenue': {m: 0 for m in range(1, 13)},
            'top_services': {}
        }
    finally:
        conn.close()
        
    return stats
