"""Update model

Revision ID: 139e8fe81a52
Revises: 66c215f9b424
Create Date: 2025-02-22 02:53:13.225792

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '139e8fe81a52'
down_revision = '66c215f9b424'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('class_teacher', schema=None) as batch_op:
        batch_op.alter_column('is_form_teacher',
               existing_type=mysql.TINYINT(display_width=1),
               nullable=True,
               existing_server_default=sa.text("'0'"))

    with op.batch_alter_table('fee_payment', schema=None) as batch_op:
        batch_op.alter_column('term',
               existing_type=mysql.ENUM('First', 'Second', 'Third'),
               nullable=True)

    with op.batch_alter_table('student_class_history', schema=None) as batch_op:
        batch_op.alter_column('start_term',
               existing_type=mysql.ENUM('First', 'Second', 'Third'),
               nullable=True,
               existing_server_default=sa.text("'First'"))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('student_class_history', schema=None) as batch_op:
        batch_op.alter_column('start_term',
               existing_type=mysql.ENUM('First', 'Second', 'Third'),
               nullable=False,
               existing_server_default=sa.text("'First'"))

    with op.batch_alter_table('fee_payment', schema=None) as batch_op:
        batch_op.alter_column('term',
               existing_type=mysql.ENUM('First', 'Second', 'Third'),
               nullable=False)

    with op.batch_alter_table('class_teacher', schema=None) as batch_op:
        batch_op.alter_column('is_form_teacher',
               existing_type=mysql.TINYINT(display_width=1),
               nullable=False,
               existing_server_default=sa.text("'0'"))

    # ### end Alembic commands ###
