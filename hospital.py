# hospital.py
from flask import  render_template,redirect,url_for
from flask import Blueprint, request, jsonify, current_app,session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from flask import Flask
from bson import ObjectId
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random
import string
from datetime import datetime

app = Flask(__name__)




hospital_bp = Blueprint('hospital', __name__, template_folder='templates')

app.config['UPLOAD_FOLDER'] = 'static/hospital/'  # Change this path to where you want to store the images


@hospital_bp.route('/hoslogin')
def hoslogin():
    return render_template('hoslogin.html')

@hospital_bp.route('/hospital')
def hospital_dashboard():
    return render_template('hospital.html')

@hospital_bp.route('/register-hospital', methods=['POST'])
def register_hospital():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    address = data.get('address')  # New field
    password = data.get('password')
    role = data.get('role', 'admin')  # Default role is admin for hospital registration

    if not all([name, email, address, password]):
        return jsonify({"success": False, "message": "All fields are required!"}), 400

    # Access the MongoDB instance from the app context
    hospitals_collection = current_app.mongo.db.hospitals

    if hospitals_collection.find_one({"email": email}):
        return jsonify({"success": False, "message": "Email already registered!"}), 400

    hashed_password = generate_password_hash(password)
    hospitals_collection.insert_one({
        "name": name,
        "email": email,
        "address": address,  # Store the address
        "password": hashed_password,
        "role": role  # Store the role
    })

    # Return success message after registration
    return jsonify({"success": True, "message": "Registration successful!You can Login now."}), 200



from flask import session, jsonify, request, current_app
from werkzeug.security import check_password_hash

@hospital_bp.route('/login-hospital', methods=['POST'])
def login_hospital():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    if not all([email, password]):
        return jsonify({"success": False, "message": "All fields are required!"}), 400

    # Access the MongoDB instance from the app context
    hospitals_collection = current_app.mongo.db.hospitals

    try:
        hospital = hospitals_collection.find_one({"email": email})

        if not hospital:
            return jsonify({"success": False, "message": "Email not registered!"}), 401

        # Check if 'password' exists in the document
        if 'password' not in hospital:
            return jsonify({"success": False, "message": "Password field is missing in the database!"}), 500

        if not check_password_hash(hospital['password'], password):
            return jsonify({"success": False, "message": "Incorrect password!"}), 401

        # Login is successful, set the email, name, and role in the session
        session['hospital_email'] = email
        session['hospital_name'] = hospital.get("name")
        session['hospital_role'] = hospital.get("role", "admin")  # Default to admin if role not specified

        return jsonify({"success": True, "message": "Login successful!", "role": hospital.get("role", "admin")}), 200
    except Exception as e:
        current_app.logger.error(f"Error during login: {str(e)}")
        return jsonify({"success": False, "message": "Internal server error!"}), 500


@hospital_bp.route('/get-hospital-details', methods=['GET'])
def get_hospital_details():
    # Fetch the logged-in hospital's email from the session
    email = session.get('hospital_email')
    if not email:
        return jsonify({"success": False, "message": "Not logged in!"}), 401

    # Access MongoDB to fetch the hospital details
    hospitals_collection = current_app.mongo.db.hospitals
    hospital = hospitals_collection.find_one({"email": email})
    if not hospital:
        return jsonify({"success": False, "message": "Hospital not found!"}), 404

    # Return the hospital details, excluding the password
    hospital_data = {
        "name": hospital.get("name"),
        "phone": hospital.get("phone", ""),
        "address": hospital.get("address", ""),
        "email": hospital.get("email"),
        "profile_picture": hospital.get("profile_picture", "")  # Profile picture field
    }

    return jsonify({"success": True, "data": hospital_data}), 200

#### Step 2: Saving updated hospital details
@hospital_bp.route('/update-hospital-details', methods=['POST'])
def update_hospital_details():
    # Check if the hospital is logged in
    email = session.get('hospital_email')
    if not email:
        return jsonify({"success": False, "message": "Not logged in!"}), 401

    data = request.form  # Use request.form for text fields when file uploads are involved
    name = data.get('name')
    phone = data.get('phone')
    address = data.get('address')

    # Validate required fields
    if not all([name, phone, address]):
        return jsonify({"success": False, "message": "All fields are required!"}), 400

    # Access MongoDB
    hospitals_collection = current_app.mongo.db.hospitals

    # Update data dictionary
    update_data = {
        "name": name,
        "phone": phone,
        "address": address,
    }

    # Handle profile picture upload
    profile_picture = request.files.get('profile_picture')
    if profile_picture:
        try:
            # Ensure the upload folder exists
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)

            # Save the file
            filename = secure_filename(profile_picture.filename)
            profile_picture_path = os.path.join(upload_folder, filename)
            profile_picture.save(profile_picture_path)

            # Add the file path to the update data
            update_data['profile_picture'] = profile_picture_path
        except Exception as e:
            return jsonify({"success": False, "message": f"File upload failed: {str(e)}"}), 500

    # Update hospital details in the database
    try:
        hospitals_collection.update_one({"email": email}, {"$set": update_data})
    except Exception as e:
        return jsonify({"success": False, "message": f"Database update failed: {str(e)}"}), 500

    return jsonify({"success": True, "message": "Hospital details updated successfully!"}), 200



def get_logged_in_email():
    """Check if the hospital is logged in by verifying the session."""
    print("[DEBUG] get_logged_in_email called")
    print(f"[DEBUG] Current session: {session}")
    email = session.get('hospital_email')
    print(f"[DEBUG] Retrieved email from session: {email}")
    if not email:
        print("[DEBUG] No email found in session, returning not logged in error")
        return None, jsonify({"success": False, "message": "Not logged in!"})
    print(f"[DEBUG] Returning email: {email}")
    return email, None


def get_logged_in_role():
    """Get the role of the logged-in hospital user."""
    return session.get('hospital_role', 'admin')  # Default to admin if role not in session


@hospital_bp.route('/add-staff', methods=['POST'])
def add_staff():
    """Add a new staff member (nurse) to the hospital."""
    try:
        # Check if the user is logged in and is an admin
        email, error_response = get_logged_in_email()
        if error_response:
            return error_response
            
        # Only admins can add staff
        role = get_logged_in_role()
        if role != 'admin':
            return jsonify({"success": False, "message": "Unauthorized. Only administrators can add staff."}), 403
            
        # Get the hospital data
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": email})
        if not hospital_data:
            return jsonify({"error": "Hospital not found"}), 404
            
        # Get staff data from request
        data = request.json
        staff_name = data.get('name')
        staff_email = data.get('email')
        staff_password = data.get('password')
        staff_role = data.get('role', 'nurse')  # Default role is nurse
        
        if not all([staff_name, staff_email, staff_password]):
            return jsonify({"success": False, "message": "All fields are required!"}), 400
            
        # Check if email already exists
        if current_app.mongo.db.hospitals.find_one({"email": staff_email}):
            return jsonify({"success": False, "message": "Email already registered!"}), 400
            
        # Create the staff member
        hashed_password = generate_password_hash(staff_password)
        staff_data = {
            "name": staff_name,
            "email": staff_email,
            "password": hashed_password,
            "role": staff_role,
            "hospital_id": str(hospital_data["_id"]),
            "hospital_name": hospital_data["name"],
            "address": hospital_data["address"]
        }
        
        # Insert the staff member
        result = current_app.mongo.db.hospitals.insert_one(staff_data)
        
        return jsonify({
            "success": True,
            "message": f"{staff_role.capitalize()} added successfully!",
            "staff_id": str(result.inserted_id)
        }), 201
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



@hospital_bp.route('/get-staff', methods=['GET'])
def get_staff():
    """Get all staff members for the logged-in hospital."""
    try:
        # Check if the user is logged in
        email, error_response = get_logged_in_email()
        if error_response:
            return error_response
            
        # Get the hospital data
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": email})
        if not hospital_data:
            return jsonify({"error": "Hospital not found"}), 404
            
        # Get all staff members for this hospital
        staff_members = list(current_app.mongo.db.hospitals.find({
            "hospital_id": str(hospital_data["_id"]),
            "role": {"$in": ["nurse", "admin"]}
        }))
        
        # Convert ObjectId to string for JSON serialization
        for staff in staff_members:
            staff["_id"] = str(staff["_id"])
            # Remove password for security
            if "password" in staff:
                del staff["password"]
        
        return jsonify(staff_members), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@hospital_bp.route('/predict-opd-appointments', methods=['GET'])
def predict_opd_appointments():
    try:
        print("[DEBUG] Starting OPD prediction function")
        # Get the logged-in hospital email
        hospital_email, error_response = get_logged_in_email()
        print(f"[DEBUG] get_logged_in_email returned: email={hospital_email}, error_response={error_response}")
        if error_response:
            print(f"[DEBUG] Error in get_logged_in_email: {error_response}")
            return error_response

        # Get the hospital data
        print(f"[DEBUG] Looking up hospital with email: {hospital_email}")
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": hospital_email})
        if not hospital_data:
            print(f"[DEBUG] Hospital not found for email: {hospital_email}")
            return jsonify({"error": "Hospital not found"}), 404

        hospital_name = hospital_data["name"]
        print(f"[DEBUG] Found hospital: {hospital_name}")
        
        # Get today's date in YYYY-MM-DD format
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"[DEBUG] Today's date: {today}")
        
        # Find all appointments for today at this hospital
        print(f"[DEBUG] Searching for appointments at hospital: {hospital_name}")
        appointments = list(current_app.mongo.db.appointments.find({
            "doctor_hospital": hospital_name,
        }))
        print(f"[DEBUG] Found {len(appointments)} appointments")
        
        # Initialize counters for different time slots
        morning_count = 0    # 9AM-12PM
        afternoon_count = 0  # 12PM-4PM
        evening_count = 0    # 4PM-8PM
        
        # Categorize appointments by time slot
        for i, appointment in enumerate(appointments):
            try:
                print(f"[DEBUG] Processing appointment {i+1}: {appointment}")
                # Extract time from date_time (format: YYYY-MM-DDTHH:MM)
                time_part = appointment['date_time'].split('T')[1]
                hour = int(time_part.split(':')[0])
                print(f"[DEBUG] Extracted hour: {hour}")
                
                # Categorize based on hour
                if 9 <= hour < 12:
                    morning_count += 1
                    print(f"[DEBUG] Added to morning count: {morning_count}")
                elif 12 <= hour < 16:
                    afternoon_count += 1
                    print(f"[DEBUG] Added to afternoon count: {afternoon_count}")
                elif 16 <= hour < 20:
                    evening_count += 1
                    print(f"[DEBUG] Added to evening count: {evening_count}")
                else:
                    print(f"[DEBUG] Hour {hour} outside of categorized time slots")
            except (IndexError, ValueError) as e:
                print(f"[DEBUG] Error processing appointment {i+1}: {str(e)}")
                # Skip appointments with invalid time format
                continue
        
        print(f"[DEBUG] Final counts - Morning: {morning_count}, Afternoon: {afternoon_count}, Evening: {evening_count}")
        
        # Determine volume levels based on counts
        def get_volume_level(count):
            if count < 5:
                return "Low"
            elif count < 10:
                return "Medium"
            else:
                return "High"
        
        morning_level = get_volume_level(morning_count)
        afternoon_level = get_volume_level(afternoon_count)
        evening_level = get_volume_level(evening_count)
        print(f"[DEBUG] Volume levels - Morning: {morning_level}, Afternoon: {afternoon_level}, Evening: {evening_level}")
        
        # Determine overall forecast
        total_count = morning_count + afternoon_count + evening_count
        print(f"[DEBUG] Total appointment count: {total_count}")
        if total_count < 10:
            overall_forecast = "Low Volume Expected"
        elif total_count < 20:
            overall_forecast = "Medium Volume Expected"
        else:
            overall_forecast = "High Volume Expected"
        print(f"[DEBUG] Overall forecast: {overall_forecast}")
        
        # Prepare response
        prediction = {
            "overall": overall_forecast,
            "morning": {
                "count": morning_count,
                "level": morning_level
            },
            "afternoon": {
                "count": afternoon_count,
                "level": afternoon_level
            },
            "evening": {
                "count": evening_count,
                "level": evening_level
            }
        }
        
        print(f"[DEBUG] Returning prediction response: {prediction}")
        return jsonify({"prediction": prediction}), 200
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"[DEBUG] Error in OPD prediction: {str(e)}")
        print(f"[DEBUG] Traceback: {error_traceback}")
        return jsonify({"error": str(e), "traceback": error_traceback}), 500


@hospital_bp.route('/delete-staff/<staff_id>', methods=['DELETE'])
def delete_staff(staff_id):
    """Delete a staff member from the hospital."""
    try:
        # Check if the user is logged in and is an admin
        email, error_response = get_logged_in_email()
        if error_response:
            return error_response
            
        # Only admins can delete staff
        role = get_logged_in_role()
        if role != 'admin':
            return jsonify({"success": False, "message": "Unauthorized. Only administrators can delete staff."}), 403
            
        # Get the hospital data
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": email})
        if not hospital_data:
            return jsonify({"success": False, "message": "Hospital not found"}), 404
            
        # Get the hospital ID
        hospital_id = str(hospital_data["_id"])
        
        try:
            # Convert string ID to ObjectId
            staff_obj_id = ObjectId(staff_id)
            
            # Find the staff member to ensure they belong to this hospital
            staff = current_app.mongo.db.hospitals.find_one({"_id": staff_obj_id})
            
            if not staff:
                return jsonify({"success": False, "message": "Staff member not found"}), 404
            
            # Check if the staff belongs to this hospital
            if 'hospital_id' not in staff or staff['hospital_id'] != hospital_id:
                return jsonify({"success": False, "message": "Unauthorized. This staff member does not belong to your hospital"}), 403
            
            # Delete the staff member
            result = current_app.mongo.db.hospitals.delete_one({"_id": staff_obj_id})
            
            if result.deleted_count > 0:
                return jsonify({"success": True, "message": "Staff member deleted successfully"}), 200
            else:
                return jsonify({"success": False, "message": "Failed to delete staff member"}), 500
                
        except Exception as e:
            return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@hospital_bp.route('/get-doctors', methods=['GET'])
def get_doctors():
    email, error_response = get_logged_in_email()
    if error_response:
        return error_response

    # Fetch the hospital name using email
    hospitals_collection = current_app.mongo.db.hospitals
    hospital = hospitals_collection.find_one({"email": email})
    if not hospital:
        return jsonify({"success": False, "message": "Hospital not found!"}), 404

    hospital_name = hospital.get("name")

    # Fetch doctors belonging to this hospital
    doctors_collection = current_app.mongo.db.doctors
    doctors = list(doctors_collection.find({"hospital": hospital_name}))

    # Transform the data for frontend consumption
    doctor_data = [
        {
            "name": doctor.get("name"),
            "specialization": doctor.get("specialization"),
            "availability": doctor.get("availability"),
            "description": doctor.get("description", {}),
        }
        for doctor in doctors
    ]

    return jsonify({"success": True, "data": doctor_data}), 200


@hospital_bp.route('/update-doctor-availability', methods=['POST'])
def update_doctor_availability():
    email, error_response = get_logged_in_email()
    if error_response:
        return error_response

    data = request.json
    doctor_name = data.get("name")
    new_availability = data.get("availability")

    if not all([doctor_name, new_availability]):
        return jsonify({"success": False, "message": "Doctor name and availability are required!"}), 400

    # Update the doctor's availability
    doctors_collection = current_app.mongo.db.doctors
    doctor = doctors_collection.find_one({"name": doctor_name})

    if not doctor:
        return jsonify({"success": False, "message": "Doctor not found!"}), 404

    # Append new availability to the existing availability
    existing_availability = doctor.get("availability", {})
    for date, slots in new_availability.items():
        if date not in existing_availability:
            existing_availability[date] = slots  # Add new date if not already present
        else:
            # Append the new time slots for the existing date
            existing_availability[date].update(slots)

    # Save the updated availability
    result = doctors_collection.update_one(
        {"name": doctor_name},
        {"$set": {"availability": existing_availability}}
    )

    return jsonify({"success": True, "message": "Availability updated successfully!"}), 200



@hospital_bp.before_app_request
def setup_upload_folder():
    """Ensure the upload folder exists."""
    upload_folder = current_app.config.get('HOSPITAL_UPLOAD_FOLDER', 'hospital_uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

@hospital_bp.route('/get_appointments', methods=['GET'])
def get_appointments():
    # Fetch the logged-in hospital's name from the session
    hospital_name = session.get('hospital_name')
    if not hospital_name:
        return jsonify({"success": False, "message": "Not logged in!"}), 401

    # Use the 'mongo' object to access the 'appointments' collection
    appointments_collection = current_app.mongo.db.appointments
    appointments = list(appointments_collection.find({"doctor_hospital": hospital_name}, {'_id': 0}))
    return jsonify(appointments)

@hospital_bp.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    appointment_id = data['appointment_id']
    status = data['status']

    appointments_collection = current_app.mongo.db.appointments
    appointments_collection.update_one(
        {'appointment_id': appointment_id},
        {'$set': {'status': status}}
    )
    return jsonify({'success': True})



def send_email(to_email, subject, body):
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "auramed1628@gmail.com"  # Replace with your email
        sender_password = "kxmg wngq ksyp pzss"  # Replace with your app-specific password

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, message.as_string())
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


@hospital_bp.route('/upload_prescription', methods=['POST'])
def upload_prescription():
    appointment_id = request.form.get('appointment_id')
    file = request.files.get('prescription')

    if not appointment_id or not file:
        return jsonify({'success': False, 'error': 'Appointment ID and file are required'}), 400

    upload_folder = current_app.config['HOSPITAL_UPLOAD_FOLDER']
    filename = file.filename
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)

    relative_file_path = os.path.join('static', 'uploads', filename).replace("\\", "/")
    appointments_collection = current_app.mongo.db.appointments
    uploads_collection = current_app.mongo.db.uploads

    appointment = appointments_collection.find_one({'appointment_id': appointment_id})
    if not appointment:
        return jsonify({'success': False, 'error': 'Invalid appointment ID'}), 400

    patient_email = appointment.get('patient_email')
    hospital_name = appointment.get('doctor_hospital', 'Unknown')
    doctor_name = appointment.get('doctor_name', 'Unknown')

    new_prescription = {
        'filename': filename,
        'uploaded_at': datetime.utcnow(),
        'file_path': relative_file_path
    }

    if uploads_collection.find_one({'email': patient_email}):
        uploads_collection.update_one(
            {'email': patient_email},
            {'$push': {'prescription': new_prescription}}
        )
    else:
        uploads_collection.insert_one({
            'email': patient_email,
            'prescription': [new_prescription]
        })

    appointments_collection.update_one(
        {'appointment_id': appointment_id},
        {'$set': {'prescription': relative_file_path}}
    )

    reminder_message = f"Prescription uploaded for appointment at {hospital_name} with {doctor_name}."
    users_collection = current_app.mongo.db.users
    users_collection.update_one(
        {'email': patient_email},
        {'$push': {'reminders': reminder_message}}
    )

    # Send email notification
    subject = "Prescription Uploaded Successfully"
    body = (
        f"Dear Patient,\n\n"
        f"Your prescription for the appointment at {hospital_name} with Dr. {doctor_name} has been successfully uploaded.\n\n"
        f"File Name: {filename}\n"
        f"Access it from your portal.\n\n"
        f"Best Regards,\nHospital Team"
    )
    email_status = send_email(patient_email, subject, body)
    if not email_status:
        return jsonify({'success': True, 'message': 'Prescription uploaded but email notification failed'}), 200

    return jsonify({'success': True, 'message': 'Prescription uploaded and email notification sent successfully'}), 200




@hospital_bp.route('/get_tests', methods=['GET'], endpoint='hospital_get_tests')
def get_tests():
    """Fetch all tests from the database for the logged-in hospital and return them as JSON."""
    hospital_name = session.get('hospital_name')
    if not hospital_name:
        return jsonify({"success": False, "message": "Not logged in!"}), 401

    tests = list(current_app.mongo.db.tests.find({"hospital_name": hospital_name}))
    for test in tests:
        test['_id'] = str(test['_id'])  # Convert ObjectId to string
    return jsonify(tests)



@hospital_bp.route('/upload_report', methods=['POST'], endpoint='hospital_upload_report')
def upload_report():
    test_slot_code = request.form.get('test_slot_code')
    file = request.files.get('file')

    if not test_slot_code:
        return jsonify({'error': 'Test slot code is required'}), 400
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(current_app.root_path, 'static/uploads', filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    file.save(save_path)

    test = current_app.mongo.db.tests.find_one({'test_slot_code': test_slot_code})
    if not test:
        return jsonify({'error': 'Test not found'}), 404

    patient_email = test.get('patient_email', 'Unknown')
    hospital_name = test.get('hospital_name', 'Unknown')
    test_type = test.get('test_type', 'Unknown')

    current_app.mongo.db.uploads.update_one(
        {'email': patient_email},
        {'$push': {'report': {
            'filename': filename,
            'uploaded_at': datetime.utcnow(),
            'file_path': f"/static/uploads/{filename}"
        }}},
        upsert=True
    )

    current_app.mongo.db.tests.update_one(
        {'test_slot_code': test_slot_code},
        {'$set': {
            'report': f"/static/uploads/{filename}",
            'status': 'completed'
        }}
    )

    reminder_message = f"Your report '{filename}' for the test '{test_type}' has been successfully uploaded."
    users_collection = current_app.mongo.db.users
    users_collection.update_one(
        {'email': patient_email},
        {'$push': {'reminders': reminder_message}}
    )

    # Send email notification
    subject = "Test Report Uploaded Successfully"
    body = (
        f"Dear Patient,\n\n"
        f"Your report for the test '{test_type}' at {hospital_name} has been successfully uploaded.\n\n"
        f"File Name: {filename}\n"
        f"Access it from your portal.\n\n"
        f"Best Regards,\nHospital Team"
    )
    email_status = send_email(patient_email, subject, body)
    if not email_status:
        return jsonify({'message': 'Report uploaded but email notification failed', 'filename': filename}), 200

    return jsonify({'message': 'Report uploaded and email notification sent successfully', 'filename': filename}), 200




@hospital_bp.route('/update_status_test', methods=['POST'], endpoint='hospital_update_status')
def update_status():
    """Update the test status to 'completed'."""
    data = request.json
    test_slot_code = data.get('test_slot_code')  # Match with the frontend
    if not test_slot_code:
        return jsonify({'error': 'Test slot code is required'}), 400

    result = current_app.mongo.db.tests.update_one(
        {'test_slot_code': test_slot_code},
        {'$set': {'status': 'completed'}}
    )

    if result.modified_count == 0:
        return jsonify({'error': 'Test not found or already updated'}), 404

    return jsonify({'message': 'Test status updated to completed'}), 200


@hospital_bp.route('/bed_availability', methods=['GET'])
def get_bed_availability():
    """Fetch the bed availability from the database for the logged-in hospital."""
    hospital_name = session.get('hospital_name')
    if not hospital_name:
        return jsonify({"success": False, "message": "Not logged in!"}), 401

    # First try to get data from the beds collection
    beds_collection = current_app.mongo.db.beds
    hospital_beds = list(beds_collection.find({"hospital_name": hospital_name}))
    
    if hospital_beds:
        # Group beds by floor and type
        beds_by_floor = {}
        for bed in hospital_beds:
            floor = bed.get("floor")
            if floor not in beds_by_floor:
                beds_by_floor[floor] = []
            beds_by_floor[floor].append({
                "bed_id": bed.get("bed_id"),
                "bed_type": bed.get("bed_type"),
                "status": bed.get("status")
            })
        
        # Calculate summary statistics
        total_beds = len(hospital_beds)
        available_beds = sum(1 for bed in hospital_beds if bed.get("status") == "available")
        occupied_beds = sum(1 for bed in hospital_beds if bed.get("status") == "occupied")
        reserved_beds = sum(1 for bed in hospital_beds if bed.get("status") == "reserved")
        maintenance_beds = sum(1 for bed in hospital_beds if bed.get("status") == "maintenance")
        
        return jsonify({
            "beds_by_floor": beds_by_floor,
            "summary": {
                "total": total_beds,
                "available": available_beds,
                "occupied": occupied_beds,
                "reserved": reserved_beds,
                "maintenance": maintenance_beds
            }
        })
    
    # Fallback to the old method if no beds found in beds collection
    hospitals_collection = current_app.mongo.db.hospitals
    hospital_data = hospitals_collection.find_one({"name": hospital_name})

    if not hospital_data or 'bed_availability' not in hospital_data:
        return jsonify([])

    bed_availability = hospital_data['bed_availability']
    formatted_data = [
        {"type": bed_type, "available": count}
        for bed_type, count in bed_availability.items()
    ]

    return jsonify(formatted_data)

@hospital_bp.route('/update_bed', methods=['POST'])
def update_bed():
    """Update the bed availability in the database."""
    data = request.json
    bed_type = data.get('type')
    available = data.get('available')

    if not bed_type or available is None:
        return jsonify({"error": "Invalid input"}), 400

    hospitals_collection = current_app.mongo.db.hospitals
    
    # Update the specific bed type
    hospitals_collection.update_one(
        {},
        {"$set": {f"bed_availability.{bed_type}": available}}
    )

    return jsonify({"message": "Bed availability updated"})

@hospital_bp.route('/update_bed_status', methods=['POST'])
def update_bed_status():
    """Update the status of a specific bed in the beds collection."""
    data = request.json
    bed_id = data.get('bed_id')
    new_status = data.get('status')
    
    if not bed_id or not new_status:
        return jsonify({"error": "Bed ID and status are required"}), 400
        
    if new_status not in ["available", "occupied", "reserved", "maintenance"]:
        return jsonify({"error": "Invalid status. Must be one of: available, occupied, reserved, maintenance"}), 400
    
    hospital_name = session.get('hospital_name')
    if not hospital_name:
        return jsonify({"success": False, "message": "Not logged in!"}), 401
    
    beds_collection = current_app.mongo.db.beds
    
    # Update the bed status
    result = beds_collection.update_one(
        {"bed_id": bed_id, "hospital_name": hospital_name},
        {"$set": {"status": new_status}}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Bed not found"}), 404
        
    return jsonify({"message": "Bed status updated successfully"})




@hospital_bp.route('/add-doctor', methods=['POST'])
def add_doctor():
    """
    Route to add a new doctor to the database.
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid data"}), 400

        # Access the MongoDB collection using current_app
        
        doctors_collection = current_app.mongo.db.doctors

        # Insert doctor data into the "doctors" collection
        doctors_collection.insert_one(data)
        return jsonify({"message": "Doctor added successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@hospital_bp.route('/get_test_slots', methods=['GET'])
def get_test_slots():
    hospital_name = session.get('hospital_name')
    if not hospital_name:
        return jsonify({"success": False, "message": "Not logged in!"}), 401

    try:
        db = current_app.mongo.db
        hospital_data = db.hospitals.find_one({"name": hospital_name})
        if not hospital_data or "test_availability" not in hospital_data:
            return jsonify({}), 200

        return jsonify(hospital_data["test_availability"]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@hospital_bp.route('/update_test_slot', methods=['POST'])
def update_test_slot():
    try:
        db = current_app.mongo.db
        data = request.json

        # Extract fields from the request
        category = data.get("category")
        test_name = data.get("testName")
        price = data.get("price")
        date = data.get("date")
        time = data.get("time")
        slots = data.get("slots")

        if not (category and test_name and price and date and time and slots):
            return jsonify({"error": "Missing required fields."}), 400

        # Fetch or create the hospital document
        hospital_data = db.hospitals.find_one()
        if not hospital_data:
            hospital_data = {
                "test_availability": {
                    category: {
                        test_name: {
                            "price": price,
                            date: {time: {"slots": int(slots)}}
                        }
                    }
                }
            }
            db.hospitals.insert_one(hospital_data)
        else:
            # Update or initialize test_availability
            test_availability = hospital_data.get("test_availability", {})

            # Add category if it doesn't exist
            if category not in test_availability:
                test_availability[category] = {}

            # Add test name if it doesn't exist
            if test_name not in test_availability[category]:
                test_availability[category][test_name] = {"price": price}
            else:
                # Update the price if it has changed
                test_availability[category][test_name]["price"] = price

            # Add or update the date and time slots
            if date not in test_availability[category][test_name]:
                test_availability[category][test_name][date] = {}

            test_availability[category][test_name][date][time] = {"slots": int(slots)}

            # Save the updated test_availability back to the database
            db.hospitals.update_one(
                {"_id": hospital_data["_id"]},
                {"$set": {"test_availability": test_availability}}
            )

        return jsonify({"message": "Test slot updated successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Patient Admission Routes
@hospital_bp.route('/admit-patient', methods=['POST'])
def admit_patient():
    try:
        # Get the logged-in hospital email
        hospital_email, error_response = get_logged_in_email()
        if error_response:
            return error_response

        # Get the hospital data
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": hospital_email})
        if not hospital_data:
            return jsonify({"error": "Hospital not found"}), 404

        # Get patient data from request
        patient_data = request.json
        
        # Add hospital information to patient data
        patient_data["hospital_id"] = str(hospital_data["_id"])
        patient_data["hospital_name"] = hospital_data["name"]
        patient_data["admission_status"] = "Admitted"
        patient_data["admission_timestamp"] = datetime.now()
        
        # Check if we have the new format with floor and bed_id directly
        if "floor" in patient_data and "bed_id" in patient_data and patient_data["floor"] and patient_data["bed_id"]:
            # We already have the correct format, just update the bed status
            beds_collection = current_app.mongo.db.beds
            
            # Create a query to find the exact bed
            bed_query = {
                "hospital_id": ObjectId(patient_data["hospital_id"]),
                "bed_id": patient_data["bed_id"],
                "$or": [
                    {"floor": patient_data["floor"]},
                    {"floor": int(patient_data["floor"]) if patient_data["floor"].isdigit() else patient_data["floor"]}
                ]
            }
            
            # Update the bed status
            beds_collection.update_one(
                bed_query,
                {"$set": {"status": "occupied"}}
            )
            
            # Add room_id for compatibility with existing code
            patient_data["room"] = patient_data["bed_id"].split("-")[1] if "-" in patient_data["bed_id"] else patient_data["bed_id"]
            patient_data["room_id"] = f"{patient_data['floor']}-{patient_data['room']}"
        
        # Fallback to the old parsing method if we don't have the new format
        elif "bed_type" in patient_data and " - Floor " in patient_data["bed_type"] and " Room " in patient_data["bed_type"]:
            try:
                bed_info = patient_data["bed_type"]
                bed_type = bed_info.split(" - Floor ")[0]
                floor_room = bed_info.split(" - Floor ")[1]
                floor = floor_room.split(" Room ")[0]
                room = floor_room.split(" Room ")[1]
                
                # Add room information to patient data
                patient_data["bed_type"] = bed_type
                patient_data["floor"] = floor
                patient_data["room"] = room
                patient_data["room_id"] = f"{floor}-{room}"
                
                # Update the corresponding bed in the beds collection to mark it as occupied
                beds_collection = current_app.mongo.db.beds
                
                # Try different bed_id formats to ensure we find the correct bed
                possible_bed_ids = [
                    f"G{floor}-{room}",  # Format: G1-01
                    f"{floor}-{room}",    # Format: 1-01
                    room                  # Format: 01 (just the room number)
                ]
                
                # Create a query with multiple possible bed_id formats
                bed_query = {
                    "hospital_id": ObjectId(patient_data["hospital_id"]),
                    "$or": [
                        {"floor": floor},
                        {"floor": int(floor) if floor.isdigit() else floor}
                    ],
                    "bed_id": {"$in": possible_bed_ids}
                }
                
                # Update the bed status
                beds_collection.update_one(
                    bed_query,
                    {"$set": {"status": "occupied"}}
                )
                
                # If no bed was updated with the above query, try a more flexible approach
                # by looking for beds on the correct floor with a bed_id containing the room number
                if beds_collection.find_one(bed_query) is None:
                    beds_collection.update_one(
                        {
                            "hospital_id": ObjectId(patient_data["hospital_id"]),
                            "$or": [
                                {"floor": floor},
                                {"floor": int(floor) if floor.isdigit() else floor}
                            ],
                            "bed_id": {"$regex": room}
                        },
                        {"$set": {"status": "occupied"}}
                    )
            except Exception as e:
                print(f"Error parsing bed format or updating bed status: {e}")
                # If parsing fails, keep the original bed_type
                pass
        
        # Insert patient into database
        result = current_app.mongo.db.patients.insert_one(patient_data)
        
        # Update bed availability
        bed_type_original = patient_data["bed_type"]
        bed_availability = hospital_data.get("bed_availability", {})
        
        if bed_type_original in bed_availability and bed_availability[bed_type_original] > 0:
            bed_availability[bed_type_original] -= 1
            current_app.mongo.db.hospitals.update_one(
                {"_id": hospital_data["_id"]},
                {"$set": {"bed_availability": bed_availability}}
            )
        
        # Create an empty patient_daily_data collection entry for this patient
        patient_daily_data = {
            "patient_id": str(result.inserted_id),
            "hospital_id": str(hospital_data["_id"]),
            "patient_name": patient_data["name"],
            "room_id": patient_data.get("room_id", ""),
            "floor": patient_data.get("floor", ""),
            "room": patient_data.get("room", ""),
            "created_at": datetime.now(),
            "daily_records": []
        }
        
        current_app.mongo.db.patient_daily_data.insert_one(patient_daily_data)
        
        return jsonify({
            "message": "Patient admitted successfully",
            "patient_id": str(result.inserted_id)
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@hospital_bp.route('/get-admitted-patients', methods=['GET'])
def get_admitted_patients():
    try:
        # Get the logged-in hospital email
        hospital_email, error_response = get_logged_in_email()
        if error_response:
            return error_response

        # Get the hospital data
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": hospital_email})
        if not hospital_data:
            return jsonify({"error": "Hospital not found"}), 404

        # Get all admitted patients for this hospital
        patients = list(current_app.mongo.db.patients.find({
            "hospital_id": str(hospital_data["_id"]),
            "admission_status": "Admitted"
        }))
        
        # Convert ObjectId to string for JSON serialization
        for patient in patients:
            patient["_id"] = str(patient["_id"])
        
        return jsonify(patients), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@hospital_bp.route('/get-patient/<patient_id>', methods=['GET'])
def get_patient(patient_id):
    try:
        # Get the logged-in hospital email
        hospital_email, error_response = get_logged_in_email()
        if error_response:
            return error_response

        # Get the hospital data
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": hospital_email})
        if not hospital_data:
            return jsonify({"error": "Hospital not found"}), 404

        # Get patient data
        patient = current_app.mongo.db.patients.find_one({
            "_id": ObjectId(patient_id),
            "hospital_id": str(hospital_data["_id"])
        })
        
        if not patient:
            return jsonify({"error": "Patient not found"}), 404
        
        # Convert ObjectId to string for JSON serialization
        patient["_id"] = str(patient["_id"])
        
        return jsonify(patient), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Patient Daily Report Routes
@hospital_bp.route('/submit-patient-report', methods=['POST'])
def submit_patient_report():
    try:
        # Get the logged-in hospital email
        hospital_email, error_response = get_logged_in_email()
        if error_response:
            return error_response

        # Get the hospital data
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": hospital_email})
        if not hospital_data:
            return jsonify({"error": "Hospital not found"}), 404

        # Get report data from request
        report_data = request.json
        
        # Get patient data
        patient = current_app.mongo.db.patients.find_one({
            "_id": ObjectId(report_data["patient_id"]),
            "hospital_id": str(hospital_data["_id"])
        })
        
        if not patient:
            return jsonify({"error": "Patient not found"}), 404
        
        # Add hospital and patient information to report data
        report_data["hospital_id"] = str(hospital_data["_id"])
        report_data["hospital_name"] = hospital_data["name"]
        report_data["patient_name"] = patient["name"]
        report_data["patient_email"] = patient.get("email", "")
        report_data["patient_phone"] = patient.get("phone", "")
        report_data["created_at"] = datetime.now()
        report_data["notification_sent"] = False
        
        # Insert report into database
        result = current_app.mongo.db.patient_reports.insert_one(report_data)
        
        # Schedule notification to be sent (this would be handled by a background task)
        # For now, we'll send it immediately
        send_report_notification(str(result.inserted_id))
        
        return jsonify({
            "message": "Patient report submitted successfully",
            "report_id": str(result.inserted_id)
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@hospital_bp.route('/get-patient-reports', methods=['GET'])
def get_patient_reports():
    try:
        # Get the logged-in hospital email
        hospital_email, error_response = get_logged_in_email()
        if error_response:
            return error_response

        # Get the hospital data
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": hospital_email})
        if not hospital_data:
            return jsonify({"error": "Hospital not found"}), 404

        # Get all reports for this hospital
        reports = list(current_app.mongo.db.patient_reports.find({
            "hospital_id": str(hospital_data["_id"])
        }).sort("created_at", -1))  # Sort by creation date, newest first
        
        # Convert ObjectId to string for JSON serialization
        for report in reports:
            report["_id"] = str(report["_id"])
            # Convert datetime objects to ISO format strings
            if "created_at" in report:
                report["created_at"] = report["created_at"].isoformat()
        
        return jsonify(reports), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@hospital_bp.route('/get-patient-report/<report_id>', methods=['GET'])
def get_patient_report(report_id):
    try:
        # Get the logged-in hospital email
        hospital_email, error_response = get_logged_in_email()
        if error_response:
            return error_response

        # Get the hospital data
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": hospital_email})
        if not hospital_data:
            return jsonify({"error": "Hospital not found"}), 404

        # Get the specific report
        report = current_app.mongo.db.patient_reports.find_one({
            "_id": ObjectId(report_id),
            "hospital_id": str(hospital_data["_id"])
        })
        
        if not report:
            return jsonify({"error": "Report not found"}), 404
        
        # Convert ObjectId to string for JSON serialization
        report["_id"] = str(report["_id"])
        
        # Convert datetime objects to ISO format strings
        if "created_at" in report:
            report["created_at"] = report["created_at"].isoformat()
        
        return jsonify(report), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@hospital_bp.route('/resend-report-notification/<report_id>', methods=['POST'])
def resend_report_notification(report_id):
    try:
        # Get the logged-in hospital email
        hospital_email, error_response = get_logged_in_email()
        if error_response:
            return error_response

        # Get the hospital data
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": hospital_email})
        if not hospital_data:
            return jsonify({"error": "Hospital not found"}), 404

        # Send the notification
        success = send_report_notification(report_id)
        
        if success:
            return jsonify({"success": True, "message": "Notification sent successfully"}), 200
        else:
            return jsonify({"success": False, "error": "Failed to send notification"}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def send_report_notification(report_id):
    try:
        # Get the report data
        report = current_app.mongo.db.patient_reports.find_one({"_id": ObjectId(report_id)})
        if not report:
            return False
        
        patient_email = report.get("patient_email")
        patient_phone = report.get("patient_phone")
        
        # If we have an email, send an email notification
        if patient_email:
            # Format the report data for email
            vitals = report.get("vitals", {})
            vitals_text = f"Blood Pressure: {vitals.get('blood_pressure', 'N/A')}\n"
            vitals_text += f"Heart Rate: {vitals.get('heart_rate', 'N/A')} bpm\n"
            vitals_text += f"Temperature: {vitals.get('temperature', 'N/A')}°F\n"
            vitals_text += f"Oxygen Level: {vitals.get('oxygen_level', 'N/A')}%\n"
            vitals_text += f"Glucose Level: {vitals.get('glucose_level', 'N/A')}\n"
            vitals_text += f"Pain Level: {vitals.get('pain_level', 'N/A')}/10\n"
            
            medications = report.get("medications", "None")
            health_summary = report.get("health_summary", "No summary provided")
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = 'hospital@auramed.com'  # Replace with your email
            msg['To'] = patient_email
            msg['Subject'] = f"Daily Health Report for {report.get('patient_name')} - {report.get('report_date')}"
            
            body = f"Dear Family Member,\n\n"
            body += f"Here is the daily health report for {report.get('patient_name')} from {report.get('hospital_name')}:\n\n"
            body += f"Date: {report.get('report_date')}\n\n"
            body += f"Vital Signs:\n{vitals_text}\n"
            body += f"Medications: {medications}\n\n"
            body += f"Health Summary:\n{health_summary}\n\n"
            body += f"This is an automated message. Please do not reply to this email.\n\n"
            body += f"Regards,\n{report.get('hospital_name')} Staff"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # In a production environment, you would use a proper email service
            # For now, we'll just log the email content
            print(f"Email would be sent to {patient_email} with content:\n{body}")
            
            # Mark the notification as sent
            current_app.mongo.db.patient_reports.update_one(
                {"_id": ObjectId(report_id)},
                {"$set": {"notification_sent": True}}
            )
            
            # In a real application, you would send the email here
            # server = smtplib.SMTP('smtp.gmail.com', 587)
            # server.starttls()
            # server.login("your_email@gmail.com", "your_password")
            # server.send_message(msg)
            # server.quit()
            
            return True
        
        # If we have a phone number, send an SMS notification
        elif patient_phone:
            # In a real application, you would integrate with an SMS service
            print(f"SMS would be sent to {patient_phone} with daily health report for {report.get('patient_name')}")
            
            # Mark the notification as sent
            current_app.mongo.db.patient_reports.update_one(
                {"_id": ObjectId(report_id)},
                {"$set": {"notification_sent": True}}
            )
            
            return True
        
        return False
    
    except Exception as e:
        print(f"Error sending report notification: {str(e)}")
        return False


@hospital_bp.route('/discharge-patient/<patient_id>', methods=['POST'])
def discharge_patient(patient_id):
    try:
        # Get the logged-in hospital email
        hospital_email, error_response = get_logged_in_email()
        if error_response:
            return error_response

        # Get the hospital data
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": hospital_email})
        if not hospital_data:
            return jsonify({"error": "Hospital not found"}), 404

        # Get patient data
        patient = current_app.mongo.db.patients.find_one({
            "_id": ObjectId(patient_id),
            "hospital_id": str(hospital_data["_id"]),
            "admission_status": "Admitted"
        })
        
        if not patient:
            return jsonify({"error": "Patient not found or already discharged"}), 404
        
        # Update patient status
        current_app.mongo.db.patients.update_one(
            {"_id": ObjectId(patient_id)},
            {"$set": {
                "admission_status": "Discharged",
                "discharge_timestamp": datetime.now()
            }}
        )
        
        # Update bed availability in hospital collection
        bed_type = patient["bed_type"]
        bed_availability = hospital_data.get("bed_availability", {})
        
        if bed_type in bed_availability:
            bed_availability[bed_type] += 1
            current_app.mongo.db.hospitals.update_one(
                {"_id": hospital_data["_id"]},
                {"$set": {"bed_availability": bed_availability}}
            )
        
        # Update bed status in beds collection
        if "bed_id" in patient and "floor" in patient:
            # If we have the exact bed_id and floor (new format)
            current_app.mongo.db.beds.update_one(
                {
                    "hospital_id": str(hospital_data["_id"]),
                    "bed_id": patient["bed_id"],
                    "floor": patient["floor"]
                },
                {"$set": {"status": "available"}}
            )
        else:
            # Try to parse from bed_type string (old format)
            try:
                parts = patient["bed_type"].split(" - Floor ")
                if len(parts) > 1:
                    bed_type_part = parts[0]
                    floor_room_part = parts[1].split(" Room ")
                    if len(floor_room_part) > 1:
                        floor = int(floor_room_part[0])
                        room = floor_room_part[1]
                        
                        # Update bed status
                        current_app.mongo.db.beds.update_one(
                            {
                                "hospital_id": str(hospital_data["_id"]),
                                "floor": floor,
                                "bed_type": bed_type_part,
                                "status": "occupied"
                            },
                            {"$set": {"status": "available"}}
                        )
            except Exception as e:
                print(f"Error updating bed status: {str(e)}")
                # Continue with discharge even if bed update fails
        
        # Delete patient_daily_data for this patient
        current_app.mongo.db.patient_daily_data.delete_one({
            "patient_id": patient_id
        })
        
        return jsonify({"message": "Patient discharged successfully"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@hospital_bp.route('/api/dashboard-metrics', methods=['GET'])
def get_dashboard_metrics():
    try:
        # Get the logged-in hospital email
        hospital_email, error_response = get_logged_in_email()
        if error_response:
            return error_response

        # Get the hospital data
        hospital_data = current_app.mongo.db.hospitals.find_one({"email": hospital_email})
        if not hospital_data:
            return jsonify({"error": "Hospital not found"}), 404

        hospital_id = str(hospital_data["_id"])
        hospital_name = hospital_data["name"]
        
        # Get count of admitted patients
        admitted_patients_count = current_app.mongo.db.patients.count_documents({
            "hospital_id": hospital_id,
            "admission_status": "Admitted"
        })
        
        # Get bed availability
        bed_availability = hospital_data.get("bed_availability", {})
        total_beds = sum(bed_availability.values())
        available_beds = sum(bed_availability.values())
        
        # Get inventory items count
        inventory_count = len(hospital_data.get("inventory", []))
        
        # Get OPD patients count (ongoing appointments)
        opd_patients_count = current_app.mongo.db.appointments.count_documents({
            "doctor_hospital": hospital_name,
            "status": "ongoing"
        })
        
        # Get tests count
        total_tests_count = current_app.mongo.db.tests.count_documents({"hospital_name": hospital_name})
        ongoing_tests_count = current_app.mongo.db.tests.count_documents({"hospital_name": hospital_name, "status": "ongoing"})
        completed_tests_count = current_app.mongo.db.tests.count_documents({"hospital_name": hospital_name, "status": "completed"})
        
        # Calculate trends (for demo purposes, we'll use random trends)
        # In a real app, you would compare with previous day/week data
        import random
        opd_trend = random.randint(-15, 15)
        beds_trend = random.randint(-10, 10)
        inventory_trend = random.randint(0, 10)
        admissions_trend = random.randint(-5, 5)
        tests_trend = random.randint(-10, 20)
        
        metrics = {
            "opd_patients": {
                "count": opd_patients_count,
                "trend": opd_trend,
                "trend_text": f"{abs(opd_trend)}% {'from yesterday' if opd_trend != 0 else ''}"
            },
            "available_beds": {
                "count": f"{available_beds}/{total_beds}",
                "trend": beds_trend,
                "trend_text": f"{abs(beds_trend)}% {'from last week' if beds_trend != 0 else ''}"
            },
            "inventory_items": {
                "count": inventory_count,
                "trend": inventory_trend,
                "trend_text": f"{inventory_trend} items {'new in stock' if inventory_trend > 0 else 'removed from stock' if inventory_trend < 0 else ''}"
            },
            "current_admissions": {
                "count": admitted_patients_count,
                "trend": admissions_trend,
                "trend_text": f"{abs(admissions_trend)}% {'occupancy rate' if admissions_trend != 0 else ''}"
            },
            "tests": {
                "count": total_tests_count,
                "ongoing": ongoing_tests_count,
                "completed": completed_tests_count,
                "trend": tests_trend,
                "trend_text": f"{abs(tests_trend)}% {'more than last week' if tests_trend > 0 else 'less than last week' if tests_trend < 0 else ''}"
            }
        }
        
        return jsonify(metrics), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

