from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'simple-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trekking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# DATABASE MODELS
# ==========================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'staff', 'user'
    status = db.Column(db.String(20), default='approved')  # 'pending', 'approved', 'blacklisted'
    contact_no = db.Column(db.String(15), nullable=True)

    bookings = db.relationship('Booking', backref='user', lazy=True)
    assigned_treks = db.relationship('Trek', backref='assigned_staff', lazy=True)

class Trek(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Open')
    start_date = db.Column(db.String(20), nullable=False)
    end_date = db.Column(db.String(20), nullable=False)
    
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    bookings = db.relationship('Booking', backref='trek', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey('trek.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Booked')

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/')
def home():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'staff':
            return redirect(url_for('staff_dashboard'))
        elif role == 'user':
            return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        contact_no = request.form.get('contact_no')
        role = request.form.get('role')

        # Admin cannot self-register
        if role not in ['user', 'staff']:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already registered.', 'warning')
            return redirect(url_for('register'))

        # Staff starts as 'pending', Users start as 'approved'
        status = 'pending' if role == 'staff' else 'approved'

        new_user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            status=status,
            contact_no=contact_no
        )

        db.session.add(new_user)
        db.session.commit()

        if role == 'staff':
            flash('Registration successful! Please wait for Admin approval before logging in.', 'info')
        else:
            flash('Registration successful! Please login.', 'success')

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('login'))

        if user.status == 'pending':
            flash('Your staff account is pending admin approval.', 'warning')
            return redirect(url_for('login'))
        elif user.status == 'blacklisted':
            flash('Your account has been blacklisted.', 'danger')
            return redirect(url_for('login'))

        session['user_id'] = user.id
        session['name'] = user.name
        session['role'] = user.role

        flash(f'Welcome back, {user.name}!', 'success')
        return redirect(url_for('home'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Placeholders for future dashboards
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('home'))

    search_query = request.args.get('search', '').strip()

    # Query metrics
    total_users = User.query.filter_by(role='user').count()
    total_staff = User.query.filter_by(role='staff').count()
    total_treks = Trek.query.count()
    total_bookings = Booking.query.count()

    # Filtered Users
    users_query = User.query.filter(User.role != 'admin')
    if search_query:
        if search_query.isdigit():
            users_query = users_query.filter(User.id == int(search_query))
        else:
            users_query = users_query.filter(User.name.ilike(f"%{search_query}%"))
    users = users_query.all()

    # Filtered Treks
    treks_query = Trek.query
    if search_query:
        if search_query.isdigit():
            treks_query = treks_query.filter(Trek.id == int(search_query))
        else:
            treks_query = treks_query.filter(Trek.name.ilike(f"%{search_query}%"))
    treks = treks_query.all()

    # Get approved staff list for assigning to new treks
    approved_staff = User.query.filter_by(role='staff', status='approved').all()

    return render_template(
        'admin_dashboard.html',
        total_treks=total_treks,
        total_users=total_users,
        total_staff= total_staff,
        total_bookings=total_bookings,
        users=users,
        treks=treks,
        approved_staff=approved_staff,
        search_query=search_query
    )


@app.route('/admin/approve-staff/<int:user_id>')
def approve_staff(user_id):
    if session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    staff_user = User.query.get_or_404(user_id)
    if staff_user.role == 'staff':
        staff_user.status = 'approved'
        db.session.commit()
        flash(f'Staff account for {staff_user.name} has been approved!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/toggle-blacklist/<int:user_id>')
def toggle_blacklist(user_id):
    if session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    user = User.query.get_or_404(user_id)
    if user.role != 'admin':
        if user.status == 'blacklisted':
            user.status = 'approved' if user.role == 'user' else 'pending'
            flash(f'User {user.name} removed from blacklist.', 'info')
        else:
            user.status = 'blacklisted'
            flash(f'User {user.name} has been blacklisted.', 'warning')
        db.session.commit()

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/create-trek', methods=['POST'])
def create_trek():
    if session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    name = request.form.get('name')
    location = request.form.get('location')
    difficulty = request.form.get('difficulty')
    duration_days = request.form.get('duration_days')
    available_slots = request.form.get('available_slots')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    assigned_staff_id = request.form.get('assigned_staff_id')

    # Convert empty staff string to None
    staff_id = int(assigned_staff_id) if assigned_staff_id else None
    # Check for date overlap if a staff member is assigned
    if staff_id:
        # Find all existing treks assigned to this staff member
        staff_treks = Trek.query.filter_by(assigned_staff_id=staff_id).all()
        
        for trek in staff_treks:
            # Overlap formula: (StartA <= EndB) and (EndA >= StartB)
            if (start_date <= trek.end_date) and (end_date >= trek.start_date):
                staff_user = User.query.get(staff_id)
                flash(
                    f'Conflict: Staff member "{staff_user.name}" is already assigned to trek "{trek.name}" '
                    f'from {trek.start_date} to {trek.end_date}.',
                    'danger'
                )
                return redirect(url_for('admin_dashboard'))

    new_trek = Trek(
        name=name,
        location=location,
        difficulty=difficulty,
        duration_days=int(duration_days),
        available_slots=int(available_slots),
        start_date=start_date,
        end_date=end_date,
        assigned_staff_id=staff_id
    )

    db.session.add(new_trek)
    db.session.commit()

    flash(f'Trek "{name}" created successfully!', 'success')
    return redirect(url_for('admin_dashboard'))




@app.route('/staff/dashboard')
def staff_dashboard():
    return f"Welcome Staff! (Dashboard coming in Step 4)"

@app.route('/user/dashboard')
def user_dashboard():
    return f"Welcome Trekker! (Dashboard coming in Step 5)"


# ==========================================
# INITIALIZE DATABASE & RUN
# ==========================================

def init_db():
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin_user = User(
                name='Super Admin',
                email='admin@trek.com',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                status='approved',
                contact_no='0000000000'
            )
            db.session.add(admin_user)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)