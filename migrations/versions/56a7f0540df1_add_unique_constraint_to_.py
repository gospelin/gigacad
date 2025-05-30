"""Add unique constraint to StudentClassHistory

Revision ID: 56a7f0540df1
Revises: 7e355402f54c
Create Date: 2025-03-03 00:38:37.352283

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '56a7f0540df1'
down_revision = '7e355402f54c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('student_class_history', schema=None) as batch_op:
        batch_op.create_unique_constraint('unique_active_enrollment', ['student_id', 'session_id', 'is_active'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('student_class_history', schema=None) as batch_op:
        batch_op.drop_constraint('unique_active_enrollment', type_='unique')

    # ### end Alembic commands ###
