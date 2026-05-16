"""
Education Management - Database Models
Handles students, teachers, classes, and subjects
"""

class Student:
    """Student model for education environment"""
    table_name = "students"
    
    fields = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "student_id": "VARCHAR(50) UNIQUE NOT NULL",
        "first_name": "VARCHAR(100) NOT NULL",
        "last_name": "VARCHAR(100) NOT NULL",
        "email": "VARCHAR(200)",
        "phone": "VARCHAR(20)",
        "class_id": "INTEGER",
        "enrollment_date": "DATE",
        "status": "VARCHAR(20) DEFAULT 'active'",
        "face_embedding": "TEXT",  # Stores facial recognition data
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    }

class Teacher:
    """Teacher model"""
    table_name = "teachers"
    
    fields = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "teacher_id": "VARCHAR(50) UNIQUE NOT NULL",
        "first_name": "VARCHAR(100) NOT NULL",
        "last_name": "VARCHAR(100) NOT NULL",
        "email": "VARCHAR(200) UNIQUE NOT NULL",
        "phone": "VARCHAR(20)",
        "specialization": "VARCHAR(200)",
        "hire_date": "DATE",
        "status": "VARCHAR(20) DEFAULT 'active'"
    }

class Class:
    """Class/Section model"""
    table_name = "classes"
    
    fields = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "VARCHAR(100) NOT NULL",
        "section": "VARCHAR(20)",
        "teacher_id": "INTEGER",
        "academic_year": "VARCHAR(20)",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    }
