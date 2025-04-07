"""Fix session_id and term in class_teacher

Revision ID: c3298336876d
Revises: 875b15a41392
Create Date: 2025-03-09 21:47:30.476938
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'c3298336876d'
down_revision = '875b15a41392'
branch_labels = None
depends_on = None

def upgrade():
    # Step 1: Ensure columns exist (add if missing, otherwise proceed)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('class_teacher')]

    with op.batch_alter_table('class_teacher', schema=None) as batch_op:
        if 'session_id' not in columns:
            batch_op.add_column(sa.Column('session_id', sa.Integer(), nullable=True))
        if 'term' not in columns:
            batch_op.add_column(sa.Column('term', sa.String(length=50), nullable=True))

    # Step 2: Populate any NULL values in existing rows
    default_session_id = conn.execute(
        text("SELECT id FROM session ORDER BY year ASC LIMIT 1")
    ).scalar() or 1  # Fallback to 1 if no sessions exist
    default_term = "Third"  # Adjust based on your TermEnum

    op.execute(
        text(
            "UPDATE class_teacher SET session_id = :session_id, term = :term WHERE session_id IS NULL OR term IS NULL"
        ).bindparams(session_id=default_session_id, term=default_term)
    )

    # Step 3: Make columns non-nullable and add foreign key
    with op.batch_alter_table('class_teacher', schema=None) as batch_op:
        batch_op.alter_column('session_id', existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column('term', existing_type=sa.String(length=50), nullable=False)
        # Add foreign key if it doesn’t exist
        if 'fk_class_teacher_session_id' not in [fk['name'] for fk in inspector.get_foreign_keys('class_teacher')]:
            batch_op.create_foreign_key('fk_class_teacher_session_id', 'session', ['session_id'], ['id'])

def downgrade():
    with op.batch_alter_table('class_teacher', schema=None) as batch_op:
        batch_op.drop_constraint('fk_class_teacher_session_id', type_='foreignkey')
        batch_op.drop_column('term')
        batch_op.drop_column('session_id')