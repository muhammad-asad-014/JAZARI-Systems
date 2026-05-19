from flask import Blueprint, render_template, request, jsonify, flash, session, redirect, url_for
from .auth import teacher_only
from werkzeug.security import generate_password_hash
from flask_login import login_required



teacherViews = Blueprint('teacherViews', __name__)


@teacherViews.route('/')
@teacher_only
def home():
    from .models import Student, Teacher, Task, Attendance, Quiz
    teacher_data = Teacher.query.filter_by(id=session['id']).first()
    tasks = Task.query.filter_by(user=session['id']).order_by(Task.date_created.desc()).all()

    data = {'students': Student.query.filter_by(classID=teacher_data.classID).count(), 
            'lectures':Attendance.query.filter_by(teacher=session['id']).count(), 
            'quizzes': Quiz.query.filter_by(teacher=session['id']).count()}
    return render_template("/teacher/teacher-home.html", data=data, tasks=tasks)



@teacherViews.route('/update-task/<task_id>', methods=['POST'])
@login_required
def update_task(task_id):
    from .models import Task
    from . import db
    task = Task.query.get_or_404(task_id)
    if task.user == session['id']:
        task.is_done = not task.is_done
        db.session.commit()
    return redirect(url_for('teacherViews.home'))

@teacherViews.route('/add-task', methods=['POST'])
@login_required
def add_task():
    title = request.form.get('task_title')
    from .models import Task
    if title:
        new_task = Task(
            title=title,
            user= session['id']
        )
        from . import db
        db.session.add(new_task)
        db.session.commit()
        flash("Task added!", "success")
    return redirect(url_for('teacherViews.home'))

@teacherViews.route('/delete-task/<task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    from .models import Task
    task = Task.query.get_or_404(task_id)
    if task.user == session['id']:
        from . import db
        db.session.delete(task)
        db.session.commit()
    return redirect(url_for('teacherViews.home'))



@teacherViews.route('/update-profile', methods=['GET', 'POST'])
@teacher_only
def updateTeacherProfile():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('old_pass')
        new_pass = request.form.get('password')
        id = request.form.get('id')
        from .models import Teacher
        from . import db
        try:
            if new_pass:
                password=generate_password_hash(new_pass,  method='pbkdf2:sha256')
            db.session.query(Teacher).filter(Teacher.id == id).update({
                "fname": fname,
                "lname": lname,
                "email": email,
                "phone": phone,
                'password': password
            })
            db.session.commit()
            session['fullname'] = fname+ " "+lname
            flash("Profile updated successfully.", 'success')
            return redirect(url_for('teacherViews.updateTeacherProfile'))
        except Exception as e:
            flash("Failed to update profile.", 'error')
            print(e)
            return redirect(url_for('teacherViews.updateTeacherProfile'))
    else:
        pass
    from .models import Teacher
    teacher_data = Teacher.query.filter_by(id=session['id']).first()
    return render_template("/teacher/teacher-profile.html", data= teacher_data)
