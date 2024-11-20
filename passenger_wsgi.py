# import imp
# import os
# import sys


# sys.path.insert(0, os.path.dirname(__file__))

# wsgi = imp.load_source('wsgi', 'application.py')
# application = wsgi.application


# import sys
# import os
# sys.path.append('/home/auntyan1/public_html/AAIS')

# from application import app as application

import sys
import os

# Add the project directory to the sys.path so Python can find the app
project_home = '/home/auntyan1/public_html/AAIS'
if project_home not in sys.path:
    sys.path.append(project_home)

# Activate virtualenv if needed (replace with the correct path to your virtualenv)
venv_activate = '/home/auntyan1/virtualenv/public_html/AAIS/3.10/bin/activate_this.py'
exec(open(venv_activate).read(), {'__file__': venv_activate})

# Optionally, load environment variables from a .env file if needed
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# Import the Flask application
from application import app as application  # The 'app' in application.py is exposed as 'application'
