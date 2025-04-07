"""Update model

Revision ID: d506be8a2feb
Revises: 50791525d753
Create Date: 2025-03-02 13:31:39.216338
"""
from alembic import op
import sqlalchemy as sa

revision = 'd506be8a2feb'
down_revision = '50791525d753'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('subject', schema=None) as batch_op:
        # Check if index exists before dropping
        conn = op.get_bind()
        if conn.dialect.has_index(conn, 'subject', '_name_section_uc'):
            batch_op.drop_index('_name_section_uc')
        batch_op.create_unique_constraint('uq_subject_name', ['name'])

def downgrade():
    with op.batch_alter_table('subject', schema=None) as batch_op:
        batch_op.drop_constraint('uq_subject_name', type_='unique')
        batch_op.create_index('_name_section_uc', ['name', 'section'], unique=True)