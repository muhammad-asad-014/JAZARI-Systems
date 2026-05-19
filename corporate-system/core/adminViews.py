from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, current_app, send_from_directory, abort
from flask_login import logout_user
from werkzeug.security import generate_password_hash
from utils import getImageEmbedding
from werkzeug.utils import secure_filename
from .auth import admin_only
import os
import json
import zipfile
import shutil
import sys
import importlib
import tempfile
import requests

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PHOTOS_FOLDER = os.path.join(BASE_PATH, '.student-pictures')
SETTINGS_FOLDER = os.path.join(BASE_PATH, '.system-settings')
adminViews = Blueprint('adminViews', __name__)
PLUGIN_FOLDER = os.path.join(os.getcwd(), 'JAZARI/core/plugins')
ALLOWED_EXTENSIONS = {'zip'}

PLUGINS_INDEX_URL = "https://raw.githubusercontent.com/muhammad-asad-014/JAZARI-Plugins/main/plugins.json"
GITHUB_REPO = "muhammad-asad-014/JAZARI-Plugins"





@adminViews.route('/')
@admin_only
def home():
    from .models import Student, Class, Teacher, Task
    user = 'admin'
    tasks = Task.query.filter_by(user=user).order_by(Task.date_created.desc()).all()
    data = {'students': Student.query.count(), 'classes':Class.query.count(), 'teachers': Teacher.query.count()}
    return render_template("/admin/admin-home.html", data=data, tasks=tasks)


@adminViews.route('/plugin-store')
@admin_only
def plugin_store():
    try:
        r = requests.get(PLUGINS_INDEX_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        plugins = data.get('plugins', [])

        installed_ids = []
        if os.path.exists(PLUGIN_FOLDER):
            installed_ids = [f for f in os.listdir(PLUGIN_FOLDER) 
                           if os.path.isdir(os.path.join(PLUGIN_FOLDER, f))]

        return render_template('/admin/admin-pluginStore.html', 
                             plugins=plugins, 
                             installed_ids=installed_ids)
    except Exception as e:
        flash(f"Failed to load plugins: {str(e)}", "danger")
        return render_template('/admin/admin-pluginStore.html', plugins=[], installed_ids=[])
    


def register_plugin_dynamic(folder_name):
    """Register plugin safely - with auto restart fallback"""
    try:
        plugin_path = os.path.join(PLUGIN_FOLDER, folder_name)
        manifest_path = os.path.join(plugin_path, 'manifest.json')
        
        if not os.path.exists(manifest_path):
            return False, "No manifest.json found"

        with open(manifest_path) as f:
            manifest = json.load(f)

        plugin_id = manifest.get('id') or folder_name
        plugin_name = manifest.get('name', plugin_id)
        url_prefix = f"/{plugin_id}"

        if url_prefix in current_app.blueprints:
            print(f"Plugin {plugin_name} already registered")
            return True, "Already registered"

        init_file = os.path.join(plugin_path, '__init__.py')
        if not os.path.exists(init_file):
            return False, "__init__.py not found"

        module_name = f"plugins.{folder_name}"
        sys.modules.pop(module_name, None)

        spec = importlib.util.spec_from_file_location(module_name, init_file)
        plugin_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = plugin_module
        spec.loader.exec_module(plugin_module)

        bp = getattr(plugin_module, 'bp', None)
        if not bp:
            return False, "No blueprint named 'bp' found"

        if not getattr(current_app, '_got_first_request', True):
            current_app.register_blueprint(bp, url_prefix=url_prefix)
            print(f"Plugin '{plugin_name}' dynamically registered at {url_prefix}")
            return True, "Successfully registered"
        else:
            print(f"Dynamic registration failed (app already handled requests). Triggering restart...")
            return False, "NEEDS_RESTART"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, str(e)



@adminViews.route('/install-plugin', methods=['POST'])
@admin_only
def install_plugin():
    plugin_id = request.form.get('plugin_id')
    print(f"[PLUGIN INSTALL] Starting installation for: {plugin_id}")

    try:
        r = requests.get(PLUGINS_INDEX_URL, timeout=15)
        r.raise_for_status()
        data = r.json()

        plugin = next((p for p in data.get('plugins', []) if p['id'] == plugin_id), None)
        if not plugin:
            return jsonify({"success": False, "message": "Plugin not found in marketplace"})

        folder_name = plugin['folder_name']
        plugin_name = plugin.get('name', plugin_id)

        print(f"[PLUGIN INSTALL] Found plugin: {plugin_name} → {folder_name}")

        zip_url = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"

        with tempfile.TemporaryDirectory() as tmp:
            zip_path = os.path.join(tmp, "repo.zip")
            
            resp = requests.get(zip_url, stream=True, timeout=45)
            resp.raise_for_status()

            with open(zip_path, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)

            extract_path = os.path.join(tmp, "extract")
            os.makedirs(extract_path, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as z:
                extracted_count = 0
                for member in z.namelist():
                    if member.startswith(f"JAZARI-Plugins-main/plugins/{folder_name}/"):
                        z.extract(member, extract_path)
                        extracted_count += 1

                if extracted_count == 0:
                    return jsonify({
                        "success": False,
                        "message": f"Plugin folder '{folder_name}' not found in repository. Check plugins.json"
                    })

            source = os.path.join(extract_path, f"JAZARI-Plugins-main/plugins/{folder_name}")
            
            if not os.path.exists(source):
                return jsonify({
                    "success": False,
                    "message": f"Extracted folder not found: {folder_name}"
                })

            destination = os.path.join(PLUGIN_FOLDER, folder_name)

            # Remove old version
            if os.path.exists(destination):
                shutil.rmtree(destination)
                print(f"[PLUGIN INSTALL] Removed previous version of {folder_name}")

            shutil.copytree(source, destination)
            print(f"[PLUGIN INSTALL] Files successfully copied to: {destination}")

        #  REGISTER PLUGIN 
        success, message = register_plugin_dynamic(folder_name)

        if success:
            return jsonify({
                "success": True,
                "message": f"{plugin_name} installed and activated successfully"
            })
        elif message == "NEEDS_RESTART":
            # Trigger auto restart
            try:
                main_file = os.path.abspath(sys.argv[0])
                os.utime(main_file, None)   # Touch main file → triggers reload
                print(f"[PLUGIN INSTALL] Restart triggered for {plugin_name}")
                
                return jsonify({
                    "success": True,
                    "message": f"{plugin_name} installed successfully. Server is restarting...",
                    "restarting": True
                })
            except Exception as restart_error:
                print(f"Failed to trigger restart: {restart_error}")
                return jsonify({
                    "success": True,
                    "message": f"{plugin_name} installed. Please restart server manually.",
                    "needs_manual_restart": True
                })
        else:
            return jsonify({
                "success": False,
                "message": f"Files installed but registration failed: {message}"
            })

    except requests.exceptions.RequestException as e:
        print(f"[PLUGIN INSTALL] Network error: {e}")
        return jsonify({"success": False, "message": "Failed to download plugin. Check internet connection."})

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[PLUGIN INSTALL] ERROR: {str(e)}")
        return jsonify({"success": False, "message": f"Installation failed: {str(e)}"})



@adminViews.route('/system-settings/logo/<filename>')
def serve_logo(filename):
    logo_dir = os.path.join(current_app.root_path, '.system-settings')
    
    if not os.path.exists(os.path.join(logo_dir, filename)):
        abort(404)
        
    return send_from_directory(logo_dir, filename)

@adminViews.route('/system-settings', methods=['GET', 'POST'])
@admin_only
def settings():
    from .models import Settings
    from . import db

    if request.method == 'POST':
        update_data = {}

        orgName = request.form.get('orgName')
        if orgName and orgName.strip() != "":
            update_data["orgName"] = orgName.strip()

        usage = request.form.get('usage')
        if usage:
            update_data["usageType"] = usage
            
        update_data["theme"] = 'light'

        orgLogo = request.files.get('orgLogo')
        if orgLogo and orgLogo.filename != '':
            filename = secure_filename(orgLogo.filename)
            file_ext = filename.split('.')[-1]
            saved_filename = f"orgLogo.{file_ext}" 
            
            photo_path = os.path.join(SETTINGS_FOLDER, saved_filename)
            orgLogo.save(photo_path)
            
            update_data["orgLogo"] = saved_filename

        if update_data:
            try:
                db.session.query(Settings).filter(Settings.orgID == '001').update(update_data)
                db.session.commit()
                flash("Settings updated successfully.", 'success')
            except Exception as e:
                db.session.rollback()
                flash("Failed to update settings.", 'error')
                print(f"Database Error: {e}")
        else:
            flash("No changes were made.", 'info')
            
        return redirect(url_for('adminViews.settings'))

    system_info = Settings.query.filter_by(orgID='001').first()
    return render_template("/admin/admin-settings.html", system_info=system_info)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@adminViews.route('/upload-plugin', methods=['POST'])
@admin_only 
def upload_plugin():
    if request.method=='POST':
        if 'plugin_file' not in request.files:
            return jsonify(success=False, message="No file part"), 400
        
        file = request.files['plugin_file']
        if file.filename == '':
            return jsonify(success=False, message="No selected file"), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            zip_path = os.path.join(PLUGIN_FOLDER, filename)
            
            file.save(zip_path)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    extract_path = os.path.join(PLUGIN_FOLDER, filename.rsplit('.', 1)[0])
                    zip_ref.extractall(extract_path)
                
                os.remove(zip_path)

                # RESTART
                main_file = os.path.abspath(sys.argv[0])
                print(main_file)
                try:
                    os.utime(main_file, None)
                except Exception as e:
                    print(f"Could not touch file: {e}")

                return jsonify(success=True, message="Plugin extracted. Server restarting.")

            except Exception as e:
                return jsonify(success=False, message=str(e)), 500

        return jsonify(success=False, message="Invalid file type. Only .zip allowed."), 400

@adminViews.route('/manage-plugins')
@admin_only
def plugins():
    return render_template("/admin/admin-plugins.html")

@adminViews.route('/delete-plugin/<plugin_dir>', methods=['DELETE'])
def delete_plugin(plugin_dir):
    plugin_path = os.path.join(PLUGIN_FOLDER, plugin_dir)

    try:
        if os.path.exists(plugin_path) and os.path.isdir(plugin_path):
            plugin_id = plugin_dir
            manifest_path = os.path.join(plugin_path, 'manifest.json')
            if os.path.exists(manifest_path):
                with open(manifest_path) as f:
                    manifest = json.load(f)
                    plugin_id = manifest.get('id', plugin_dir)
            shutil.rmtree(plugin_path)
            url_prefix = f"/{plugin_id}"
            if url_prefix in current_app.blueprints:
                current_app.blueprints.pop(url_prefix, None)
            
            sys.modules.pop(f"plugins.{plugin_dir}", None)
            return jsonify(success=True, message=f"Plugin {plugin_dir} removed successfully.")
        else:
            return jsonify(success=False, message="Plugin folder not found."), 404
            
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500
            


@adminViews.route('/manage-teacher')
@admin_only
def manageTeachers():
    from .models import Teacher
    from . import db
    data = db.session.execute(db.select(Teacher.id, Teacher.fname, Teacher.lname)).all()
    return render_template("/admin/admin-manageTeachers.html", data=data)


@adminViews.route('/student-photo/<filename>')
def serve_photo(filename):
    print(PHOTOS_FOLDER)
    print(filename)
    photo_dir = os.path.join(current_app.root_path, PHOTOS_FOLDER)
    print(photo_dir)
    return send_from_directory(photo_dir, filename)


@adminViews.route('/manage-student')
@admin_only
def manageStudents():
    from .models import Student
    from . import db
    data = db.session.execute(db.select(Student.id, Student.fname, Student.lname)).all()
    return render_template("/admin/admin-manageStudents.html", data = data)

@adminViews.route('/manage-class')
@admin_only
def manageClasses():
    from .models import Class
    from . import db
    data = db.session.execute(db.select(Class.id, Class.name)).all()
    return render_template("/admin/admin-manageClasses.html", data= data)

@adminViews.route('/update-profile', methods=['GET', 'POST'])
@admin_only
def updateAdminProfile():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        old_uname = request.form.get('old_uname')
        password = request.form.get('old_pass')
        uname = request.form.get('uname')
        new_password = request.form.get('password')
        from .models import Administrator
        from . import db
        try:
            if new_password:
                password = generate_password_hash(new_password,  method='pbkdf2:sha256')
            db.session.query(Administrator).filter(Administrator.username == old_uname).update({
                "username": uname,
                "fname": fname,
                'lname': lname,
                'email': email,
                'password': password
                })
            db.session.commit()
            flash("Admin updated successfully.", 'success')
            session['fullname'] = fname+ " "+lname
            return redirect(url_for('adminViews.updateAdminProfile'))
        except Exception as e:
            flash("Failed to update admin.", 'error')
            print(e)
            return redirect(url_for('adminViews.updateAdminProfile'))
    else:
        pass
    
    from .models import Administrator
    from . import db
    admin_data = Administrator.query.filter_by(username=session['username']).first()
    return render_template("/admin/admin-profile.html", data= admin_data)

@adminViews.route('/manage-teacher/add-teacher', methods = ['GET', 'POST'])
@admin_only
def addTeacher():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        phone = request.form.get('phone')
        classID = request.form.get('class')
        designation = request.form.get('designation')
        id = request.form.get('employee_id').lower()
        from .models import Teacher, Class
        new_teacher = Teacher(id=id, fname=fname, lname=lname, email=email, password=generate_password_hash('password',  method='pbkdf2:sha256'),
                       phone=phone, classID = classID, designation=designation )
        try:
            from . import db
            selected_class = Class.query.get(classID)
            selected_class.teacher_id = id
            db.session.add(new_teacher)
            db.session.commit()
            flash("Teacher registered successfully.", 'success')
            return redirect(url_for('adminViews.addTeacher'))
        except Exception as e:
            flash("Failed to register teacher.", 'error')
            return redirect(url_for('adminViews.addTeacher'))
    from .models import Class
    classes = Class.query.filter(Class.teacher_id == None).all()
    return render_template("/admin/admin-addTeacher.html", data = classes)

@adminViews.route('/manage-student/add-student', methods = ['GET', "POST"])
@admin_only
def addStudent():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        phone = request.form.get('phone')
        photo = request.files['photo']
        classID = request.form.get('class')
        id = request.form.get('student_id').lower()
        if photo:
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(PHOTOS_FOLDER,id+"."+filename.split('.')[1])
            photo.save(photo_path)
        
        from .models import Student
        try:
            embedding = getImageEmbedding(photo_path)
            emb = {"id":id, "Embedding":embedding[0]['embedding']}
            embedding = json.dumps(emb)
            new_student = Student(id=id, fname=fname, lname=lname, email=email, photo=photo_path,
                       phone=phone, classID = classID, embedding=embedding )
            from . import db
            db.session.add(new_student)
            db.session.commit()
            flash("Student registered successfully.", 'success')
            return redirect(url_for('adminViews.addStudent'))
        except Exception as e:
            flash("Failed to register student.", 'error')
            return redirect(url_for('adminViews.addStudent'))
    from .models import Class
    from . import db
    classes = db.session.execute(db.select(Class.id)).scalars().all()
    return render_template("/admin/admin-addStudent.html", data=classes)

@adminViews.route('/manage-class/add-class', methods=['GET', 'POST'])
@admin_only
def addClass():
    if request.method == 'POST':
        cname = request.form.get('class_name')
        croom = request.form.get('room')
        cId = request.form.get('class_id').lower()
        from .models import Class
        new_class = Class(id=cId, name=cname, room= croom)
        try:
            from . import db
            db.session.add(new_class)
            db.session.commit()
            flash("Class registered successfully.", 'success')
            return redirect(url_for('adminViews.addClass'))
        except Exception as e:
            flash("Failed to register class.", 'error')
            return redirect(url_for('adminViews.addClass'))
    room_no = [1,2,3,4]    
    return render_template("/admin/admin-addClass.html", data=room_no)

@adminViews.route('/manage-class/update-class/<class_id>', methods = ["GET", "POST"])
@admin_only
def updateClass(class_id):
    if request.method == 'POST':
        cname = request.form.get('class_name')
        croom = request.form.get('room')
        cId = request.form.get('class_id').lower()
        print(cname, croom, cId)
        from .models import Class
        from . import db
        try:
            db.session.query(Class).filter(Class.id == cId).update({
                "name": cname,
                "room": croom
                })
            db.session.commit()
            flash("Class updated successfully.", 'success')
            return redirect(url_for('adminViews.updateClass', class_id= cId))
        except Exception as e:
            flash("Failed to update class.", 'error')
            print(e)
            return redirect(url_for('adminViews.updateClass', class_id=cId))
    else:
        pass
    from .models import Class
    from . import db
    class_data = Class.query.filter_by(id=class_id).first()
    room_no = [1,2,3,4]
    return render_template("/admin/admin-updateClass.html", data= class_data, rooms = room_no)

@adminViews.route('/manage-teacher/update-teacher/<teacher_id>', methods = ["GET", "POST"])
@admin_only
def updateTeacher(teacher_id):
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        phone = request.form.get('phone')
        classID = request.form.get('class')
        old_class = request.form.get('old_class')
        designation = request.form.get('designation')
        password = request.form.get('old_pass')
        new_pass = request.form.get('password')
        id = request.form.get('employee_id').lower()
        from .models import Teacher,Class
        from . import db
        try:
            if new_pass:
                password=generate_password_hash(new_pass,  method='pbkdf2:sha256')
            old_class = Class.query.get(old_class)
            old_class.teacher_id = None
            db.session.query(Teacher).filter(Teacher.id == id).update({
                "fname": fname,
                "lname": lname,
                "email": email,
                "phone": phone,
                "classID": classID,
                'designation': designation,
                'password': password
            })
            selected_class = Class.query.get(classID)
            selected_class.teacher_id = id
            db.session.commit()
            flash("Teacher updated successfully.", 'success')
            return redirect(url_for('adminViews.updateTeacher', teacher_id= id))
        except Exception as e:
            flash("Failed to update teacher.", 'error')
            print(e)
            return redirect(url_for('adminViews.updateTeacher', teacher_id=id))
    else:
        pass
    from .models import Teacher, Class
    teacher_data = Teacher.query.filter_by(id=teacher_id).first()
    classes = Class.query.filter(Class.teacher_id == None).all()
    return render_template("/admin/admin-updateTeacher.html", data=teacher_data, classes = classes)

@adminViews.route('/manage-student/update-student/<student_id>', methods = ["GET", "POST"])
@admin_only
def updateStudent(student_id):
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        phone = request.form.get('phone')
        photo_path = request.form.get('photo_path')
        embedding = request.form.get('embedding')
        photo = request.files['photo']
        classID = request.form.get('class')
        id = request.form.get('student_id').lower()
        from .models import Student
        from . import db
        try:
            if photo:
                filename = secure_filename(photo.filename)
                photo_path = os.path.join(PHOTOS_FOLDER,id+"."+filename.split('.')[1])
                photo.save(photo_path)
                embedding = getImageEmbedding(photo_path)
                emb = {"id":id, "Embedding":embedding[0]['embedding']}
                embedding = json.dumps(emb)         
            db.session.query(Student).filter(Student.id == id).update({
                "fname": fname,
                "lname": lname,
                "email": email,
                "phone": phone,
                'photo': photo_path,
                'embedding': embedding,
                "classID": classID
            })
            db.session.commit()
            flash("Student updated successfully.", 'success')
            return redirect(url_for('adminViews.updateStudent', student_id= id))
        except Exception as e:
            flash("Failed to update teacher.", 'error')
            print(e)
            return redirect(url_for('adminViews.updateStudent', student_id=id))
    else:
        pass
    from .models import Student
    from .models import Class
    from . import db
    student_data = Student.query.filter_by(id=student_id).first()
    from . import db
    classes = db.session.execute(db.select(Class.id)).scalars().all()
    return render_template("/admin/admin-updateStudent.html", data = student_data, classes = classes)


@adminViews.route('/manage-teacher/delete-teacher/<teacher_id>', methods=['DELETE'])
@admin_only
def delete_teacher(teacher_id):
    try:
        from .models import Teacher, Class
        from . import db
        teacher_to_delete = Teacher.query.get(teacher_id)
        selected_class = Class.query.get(teacher_to_delete.classID)
        selected_class.teacher_id = None
        if teacher_to_delete:
            db.session.delete(teacher_to_delete)
            db.session.commit()
            # flash("Teacher deleted successfully", 'success')
        else:
            flash("Teacher not found", 'error')
        # 2. Return success
        return jsonify({"success": True, "message": "Teacher deleted successfully"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@adminViews.route('/manage-student/delete-student/<student_id>', methods=['DELETE'])
@admin_only
def delete_student(student_id):
    try:
        from .models import Student
        from . import db
        student_to_delete = Student.query.get(student_id)
        if student_to_delete:
            db.session.delete(student_to_delete)
            db.session.commit()
            # flash("Student deleted successfully", 'success')
        else:
            flash("Student not found", 'error')
        # 2. Return success
        return jsonify({"success": True, "message": "Student deleted successfully"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@adminViews.route('/manage-class/delete-class/<class_id>', methods=['DELETE'])
@admin_only
def delete_class(class_id):
    try:
        from .models import Class
        from . import db
        class_to_delete = Class.query.get(class_id)
        if class_to_delete:
            db.session.delete(class_to_delete)
            db.session.commit()
            # flash("Class deleted successfully", 'success')
        else:
            flash("Class not found", 'error')
        # 2. Return success
        return jsonify({"success": True, "message": "Class deleted successfully"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@adminViews.route('/update-task/<task_id>', methods=['POST'])
@admin_only
def update_task(task_id):
    from .models import Task
    from . import db
    task = Task.query.get_or_404(task_id)
    if task.user == 'admin':
        task.is_done = not task.is_done
        db.session.commit()
    return redirect(url_for('adminViews.home'))

@adminViews.route('/add-task', methods=['POST'])
@admin_only
def add_task():
    title = request.form.get('task_title')
    from .models import Task
    if title:
        new_task = Task(
            title=title,
            user= 'admin'
        )
        from . import db
        db.session.add(new_task)
        db.session.commit()
        flash("Task added!", "success")
    return redirect(url_for('adminViews.home'))

@adminViews.route('/delete-task/<task_id>', methods=['POST'])
@admin_only
def delete_task(task_id):
    from .models import Task
    task = Task.query.get_or_404(task_id)
    if task.user == 'admin':
        from . import db
        db.session.delete(task)
        db.session.commit()
    return redirect(url_for('adminViews.home'))
