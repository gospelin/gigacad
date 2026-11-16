import pymysql
from urllib.parse import urlparse
from datetime import datetime
from application import create_app, db
from application.models import nigeria_now, cipher

def export_database_to_sql():
    app = create_app()
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
        db_connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = db_connection.cursor()

        # List of tables to export (based on models.py)
        tables = [
            'session', 'user', 'admin_privilege', 'user_session_preference', 'audit_log',
            'classes', 'teacher', 'subject', 'class_teacher', 'class_subject', 'teacher_subject',
            'student', 'student_class_history', 'fee_payment', 'student_term_summary', 'result'
        ]

        # Path where the backup will be saved
        backup_file_path = "/home/gigo/GIGACAD/database_backup.sql"

        try:
            with open(backup_file_path, "w") as f:
                f.write(f"-- Database backup for {database}\n")
                f.write(f"-- Generated on: {nigeria_now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

                for table in tables:
                    # Check if table exists
                    cursor.execute("SHOW TABLES LIKE %s", (table,))
                    if not cursor.fetchone():
                        app.logger.warning(f"Table {table} does not exist, skipping...")
                        continue

                    # Write the table creation command
                    cursor.execute(f"SHOW CREATE TABLE {table}")
                    create_table_query = cursor.fetchone()['Create Table']
                    f.write(f"-- Table structure for `{table}`\n")
                    f.write(f"{create_table_query};\n\n")

                    # Write the data to insert statements
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()

                    if rows:
                        # Retrieve column names and types to handle special cases
                        cursor.execute(f"DESCRIBE {table}")
                        columns_info = cursor.fetchall()
                        column_names = [col['Field'] for col in columns_info]
                        date_columns = ['date_of_birth', 'date_registered', 'join_date', 
                                      'leave_date', 'created_at', 'timestamp']

                        f.write(f"-- Data for `{table}`\n")
                        for row in rows:
                            # Transform date fields to strings
                            for date_col in date_columns:
                                if date_col in row and row[date_col]:
                                    if isinstance(row[date_col], datetime):
                                        row[date_col] = row[date_col].strftime("%Y-%m-%d %H:%M:%S")
                                    else:
                                        row[date_col] = str(row[date_col])

                            # Handle encrypted fields (e.g., parent_phone_number)
                            if table == 'student' and 'parent_phone_number' in row and row['parent_phone_number']:
                                try:
                                    row['parent_phone_number'] = cipher.decrypt(row['parent_phone_number'].encode()).decode()
                                except Exception as e:
                                    app.logger.error(f"Error decrypting parent_phone_number for student ID {row.get('id', 'unknown')}: {e}")
                                    row['parent_phone_number'] = 'NULL'

                            # Format values for SQL INSERT
                            values = []
                            for col in column_names:
                                value = row[col]
                                if value is None:
                                    values.append('NULL')
                                elif isinstance(value, bool):
                                    values.append('1' if value else '0')
                                elif isinstance(value, (int, float)):
                                    values.append(str(value))
                                else:
                                    # Escape single quotes outside f-string
                                    escaped_value = str(value).replace("'", "''")
                                    values.append(f"'{escaped_value}'")

                            f.write(f"INSERT INTO `{table}` ({', '.join([f'`{col}`' for col in column_names])}) "
                                   f"VALUES ({', '.join(values)});\n")
                        f.write("\n")

                f.write("SET FOREIGN_KEY_CHECKS=1;\n")

            app.logger.info(f"Database export completed. Backup saved at: {backup_file_path}")

        except Exception as e:
            app.logger.error(f"Error during export: {e}", exc_info=True)
            raise

        finally:
            cursor.close()
            db_connection.close()

if __name__ == "__main__":
    export_database_to_sql()