from pymongo import MongoClient
import random

# Connect to MongoDB
client = MongoClient("mongodb+srv://mahadiqbalaiml27:9Gx_qVZ-tpEaHUu@healthcaresystem.ilezc.mongodb.net/healthcaresystem?retryWrites=true&w=majority&appName=Healthcaresystem")  # Modify if needed
db = client["healthcaresystem"]

hospitals_collection = db["hospitals"]
beds_collection = db["beds"]

# Define bed statuses and types
statuses = ["available", "occupied", "reserved", "maintenance"]
general_beds_per_floor = 5
icu_beds_per_floor = 3

def generate_bed_data(hospital, num_floors=5):
    bed_data = []
    for floor in range(1, num_floors + 1):
        # General Beds
        for i in range(1, general_beds_per_floor + 1):
            bed_data.append({
                "hospital_id": hospital["_id"],
                "hospital_name": hospital["name"],
                "floor": floor,
                "bed_id": f"G{floor}-{i:02}",
                "bed_type": "General",
                "status": random.choice(statuses)
            })
        # ICU Beds
        for i in range(1, icu_beds_per_floor + 1):
            bed_data.append({
                "hospital_id": hospital["_id"],
                "hospital_name": hospital["name"],
                "floor": floor,
                "bed_id": f"I{floor}-{i:02}",
                "bed_type": "ICU",
                "status": random.choice(statuses)
            })
    return bed_data

# Iterate through all hospitals and insert bed data
all_hospitals = hospitals_collection.find()
for hospital in all_hospitals:
    beds = generate_bed_data(hospital)
    beds_collection.insert_many(beds)
    print(f"Inserted {len(beds)} beds for {hospital['name']}")
