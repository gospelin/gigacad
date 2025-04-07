from application import create_app
app = create_app()

# if __name__ == "__main__":
#     debug = app.config["DEBUG"]
#     app.run(debug=debug)
    # app.run(host='app')
    # from waitress import serve

    # serve(app, host="0.0.0.0", port=5000)
    


# import os
# import sys
# from application import create_app
# from waitress import serve
# import logging

# # Ensure application package is in PYTHONPATH
# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# def main():
#     """Run the Flask application."""
#     # Determine environment from FLASK_ENV or default to 'development'
#     config_name = os.getenv("FLASK_ENV", "development")
#     app = create_app(config_name)

#     # Log startup
#     app.logger.info(f"Starting application in {config_name} environment")

#     try:
#         if config_name == "production":
#             # Use Waitress for production
#             host = os.getenv("APP_HOST", "0.0.0.0")
#             port = int(os.getenv("APP_PORT", 5000))
#             serve(app, host=host, port=port)
#             app.logger.info(f"Running production server with Waitress on {host}:{port}")
#         else:
#             # Use Flask dev server for non-production
#             debug = app.config.get("DEBUG", False)
#             host = os.getenv("APP_HOST", "127.0.0.1")
#             port = int(os.getenv("APP_PORT", 5000))
#             app.run(host=host, port=port, debug=debug)
#             app.logger.info(f"Running development server on {host}:{port} with debug={debug}")
#     except Exception as e:
#         app.logger.error(f"Failed to start application: {str(e)}")
#         raise

# if __name__ == "__main__":
#     main()