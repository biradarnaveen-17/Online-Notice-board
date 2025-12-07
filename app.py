import os
import uuid
import smtplib
from datetime import datetime, date, timedelta
from email.mime.text import MIMEText
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_123' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# --- EMAIL CONFIGURATION ---
EMAIL_ADDRESS = "biradarnaveen637@gmail.com"  
EMAIL_PASSWORD = "Naveen123"    

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False) 
    department = db.Column(db.String(100), nullable=True)
    full_name = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    email = db.Column(db.String(120), nullable=True)
    profile_pic = db.Column(db.String(300), nullable=True) 
    reset_code = db.Column(db.String(6), nullable=True)
    reset_expiry = db.Column(db.DateTime, nullable=True)

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(20), nullable=False) 
    category = db.Column(db.String(50), nullable=False, default='General')
    file_path = db.Column(db.String(300), nullable=True)
    duration = db.Column(db.Integer, default=5000) 
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    expiration_date = db.Column(db.Date, nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    external_link = db.Column(db.String(300), nullable=True) 
    attachment = db.Column(db.String(300), nullable=True)
    bg_color = db.Column(db.String(20), default='#000000') 
    text_color = db.Column(db.String(20), default='#ffffff')
    author = db.relationship('User', backref='notices')

class StudentRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) 
    contact_info = db.Column(db.String(150), nullable=True)
    department = db.Column(db.String(100), nullable=True) # Kept for backward compatibility/general info
    target_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # NEW: Specific admin target
    message = db.Column(db.Text, nullable=False)
    media_path = db.Column(db.String(300), nullable=True)
    date_sent = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending') # Pending, Accepted, Rejected
    
    target_admin = db.relationship('User', foreign_keys=[target_admin_id])


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- EMAIL FUNCTION ---
def send_email(to_email, subject, body):
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

# --- ROUTES ---
@app.route('/')
def home():
    today = date.today()
    try:
        all_notices = Notice.query.order_by(Notice.date_posted.desc()).all()
        active_notices = [n for n in all_notices if not n.expiration_date or n.expiration_date >= today]
        return render_template('index.html', notices=active_notices)
    except Exception as e:
        return f"Database Error: {e}. Please delete database.db and restart."

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'error')
    return render_template('admin/login.html')

@app.route('/admin/forgot_password', methods=['POST'])
def forgot_password():
    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()
    
    if user and user.email:
        code = ''.join(random.choices(string.digits, k=4))
        user.reset_code = code
        user.reset_expiry = datetime.utcnow() + timedelta(minutes=15)
        db.session.commit()
        
        body = f"Hello {user.username},\n\nYour password reset code is: {code}\n\nThis code expires in 15 minutes."
        sent = send_email(user.email, "Password Reset Code", body)
        
        if sent:
            session['reset_user_id'] = user.id
            flash(f'Code sent to {user.email}', 'info')
            return redirect(url_for('verify_code'))
        else:
            flash('Error sending email.', 'error')
    else:
        flash('User not found or no email set.', 'error')
        
    return redirect(url_for('login'))

@app.route('/admin/verify_code', methods=['GET', 'POST'])
def verify_code():
    if 'reset_user_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        code = request.form.get('code')
        user = User.query.get(session['reset_user_id'])
        
        if user and user.reset_code == code and user.reset_expiry > datetime.utcnow():
            return redirect(url_for('reset_password_new'))
        else:
            flash('Invalid or expired code.', 'error')
            
    return render_template('admin/verify_code.html')

@app.route('/admin/reset_password_new', methods=['GET', 'POST'])
def reset_password_new():
    if 'reset_user_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        
        if password == confirm:
            user = User.query.get(session['reset_user_id'])
            user.password = generate_password_hash(password, method='pbkdf2:sha256')
            user.reset_code = None
            user.reset_expiry = None
            db.session.commit()
            session.pop('reset_user_id', None)
            flash('Password reset successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Passwords do not match.', 'error')
            
    return render_template('admin/reset_password.html')

@app.route('/admin/dashboard')
@login_required
def dashboard():
    if current_user.role == 'SuperAdmin':
        notices = Notice.query.order_by(Notice.date_posted.desc()).all()
        # SuperAdmin sees all requests
        requests = StudentRequest.query.order_by(StudentRequest.date_sent.desc()).all()
    else:
        notices = Notice.query.filter_by(author_id=current_user.id).order_by(Notice.date_posted.desc()).all()
        # Admin sees requests targeted to them OR general requests for their department
        requests = StudentRequest.query.filter(
            (StudentRequest.target_admin_id == current_user.id) | 
            (StudentRequest.department == current_user.department)
        ).order_by(StudentRequest.date_sent.desc()).all()
    return render_template('admin/dashboard.html', notices=notices, requests=requests)

@app.route('/admin/create', methods=['GET', 'POST'])
@login_required
def create_notice():
    if request.method == 'POST':
        title = request.form.get('title')
        type = request.form.get('type')
        category = request.form.get('category')
        content = request.form.get('content')
        link = request.form.get('link')
        duration = int(request.form.get('duration') or 5) * 1000
        
        bg_color = request.form.get('bg_color')
        text_color = request.form.get('text_color')
        
        exp_str = request.form.get('expiration_date')
        expiration = datetime.strptime(exp_str, '%Y-%m-%d').date() if exp_str else None
        
        file_path = None
        attachment_path = None

        file = request.files.get('file')
        if file and file.filename != '':
            fname = secure_filename(file.filename)
            sub = 'videos' if 'video' in file.content_type else 'images'
            sdir = os.path.join(app.config['UPLOAD_FOLDER'], sub)
            if not os.path.exists(sdir): os.makedirs(sdir)
            file.save(os.path.join(sdir, fname))
            file_path = f'uploads/{sub}/{fname}'
            if type == 'text': type = 'image' if sub == 'images' else 'video'

        doc = request.files.get('attachment')
        if doc and doc.filename != '':
            dname = secure_filename(doc.filename)
            ddir = os.path.join(app.config['UPLOAD_FOLDER'], 'documents')
            if not os.path.exists(ddir): os.makedirs(ddir)
            doc.save(os.path.join(ddir, dname))
            attachment_path = f'uploads/documents/{dname}'

        new_notice = Notice(
            title=title, content=content, type=type, category=category, 
            file_path=file_path, duration=duration, author_id=current_user.id, 
            external_link=link, attachment=attachment_path, expiration_date=expiration,
            bg_color=bg_color, text_color=text_color
        )
        db.session.add(new_notice)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('admin/create_notice.html')

@app.route('/admin/notice/delete/<int:nid>')
@login_required
def delete_notice(nid):
    n = Notice.query.get(nid)
    if n and (n.author_id == current_user.id or current_user.role == 'SuperAdmin'):
        db.session.delete(n)
        db.session.commit()
        flash('Notice Deleted', 'success')
    else:
        flash('Permission Denied', 'error')
    return redirect(url_for('dashboard'))

# --- REQUEST HANDLING (Accept/Reject) ---
@app.route('/admin/request/accept/<int:rid>')
@login_required
def accept_request(rid):
    req = StudentRequest.query.get(rid)
    if req:
        # Determine type based on media path
        notice_type = 'text'
        if req.media_path:
            if req.media_path.lower().endswith(('.mp4', '.mov', '.avi')):
                notice_type = 'video'
            else:
                notice_type = 'image'

        # Convert Request to Notice
        new_notice = Notice(
            title=f"Req: {req.name}",
            content=req.message,
            type=notice_type, 
            category='General',
            author_id=current_user.id,
            file_path=req.media_path, # Use uploaded proof if compatible
            date_posted=datetime.utcnow()
        )
        db.session.add(new_notice)
        db.session.delete(req) # Remove request after accepting
        db.session.commit()
        flash('Request Accepted and Published as Notice', 'success')
    else:
        flash('Request not found.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/admin/request/reject/<int:rid>')
@login_required
def reject_request(rid):
    req = StudentRequest.query.get(rid)
    if req:
        db.session.delete(req)
        db.session.commit()
        flash('Request Rejected', 'info')
    return redirect(url_for('dashboard'))


@app.route('/admin/users')
@login_required
def manage_users():
    if current_user.role != 'SuperAdmin': return redirect(url_for('dashboard'))
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('admin/manage_users.html', users=users)

@app.route('/admin/users/create', methods=['POST'])
@login_required
def create_user():
    if current_user.role != 'SuperAdmin': return redirect(url_for('dashboard'))
    uname = request.form.get('username')
    pw = request.form.get('password')
    dept = request.form.get('department')
    email = request.form.get('email')
    
    if User.query.filter_by(username=uname).first():
        flash(f'Error: Username "{uname}" already taken.', 'error')
        return redirect(url_for('manage_users'))

    if User.query.filter_by(department=dept).first():
        flash(f'Error: The department "{dept}" already has an admin.', 'error')
        return redirect(url_for('manage_users'))
    
    try:
        hashed = generate_password_hash(pw, method='pbkdf2:sha256')
        new_user = User(username=uname, password=hashed, role='DeptAdmin', department=dept, email=email)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Success: Admin for {dept} created!', 'success')
    except Exception as e:
        db.session.rollback() 
        flash('Database Integrity Error.', 'error')

    return redirect(url_for('manage_users'))

@app.route('/admin/users/delete/<int:uid>')
@login_required
def delete_user(uid):
    if current_user.role != 'SuperAdmin': return redirect(url_for('dashboard'))
    u = User.query.get(uid)
    if u: db.session.delete(u); db.session.commit()
    return redirect(url_for('manage_users'))

@app.route('/admin/profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        current_user.email = request.form.get('email')
        current_user.bio = request.form.get('bio')
        pic = request.files.get('profile_pic')
        if pic and pic.filename != '':
            fname = secure_filename(pic.filename)
            sdir = os.path.join(app.config['UPLOAD_FOLDER'], 'profiles')
            if not os.path.exists(sdir): os.makedirs(sdir)
            pic.save(os.path.join(sdir, fname))
            current_user.profile_pic = f'uploads/profiles/{fname}'
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('admin/edit_profile.html')

# --- APIs ---
@app.route('/api/notices/<date_str>')
def get_notices_by_date(date_str):
    try:
        target = datetime.strptime(date_str, '%Y-%m-%d').date()
        matches = [{'title': n.title, 'type': n.type, 'dept': n.author.department or 'General', 'content': n.content} 
                   for n in Notice.query.all() if n.date_posted.date() == target]
        return jsonify(matches)
    except ValueError: return jsonify([])

@app.route('/api/admins')
def get_admins():
    # Return all admins so student can choose who to message
    admins = User.query.filter(User.role != 'SuperAdmin').all()
    data = [{'id': a.id, 'name': a.full_name or a.username, 'dept': a.department, 'email': a.email, 'bio': a.bio or "", 'pic': a.profile_pic or 'default.png'} for a in admins]
    return jsonify(data)

@app.route('/api/admin_notices/<int:aid>')
def get_admin_notices(aid):
    notices = Notice.query.filter_by(author_id=aid).order_by(Notice.date_posted.desc()).all()
    return jsonify([{'title': n.title, 'date': n.date_posted.strftime('%Y-%m-%d')} for n in notices])

@app.route('/submit_request', methods=['POST'])
def submit_request():
    name = request.form.get('name')
    contact = request.form.get('contact')
    target_id = request.form.get('target_admin') # ID of specific admin
    msg = request.form.get('message')
    
    mpath = None
    f = request.files.get('media')
    if f and f.filename != '':
        fn = secure_filename(f.filename)
        sd = os.path.join(app.config['UPLOAD_FOLDER'], 'requests')
        if not os.path.exists(sd): os.makedirs(sd)
        f.save(os.path.join(sd, fn))
        mpath = f'uploads/requests/{fn}'
    
    # Fetch admin to get dept name for fallback
    admin = User.query.get(target_id)
    dept = admin.department if admin else "General"

    db.session.add(StudentRequest(name=name, contact_info=contact, department=dept, target_admin_id=target_id, message=msg, media_path=mpath))
    db.session.commit()
    return jsonify({'success': 'Sent!'})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

def create_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(role='SuperAdmin').first():
            hashed = generate_password_hash('admin123', method='pbkdf2:sha256')
            super_admin = User(username='admin', password=hashed, role='SuperAdmin', department='Head Office', email='biradarnaveen637@gmail.com')
            db.session.add(super_admin)
            db.session.commit()
            print(">>> SUPER ADMIN READY")

if __name__ == '__main__':
    create_db()
    app.run(debug=True, host='0.0.0.0', port=5000)