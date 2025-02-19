from application import app, db
import pymysql
from urllib.parse import urlparse
from datetime import datetime

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

        # Table to export
        table = "student"  # Replace with your table name

        # Path where the backup will be saved
        backup_file_path = "/home/gigo/AAIS/export_student_backup.sql"

        with open(backup_file_path, "w") as f:
            # Write the table creation command (optional)
            cursor.execute(f"SHOW CREATE TABLE {table}")
            create_table_query = cursor.fetchone()[1]
            f.write(f"-- Table structure for `{table}`\n")
            f.write(f"{create_table_query};\n\n")

            # Write the data to insert statements
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()

            if rows:
                # Retrieve column names to identify date fields
                cursor.execute(f"DESCRIBE {table}")
                columns = [col[0] for col in cursor.fetchall()]
                date_columns = ["date_of_birth", "date_registered"]

                f.write(f"-- Data for `{table}`\n")
                for row in rows:
                    # Convert the row to a dictionary
                    row_dict = dict(zip(columns, row))

                    # Transform date fields to strings
                    for date_col in date_columns:
                        if date_col in row_dict and row_dict[date_col]:
                            if isinstance(row_dict[date_col], datetime):
                                row_dict[date_col] = row_dict[date_col].strftime("%Y-%m-%d %H:%M:%S")  # Ensure full datetime format
                            else:
                                row_dict[date_col] = str(row_dict[date_col])

                    # Format each row into an `INSERT INTO` statement
                    # Format each row into an `INSERT INTO` statement
                    values = ', '.join([repr(value) if value is not None else 'NULL' for value in row_dict.values()])
                    f.write(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({values});\n")
                f.write("\n")

        cursor.close()
        db_connection.close()

        print(f"Database export completed. Backup saved at: {backup_file_path}")

if __name__ == "__main__":
    export_database_to_sql()
