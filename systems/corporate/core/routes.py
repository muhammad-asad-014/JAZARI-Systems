"""
Corporate Management - Routes/Views
Handles all corporate-specific page routes
"""

CORPORATE_ROUTES = [
    {
        "url": "/employees",
        "name": "employees_list",
        "methods": ["GET"],
        "template": "corporate/employees/list.html",
        "menu": {"name": "Employees", "icon": "fa-users", "order": 1}
    },
    {
        "url": "/employees/add",
        "name": "employees_add",
        "methods": ["GET", "POST"],
        "template": "corporate/employees/add.html",
        "menu": None
    },
    {
        "url": "/employees/<id>/edit",
        "name": "employees_edit",
        "methods": ["GET", "POST"],
        "template": "corporate/employees/edit.html",
        "menu": None
    },
    {
        "url": "/departments",
        "name": "departments_list",
        "methods": ["GET"],
        "template": "corporate/departments/list.html",
        "menu": {"name": "Departments", "icon": "fa-sitemap", "order": 2}
    },
    {
        "url": "/departments/add",
        "name": "departments_add",
        "methods": ["GET", "POST"],
        "template": "corporate/departments/add.html",
        "menu": None
    }
]
