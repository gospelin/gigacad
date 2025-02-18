from application import create_app, db
from application.models import Subject, Classes, class_subject

# Initialize the Flask application
app = create_app()  # Ensure you have a `create_app` factory function in your application

def assign_subjects_to_classes_based_on_section():
    with app.app_context():  # Push the application context
        # Fetch all classes and subjects
        classes = Classes.query.all()
        subjects = Subject.query.all()

        for class_ in classes:
            for subject in subjects:
                # Check if the class section matches the subject section
                if class_.section == subject.section:
                    # Check if the subject is not already linked to the class
                    existing_link = db.session.query(class_subject).filter_by(class_id=class_.id, subject_id=subject.id).first()
                    if not existing_link:
                        # Link the subject to the class
                        new_link = class_subject.insert().values(class_id=class_.id, subject_id=subject.id)
                        db.session.execute(new_link)
                        print(f"Subject {subject.name} linked to Class {class_.name} ({class_.section} section).")
        
        db.session.commit()  # Commit all changes
        print("All relevant subjects have been assigned to their respective classes based on section.")

if __name__ == "__main__":
    assign_subjects_to_classes_based_on_section()
