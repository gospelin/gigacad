from application import create_app, db
from application.models import Student, User

# Initialize the Flask application
app = create_app()  # Ensure you have a `create_app` factory function in your application

def update_student_password_to_reg_no():
    with app.app_context():  # Push the application context
        students = Student.query.all()  # Fetch all students
        for student in students:
            if student.reg_no:  # Ensure reg_no exists
                user = User.query.get(student.user_id)  # Fetch the linked User
                if user:
                    # Update password to the student's reg_no
                    user.set_password(student.reg_no)  # Hash the reg_no
                    print(f"Password updated for Student ID {student.id}: {student.reg_no}")
                else:
                    print(f"No linked User found for Student ID {student.id}. Skipping.")
        
        db.session.commit()  # Commit all changes
        print("All student passwords have been updated to their reg_no.")

if __name__ == "__main__":
    update_student_password_to_reg_no()