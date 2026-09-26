from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import os
import json

from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ==================== MODELS ====================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='member')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    memberships = db.relationship('Membership', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class PhoneOTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(15), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(20), default='register')
    name = db.Column(db.String(100))
    password_hash = db.Column(db.String(200))
    is_used = db.Column(db.Boolean, default=False)
    attempts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)


class Chama(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    contribution_amount = db.Column(db.Float, default=1000.0)
    contribution_day = db.Column(db.Integer, default=5)
    loan_interest_rate = db.Column(db.Float, default=5.0)
    max_loan_multiplier = db.Column(db.Float, default=3.0)
    currency = db.Column(db.String(10), default='KES')
    fine_amount = db.Column(db.Float, default=200.0)
    fine_grace_days = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    memberships = db.relationship('Membership', backref='chama', lazy=True)
    contributions = db.relationship('Contribution', backref='chama', lazy=True)
    loans = db.relationship('Loan', backref='chama', lazy=True)
    merry_go_rounds = db.relationship('MerryGoRound', backref='chama', lazy=True)
    meetings = db.relationship('Meeting', backref='chama', lazy=True)
    fines = db.relationship('Fine', backref='chama', lazy=True)


class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chama_id = db.Column(db.Integer, db.ForeignKey('chama.id'), nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_savings = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    role_in_chama = db.Column(db.String(20), default='member')


class Contribution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chama_id = db.Column(db.Integer, db.ForeignKey('chama.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    contribution_date = db.Column(db.Date, default=date.today)
    month = db.Column(db.String(7))
    payment_method = db.Column(db.String(30), default='Cash')
    mpesa_code = db.Column(db.String(20))
    notes = db.Column(db.String(200))
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', foreign_keys=[user_id])


class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chama_id = db.Column(db.Integer, db.ForeignKey('chama.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    total_repayable = db.Column(db.Float, nullable=False)
    amount_paid = db.Column(db.Float, default=0.0)
    purpose = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    approval_date = db.Column(db.DateTime)
    due_date = db.Column(db.Date)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', foreign_keys=[user_id])
    repayments = db.relationship('LoanRepayment', backref='loan', lazy=True)


class LoanRepayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, default=date.today)
    payment_method = db.Column(db.String(30), default='Cash')
    mpesa_code = db.Column(db.String(20))
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MerryGoRound(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chama_id = db.Column(db.Integer, db.ForeignKey('chama.id'), nullable=False)
    name = db.Column(db.String(100), default='Merry Go Round')
    contribution_per_member = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.Date, default=date.today)
    frequency = db.Column(db.String(20), default='monthly')
    is_active = db.Column(db.Boolean, default=True)
    rounds = db.relationship('MGRRound', backref='merry_go_round', lazy=True, order_by='MGRRound.round_number')


class MGRRound(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mgr_id = db.Column(db.Integer, db.ForeignKey('merry_go_round.id'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scheduled_date = db.Column(db.Date)
    amount = db.Column(db.Float)
    status = db.Column(db.String(20), default='upcoming')
    paid_date = db.Column(db.Date)
    recipient = db.relationship('User')


class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chama_id = db.Column(db.Integer, db.ForeignKey('chama.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    meeting_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    agenda = db.Column(db.Text)
    minutes = db.Column(db.Text)
    status = db.Column(db.String(20), default='scheduled')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meeting.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    present = db.Column(db.Boolean, default=False)
    apology = db.Column(db.String(200))


class Fine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chama_id = db.Column(db.Integer, db.ForeignKey('chama.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    month = db.Column(db.String(7))
    status = db.Column(db.String(20), default='unpaid')
    issued_date = db.Column(db.Date, default=date.today)
    paid_date = db.Column(db.Date)
    issued_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', foreign_keys=[user_id])


class MpesaTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chama_id = db.Column(db.Integer, db.ForeignKey('chama.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    purpose = db.Column(db.String(50))
    reference = db.Column(db.String(50))
    checkout_request_id = db.Column(db.String(100))
    merchant_request_id = db.Column(db.String(100))
    mpesa_receipt = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')
    result_desc = db.Column(db.String(200))
    loan_id = db.Column(db.Integer, db.ForeignKey('loan.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    user = db.relationship('User', foreign_keys=[user_id])


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    # ==================== HELPERS ====================

def get_user_chamas(user):
    return Chama.query.join(Membership).filter(
        Membership.user_id == user.id,
        Membership.is_active == True
    ).all()

def get_membership(user_id, chama_id):
    return Membership.query.filter_by(user_id=user_id, chama_id=chama_id, is_active=True).first()

def is_treasurer_or_chair(user, chama_id):
    m = get_membership(user.id, chama_id)
    if not m:
        return False
    return m.role_in_chama in ['treasurer', 'chairperson'] or user.role in ['treasurer', 'chairperson']

def calculate_group_balance(chama_id):
    total_contrib = db.session.query(db.func.sum(Contribution.amount)).filter_by(chama_id=chama_id).scalar() or 0
    total_loans = db.session.query(db.func.sum(Loan.amount)).filter(
        Loan.chama_id == chama_id,
        Loan.status.in_(['approved', 'active'])
    ).scalar() or 0
    total_repaid = db.session.query(db.func.sum(LoanRepayment.amount)).join(Loan).filter(
        Loan.chama_id == chama_id
    ).scalar() or 0
    return total_contrib - total_loans + total_repaid

def format_money(amount, currency='KES'):
    symbols = {'KES': 'KES', 'UGX': 'UGX', 'TZS': 'TZS', 'USD': '$', 'EUR': '€', 'GBP': '£', 'RWF': 'RWF'}
    symbol = symbols.get(currency, currency)
    return f"{symbol} {amount:,.0f}"

def get_unpaid_members_this_month(chama_id):
    chama = Chama.query.get(chama_id)
    if not chama:
        return []
    this_month = date.today().strftime('%Y-%m')
    members = Membership.query.filter_by(chama_id=chama_id, is_active=True).all()
    unpaid = []
    for m in members:
        paid = Contribution.query.filter_by(chama_id=chama_id, user_id=m.user_id, month=this_month).first()
        if not paid:
            unpaid.append(m)
    return unpaid

# ==================== ROUTES ====================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

def _normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(' ', '').replace('-', '').replace('+', '')
    if phone.startswith('254'):
        phone = '0' + phone[3:]
    if not phone.startswith('0') and len(phone) == 9:
        phone = '0' + phone
    return phone

def _generate_otp() -> str:
    import random
    return f"{random.randint(100000, 999999)}"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = _normalize_phone(request.form.get('phone', ''))
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not name or not phone or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')
        if len(phone) < 10:
            flash('Enter a valid Kenyan phone number (e.g. 07XXXXXXXX).', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')
        if User.query.filter_by(phone=phone).first():
            flash('Phone number already registered. Please login.', 'danger')
            return render_template('register.html')
        PhoneOTP.query.filter_by(phone=phone, purpose='register', is_used=False).update({'is_used': True})
        code = _generate_otp()
        otp = PhoneOTP(
            phone=phone, code=code, purpose='register', name=name,
            password_hash=generate_password_hash(password),
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(otp)
        db.session.commit()
        try:
            from services.sms import SMSService
            sms = SMSService()
            result = sms.send(phone, f"Your ChamaApp verification code is: {code}. Valid for 10 minutes. Do not share this code.")
            if result.get('simulated'):
                session['debug_otp'] = code
        except Exception as e:
            print(f'OTP SMS error: {e}')
            session['debug_otp'] = code
        session['otp_phone'] = phone
        flash('Verification code sent to your phone. Enter it below.', 'success')
        return redirect(url_for('verify_otp'))
    return render_template('register.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    phone = session.get('otp_phone')
    if not phone:
        flash('Please start registration first.', 'warning')
        return redirect(url_for('register'))
    debug_otp = session.get('debug_otp')
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        action = request.form.get('action', 'verify')
        if action == 'resend':
            PhoneOTP.query.filter_by(phone=phone, purpose='register', is_used=False).update({'is_used': True})
            new_code = _generate_otp()
            last = PhoneOTP.query.filter_by(phone=phone, purpose='register').order_by(PhoneOTP.created_at.desc()).first()
            otp = PhoneOTP(
                phone=phone, code=new_code, purpose='register',
                name=last.name if last else '', password_hash=last.password_hash if last else '',
                expires_at=datetime.utcnow() + timedelta(minutes=10)
            )
            db.session.add(otp)
            db.session.commit()
            try:
                from services.sms import SMSService
                SMSService().send(phone, f"Your ChamaApp verification code is: {new_code}. Valid for 10 minutes.")
                session['debug_otp'] = new_code
            except Exception:
                session['debug_otp'] = new_code
            flash('New code sent to your phone.', 'success')
            return redirect(url_for('verify_otp'))
        otp = PhoneOTP.query.filter_by(phone=phone, purpose='register', is_used=False, code=code).order_by(PhoneOTP.created_at.desc()).first()
        if not otp:
            latest = PhoneOTP.query.filter_by(phone=phone, purpose='register', is_used=False).order_by(PhoneOTP.created_at.desc()).first()
            if latest:
                latest.attempts += 1
                db.session.commit()
                if latest.attempts >= 5:
                    latest.is_used = True
                    db.session.commit()
                    flash('Too many wrong attempts. Please register again.', 'danger')
                    session.pop('otp_phone', None)
                    session.pop('debug_otp', None)
                    return redirect(url_for('register'))
            flash('Invalid code. Please try again.', 'danger')
            return render_template('verify_otp.html', phone=phone, debug_otp=session.get('debug_otp'))
        if otp.expires_at < datetime.utcnow():
            otp.is_used = True
            db.session.commit()
            flash('Code expired. Please register again.', 'danger')
            session.pop('otp_phone', None)
            session.pop('debug_otp', None)
            return redirect(url_for('register'))
        if User.query.filter_by(phone=phone).first():
            flash('Phone already registered. Please login.', 'warning')
            session.pop('otp_phone', None)
            session.pop('debug_otp', None)
            return redirect(url_for('login'))
        user = User(name=otp.name, phone=phone, password_hash=otp.password_hash)
        db.session.add(user)
        otp.is_used = True
        db.session.commit()
        session.pop('otp_phone', None)
        session.pop('debug_otp', None)
        login_user(user, remember=True)
        flash('Phone verified! Welcome to ChamaApp.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('verify_otp.html', phone=phone, debug_otp=debug_otp)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        phone = _normalize_phone(request.form.get('phone', ''))
        password = request.form.get('password', '')
        user = User.query.filter_by(phone=phone).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash('Invalid phone or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    chamas = get_user_chamas(current_user)
    total_savings = 0
    active_loans = 0
    for c in chamas:
        m = get_membership(current_user.id, c.id)
        if m:
            total_savings += m.total_savings
        loans = Loan.query.filter_by(user_id=current_user.id, chama_id=c.id, status='active').all()
        active_loans += sum(l.total_repayable - l.amount_paid for l in loans)
    upcoming_meetings = Meeting.query.join(Membership, Meeting.chama_id == Membership.chama_id).filter(
        Membership.user_id == current_user.id,
        Meeting.meeting_date >= datetime.now(),
        Meeting.status == 'scheduled'
    ).order_by(Meeting.meeting_date).limit(5).all()
    return render_template('dashboard.html', chamas=chamas, total_savings=total_savings, active_loans=active_loans, upcoming_meetings=upcoming_meetings)

@app.route('/chama/create', methods=['GET', 'POST'])
@login_required
def create_chama():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        amount = float(request.form.get('contribution_amount', 1000))
        day = int(request.form.get('contribution_day', 5))
        interest = float(request.form.get('loan_interest_rate', 5))
        currency = request.form.get('currency', 'KES')
        if not name:
            flash('Chama name is required.', 'danger')
            return render_template('create_chama.html')
        chama = Chama(name=name, description=description, contribution_amount=amount, contribution_day=day, loan_interest_rate=interest, currency=currency)
        db.session.add(chama)
        db.session.flush()
        db.session.add(Membership(user_id=current_user.id, chama_id=chama.id, role_in_chama='chairperson', total_savings=0))
        db.session.commit()
        flash(f'Chama "{name}" created successfully!', 'success')
        return redirect(url_for('chama_detail', chama_id=chama.id))
    return render_template('create_chama.html')

@app.route('/chama/<int:chama_id>')
@login_required
def chama_detail(chama_id):
    chama = Chama.query.get_or_404(chama_id)
    membership = get_membership(current_user.id, chama_id)
    if not membership:
        flash('You are not a member of this Chama.', 'danger')
        return redirect(url_for('dashboard'))
    members = Membership.query.filter_by(chama_id=chama_id, is_active=True).all()
    recent_contribs = Contribution.query.filter_by(chama_id=chama_id).order_by(Contribution.created_at.desc()).limit(10).all()
    active_loans = Loan.query.filter(Loan.chama_id == chama_id, Loan.status.in_(['pending', 'active', 'approved'])).all()
    group_balance = calculate_group_balance(chama_id)
    is_admin = is_treasurer_or_chair(current_user, chama_id)
    mgr = MerryGoRound.query.filter_by(chama_id=chama_id, is_active=True).first()
    return render_template('chama_detail.html', chama=chama, membership=membership, members=members, recent_contribs=recent_contribs, active_loans=active_loans, group_balance=group_balance, is_admin=is_admin, mgr=mgr)

@app.route('/chama/<int:chama_id>/members')
@login_required
def chama_members(chama_id):
    chama = Chama.query.get_or_404(chama_id)
    membership = get_membership(current_user.id, chama_id)
    if not membership:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    members = Membership.query.filter_by(chama_id=chama_id, is_active=True).all()
    is_admin = is_treasurer_or_chair(current_user, chama_id)
    return render_template('members.html', chama=chama, members=members, is_admin=is_admin)

@app.route('/chama/<int:chama_id>/add_member', methods=['POST'])
@login_required
def add_member(chama_id):
    if not is_treasurer_or_chair(current_user, chama_id):
        flash('Only treasurer or chairperson can add members.', 'danger')
        return redirect(url_for('chama_members', chama_id=chama_id))
    phone = _normalize_phone(request.form.get('phone', ''))
    role = request.form.get('role', 'member')
    user = User.query.filter_by(phone=phone).first()
    if not user:
        flash('User with that phone not found. They must register first.', 'danger')
        return redirect(url_for('chama_members', chama_id=chama_id))
    if get_membership(user.id, chama_id):
        flash('User is already a member.', 'warning')
        return redirect(url_for('chama_members', chama_id=chama_id))
    db.session.add(Membership(user_id=user.id, chama_id=chama_id, role_in_chama=role))
    db.session.commit()
    flash(f'{user.name} added successfully!', 'success')
    return redirect(url_for('chama_members', chama_id=chama_id))

@app.route('/chama/<int:chama_id>/contributions')
@login_required
def contributions(chama_id):
    chama = Chama.query.get_or_404(chama_id)
    membership = get_membership(current_user.id, chama_id)
    if not membership:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    contribs = Contribution.query.filter_by(chama_id=chama_id).order_by(Contribution.contribution_date.desc()).all()
    is_admin = is_treasurer_or_chair(current_user, chama_id)
    members = Membership.query.filter_by(chama_id=chama_id, is_active=True).all()
    return render_template('contributions.html', chama=chama, contribs=contribs, is_admin=is_admin, members=members)

@app.route('/chama/<int:chama_id>/add_contribution', methods=['POST'])
@login_required
def add_contribution(chama_id):
    if not is_treasurer_or_chair(current_user, chama_id):
        flash('Only treasurer or chairperson can record contributions.', 'danger')
        return redirect(url_for('contributions', chama_id=chama_id))
    user_id = int(request.form.get('user_id'))
    amount = float(request.form.get('amount'))
    contrib_date = request.form.get('contribution_date')
    method = request.form.get('payment_method', 'Cash')
    mpesa = request.form.get('mpesa_code', '')
    notes = request.form.get('notes', '')
    if contrib_date:
        contrib_date = datetime.strptime(contrib_date, '%Y-%m-%d').date()
    else:
        contrib_date = date.today()
    month = contrib_date.strftime('%Y-%m')
    contrib = Contribution(chama_id=chama_id, user_id=user_id, amount=amount, contribution_date=contrib_date, month=month, payment_method=method, mpesa_code=mpesa if method == 'M-Pesa' else None, notes=notes, recorded_by=current_user.id)
    db.session.add(contrib)
    membership = get_membership(user_id, chama_id)
    if membership:
        membership.total_savings += amount
    db.session.commit()
    try:
        from services.sms import SMSService
        user = User.query.get(user_id)
        chama = Chama.query.get(chama_id)
        if user and chama and membership:
            SMSService().notify_contribution_received(user.phone, user.name, amount, chama.name, membership.total_savings)
    except Exception as e:
        print(f'SMS error: {e}')
    flash('Contribution recorded successfully! SMS sent to member.', 'success')
    return redirect(url_for('contributions', chama_id=chama_id))

@app.route('/chama/<int:chama_id>/loans')
@login_required
def loans(chama_id):
    chama = Chama.query.get_or_404(chama_id)
    membership = get_membership(current_user.id, chama_id)
    if not membership:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    all_loans = Loan.query.filter_by(chama_id=chama_id).order_by(Loan.application_date.desc()).all()
    is_admin = is_treasurer_or_chair(current_user, chama_id)
    return render_template('loans.html', chama=chama, loans=all_loans, is_admin=is_admin, membership=membership)

@app.route('/chama/<int:chama_id>/apply_loan', methods=['POST'])
@login_required
def apply_loan(chama_id):
    membership = get_membership(current_user.id, chama_id)
    if not membership:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    chama = Chama.query.get_or_404(chama_id)
    amount = float(request.form.get('amount'))
    purpose = request.form.get('purpose', '')
    max_loan = membership.total_savings * chama.max_loan_multiplier
    if amount > max_loan:
        flash(f'Maximum loan allowed is KES {max_loan:,.0f} (based on your savings).', 'danger')
        return redirect(url_for('loans', chama_id=chama_id))
    if amount <= 0:
        flash('Invalid amount.', 'danger')
        return redirect(url_for('loans', chama_id=chama_id))
    total_repayable = amount * (1 + chama.loan_interest_rate / 100)
    loan = Loan(chama_id=chama_id, user_id=current_user.id, amount=amount, interest_rate=chama.loan_interest_rate, total_repayable=total_repayable, purpose=purpose, status='pending', due_date=date.today() + relativedelta(months=3))
    db.session.add(loan)
    db.session.commit()
    flash('Loan application submitted successfully!', 'success')
    return redirect(url_for('loans', chama_id=chama_id))

@app.route('/loan/<int:loan_id>/approve', methods=['POST'])
@login_required
def approve_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if not is_treasurer_or_chair(current_user, loan.chama_id):
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    action = request.form.get('action')
    user = User.query.get(loan.user_id)
    chama = Chama.query.get(loan.chama_id)
    if action == 'approve':
        loan.status = 'active'
        loan.approval_date = datetime.utcnow()
        loan.approved_by = current_user.id
        flash('Loan approved! SMS sent to member.', 'success')
        try:
            from services.sms import SMSService
            if user and chama:
                SMSService().notify_loan_approved(user.phone, user.name, loan.amount, chama.name, loan.total_repayable)
        except Exception as e:
            print(f'SMS error: {e}')
    else:
        loan.status = 'rejected'
        flash('Loan rejected. SMS sent to member.', 'info')
        try:
            from services.sms import SMSService
            if user and chama:
                SMSService().notify_loan_rejected(user.phone, user.name, loan.amount, chama.name)
        except Exception as e:
            print(f'SMS error: {e}')
    db.session.commit()
    return redirect(url_for('loans', chama_id=loan.chama_id))

@app.route('/loan/<int:loan_id>/repay', methods=['POST'])
@login_required
def repay_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if not is_treasurer_or_chair(current_user, loan.chama_id) and loan.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    amount = float(request.form.get('amount'))
    method = request.form.get('payment_method', 'Cash')
    mpesa = request.form.get('mpesa_code', '')
    if amount <= 0:
        flash('Invalid amount.', 'danger')
        return redirect(url_for('loans', chama_id=loan.chama_id))
    remaining = loan.total_repayable - loan.amount_paid
    if amount > remaining:
        amount = remaining
    repayment = LoanRepayment(loan_id=loan.id, amount=amount, payment_method=method, mpesa_code=mpesa if method == 'M-Pesa' else None, recorded_by=current_user.id)
    db.session.add(repayment)
    loan.amount_paid += amount
    if loan.amount_paid >= loan.total_repayable:
        loan.status = 'repaid'
    db.session.commit()
    flash(f'Repayment of KES {amount:,.0f} recorded!', 'success')
    return redirect(url_for('loans', chama_id=loan.chama_id))

@app.route('/chama/<int:chama_id>/mgr')
@login_required
def merry_go_round(chama_id):
    chama = Chama.query.get_or_404(chama_id)
    membership = get_membership(current_user.id, chama_id)
    if not membership:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    mgr = MerryGoRound.query.filter_by(chama_id=chama_id, is_active=True).first()
    is_admin = is_treasurer_or_chair(current_user, chama_id)
    members = Membership.query.filter_by(chama_id=chama_id, is_active=True).all()
    return render_template('mgr.html', chama=chama, mgr=mgr, is_admin=is_admin, members=members)

@app.route('/chama/<int:chama_id>/create_mgr', methods=['POST'])
@login_required
def create_mgr(chama_id):
    if not is_treasurer_or_chair(current_user, chama_id):
        flash('Access denied.', 'danger')
        return redirect(url_for('merry_go_round', chama_id=chama_id))
    existing = MerryGoRound.query.filter_by(chama_id=chama_id, is_active=True).all()
    for e in existing:
        e.is_active = False
    name = request.form.get('name', 'Merry Go Round')
    amount = float(request.form.get('contribution_per_member'))
    frequency = request.form.get('frequency', 'monthly')
    mgr = MerryGoRound(chama_id=chama_id, name=name, contribution_per_member=amount, frequency=frequency)
    db.session.add(mgr)
    db.session.flush()
    members = Membership.query.filter_by(chama_id=chama_id, is_active=True).all()
    start = date.today()
    for i, m in enumerate(members):
        sched = start + relativedelta(months=i) if frequency == 'monthly' else start + timedelta(weeks=i)
        total_pot = amount * len(members)
        db.session.add(MGRRound(mgr_id=mgr.id, round_number=i + 1, recipient_id=m.user_id, scheduled_date=sched, amount=total_pot, status='upcoming'))
    db.session.commit()
    flash('Merry Go Round created successfully!', 'success')
    return redirect(url_for('merry_go_round', chama_id=chama_id))

@app.route('/mgr_round/<int:round_id>/mark_paid', methods=['POST'])
@login_required
def mark_mgr_paid(round_id):
    rnd = MGRRound.query.get_or_404(round_id)
    mgr = MerryGoRound.query.get(rnd.mgr_id)
    if not is_treasurer_or_chair(current_user, mgr.chama_id):
        flash('Access denied.', 'danger')
        return redirect(url_for('merry_go_round', chama_id=mgr.chama_id))
    rnd.status = 'paid'
    rnd.paid_date = date.today()
    db.session.commit()
    try:
        from services.sms import SMSService
        chama = Chama.query.get(mgr.chama_id)
        if chama and rnd.recipient:
            SMSService().notify_mgr_payout(rnd.recipient.phone, rnd.recipient.name, rnd.amount or 0, rnd.round_number, chama.name)
    except Exception as e:
        print(f'SMS error: {e}')
    flash(f'Round {rnd.round_number} marked as paid to {rnd.recipient.name}! SMS sent.', 'success')
    return redirect(url_for('merry_go_round', chama_id=mgr.chama_id))
    @app.route('/chama/<int:chama_id>/meetings')
@login_required
def meetings(chama_id):
    chama = Chama.query.get_or_404(chama_id)
    membership = get_membership(current_user.id, chama_id)
    if not membership:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    all_meetings = Meeting.query.filter_by(chama_id=chama_id).order_by(Meeting.meeting_date.desc()).all()
    is_admin = is_treasurer_or_chair(current_user, chama_id)
    return render_template('meetings.html', chama=chama, meetings=all_meetings, is_admin=is_admin)


@app.route('/chama/<int:chama_id>/create_meeting', methods=['POST'])
@login_required
def create_meeting(chama_id):
    if not is_treasurer_or_chair(current_user, chama_id):
        flash('Only treasurer or chairperson can schedule meetings.', 'danger')
        return redirect(url_for('meetings', chama_id=chama_id))
    title = request.form.get('title', '').strip()
    meeting_date_str = request.form.get('meeting_date')
    location = request.form.get('location', '')
    agenda = request.form.get('agenda', '')
    if not title or not meeting_date_str:
        flash('Title and date are required.', 'danger')
        return redirect(url_for('meetings', chama_id=chama_id))
    meeting_date = datetime.strptime(meeting_date_str, '%Y-%m-%dT%H:%M')
    meeting = Meeting(
        chama_id=chama_id,
        title=title,
        meeting_date=meeting_date,
        location=location,
        agenda=agenda,
        created_by=current_user.id
    )
    db.session.add(meeting)
    db.session.commit()
    flash('Meeting scheduled successfully!', 'success')
    return redirect(url_for('meetings', chama_id=chama_id))


@app.route('/meeting/<int:meeting_id>')
@login_required
def meeting_detail(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    membership = get_membership(current_user.id, meeting.chama_id)
    if not membership:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    attendances = Attendance.query.filter_by(meeting_id=meeting_id).all()
    members = Membership.query.filter_by(chama_id=meeting.chama_id, is_active=True).all()
    is_admin = is_treasurer_or_chair(current_user, meeting.chama_id)
    return render_template('meeting_detail.html', meeting=meeting, attendances=attendances, members=members, is_admin=is_admin)


@app.route('/meeting/<int:meeting_id>/attendance', methods=['POST'])
@login_required
def mark_attendance(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    if not is_treasurer_or_chair(current_user, meeting.chama_id):
        flash('Access denied.', 'danger')
        return redirect(url_for('meeting_detail', meeting_id=meeting_id))
    present_ids = request.form.getlist('present')
    members = Membership.query.filter_by(chama_id=meeting.chama_id, is_active=True).all()
    for m in members:
        att = Attendance.query.filter_by(meeting_id=meeting_id, user_id=m.user_id).first()
        if not att:
            att = Attendance(meeting_id=meeting_id, user_id=m.user_id)
            db.session.add(att)
        att.present = str(m.user_id) in present_ids
    db.session.commit()
    flash('Attendance recorded.', 'success')
    return redirect(url_for('meeting_detail', meeting_id=meeting_id))


@app.route('/meeting/<int:meeting_id>/minutes', methods=['POST'])
@login_required
def update_minutes(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    if not is_treasurer_or_chair(current_user, meeting.chama_id):
        flash('Access denied.', 'danger')
        return redirect(url_for('meeting_detail', meeting_id=meeting_id))
    meeting.minutes = request.form.get('minutes', '')
    meeting.status = 'completed'
    db.session.commit()
    flash('Minutes saved.', 'success')
    return redirect(url_for('meeting_detail', meeting_id=meeting_id))


@app.route('/chama/<int:chama_id>/fines')
@login_required
def fines(chama_id):
    chama = Chama.query.get_or_404(chama_id)
    membership = get_membership(current_user.id, chama_id)
    if not membership:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    all_fines = Fine.query.filter_by(chama_id=chama_id).order_by(Fine.issued_date.desc()).all()
    is_admin = is_treasurer_or_chair(current_user, chama_id)
    members = Membership.query.filter_by(chama_id=chama_id, is_active=True).all()
    return render_template('fines.html', chama=chama, fines=all_fines, is_admin=is_admin, members=members)


@app.route('/chama/<int:chama_id>/issue_fine', methods=['POST'])
@login_required
def issue_fine(chama_id):
    if not is_treasurer_or_chair(current_user, chama_id):
        flash('Only treasurer or chairperson can issue fines.', 'danger')
        return redirect(url_for('fines', chama_id=chama_id))
    user_id = int(request.form.get('user_id'))
    amount = float(request.form.get('amount', 200))
    reason = request.form.get('reason', '').strip()
    notes = request.form.get('notes', '')
    if not reason:
        flash('Reason is required.', 'danger')
        return redirect(url_for('fines', chama_id=chama_id))
    month = date.today().strftime('%Y-%m')
    fine = Fine(
        chama_id=chama_id,
        user_id=user_id,
        amount=amount,
        reason=reason,
        month=month,
        issued_by=current_user.id,
        notes=notes
    )
    db.session.add(fine)
    db.session.commit()
    try:
        from services.sms import SMSService
        user = User.query.get(user_id)
        chama = Chama.query.get(chama_id)
        if user and chama:
            SMSService().send(user.phone, f"Hi {user.name}, you have been issued a fine of KES {amount:,.0f} in {chama.name}. Reason: {reason}")
    except Exception as e:
        print(f'SMS error: {e}')
    flash('Fine issued successfully!', 'success')
    return redirect(url_for('fines', chama_id=chama_id))


@app.route('/fine/<int:fine_id>/pay', methods=['POST'])
@login_required
def pay_fine(fine_id):
    fine = Fine.query.get_or_404(fine_id)
    if not is_treasurer_or_chair(current_user, fine.chama_id) and fine.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    fine.status = 'paid'
    fine.paid_date = date.today()
    db.session.commit()
    flash('Fine marked as paid.', 'success')
    return redirect(url_for('fines', chama_id=fine.chama_id))


@app.route('/chama/<int:chama_id>/settings', methods=['GET', 'POST'])
@login_required
def chama_settings(chama_id):
    chama = Chama.query.get_or_404(chama_id)
    if not is_treasurer_or_chair(current_user, chama_id):
        flash('Access denied.', 'danger')
        return redirect(url_for('chama_detail', chama_id=chama_id))
    if request.method == 'POST':
        chama.name = request.form.get('name', chama.name).strip()
        chama.description = request.form.get('description', '')
        chama.contribution_amount = float(request.form.get('contribution_amount', chama.contribution_amount))
        chama.contribution_day = int(request.form.get('contribution_day', chama.contribution_day))
        chama.loan_interest_rate = float(request.form.get('loan_interest_rate', chama.loan_interest_rate))
        chama.max_loan_multiplier = float(request.form.get('max_loan_multiplier', chama.max_loan_multiplier))
        chama.fine_amount = float(request.form.get('fine_amount', chama.fine_amount))
        chama.fine_grace_days = int(request.form.get('fine_grace_days', chama.fine_grace_days))
        chama.currency = request.form.get('currency', chama.currency)
        db.session.commit()
        flash('Chama settings updated.', 'success')
        return redirect(url_for('chama_settings', chama_id=chama_id))
    return render_template('chama_settings.html', chama=chama)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if name:
            current_user.name = name
            db.session.commit()
            flash('Profile updated.', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html')


# ==================== MPESA (STK Push) ====================

@app.route('/chama/<int:chama_id>/pay', methods=['GET', 'POST'])
@login_required
def mpesa_pay(chama_id):
    chama = Chama.query.get_or_404(chama_id)
    membership = get_membership(current_user.id, chama_id)
    if not membership:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        purpose = request.form.get('purpose', 'contribution')
        phone = _normalize_phone(request.form.get('phone', current_user.phone))
        if amount <= 0:
            flash('Invalid amount.', 'danger')
            return redirect(url_for('mpesa_pay', chama_id=chama_id))
        # Create pending transaction
        txn = MpesaTransaction(
            chama_id=chama_id,
            user_id=current_user.id,
            amount=amount,
            phone=phone,
            purpose=purpose,
            status='pending'
        )
        db.session.add(txn)
        db.session.commit()
        try:
            from services.mpesa import MpesaService
            mpesa = MpesaService()
            result = mpesa.stk_push(phone, amount, account_reference=f"CHAMA{chama_id}", description=purpose)
            if result.get('CheckoutRequestID'):
                txn.checkout_request_id = result['CheckoutRequestID']
                txn.merchant_request_id = result.get('MerchantRequestID')
                db.session.commit()
                flash('STK Push sent! Check your phone to complete payment.', 'success')
            else:
                txn.status = 'failed'
                txn.result_desc = str(result)
                db.session.commit()
                flash('Failed to initiate M-Pesa payment. Try again later.', 'danger')
        except Exception as e:
            print(f'M-Pesa error: {e}')
            txn.status = 'failed'
            txn.result_desc = str(e)
            db.session.commit()
            flash('M-Pesa service unavailable. Please try again later.', 'danger')
        return redirect(url_for('chama_detail', chama_id=chama_id))
    return render_template('mpesa_pay.html', chama=chama)


@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    data = request.get_json(silent=True) or {}
    try:
        body = data.get('Body', {}).get('stkCallback', {})
        result_code = body.get('ResultCode')
        checkout_id = body.get('CheckoutRequestID')
        txn = MpesaTransaction.query.filter_by(checkout_request_id=checkout_id).first()
        if not txn:
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})
        if result_code == 0:
            # Success
            metadata = body.get('CallbackMetadata', {}).get('Item', [])
            receipt = None
            for item in metadata:
                if item.get('Name') == 'MpesaReceiptNumber':
                    receipt = item.get('Value')
            txn.status = 'completed'
            txn.mpesa_receipt = receipt
            txn.completed_at = datetime.utcnow()
            txn.result_desc = body.get('ResultDesc', 'Success')
            # Auto-record contribution if purpose is contribution
            if txn.purpose == 'contribution':
                month = date.today().strftime('%Y-%m')
                contrib = Contribution(
                    chama_id=txn.chama_id,
                    user_id=txn.user_id,
                    amount=txn.amount,
                    contribution_date=date.today(),
                    month=month,
                    payment_method='M-Pesa',
                    mpesa_code=receipt,
                    recorded_by=txn.user_id
                )
                db.session.add(contrib)
                membership = get_membership(txn.user_id, txn.chama_id)
                if membership:
                    membership.total_savings += txn.amount
            db.session.commit()
        else:
            txn.status = 'failed'
            txn.result_desc = body.get('ResultDesc', 'Failed')
            db.session.commit()
    except Exception as e:
        print(f'Callback error: {e}')
    return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ==================== INIT ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
