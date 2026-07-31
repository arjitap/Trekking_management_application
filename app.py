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

# ======================
#ADMIN DASHBOARD
# ======================

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


#=============================
#STAFF DASHBOARD 
# ============================

@app.route('/staff/dashboard')
def staff_dashboard():
    # Role & Status Check
    if session.get('role') != 'staff':
        flash('Access denied. Staff privileges required.', 'danger')
        return redirect(url_for('home'))

    current_user = User.query.get(session['user_id'])
    if current_user.status != 'approved':
        flash('Your account is not approved by the admin yet.', 'warning')
        return redirect(url_for('logout'))

    # Query treks assigned to this specific staff member
    assigned_treks = Trek.query.filter_by(assigned_staff_id=current_user.id).all()

    # Bundle trek info with registered bookings
    trek_data = []
    for trek in assigned_treks:
        active_bookings = Booking.query.filter_by(trek_id=trek.id).all()
        trek_data.append({
            'trek': trek,
            'bookings': active_bookings,
            'booking_count': len(active_bookings)
        })

    return render_template('staff_dashboard.html', assigned_treks=assigned_treks, trek_data=trek_data)


@app.route('/staff/update-trek/<int:trek_id>', methods=['POST'])
def update_trek_staff(trek_id):
    if session.get('role') != 'staff':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    trek = Trek.query.get_or_404(trek_id)

    # Security Check: Ensure staff can ONLY update treks assigned to THEM
    if trek.assigned_staff_id != session.get('user_id'):
        flash('Security Alert: You can only manage treks assigned to you.', 'danger')
        return redirect(url_for('staff_dashboard'))

    new_slots = request.form.get('available_slots')
    new_status = request.form.get('status')

    if new_slots is not None:
        trek.available_slots = int(new_slots)
    if new_status:
        trek.status = new_status

    db.session.commit()
    flash(f'Trek "{trek.name}" details updated successfully!', 'success')
    return redirect(url_for('staff_dashboard'))



#===========================
#USER DASHBOARD 
#===========================


@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        flash('Access denied. Trekker privileges required.', 'danger')
        return redirect(url_for('home'))

    user_id = session.get('user_id')
    current_user = User.query.get(user_id)

    # Search & Filter Parameters
    search_query = request.args.get('search', '').strip()
    selected_difficulty = request.args.get('difficulty', '').strip()

    # Query User's Bookings
    user_bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.booking_date.desc()).all()
    
    # IDs of treks user has already booked 
    booked_trek_ids = [b.trek_id for b in user_bookings if b.status == 'Booked']

    # Query Available Open Treks
    treks_query = Trek.query.filter_by(status='Open')

    if search_query:
        treks_query = treks_query.filter(
            (Trek.name.ilike(f"%{search_query}%")) | (Trek.location.ilike(f"%{search_query}%"))
        )
    if selected_difficulty:
        treks_query = treks_query.filter(Trek.difficulty == selected_difficulty)

    open_treks = treks_query.all()

    return render_template(
        'user_dashboard.html',
        current_user=current_user,
        user_bookings=user_bookings,
        open_treks=open_treks,
        booked_trek_ids=booked_trek_ids,
        search_query=search_query,
        selected_difficulty=selected_difficulty
    )


@app.route('/user/book-trek/<int:trek_id>')
def book_trek(trek_id):
    if session.get('role') != 'user':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    user_id = session.get('user_id')
    trek = Trek.query.get_or_404(trek_id)

    # Constraint Check 1: Trek must be Open
    if trek.status != 'Open':
        flash('Booking Failed: This trek is not currently open for registration.', 'danger')
        return redirect(url_for('user_dashboard'))

    # Constraint Check 2: Prevent Overbooking
    if trek.available_slots <= 0:
        flash('Booking Failed: No available slots left for this trek.', 'danger')
        return redirect(url_for('user_dashboard'))

    # Constraint Check 3: Prevent duplicate active booking
    existing_booking = Booking.query.filter_by(user_id=user_id, trek_id=trek_id, status='Booked').first()
    if existing_booking:
        flash('You have already booked this trek.', 'warning')
        return redirect(url_for('user_dashboard'))

    # Create Booking
    new_booking = Booking(
        user_id=user_id,
        trek_id=trek.id,
        status='Booked'
    )

    # Reduce available slots
    trek.available_slots -= 1

    db.session.add(new_booking)
    db.session.commit()

    flash(f'Successfully booked "{trek.name}"!', 'success')
    return redirect(url_for('user_dashboard'))


@app.route('/user/cancel-booking/<int:booking_id>')
def cancel_booking(booking_id):
    if session.get('role') != 'user':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    user_id = session.get('user_id')
    booking = Booking.query.get_or_404(booking_id)

    # Security check: User can only cancel their own booking
    if booking.user_id != user_id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('user_dashboard'))

    if booking.status == 'Booked':
        booking.status = 'Cancelled'
        # Restore slot back to trek
        booking.trek.available_slots += 1
        db.session.commit()
        flash('Booking cancelled successfully.', 'info')

    return redirect(url_for('user_dashboard'))


@app.route('/user/update-profile', methods=['POST'])
def update_user_profile():
    if session.get('role') != 'user':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    current_user = User.query.get(session['user_id'])
    new_name = request.form.get('name')
    new_contact = request.form.get('contact_no')

    if new_name:
        current_user.name = new_name
        session['name'] = new_name  # Update session name too
    if new_contact:
        current_user.contact_no = new_contact

    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('user_dashboard'))


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