from application import create_app, db
from application.models import Student

def update_student_records():
    """
    Update the student records:
    1. Remove the username field from the database.
    2. Set the password field to match the reg_no.
    """
    app = create_app()

    with app.app_context():
        try:
            # Update each student's password to match their reg_no
            students = Student.query.all()
            for student in students:
                if student.reg_no:  # Ensure the reg_no exists
                    student.password = student.reg_no
                    print(f"Updated password for Student ID {student.id} to {student.reg_no}")

            db.session.commit()
            print("Successfully updated student records.")
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    update_student_records()
