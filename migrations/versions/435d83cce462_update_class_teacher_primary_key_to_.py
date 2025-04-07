"""Update class_teacher primary key to include session_id and term

Revision ID: 435d83cce462
Revises: c3298336876d
Create Date: 2025-03-09 23:32:25.882103
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '435d83cce462'
down_revision = 'c3298336876d'
branch_labels = None
depends_on = None

def upgrade():
    # Step 1: Drop the foreign key constraint that depends on session_id
    with op.batch_alter_table('class_teacher', schema=None) as batch_op:
        batch_op.drop_constraint('fk_class_teacher_session_id', type_='foreignkey')

    # Step 2: Drop the existing primary key and create the new one
    with op.batch_alter_table('class_teacher', schema=None) as batch_op:
        batch_op.drop_constraint('PRIMARY', type_='primary')
        batch_op.create_primary_key('pk_class_teacher', ['class_id', 'teacher_id', 'session_id', 'term'])

    # Step 3: Re-add the foreign key constraint
    with op.batch_alter_table('class_teacher', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_class_teacher_session_id', 'session', ['session_id'], ['id'])

def downgrade():
    # Step 1: Drop the foreign key constraint
    with op.batch_alter_table('class_teacher', schema=None) as batch_op:
        batch_op.drop_constraint('fk_class_teacher_session_id', type_='foreignkey')

    # Step 2: Drop the new primary key and restore the old one
    with op.batch_alter_table('class_teacher', schema=None) as batch_op:
        batch_op.drop_constraint('pk_class_teacher', type_='primary')
        batch_op.create_primary_key('PRIMARY', ['class_id', 'teacher_id'])

    # Step 3: Re-add the foreign key constraint
    with op.batch_alter_table('class_teacher', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_class_teacher_session_id', 'session', ['session_id'], ['id'])