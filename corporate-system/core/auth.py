from flask import Blueprint, render_template, request,redirect, url_for, session
from flask_login import login_required,  login_user, logout_user
from werkzeug.security import check_password_hash

auth = Blueprint('auth', __name__)

@auth.route('/', methods= ['GET','POST'])
def login():
    from .models import Administrator, Teacher
    if request.method == 'POST':
        uname = request.form.get('uname').lower()
        psw = request.form.get('psw')
        admin = Administrator.query.filter_by(username=uname).first()
        teacher = Teacher.query.filter_by(id = uname).first()
        if admin:
            if check_password_hash(admin.password, psw):
                print('it is admin')
                session['user_role'] = 'admin'
                session['username'] = admin.username
                session['fullname'] = admin.fname+" "+admin.lname
                login_user(admin, remember=True)
                return redirect(url_for('adminViews.home'))
        elif teacher:
            if check_password_hash(teacher.password, psw):
                print('it is teacher')
                session['user_role'] = 'teacher'
                session['id'] = teacher.id
                session['classID'] = teacher.classID
                session['fullname']  = teacher.fname+" "+teacher.lname
                login_user(teacher,remember=True)
                return redirect(url_for('teacherViews.home'))
        else:
            print('no user found')
            return render_template("login.html")
    if current_user.is_authenticated:
        if current_user.user_role == 'admin':
            return redirect(url_for('adminViews.home'))
        elif current_user.user_role == 'teacher':
            return redirect(url_for('teacherViews.home'))
    return render_template("login.html")

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('user_role', None)
    return redirect(url_for('auth.login'))



from functools import wraps
from flask import abort
from flask_login import current_user

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_role != 'admin':
            abort(403) 
        return f(*args, **kwargs)
    return decorated_function

def teacher_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_role != 'teacher':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function