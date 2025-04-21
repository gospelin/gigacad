# GIGACAD

GIGACAD is a robust, secure, and scalable Flask-based web application developed for managing academic operations such as student records, authentication, results, and sessional data for educational institutions. Designed for clarity, performance, and maintainability, it integrates advanced configuration, structured logging, CSRF protection, and environment-specific settings.

## Features

- **Role-Based Authentication**: Secure user authentication with MFA (TOTP) and strong session protection for admins, students, and teachers.
- **Admin Dashboard**: Centralized interface with real-time metrics (e.g., student/teacher counts, active sessions).
- **User Management**: Create, edit, and delete admin accounts with granular privilege controls (e.g., manage users, sessions, results).
- **Session & Term Management**: Configure academic sessions and terms per user, with validation and audit logging.
- **Student Management**: Register students, assign classes, and filter by enrollment, fee, or approval status with paginated, AJAX-enabled views.
- **Security Features**:
  - CSRF protection via Flask-WTF for all forms.
  - Rate limiting (e.g., 10 admin creations per minute) with Flask-Limiter.
  - Secure session cookies (HTTP-only, SameSite=Lax, secure in production).
  - Input sanitization using `bleach` to prevent XSS attacks.
  - Audit logging for critical actions (e.g., admin creation/deletion).
- **Structured Logging**: JSON-formatted logs in Nigerian timezone (Africa/Lagos) with request context and error tracking.
- **Database Management**: SQLAlchemy ORM with Flask-Migrate for schema migrations and robust error handling.
- **Customizable UI**: Theme switching (light/dark) with cookie-based persistence.
- **Extensible**: Modular blueprint structure for easy feature additions and API integrations.


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

```bash
flask run
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
- colorlog / python-json-logger
- tenacity
- pytz

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

## Development Tips

- Always use a virtual environment
- Set a secure `SECRET_KEY` in production
- Do not commit the `.env` file
- Check log files regularly
- Use `FLASK_ENV=development` for debugging

## Deployment Notes

- Use a WSGI server like Gunicorn or uWSGI in production
- Always enable HTTPS in production
- On PythonAnywhere, logs are redirected to standard error
- Set `PYTHONANYWHERE=true` in `.env` if using PythonAnywhere

## Support

For bug reports or support, please contact the project maintainer or file an issue in the repository.

### License

This project is licensed under the MIT License. See the LICENSE file for details.

## Credits

GIGACAD

Engineered by Gospel Isaac
