import sys
import os

# Add the project directory to the sys.path so Python can find the app
# Add the project directory to sys.path
project_home = '/home/auntyan1/public_html/auntyannesschools.com.ng/AAIS'
if project_home not in sys.path:
    sys.path.append(project_home)

# Activate the virtual environment
venv_activate = '/home/auntyan1/virtualenv/public_html/auntyannesschools.com.ng/AAIS/3.12/bin/activate_this.py'
exec(open(venv_activate).read(), {'__file__': venv_activate})

# Load environment variables if needed
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# Create the Flask app
from application import create_app
application = create_app()