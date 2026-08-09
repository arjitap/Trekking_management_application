# Trekking Management Application

A role-based web application developed using **Flask** to manage treks, trek staff, users, and bookings.

## Features

### Admin

* Admin login using a pre-existing admin account.
* Create, edit, and delete treks.
* Approve or blacklist trek staff and users.
* Assign staff members to treks.
* Search users, staff, and treks.
* View bookings and trekking information.

### Trek Staff

* Register and log in after admin approval.
* View treks assigned by the admin.
* Update available slots and trek status.
* View the list of users registered for assigned treks.
* Mark a trek as completed.

### Trekker (User)

* Register and log in.
* View available treks.
* Search and filter treks by name, location, and difficulty.
* Book available treks.
* Cancel bookings.
* View booking status and trekking history.
* Update profile information.

### Additional Features

* Prevents users from booking when no slots are available.
* Prevents overbooking of treks.
* Checks for date conflicts when assigning staff to treks.
* Automatically updates active bookings when a trek is marked as completed.
* Restores available slots when a booking is cancelled.
* Passwords are stored using secure password hashing with Werkzeug.

## Technologies Used

* Python
* Flask – Backend framework
* Flask-SQLAlchemy / SQLAlchemy – Database handling
* Jinja2 – Template rendering
* Bootstrap 5 – User interface styling
* SQLite – Database
* Werkzeug – Password hashing

## How to Run the Application

### 1. Prerequisites

Make sure Python is installed on your computer.

### 2. Create a Virtual Environment

Open a terminal in the project folder and run:

```bash
python -m venv venv
```

Activate the virtual environment on Windows:

```bash
venv\Scripts\activate
```

### 3. Install Required Packages

Install the required Python packages using:

```bash
pip install -r requirements.txt
```

### 4. Run the Application

Start the Flask application using:

```bash
python app.py
```

The application will be available at:

```
http://127.0.0.1:5000/
```

The SQLite database and its tables are created programmatically by the application.

## Admin Login

The application contains a pre-configured admin account.

* **Email:** admin@gmail.com
* **Password:** admin123

## Project Structure

```
Trekking_management/
│
├── app.py
├── README.md
├── requirements.txt
│
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── admin_dashboard.html
    ├── admin_all_treks.html
    ├── admin_all_bookings.html
    ├── admin_all_users.html
    ├── edit_trek.html
    ├── staff_dashboard.html
    └── user_dashboard.html
```

## Database

The application uses SQLite as required by the project.
The database is created programmatically using SQLAlchemy. The database file is stored inside the `instance` folder when the application is run.
No manual database creation is required.
