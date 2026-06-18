# 📄 Document-Constructor-Engine

An automated document template management system for commercial organizations. The project is designed to rapidly generate legal and HR documents based on dynamic templates.

### 🛠 My Contributions (Backend Development)

As part of the development team, I was responsible for the server-side logic and data architecture:

* Database Design (SQLite): Developed the schema for storing partner profiles, document templates, and user metadata.
* Auto-fill Engine: Implemented a engine that parses templates and populates variables (full names, dates, salaries, positions, etc.) sourced from the database.
* Templating System: Created the backend logic to manage custom templates tailored for various partners.
* API/Business Logic: Handled requests for generating documents ready for signature.

### 🚀 Key Features

* Multi-tenant Templates: Supports unique document forms for different partner organizations.
* Dynamic Fields: Automatic document generation incorporating real-time HR data.
* Constructor: Allows for the addition of new document types to the system without requiring source code modifications.

### 📈 Technical Stack

* Core: Python
* Storage: SQLite
* Logic: Modular architecture designed for seamless partner integration.
