# Aunty Anne's International School Official Website

## Setup Instructions

Clone the repository:

```bash
git clone <https://github.com/gospelin/AAIS.git>
cd AAIS
```

Create a virtual environment to manage your dependencies and activate it:

```bash
python -m venv venv
source venv/bin/activate # On Windows use `venv\Scripts\activate` 
```

Install the required dependencies using pip:

```bash
pip install -r requirements.txt
```

Create a `.env` file based on the provided .env.example file:

```bash
cp .env.example .env
```

Edit the `.env` file to include your actual configuration values:

SECRET_KEY="your_secret_key"
   SQLALCHEMY_DATABASE_URI="mysql://user:password@localhost:3306/school_database"

Set the `FLASK_ENV` environment variable to specify the configuration you want to use (development, testing, production):

```bash

export FLASK_ENV=development # On Windows use `set FLASK_ENV=development` 
```

Run the Flask application:

```bash

flask run
```

### Configuration

The application uses different configurations for development, testing, and production environments. These configurations are managed using environment variables and a configuration file `(config.py)`.

**Configuration Classes**

The `config.py` file defines several configuration classes:

- `Config`: Base configuration.
- `DevelopmentConfig`: Development configuration.
- `TestingConfig`: Testing configuration.
- `ProductionConfig`: Production configuration.

**Configuration Files**

- .env: Stores sensitive configuration details like `SECRET_KEY` and `SQLALCHEMY_DATABASE_URI`.
- `.flaskenv`: Specifies the Flask environment (`FLASK_ENV`) and the application entry point (`FLASK_APP`).

### Project Structure

your_repository/

├── .env

├── .flaskenv

├── .gitignore

├── README.md

├── application/

│ ├── **init**.py

│ ├── models.py

│ ├── routes.py

│ ├── templates/

│ │ └── ...

│ └── ...

├── config.py

├── requirements.txt

└── ...

### Database Migrations

To manage database migrations, use Flask-Migrate. Common commands include:

```bash

flask db init # Initialize a new migrations directory
flask db migrate # Generate a new migration
flask db upgrade # Apply migrations
```

### Running Tests

To run tests, use the following command:

```bash

pytest
```

### Deployment

For deployment, ensure that the FLASK_ENV environment variable is set to production and that the production configuration values are correctly set in your environment variables.

Example Deployment with Gunicorn

```bash

gunicorn -w 4 -b 0.0.0.0:8000 application:app
```

### Contributing

If you would like to contribute to this project, please fork the repository and create a pull request with your changes.

### License

This project is licensed under the MIT License. See the LICENSE file for details.

Thanks for visiting.
