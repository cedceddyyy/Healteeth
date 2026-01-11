from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dbhelper import (
    get_all_services, get_all_branches, get_schedules_by_branch, get_customer_by_name,
    insert_new_customer, update_customer_in_db, get_user, get_appointments_by_branch,
    get_all_dentists, insert_service, insert_schedule, insert_appointment,
    get_schedule_details_by_id, update_service_in_db, delete_service_in_db,
    update_schedule_in_db, delete_schedule_in_db, update_schedule_status_to_inactive,
    update_appointment_with_user, get_appointment_by_id, update_appointment_approval_status,
    get_appointments_by_status, get_inactive_schedules_by_branch,
    get_branches_by_service, insert_service_branch, delete_service_branch,
    get_available_branches_for_service, get_dashboard_stats, DATABASE_NAME
)
from datetime import datetime
from setup_db import setup_database
import os

# Initialize database only if it doesn't exist
if not os.path.exists(DATABASE_NAME):
    print("Database not found. Initializing...")
    setup_database()
else:
    print("Database found. Skipping initialization.")

app = Flask(__name__)
app.secret_key = 'database123@#$'
app.secret_key = 'database123@#$'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = get_user(username, password)
        
        if user:
            session['user_id'] = user['USER_ID']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard', branch_id=1))  
        else:
            flash('Invalid username or password', 'error')
            return render_template('login.html', error='Invalid credentials.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/select_service/<int:service_id>', methods=['POST'])
def select_service(service_id):
    session['selected_service'] = next(
        (service for service in get_all_services() if service['SERVICE_ID'] == service_id), 
        None
    )
    return redirect(url_for('index'))

@app.route('/select_branch/<int:branch_id>', methods=['POST'])
def select_branch(branch_id):
    selected_branch = next(
        (branch for branch in get_all_branches() if branch['BRANCH_ID'] == branch_id), 
        None
    )
    if selected_branch:
        selected_branch['BRANCH_NAME'] = selected_branch['BRANCH_LOC']  # Add BRANCH_NAME
    session['selected_branch'] = selected_branch
    return redirect(url_for('schedule', branch_id=branch_id))

@app.route('/select_schedule', methods=['POST'])
def select_schedule():
    sched_id = request.form['sched_id']
    sched_slotnum = request.form['sched_slotnum']
    sched_datetime = request.form['sched_datetime']

    # Save selected schedule to session
    session['selected_schedule'] = {
        'sched_id': sched_id,
        'sched_slotnum': sched_slotnum,
        'sched_datetime': sched_datetime
    }

    flash("Schedule selected successfully!", "success")
    return redirect(url_for(
        'display_customer_info', 
        sched_id=sched_id, 
        sched_slotnum=sched_slotnum, 
        sched_datetime=sched_datetime
    ))

@app.route('/')
def index():
    services = get_all_services()
    # Get available branches for each service
    for service in services:
        service['available_branches'] = get_available_branches_for_service(service['SERVICE_ID'])
    return render_template('index.html', pagetitle="Services", services=services)

@app.route('/schedule/<int:branch_id>', methods=['GET', 'POST'])
def schedule(branch_id):
    schedules = get_schedules_by_branch(branch_id)  # Get the schedules for this branch
    return render_template('schedule.html', pagetitle="Select a Schedule", schedules=schedules, branch_id=branch_id)

@app.route('/add_customer', methods=['POST'])
def add_customer():
    # Retrieve personal information from the form
    first_name = request.form['first_name']
    middle_name = request.form['middle_name']
    last_name = request.form['last_name']
    gender = request.form['gender']
    address = request.form['address']
    phone = request.form['phone']
    email = request.form['email']
    birthdate = request.form['birthdate']

    # Retrieve schedule details
    sched_id = request.form['sched_id']
    sched_slotnum = request.form['sched_slotnum']
    sched_datetime = request.form['sched_datetime']
    
    # Check if customer already exists
    existing_customer = get_customer_by_name(first_name, last_name)
    
    if existing_customer:
        # If customer exists, use their data
        customer_data = existing_customer
        flash("Customer already exists. Displaying existing information.", "info")
    else:
        # Insert new customer into the database
        insert_new_customer(first_name, middle_name, last_name, gender, address, phone, email, birthdate)
        
        # Retrieve the newly inserted customer
        customer_data = get_customer_by_name(first_name, last_name)
        flash("New customer information saved successfully!", "success")

    if not customer_data:
        flash("Failed to retrieve customer information.", "error")
        return redirect(url_for('schedule'))

    # Save the customer data in the session
    session['customer_data'] = customer_data

    return redirect(url_for(
        'display_customer_info', 
        sched_id=sched_id, 
        sched_slotnum=sched_slotnum, 
        sched_datetime=sched_datetime
    ))

@app.route('/display_customer_info')
def display_customer_info():
    # Get query parameters for schedule details
    sched_id = request.args.get('sched_id')
    sched_slotnum = request.args.get('sched_slotnum')
    sched_datetime = request.args.get('sched_datetime')

    customer = session.get('customer_data')

    if not customer:
        flash("No customer data available.")
        return redirect(url_for('schedule'))

    # Check if 'CUST_BDATE' is a string and handle the formats
    if isinstance(customer['CUST_BDATE'], str):
        try:
            customer['CUST_BDATE'] = datetime.strptime(customer['CUST_BDATE'], '%a, %d %b %Y %H:%M:%S GMT')
        except ValueError:
            try:
                customer['CUST_BDATE'] = datetime.strptime(customer['CUST_BDATE'], '%Y-%m-%d')
            except ValueError:
                pass

    if isinstance(customer['CUST_BDATE'], datetime):
        customer['CUST_BDATE'] = customer['CUST_BDATE'].strftime('%Y-%m-%d')

    # Save schedule in session
    session['selected_schedule'] = {
        'sched_id': sched_id,
        'sched_slotnum': sched_slotnum,
        'sched_datetime': sched_datetime
    }

    return render_template(
        'display_customer_info.html',
        pagetitle="Personal Information",
        customer=customer,
        schedule=session['selected_schedule']
    )
        
@app.route('/update_customer_info', methods=['POST'])
def update_customer_info():
    customer_data = {
        'CUST_ID': request.form['cust_id'],
        'CUST_FNAME': request.form['first_name'],
        'CUST_MNAME': request.form['middle_name'],
        'CUST_LNAME': request.form['last_name'],
        'CUST_GENDER': request.form['gender'],
        'CUST_ADDRESS': request.form['address'],
        'CUST_PHONE': request.form['phone'],
        'CUST_EMAIL': request.form['email'],
        'CUST_BDATE': request.form['birthdate']  
    }

    try:
        customer_data['CUST_BDATE'] = datetime.strptime(customer_data['CUST_BDATE'], '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid birthdate format.", "error")
        return redirect(url_for('display_customer_info'))

    # Update the customer data in the database
    update_customer_in_db(customer_data)

    updated_customer = get_customer_by_name(customer_data['CUST_FNAME'], customer_data['CUST_LNAME'])

    if not updated_customer:
        flash("Failed to retrieve updated customer information.", "error")
        return redirect(url_for('schedule'))

    session['customer_data'] = updated_customer
    
    sched_id = request.form['sched_id']
    sched_slotnum = request.form['sched_slotnum']
    sched_datetime = request.form['sched_datetime']

    flash('Customer information updated successfully!')
    return redirect(url_for(
        'display_customer_info', 
        sched_id=sched_id, 
        sched_slotnum=sched_slotnum, 
        sched_datetime=sched_datetime
    ))

@app.route('/appointment_form', methods=['GET', 'POST'])
def appointment_form():
    selected_service = session.get('selected_service', {})
    selected_branch = session.get('selected_branch', {})
    selected_schedule = session.get('selected_schedule', {})  # Retrieve schedule from session
    customer_data = session.get('customer_data', {})

    print("Debugging Session Data:")
    print("Selected Service:", selected_service)
    print("Selected Branch:", selected_branch)
    print("Selected Schedule:", selected_schedule)
    print("Customer Data:", customer_data)

    return render_template(
        'appointment_form.html',
        pagetitle="Appointment Form",
        selected_service=selected_service,
        selected_branch=selected_branch,
        selected_schedule=selected_schedule,
        customer_data=customer_data
    )
    
@app.route('/confirm_appointment', methods=['GET', 'POST'])
def confirm_appointment():
    # Get data from session
    selected_service = session.get('selected_service', {})
    selected_branch = session.get('selected_branch', {})
    selected_schedule = session.get('selected_schedule', {})
    customer_data = session.get('customer_data', {})

    if request.method == 'POST':
        # Ensure 'CUST_ID' exists in customer_data
        if 'CUST_ID' not in customer_data:
            flash('Customer ID not found.', 'error')
            return redirect(url_for('appointment_form'))
        
        # Extract the number of teeth to extract
        try:
            numteeth_to_extract = int(request.form.get('numteeth_to_extract', 0))
        except ValueError:
            flash('Invalid number of teeth to extract.', 'error')
            return redirect(url_for('appointment_form'))

        service_name = selected_service.get('SERVICE_NAME', '').lower()
        try:
            service_price = float(selected_service.get('SERVICE_PRICE', 0))
        except ValueError:
            service_price = 0.0

        # Calculate total price
        if service_name == 'extraction':
            total_price = service_price * numteeth_to_extract
        else:
            total_price = service_price

        # Insert appointment into the database
        appointment_id = insert_appointment(
            selected_service['SERVICE_ID'],
            selected_branch['BRANCH_ID'],
            selected_schedule['sched_id'],
            customer_data['CUST_ID'],
            numteeth_to_extract
        )

        # Update schedule status to 'inactive'
        update_schedule_status_to_inactive(selected_schedule['sched_id'])

        # Create an appointment object to display on the confirmation page
        appointment = {
            'service': selected_service,
            'branch': selected_branch,
            'schedule': selected_schedule,
            'customer': customer_data,
            'numteeth_to_extract': numteeth_to_extract,
            'total_price': total_price
        }

        # Render the confirmation page with appointment details (including the total price)
        return render_template('appointment_confirm.html', appointment=appointment)

    return redirect(url_for('appointment_form'))  # In case the POST request fails

# FOR ADMIN/DENTIST/STAFF
@app.route('/appointments', defaults={'branch_id': None})
@app.route('/appointments/<int:branch_id>')
def appointments(branch_id):
    branches = get_all_branches()
    pending_appointments = []
    approved_appointments = []
    disapproved_appointments = []
    
    if branch_id:
        pending_appointments = get_appointments_by_status(branch_id, 'Pending')
        approved_appointments = get_appointments_by_status(branch_id, 'Approved')
        disapproved_appointments = get_appointments_by_status(branch_id, 'Disapproved')
    
    return render_template(
        'appointments.html', 
        pagetitle="Appointments", 
        branches=branches, 
        selected_branch=branch_id, 
        pending_appointments=pending_appointments,
        approved_appointments=approved_appointments,
        disapproved_appointments=disapproved_appointments
    )

@app.route('/services')
def services():
    services = get_all_services()
    branches = get_all_branches()
    # Get available branches for each service
    for service in services:
        service['available_branches'] = get_available_branches_for_service(service['SERVICE_ID'])
    return render_template(
        'services.html', 
        pagetitle="Services", 
        services=services,
        branches=branches
    )   

@app.route('/schedules', defaults={'branch_id': None})
@app.route('/schedules/<int:branch_id>')
def schedules(branch_id):
    schedules = []  
    inactive_schedules = []
    branches = get_all_branches()
    if branch_id:
        schedules = get_schedules_by_branch(branch_id)
        inactive_schedules = get_inactive_schedules_by_branch(branch_id)
    return render_template(
        'schedules.html',
        pagetitle="Schedules",
        branches=branches,
        selected_branch=branch_id,
        schedules=schedules,
        inactive_schedules=inactive_schedules
    )

@app.route('/dashboard')
def dashboard():
    stats = get_dashboard_stats()
    return render_template('dashboard.html', pagetitle="Dashboard", stats=stats)

@app.route('/dentists')
def dentists():
    dentists_list = get_all_dentists()
    return render_template('dentists.html', pagetitle="Dentists", dentists=dentists_list)
    
@app.route('/add_service', methods=['POST'])
def add_service():
    service_name = request.form['service_name']
    service_desc = request.form['service_desc']
    service_price = request.form['service_price']
    service_image = request.form['service_image']

    insert_service(service_name, service_desc, service_price, service_image)

    flash('Service added successfully!', 'success')
    return redirect(url_for('services'))
    
@app.route('/update_service', methods=['POST'])
def update_service():
    service_name = request.form['service_name']
    service_desc = request.form['service_desc']
    service_price = request.form['service_price']
    service_image = request.form['service_image']

    # Call stored procedure to update or insert service
    update_service_in_db(service_name, service_desc, service_price, service_image)
    flash('Service updated successfully!', 'success')
    return redirect(url_for('services'))


@app.route('/delete_service/<string:service_name>', methods=['POST'])
def delete_service(service_name):
    delete_service_in_db(service_name)
    flash('Service deleted successfully!', 'success')
    return redirect(url_for('services'))

@app.route('/add_schedule', methods=['POST'])
def add_schedule():
    branch_id = request.form['branch_id']
    schedule_date = request.form['schedule_date']
    schedule_slot = request.form['schedule_slot']

    insert_schedule(branch_id, schedule_date, schedule_slot)

    flash('Schedule added successfully!', 'success')
    return redirect(url_for('schedules', branch_id=branch_id))  
    
@app.route('/update_schedule', methods=['POST'])
def update_schedule():
    try:
        schedule_id = request.form['schedule_id']
        schedule_date = request.form['schedule_date']
        schedule_slot = request.form['schedule_slot']
        
        update_schedule_in_db(schedule_id, schedule_date, schedule_slot)
        flash('Schedule updated successfully!', 'success')
        return redirect(url_for('schedules'))
    except Exception as e:
        flash(f'Error updating schedule: {str(e)}', 'error')
        return redirect(url_for('schedules'))

@app.route('/delete_schedule/<int:schedule_id>', methods=['POST'])
def delete_schedule(schedule_id):
    try:
        delete_schedule_in_db(schedule_id)
        return '', 200
    except Exception as e:
        return str(e), 500

@app.route('/approve_appointment/<int:appoint_id>', methods=['POST'])
def approve_appointment(appoint_id):
    try:
        update_appointment_approval_status(appoint_id, 'Approved')
        flash('Appointment approved successfully!', 'success')
    except Exception as e:
        flash(f'Error approving appointment: {str(e)}', 'error')
    return redirect(url_for('appointments'))

@app.route('/disapprove_appointment/<int:appoint_id>', methods=['POST'])
def disapprove_appointment(appoint_id):
    try:
        update_appointment_approval_status(appoint_id, 'Disapproved')
        flash('Appointment disapproved successfully!', 'warning')
    except Exception as e:
        flash(f'Error disapproving appointment: {str(e)}', 'error')
    return redirect(url_for('appointments'))

@app.route('/get_service_branches/<int:service_id>')
def get_service_branches(service_id):
    branches = get_branches_by_service(service_id)
    return jsonify(branches)

@app.route('/update_service_branches', methods=['POST'])
def update_service_branches():
    data = request.get_json()
    service_id = data['service_id']
    new_branch_ids = set(data['branch_ids'])
    
    # Get current branches
    current_branches = get_branches_by_service(service_id)
    current_branch_ids = set(str(branch['BRANCH_ID']) for branch in current_branches)
    
    # Remove branches that are no longer selected
    for branch_id in current_branch_ids - new_branch_ids:
        delete_service_branch(service_id, branch_id)
    
    # Add newly selected branches
    for branch_id in new_branch_ids - current_branch_ids:
        insert_service_branch(service_id, branch_id)
    
    flash('Service branches updated successfully!', 'success')
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)
