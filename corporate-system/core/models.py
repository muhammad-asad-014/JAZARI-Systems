from . import db
from flask_login import UserMixin
from datetime import datetime, timezone
UTC = timezone.utc

class Administrator(db.Model, UserMixin):
    username = db.Column(db.String(10), primary_key = True) # default is "admin"
    password = db.Column(db.String(20)) # default is "admin"
    fname = db.Column(db.String(150))
    lname = db.Column(db.String(150))
    email = db.Column(db.String(150))
    role = db.Column(db.String(150), default = "admin")

    def get_id(self):
        return str(self.username)

    @property
    def user_role(self):
        return "admin"


class Teacher(db.Model, UserMixin):
    id = db.Column(db.String(10), primary_key = True)
    password = db.Column(db.String(20), default = 'password') #default password for any newly added teacher is "password"
    fname = db.Column(db.String(150))
    lname = db.Column(db.String(150))
    designation = db.Column(db.String(150))
    email = db.Column(db.String(150))
    phone = db.Column(db.String(150))
    role = db.Column(db.String(150), default = "teacher")
    classID = db.Column(db.String(10), db.ForeignKey('class.id', ondelete='SET NULL'), nullable=True)

    @property
    def user_role(self):
        return "teacher"


class Settings(db.Model):
    orgID = db.Column(db.String(3), primary_key = True, default = '001')
    orgName = db.Column(db.String(150), default = "NONE")
    orgLogo = db.Column(db.String(255), default = "NONE") # Store file path (.system-settings/orgLogo.jpg)
    usageType = db.Column(db.String(150), default = "classroom")
    theme = db.Column(db.String(150), default = "light")

class Class(db.Model):
    id = db.Column(db.String(10), primary_key = True)
    name = db.Column(db.String(150))
    room = db.Column(db.Integer)
    students = db.relationship('Student', backref='assigned_class', passive_deletes=True)
    teacher_id = db.Column(db.String(20), db.ForeignKey('teacher.id'), unique=True, nullable=True)

class Student(db.Model, UserMixin):
    id = db.Column(db.String(10), primary_key = True)
    fname = db.Column(db.String(150))
    lname = db.Column(db.String(150))
    email = db.Column(db.String(150))
    phone = db.Column(db.String(150))
    photo = db.Column(db.String(255)) # Store file path (.student-pictures/STR2026075.jpg)
    embedding = db.Column(db.JSON)
    classID = db.Column(db.String(10), db.ForeignKey('class.id', ondelete='SET NULL'), nullable=True)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now(UTC))
    is_done = db.Column(db.Boolean, default=False)
    user = db.Column(db.String(20), nullable=False) 

class Attendance(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    teacher = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now(UTC))
    class_id = db.Column(db.String(20), nullable=False)

class Quiz(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    teacher = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now(UTC))
    embedding = db.Column(db.JSON)
    class_id = db.Column(db.String(20), nullable=False)

class Notes(db.Model):
    
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    teacher = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now(UTC))
