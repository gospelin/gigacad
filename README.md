# GIGACAD


GIGACAD is a robust, secure, and scalable Flask-based web application developed for managing academic operations such as student records, authentication, results, and sessional data for educational institutions. Designed for clarity, performance, and maintainability, it integrates advanced configuration, structured logging, CSRF protection, and environment-specific settings.

# Key Features

### 🛡️ Security & Authentication
- **Multi-Factor Authentication (MFA)** with TOTP and QR code setup
- **Role-based access control** (Admin, Teacher, Student)
- CSRF protection via Flask-WTF for all forms
- **Granular admin privileges** with 7 distinct permission levels
- **Secure session management** with CSRF protection
- **Password hashing** using Flask-Bcrypt
- **Rate limiting** for API endpoints (10 requests/minute)

### 👨‍💼 Admin Dashboard Features
- **User Management**
  - Create/edit/delete admin accounts
  - Manage admin privileges (users, sessions, classes, results, teachers, subjects, reports)
  - MFA enforcement for all admin accounts
- **Student Management**
  - Complete student registration with auto-generated registration numbers
  - Class assignment and promotion tracking
  - Detailed student profiles (personal info, parent contacts, academic history)
- **Academic Management**
  - Session and term configuration
  - Class and subject management
  - Teacher assignment to classes and subjects
- **Data Security**
  - Audit logging for all admin actions
  - Secure headers (XSS protection, no-sniff, CSRF tokens)
  - Theme preference persistence
- **Extensible**: Modular blueprint structure for easy feature additions and API integrations.


### 📊 Academic Features
- **Result Management**
  - Termly result entry and editing
  - Broad sheet generation in Excel format
  - Comprehensive student performance tracking
- **Class Management**
  - Hierarchical class organization
  - Student promotion between classes
  - Class-wide field updates
- **Reporting**
  - Filterable student lists (by enrollment, fee, approval status)
  - Paginated data views
  - Session-based academic tracking



## Project Structure

```
gigacad/
├── application/
│   ├── auth/                # Authentication routes and logic
│   ├── admin/               # Admin-specific routes and logic
│   ├── main/                # Main application routes
│   ├── student/             # Student-specific routes and logic
│   ├── teacher/             # Teacher-specific routes and logic
│   ├── models.py            # SQLAlchemy models
│   ├── helpers.py           # Helper functions
│   ├── templates/           # Jinja2 templates
│   └── static/              # Static assets (CSS, JS, images)
├── logs/                    # Log files
├── config.py                # Configuration settings
├── __init__.py              # Flask app factory and initialization
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
└── README.md                # Project documentation
```

## Getting Started

Follow these steps to clone and run the project locally.

### 1. Clone the Repository

```bash
git clone https://github.com/gospelin/gigacad.git
cd gigacad
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` File

Create a `.env` file in the root directory and add the following environment variables:

```
cp .env.example .env
nano .env  # Edit with your configuration
```

```
FLASK_ENV=development
SECRET_KEY=your-secret-key
DB_USER=mysql_user
DB_PASSWORD=mysql_password
DB_HOST=localhost
DB_NAME=school_database
LOG_DIR=./logs
SESSION_LIFETIME=SESSION_LIFETIME
```

### 5. Set Up the Database

```bash
flask db init
flask db migrate -m "Initial migration."
flask db upgrade
```

### 6. Run the Application

### Development Mode
```bash
export FLASK_ENV=development
flask run 
```

### Production Deployment
```bash
gunicorn -w 4 -b :5000 wsgi:app
```

Visit `http://localhost:5000` in your browser.

---

## Config Classes (from config.py)

- `Config`: Base config class with shared settings
- `DevelopmentConfig`: Enables debugging and SQL echo
- `TestingConfig`: Uses in-memory SQLite and disables CSRF
- `ProductionConfig`: Requires secure settings, disables debugging

## Application Factory (__init__.py)

The `create_app()` function initializes the application with:

- Config loading based on environment (`FLASK_ENV`)
- Secure session cookie settings
- Database and migration setup
- CSRF protection
- Logging with a custom JSON formatter and colored console output (except on PythonAnywhere)
- Retry mechanism for user loading
- Custom `datetimeformat` Jinja filter

## Authentication and Login

- Login managed by `flask_login`
- User loader with retry using `tenacity`
- Session protection set to `"strong"`
- Redirects to login on unauthenticated access

## Extensions Used

- Flask SQLAlchemy
- Flask Migrate
- Flask Login
- Flask Bcrypt
- Flask WTF
- Flask Limiter
- python-dotenv
- pyotp (MFA)
- qrcode (MFA QR codes)
- colorlog / python-json-logger
- tenacity
- pytz

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.0%2B-green)
![MySQL](https://img.shields.io/badge/mysql-8.0%2B-orange)
![License](https://img.shields.io/badge/license-MIT-brightgreen)

## Testing Configuration

To enable test configuration, set `FLASK_ENV=testing` or pass `config_name='testing'` to `create_app()`. This:

- Uses SQLite in-memory DB
- Disables CSRF protection
- Disables SQLAlchemy engine options

## Logging System

- Logs are written to the `logs/` directory.
- Uses `PrettyJsonFormatter` for JSON-formatted logs with Nigerian time zone.
- Each log entry includes:
  - Timestamp
  - Log level
  - Logger name
  - Path, function, and line number
  - Blueprint, endpoint, and URL
  - A request ID
- SQLAlchemy logs are suppressed unless they are warnings or errors.

## Timezone Support

- All logs and timestamps are converted to `Africa/Lagos` timezone.
- Uses `pytz` and `datetime` for conversion and formatting.
- Available as a Jinja2 filter: `{{ some_datetime|datetimeformat }}`

## Session Management

- Sessions use `permanent = True` and respect `PERMANENT_SESSION_LIFETIME`
- Secure cookies are enabled in production
- Cookies are HTTP-only with SameSite policy set to `Lax`

## Error Handling and Warnings

- Warns when:
  - `.env` file is missing
  - Default credentials are detected
  - `SECRET_KEY` is missing or weak
- Handles:
  - User loading failures
  - Invalid user ID errors
  - Database connection retries
- Logs traceback and critical info for errors

## Custom Logging Formatter (PrettyJsonFormatter)

Logs include the following structured fields:

```
{
  "asctime": "2025-04-21 18:04:00",
  "name": "flask.app",
  "levelname": "INFO",
  "pathname": "/path/to/file.py",
  "lineno": 42,
  "funcName": "function_name",
  "message": "Log message content",
  "blueprint": "auth",
  "endpoint": "login",
  "url": "https://example.com/login",
  "request_id": "generated-uuid",
  "timestamp": "2025-04-21T18:04:00+01:00",
  "exc_info": null
}
```

## API Endpoints

### Admin Routes
- `GET /admin/dashboard` - Admin dashboard
- `POST /admin/set_theme` - Set user theme preference
- `GET/POST /admin/create_admin` - Create new admin with MFA
- `GET /admin/view_admins` - List all admin users
- `GET/POST /admin/edit_admin/<int:user_id>` - Edit admin details
- `GET/POST /admin/edit_admin_privileges/<int:user_id>` - Modify admin privileges
- `POST /admin/delete_admin/<int:user_id>` - Delete admin account
- `GET/POST /admin/manage_sessions` - Configure academic sessions
- `GET/POST /admin/register/student` - Register new student
- `GET/POST /admin/students/<string:action>` - View/filter students


## Contributing	

Contributions are welcome! Please follow these steps:

 - Fork the repository.

 - Create a feature branch 
	```git
	git checkout -b feature/new-feature
	```

 - Commit changes 
	```git
	git commit -m "Add new feature"
	```

 - Push to the branch 
	```git
	git push origin feature/new-feature
	```
	
 - Open a pull request.

### License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.


## Credits

Developed by Gospel Isaac
