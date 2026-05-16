"""
Education Management - Routes/Views
Handles all education-specific page routes
"""

EDUCATION_ROUTES = [
    {
        "url": "/students",
        "name": "students_list",
        "methods": ["GET"],
        "template": "education/students/list.html",
        "menu": {"name": "Students", "icon": "fa-user-graduate", "order": 1}
    },
    {
        "url": "/students/add",
        "name": "students_add",
        "methods": ["GET", "POST"],
        "template": "education/students/add.html",
        "menu": None
    },
    {
        "url": "/teachers",
        "name": "teachers_list",
        "methods": ["GET"],
        "template": "education/teachers/list.html",
        "menu": {"name": "Teachers", "icon": "fa-chalkboard-teacher", "order": 2}
    },
    {
        "url": "/classes",
        "name": "classes_list",
        "methods": ["GET"],
        "template": "education/classes/list.html",
        "menu": {"name": "Classes", "icon": "fa-door-open", "order": 3}
    }
]
