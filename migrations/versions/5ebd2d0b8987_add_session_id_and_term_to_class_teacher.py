"""Add session_id and term to class_teacher

Revision ID: 875b15a41392
Revises: b9f49678448d
Create Date: 2025-03-09 20:20:43.562515
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '875b15a41392'
down_revision = 'b9f49678448d'
branch_labels = None
depends_on = None

def upgrade():
    pass
    # Step 1: Add columns with nullable=True initially
    # with op.batch_alter_table('class_teacher', schema=None) as batch_op:
    #     batch_op.add_column(sa.Column('session_id', sa.Integer(), nullable=True))  # Temporarily nullable
    #     batch_op.add_column(sa.Column('term', sa.String(length=50), nullable=True))

    # # Step 2: Populate existing rows with a default session_id and term
    # # Assume the earliest session or current session as default
    # default_session_id = op.get_bind().execute(
    #     sa.text("SELECT id FROM session ORDER BY year ASC LIMIT 1")
    # ).scalar() or 1  # Fallback to 1 if no sessions exist
    # default_term = "Third"  # Default term, adjust as needed

    # op.execute(
    #     sa.text(
    #         "UPDATE class_teacher SET session_id = :session_id, term = :term WHERE session_id IS NULL"
    #     ).bindparams(session_id=default_session_id, term=default_term)
    # )

    # # Step 3: Alter columns to be non-nullable and add foreign key
    # with op.batch_alter_table('class_teacher', schema=None) as batch_op:
    #     batch_op.alter_column('session_id', nullable=False)
    #     batch_op.alter_column('term', nullable=False)
    #     batch_op.create_foreign_key('fk_class_teacher_session_id', 'session', ['session_id'], ['id'])

def downgrade():
    with op.batch_alter_table('class_teacher', schema=None) as batch_op:
        batch_op.drop_constraint('fk_class_teacher_session_id', type_='foreignkey')
        batch_op.drop_column('term')
        batch_op.drop_column('session_id')
