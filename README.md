
# AuraMed – Unified Smart Healthcare Platform

**AuraMed** is an all-in-one digital healthcare solution designed to bridge critical gaps in hospital operations and patient care, especially in underserved and rural communities. With an emphasis on real-time data, intelligent automation, and AI-driven insights, AuraMed empowers both healthcare providers and patients through a unified interface.

---

## 📌 Table of Contents

* [Overview](#overview)
* [Core Features](#core-features)

  * [Patient Portal](#patient-portal)
  * [Hospital Portal](#hospital-portal)
* [Technology Stack](#technology-stack)
* [System Architecture](#system-architecture)
* [Impact](#impact)
* [Future Development](#future-development)
* [Demo & Resources](#demo--resources)
* [Acknowledgements](#acknowledgements)

---

## 🔍 Overview

Despite advancements in digital health, many hospitals and clinics—especially in rural regions—still face challenges like:

* Disconnected patient data and systems
* Inefficient resource and bed management
* Inaccessible emergency support
* Lack of proactive AI-driven diagnostics

AuraMed addresses these challenges by offering:

* A **Patient Dashboard** for health records, appointments, diagnostics, and emergency support.
* A **Hospital Dashboard** for admissions, real-time monitoring, video consultations, inventory, and doctor management.

---

## 🚀 Core Features

### 👨‍⚕️ Patient Portal

* **Nearby Hospital Locator** – View hospitals by proximity and availability
* **AI Symptom Checker** – Initial diagnosis using machine learning models
* **Digital Health Record Storage** – Access reports, prescriptions, and appointments
* **Appointment & Test Booking** – Schedule visits and diagnostics with wait-time estimates
* **SOS Emergency Button** – One-tap voice, location, and multilingual alert system
* **Medicine & Test Reminders** – Automated notifications for patients

### 🏥 Hospital Portal

* **Doctor & Bed Availability Management** – Monitor and allocate resources in real time
* **Patient Admission System** – Track health metrics and automate onboarding
* **Inventory Tracking** – Real-time monitoring of supplies and medicine stock
* **Video Consultation Management** – Secure telemedicine via WebRTC
* **Health Report Sharing** – Automatically send daily updates to patient relatives
* **Analytics Dashboard** – Insights for hospital operations and resource usage

---

## 🛠 Technology Stack

### Frontend

* React.js, HTML/CSS, Leaflet.js, OpenStreetMap

### Backend

* Python (Flask, Flask-CORS), Node.js, Express.js, Firebase, MongoDB Atlas

### AI/ML & Chatbot

* Scikit-learn (Random Forest, Naïve Bayes, SVM), XGBoost, TensorFlow, Keras, Dialogflow

### Real-Time & Communication

* WebRTC, Socket.IO, Twilio (SMS), Google OAuth 2.0, SMTP, APScheduler

### Geolocation

* OpenCage Geocoding API

### Security

* Cryptography for health data encryption

---

## 🧠 System Architecture

AuraMed is designed using a modular microservices architecture. It includes separate services for:

* Frontend interface (React)
* Patient management APIs (Flask)
* Hospital resource APIs (Node.js)
* AI & symptom checker (Python ML models)
* Real-time communication (WebRTC, Socket.IO)
* Secure user authentication (Google OAuth 2.0)

*Visual architecture diagrams can be found in the [Product Snapshots](https://drive.google.com/file/d/144CDMpJtkRhnbsi2zv_eBjwMyq4YGR79/view?usp=sharing)*

---

## 🌍 Impact

### Rural Healthcare

* **Improved Access:** View availability and consult remotely
* **Timely Bed Booking:** Reduce admission delay in emergencies
* **Inventory Insights:** Prevent critical medicine shortages

### Urban Healthcare

* **Decongestion:** Smart bed and appointment scheduling
* **Record Efficiency:** Secure and centralized health data
* **Faster Emergency Response:** SOS alerts and proximity-based navigation

---

## 🔮 Future Development

* **Wearable Device Integration:** Connect biosensors to monitor vitals (heart rate, BP, glucose)
* **Multilingual Telemedicine:** Expand video consultations to regional languages
* **AI-Driven Report Analysis:** Provide pre-consultation insights using lab/test uploads
* **Dedicated Mobile App:** Extend access to smartphones across patient demographics

---

## 🎬 Demo & Resources

* 🔗 [Live MVP (Google Cloud Deployment)](https://auramed-app-156513904358.us-central1.run.app) *(Note: May be limited under free-tier hosting)*
* 📹 [Demo Video](https://www.youtube.com/watch?v=ECsVEbnQ51I)
* 📍 [Hospital Locator GitHub Repo](https://github.com/SAPtadeep27/hospital_map)
* 📷 [Product Snapshots](https://drive.google.com/file/d/144CDMpJtkRhnbsi2zv_eBjwMyq4YGR79/view?usp=sharing)

---

## 🙏 Acknowledgements

Special thanks to **Dr. Md. Hesamuddin**, Physician & Surgeon, for his professional insights during development.

---

**AuraMed is committed to reimagining healthcare—connecting patients and hospitals through intelligent digital solutions.**
*Help us shape a healthier future.*

