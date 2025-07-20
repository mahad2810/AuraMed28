from flask import Blueprint, jsonify, request, current_app
import wfdb
import os
import os.path
import shutil
import time
from bson.objectid import ObjectId

patient_management_bp = Blueprint("patient_management", __name__)

@patient_management_bp.route("/api/ecg", methods=["GET"])
def get_ecg_waveform():
    try:
        # Get patient name or ID from query parameter
        patient_name = request.args.get('patient')
        patient_id = request.args.get('patient_id')
        
        # Base directory for ECG files
        ecg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ECG")
        
        # Default ECG file - only used if no patient name match is found
        record_name = None
        
        # If patient_id is provided, try to get the patient from the database
        if patient_id:
            try:
                patients_collection = current_app.mongo.db.patients
                patient = patients_collection.find_one({"_id": ObjectId(patient_id)})
                if patient and "name" in patient:
                    # Only set patient_name if it's not already provided in the request
                    if not patient_name:
                        patient_name = patient["name"]
                        current_app.logger.info(f"Using patient name from database: {patient_name}")
            except Exception as e:
                current_app.logger.error(f"Error fetching patient by ID: {str(e)}")
        
        # Get all available ECG files
        all_files = os.listdir(ecg_dir)
        
        # Separate files by extension
        hea_files = [f for f in all_files if f.endswith('.hea')]
        dat_files = [f for f in all_files if f.endswith('.dat')]
        
        # Get base names (without extensions) for all valid ECG files (must have both .dat and .hea)
        valid_ecg_files = []
        for hea_file in hea_files:
            base_name = os.path.splitext(hea_file)[0]
            if f"{base_name}.dat" in dat_files:
                valid_ecg_files.append(base_name)
        
        # Get sample files for fallback (only those with both .dat and .hea)
        sample_files = [f for f in valid_ecg_files if f.lower().startswith("aami")]
        
        # Check if specific sample files exist, in order of preference
        preferred_samples = ["aami3d", "aami3c", "aami3b", "aami4a", "aami4b"]
        default_sample = None
        
        # Try to find a preferred sample that exists
        for sample in preferred_samples:
            if sample in sample_files:
                default_sample = sample
                break
                
        # If no preferred sample found, use any available sample
        if not default_sample and sample_files:
            default_sample = sample_files[0]
            
        # Log available sample files
        current_app.logger.info(f"Available sample ECG files: {sample_files}")
        current_app.logger.info(f"Selected default sample: {default_sample}")
        
        if patient_name:
            # Normalize patient name (remove spaces, lowercase)
            normalized_name = patient_name.replace(" ", "").lower()
            current_app.logger.info(f"Looking for ECG file matching: {normalized_name}")
            
            # Try exact match only - case insensitive but preserve original case
            exact_match = None
            for file_base in valid_ecg_files:
                if normalized_name == file_base.lower():
                    exact_match = file_base  # Keep original case for the file
                    current_app.logger.info(f"Found exact match ECG file: {exact_match}")
                    break
            
            # Use the exact match if found
            if exact_match:
                record_name = exact_match
        
        # If no match found, use default sample
        if not record_name:
            if patient_name:
                current_app.logger.warning(f"No ECG file found matching patient name: {patient_name}")
            
            record_name = default_sample
            if record_name:
                current_app.logger.info(f"Using sample ECG file: {record_name}")
            else:
                current_app.logger.error("No sample ECG files available in the system")
                return jsonify({"error": "No ECG files available in the system"}), 500
        
        # Double-check that both .dat and .hea files exist for the selected record
        dat_path = os.path.join(ecg_dir, f"{record_name}.dat")
        hea_path = os.path.join(ecg_dir, f"{record_name}.hea")
        
        if not os.path.exists(dat_path) or not os.path.exists(hea_path):
            current_app.logger.error(f"Missing required files for {record_name}. DAT exists: {os.path.exists(dat_path)}, HEA exists: {os.path.exists(hea_path)}")
            
            # Try fallback if the original record is missing files
            if record_name != default_sample and default_sample:
                record_name = default_sample
                current_app.logger.warning(f"Falling back to default sample: {record_name}")
                
                # Verify fallback files exist
                dat_path = os.path.join(ecg_dir, f"{record_name}.dat")
                hea_path = os.path.join(ecg_dir, f"{record_name}.hea")
                
                if not os.path.exists(dat_path) or not os.path.exists(hea_path):
                    current_app.logger.error(f"Missing required files for fallback {record_name}")
                    return jsonify({"error": f"Could not find required files for ECG record: {record_name}"}), 500
            else:
                return jsonify({"error": f"Could not find required files for ECG record: {record_name}"}), 500
        
        # Read the ECG signal using the full path
        try:
            # Use the full path to the directory and the record name
            full_record_path = os.path.join(ecg_dir, record_name)
            current_app.logger.info(f"Attempting to read ECG file from: {full_record_path}")
            
            # Initialize referenced_record to None
            referenced_record = None
            
            # Check if the header file exists and read its content to determine the actual .dat filename
            hea_file_path = os.path.join(ecg_dir, f"{record_name}.hea")
            if os.path.exists(hea_file_path):
                with open(hea_file_path, 'r') as hea_file:
                    first_line = hea_file.readline().strip()
                    # The first word in the first line is the record name that points to the .dat file
                    referenced_record = first_line.split()[0] if first_line else None
                    
                    if referenced_record and referenced_record != record_name:
                        current_app.logger.info(f"Header file references a different record: {referenced_record}")
                        # Check if the referenced .dat file exists
                        referenced_dat_path = os.path.join(ecg_dir, f"{referenced_record}.dat")
                        target_dat_path = os.path.join(ecg_dir, f"{record_name}.dat")
                        
                        if os.path.exists(referenced_dat_path):
                            current_app.logger.info(f"Referenced .dat file exists: {referenced_dat_path}")
                            
                            # Create a temporary copy of the referenced .dat file with the expected name
                            try:
                                shutil.copy2(referenced_dat_path, target_dat_path)
                                current_app.logger.info(f"Created temporary copy of {referenced_record}.dat as {record_name}.dat")
                                # Make sure to remove the temporary file later
                            except Exception as copy_error:
                                current_app.logger.error(f"Error copying .dat file: {str(copy_error)}")
            
            # Read the record with wfdb
            record = wfdb.rdrecord(full_record_path)
            current_app.logger.info(f"Successfully loaded ECG file: {record_name}")
            
            # Clean up any temporary files we created
            temp_dat_path = os.path.join(ecg_dir, f"{record_name}.dat")
            if os.path.exists(temp_dat_path) and referenced_record and record_name != referenced_record:
                # Track if we created this file as a temporary copy
                created_temp_file = False
                
                # Check if this was a file we created (by comparing modification times)
                try:
                    # If the file was just created, it's likely our temporary file
                    file_mod_time = os.path.getmtime(temp_dat_path)
                    current_time = time.time()
                    
                    # If the file was modified in the last 10 seconds, it's likely our temporary file
                    if current_time - file_mod_time < 10:  # 10 seconds threshold
                        created_temp_file = True
                except Exception as time_error:
                    current_app.logger.error(f"Error checking file modification time: {str(time_error)}")
                
                # Only remove if we're confident it's a temporary file we created
                if created_temp_file:
                    try:
                        os.remove(temp_dat_path)
                        current_app.logger.info(f"Removed temporary file: {temp_dat_path}")
                    except Exception as remove_error:
                        current_app.logger.error(f"Error removing temporary file: {str(remove_error)}")
                else:
                    current_app.logger.info(f"Skipped removing file that may be original: {temp_dat_path}")
                    
        except Exception as e:
            current_app.logger.error(f"Error reading ECG file with wfdb: {str(e)}")
            
            # Try fallback if reading the original record failed
            if record_name != default_sample and default_sample:
                try:
                    fallback_path = os.path.join(ecg_dir, default_sample)
                    current_app.logger.warning(f"Falling back to default sample: {default_sample} at {fallback_path}")
                    
                    # Initialize fallback_referenced_record to None
                    fallback_referenced_record = None
                    
                    # Check if the fallback header file exists and read its content
                    fallback_hea_path = os.path.join(ecg_dir, f"{default_sample}.hea")
                    if os.path.exists(fallback_hea_path):
                        with open(fallback_hea_path, 'r') as hea_file:
                            first_line = hea_file.readline().strip()
                            # The first word in the first line is the record name that points to the .dat file
                            fallback_referenced_record = first_line.split()[0] if first_line else None
                            
                            if fallback_referenced_record and fallback_referenced_record != default_sample:
                                current_app.logger.info(f"Fallback header references a different record: {fallback_referenced_record}")
                                # Check if the referenced .dat file exists
                                referenced_dat_path = os.path.join(ecg_dir, f"{fallback_referenced_record}.dat")
                                target_dat_path = os.path.join(ecg_dir, f"{default_sample}.dat")
                                
                                if os.path.exists(referenced_dat_path):
                                    current_app.logger.info(f"Referenced fallback .dat file exists: {referenced_dat_path}")
                                    
                                    # Create a temporary copy of the referenced .dat file with the expected name
                                    try:
                                        shutil.copy2(referenced_dat_path, target_dat_path)
                                        current_app.logger.info(f"Created temporary copy of {fallback_referenced_record}.dat as {default_sample}.dat")
                                    except Exception as copy_error:
                                        current_app.logger.error(f"Error copying fallback .dat file: {str(copy_error)}")
                    
                    record = wfdb.rdrecord(fallback_path)
                    current_app.logger.info(f"Successfully loaded fallback ECG file: {default_sample}")
                    
                    # Clean up any temporary files we created for fallback
                    temp_fallback_dat = os.path.join(ecg_dir, f"{default_sample}.dat")
                    if os.path.exists(temp_fallback_dat) and fallback_referenced_record and default_sample != fallback_referenced_record:
                        # Track if we created this file as a temporary copy
                        created_temp_file = False
                        
                        # Check if this was a file we created (by comparing modification times)
                        try:
                            # If the file was just created, it's likely our temporary file
                            file_mod_time = os.path.getmtime(temp_fallback_dat)
                            current_time = time.time()
                            
                            # If the file was modified in the last 10 seconds, it's likely our temporary file
                            if current_time - file_mod_time < 10:  # 10 seconds threshold
                                created_temp_file = True
                        except Exception as time_error:
                            current_app.logger.error(f"Error checking file modification time: {str(time_error)}")
                        
                        # Only remove if we're confident it's a temporary file we created
                        if created_temp_file:
                            try:
                                os.remove(temp_fallback_dat)
                                current_app.logger.info(f"Removed temporary fallback file: {temp_fallback_dat}")
                            except Exception as remove_error:
                                current_app.logger.error(f"Error removing temporary fallback file: {str(remove_error)}")
                        else:
                            current_app.logger.info(f"Skipped removing file that may be original: {temp_fallback_dat}")
                    
                    # Update record_name to reflect the file we actually used
                    record_name = default_sample
                except Exception as fallback_error:
                    current_app.logger.error(f"Error reading fallback ECG file: {str(fallback_error)}")
                    return jsonify({"error": f"Could not read ECG file: {record_name} or fallback file: {default_sample}"}), 500
            else:
                # If no fallback is available or we were already trying the fallback, return error
                return jsonify({"error": f"Could not read ECG file: {record_name}. Error: {str(e)}"}), 500

        # Extract signal from first channel (could loop if you want all)
        signal = record.p_signal[:, 0]  # Use [:, 1] for second channel if available

        # Optionally downsample for performance
        downsampled_signal = signal[::10]  # Every 10th sample

        # Determine if this is a patient-specific ECG or a sample
        is_sample = record_name.lower().startswith("aami")
        ecg_source = "sample" if is_sample else "patient"
        
        return jsonify({
            "ecg": downsampled_signal.tolist(),
            "fs": record.fs,  # sampling frequency
            "units": record.units[0],
            "sig_name": record.sig_name[0],
            "record_name": record_name,
            "is_sample": is_sample,
            "ecg_source": ecg_source,
            "requested_patient": patient_name if patient_name else None
        })
    except Exception as e:
        current_app.logger.error(f"Error in get_ecg_waveform: {str(e)}")
        return jsonify({"error": str(e)}), 500

@patient_management_bp.route("/api/available-ecg-files", methods=["GET"])
def get_available_ecg_files():
    try:
        # Get the list of ECG files
        ecg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ECG")
        ecg_files = [os.path.splitext(f)[0] for f in os.listdir(ecg_dir) if f.endswith('.hea')]
        
        # Create a more detailed response with file information
        ecg_file_info = []
        for file_name in ecg_files:
            # Determine if this is a sample ECG file
            is_sample = file_name.lower().startswith("aami")
            
            file_info = {
                "file_name": file_name,
                "type": "sample" if is_sample else "patient-specific",
                "is_sample": is_sample
            }
            ecg_file_info.append(file_info)
        
        # Sort files: patient-specific first, then samples
        ecg_file_info.sort(key=lambda x: (x["is_sample"], x["file_name"]))
        
        return jsonify({
            "files": ecg_file_info,
            "total_count": len(ecg_file_info),
            "patient_specific_count": sum(1 for f in ecg_file_info if not f["is_sample"]),
            "sample_count": sum(1 for f in ecg_file_info if f["is_sample"])
        })
    except Exception as e:
        current_app.logger.error(f"Error in get_available_ecg_files: {str(e)}")
        return jsonify({"error": str(e)}), 500

@patient_management_bp.route("/api/ecg-beds", methods=["GET"])
def get_ecg_beds():
    try:
        # Get floor from query parameters
        floor_param = request.args.get("floor")
        
        # Get beds from the beds collection
        beds_collection = current_app.mongo.db.beds
        query = {}
        
        # If floor parameter is provided, filter beds by floor
        if floor_param:
            # Handle both string and integer floor values
            query["$or"] = [
                {"floor": floor_param}, 
                {"floor": str(floor_param)}, 
                {"floor": int(floor_param) if floor_param.isdigit() else floor_param},
                # Also match if floor is stored as a string representation of a number
                {"floor": float(floor_param) if floor_param.replace('.', '', 1).isdigit() else floor_param}
            ]
        
        beds = list(beds_collection.find(query))
        
        # Convert ObjectId to string for JSON serialization
        for bed in beds:
            if "_id" in bed:
                bed["_id"] = str(bed["_id"])
        
        # Group beds by floor
        floors = {}
        for bed in beds:
            floor = bed.get("floor")
            if floor:
                if floor not in floors:
                    floors[floor] = []
                floors[floor].append(bed)
        
        return jsonify({
            "beds": beds,
            "floors": floors
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@patient_management_bp.route("/api/ecg-patients", methods=["GET"])
def get_ecg_patients():
    try:
        # Get floor and room from query parameters
        floor = request.args.get("floor")
        room = request.args.get("room")
        
        # Query patients collection
        patients_collection = current_app.mongo.db.patients
        query = {"admission_status": "Admitted"}
        
        # Build query conditions
        query_conditions = []
        
        if floor:
            # Handle both string and integer floor values
            floor_condition = {"$or": [{"floor": floor}, {"floor": str(floor)}, {"floor": int(floor) if floor.isdigit() else floor}]}
            query_conditions.append(floor_condition)
        
        if room:
            # Try to match by room or room_id
            room_condition = {"$or": [
                {"room": room},
                {"room": str(room)},
                {"room_id": f"{floor}-{room}" if floor else room}
            ]}
            query_conditions.append(room_condition)
        
        # Combine all conditions with $and if we have any
        if query_conditions:
            query["$and"] = query_conditions
        
        patients = list(patients_collection.find(query))
        
        # Convert ObjectId to string for JSON serialization
        for patient in patients:
            if "_id" in patient:
                patient["_id"] = str(patient["_id"])
        
        # Get available ECG files with both .dat and .hea extensions
        ecg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ECG")
        all_files = os.listdir(ecg_dir)
        hea_files = [f for f in all_files if f.endswith('.hea')]
        dat_files = [f for f in all_files if f.endswith('.dat')]
        
        # Get base names (without extensions) for all valid ECG files (must have both .dat and .hea)
        valid_ecg_files = []
        for hea_file in hea_files:
            base_name = os.path.splitext(hea_file)[0]
            if f"{base_name}.dat" in dat_files:
                valid_ecg_files.append(base_name)
        
        # Get lowercase versions for case-insensitive matching
        valid_ecg_files_lower = [f.lower() for f in valid_ecg_files]
        
        # Mark patients with available ECG files and match specific ECG files
        for patient in patients:
            patient_name = patient.get("name", "")
            patient_name_normalized = patient_name.replace(" ", "").lower()
            
            # Log the patient we're processing
            current_app.logger.info(f"Checking ECG files for patient: {patient_name} (normalized: {patient_name_normalized})")
            
            # Check for exact match only - case insensitive but preserve original case
            exact_match = None
            if patient_name_normalized in valid_ecg_files_lower:
                # Find the original case version
                index = valid_ecg_files_lower.index(patient_name_normalized)
                exact_match = valid_ecg_files[index]
                current_app.logger.info(f"Found exact match ECG file for {patient_name}: {exact_match}")
            
            # If still no match, use AAMI sample files
            aami_files = [file for file in valid_ecg_files if file.lower().startswith("aami")]
            default_file = aami_files[0] if aami_files else None
            
            # Assign the best matching ECG file
            patient_ecg_file = exact_match or default_file
            
            # Determine if this is a patient-specific ECG or a sample
            is_patient_specific = patient_ecg_file and not patient_ecg_file.startswith("aami")
            
            # Add ECG information to patient record
            patient["ecg_file"] = patient_ecg_file
            patient["has_ecg"] = bool(patient_ecg_file)
            patient["has_patient_specific_ecg"] = is_patient_specific
            
            # Add ECG file type (patient-specific or sample)
            if patient_ecg_file:
                if patient_ecg_file.startswith("aami"):
                    patient["ecg_type"] = "sample"
                    current_app.logger.info(f"Using sample ECG file for {patient_name}: {patient_ecg_file}")
                else:
                    patient["ecg_type"] = "patient-specific"
                    current_app.logger.info(f"Using patient-specific ECG file for {patient_name}: {patient_ecg_file}")
            else:
                current_app.logger.warning(f"No ECG file available for {patient_name}")
                patient["ecg_type"] = "none"
        
        return jsonify(patients)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
