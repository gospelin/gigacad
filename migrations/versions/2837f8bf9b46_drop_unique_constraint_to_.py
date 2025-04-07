"""Drop unique_active_enrollment index from StudentClassHistory and handle foreign key constraints

Revision ID: 2837f8bf9b46
Revises: 56a7f0540df1
Create Date: 2025-03-03 07:48:51.140075
"""
from alembic import op
import sqlalchemy as sa

revision = '2837f8bf9b46'
down_revision = '56a7f0540df1'
branch_labels = None
depends_on = None

def upgrade():
    # Step 1: Drop foreign key constraints that might interfere
    with op.batch_alter_table('student_class_history', schema=None) as batch_op:
        batch_op.drop_constraint('student_class_history_ibfk_1', type_='foreignkey')  # session_id
        batch_op.drop_constraint('student_class_history_ibfk_2', type_='foreignkey')  # student_id
        batch_op.drop_constraint('student_class_history_ibfk_3', type_='foreignkey')  # class_id

    # Step 2: Drop the unique index
    with op.batch_alter_table('student_class_history', schema=None) as batch_op:
        batch_op.drop_index('unique_active_enrollment')

    # Step 3: Recreate foreign key constraints without relying on the unique index
    with op.batch_alter_table('student_class_history', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'student_class_history_ibfk_1', 'session', ['session_id'], ['id']
        )
        batch_op.create_foreign_key(
            'student_class_history_ibfk_2', 'student', ['student_id'], ['id']
        )
        batch_op.create_foreign_key(
            'student_class_history_ibfk_3', 'classes', ['class_id'], ['id']
        )

    # Optional: Add a non-unique index for performance
    with op.batch_alter_table('student_class_history', schema=None) as batch_op:
        batch_op.create_index('idx_student_session', ['student_id', 'session_id'], unique=False)

def downgrade():
    # Remove the non-unique index
    with op.batch_alter_table('student_class_history', schema=None) as batch_op:
        batch_op.drop_index('idx_student_session')

    # Drop the recreated foreign keys
    with op.batch_alter_table('student_class_history', schema=None) as batch_op:
        batch_op.drop_constraint('student_class_history_ibfk_1', type_='foreignkey')
        batch_op.drop_constraint('student_class_history_ibfk_2', type_='foreignkey')
        batch_op.drop_constraint('student_class_history_ibfk_3', type_='foreignkey')

    # Recreate the unique index
    with op.batch_alter_table('student_class_history', schema=None) as batch_op:
        batch_op.create_index('unique_active_enrollment', ['student_id', 'session_id', 'is_active'], unique=True)

    # Recreate the original foreign keys
    with op.batch_alter_table('student_class_history', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'student_class_history_ibfk_1', 'session', ['session_id'], ['id']
        )
        batch_op.create_foreign_key(
            'student_class_history_ibfk_2', 'student', ['student_id'], ['id']
        )
        batch_op.create_foreign_key(
            'student_class_history_ibfk_3', 'classes', ['class_id'], ['id']
        )