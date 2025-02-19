from application import app, db
import pymysql
import os
from urllib.parse import urlparse

def export_database_to_sql():
    with app.app_context():
        # Extract database connection details from SQLALCHEMY_DATABASE_URI
        uri = app.config['SQLALCHEMY_DATABASE_URI']
        parsed_uri = urlparse(uri)

        # Database connection details from the URI
        host = parsed_uri.hostname
        user = parsed_uri.username
        password = parsed_uri.password
        database = parsed_uri.path[1:]  # Strip the leading slash from the database name

        # Connect to the MySQL database
        db_connection = pymysql.connect(host=host, user=user, password=password, database=database)
        cursor = db_connection.cursor()

        # List of tables to export (you can add more tables to this list)
        tables = ["result"]  # Replace with your table names

        # Path where the backup will be saved
        backup_file_path = backup_file_path = "/home/gigo/AAIS/result_backup.sql"

        with open(backup_file_path, "w") as f:
            for table in tables:
                # Write the table creation command (optional)
                cursor.execute(f"SHOW CREATE TABLE {table}")
                create_table_query = cursor.fetchone()[1]
                f.write(f"-- Table structure for `{table}`\n")
                f.write(f"{create_table_query};\n\n")

                # Write the data to insert statements
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()

                if rows:
                    f.write(f"-- Data for `{table}`\n")
                    for row in rows:
                        # Format each row into an `INSERT INTO` statement
                        values = ', '.join([repr(value) for value in row])
                        f.write(f"INSERT INTO {table} VALUES ({values});\n")
                    f.write("\n")

        cursor.close()
        db_connection.close()

        print(f"Database backup completed. Backup saved at: {backup_file_path}")

if __name__ == "__main__":
    export_database_to_sql()
