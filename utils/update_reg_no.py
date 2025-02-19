from application import create_app, db
from application.models import Student

app = create_app()


def update_student_reg_no():
    with app.app_context():
        students = Student.query.all()  # Fetch all students
        for student in students:
            if not student.reg_no:  # Only update if `reg_no` is not already set
                student.reg_no = f"AAIS/0559/{student.id:03}"  # Format the reg_no
                print(f"Updating reg_no for Student ID {student.id}: {student.reg_no}")
            
        db.session.commit()  # Commit all changes
        print("All student reg_no fields have been updated.")


if __name__ == "__main__":
    update_student_reg_no()