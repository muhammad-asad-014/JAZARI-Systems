"""
Corporate Management - Database Models
Handles employees, departments, and positions
"""

class Employee:
    """Employee model for corporate environment"""
    table_name = "employees"
    
    fields = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "employee_id": "VARCHAR(50) UNIQUE NOT NULL",
        "first_name": "VARCHAR(100) NOT NULL",
        "last_name": "VARCHAR(100) NOT NULL",
        "email": "VARCHAR(200) UNIQUE NOT NULL",
        "phone": "VARCHAR(20)",
        "department_id": "INTEGER",
        "position": "VARCHAR(100)",
        "manager_id": "INTEGER",
        "hire_date": "DATE",
        "status": "VARCHAR(20) DEFAULT 'active'",
        "face_embedding": "TEXT",  # Stores facial recognition data
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    }

class Department:
    """Department model"""
    table_name = "departments"
    
    fields = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "VARCHAR(200) NOT NULL",
        "code": "VARCHAR(20) UNIQUE",
        "manager_id": "INTEGER",
        "description": "TEXT",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    }
