from application import create_app, db
from application.models import Student, FeePayment, Session

# Initialize the Flask application
app = create_app()

def migrate_fee_payments():
    with app.app_context():  
        # Get the current session and term
        session, term = Session.get_current_session_and_term(include_term=True)
        if not session or not term:
            print("No active session or term found. Cannot migrate fee payments.")
            return
    
        # Fetch all students who have paid fees
        students = Student.query.filter_by(has_paid_fee=True).all()
    
        for student in students:
            # Check if a FeePayment record already exists for this student, session, and term
            existing_payment = FeePayment.query.filter_by(
                student_id=student.id,
                session_id=session.id,
                term=term
            ).first()
    
            if not existing_payment:
                # Create a new FeePayment record
                fee_payment = FeePayment(
                    student_id=student.id,
                    session_id=session.id,
                    term=term,
                    has_paid_fee=True
                )
                db.session.add(fee_payment)
    
        db.session.commit()
        print(f"Migrated fee payments for {len(students)} students.")


if __name__ == "__main__":
    migrate_fee_payments()
    