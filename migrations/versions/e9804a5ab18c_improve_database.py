"""Improve database

Revision ID: e9804a5ab18c
Revises: None
Create Date: 2025-02-21 23:42:09.071517
"""

from alembic import op
import sqlalchemy as sa

# Define enum values for consistency with TermEnum and RoleEnum in models.py
TERM_ENUM_VALUES = ["First", "Second", "Third"]
ROLE_ENUM_VALUES = ["admin", "student", "teacher"]

# revision identifiers, used by Alembic
revision = 'e9804a5ab18c'
down_revision = None
branch_labels = None
depends_on = None

def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column_name in [col['name'] for col in insp.get_columns(table_name)]

def upgrade():
    # Alter class_teacher
    op.alter_column(
        'class_teacher',
        'is_form_teacher',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default='0'
    )

    # Alter classes
    op.alter_column(
        'classes',
        'name',
        existing_type=sa.String(length=50),
        nullable=False
    )

    # Alter fee_payment
    if not column_exists('fee_payment', 'temp_term'):
        op.add_column('fee_payment', sa.Column('temp_term', sa.String(length=20), nullable=True))
    op.execute("""
        UPDATE fee_payment 
        SET temp_term = CASE 
            WHEN UPPER(term) IN ('FIRST', '1', '1ST') THEN 'First'
            WHEN UPPER(term) IN ('SECOND', '2', '2ND') THEN 'Second'
            WHEN UPPER(term) IN ('THIRD', '3', '3RD') THEN 'Third'
            ELSE 'First' END
        WHERE term IS NOT NULL
    """)
    op.execute("""
        DELETE f1 FROM fee_payment f1
        INNER JOIN fee_payment f2
        WHERE 
            f1.student_id = f2.student_id AND
            f1.session_id = f2.session_id AND
            f1.temp_term = f2.temp_term AND
            f1.id < f2.id
    """)
    op.execute("UPDATE fee_payment SET term = temp_term")
    op.alter_column(
        'fee_payment',
        'term',
        existing_type=sa.String(length=20),
        type_=sa.Enum(*TERM_ENUM_VALUES, name='termenum'),
        nullable=False
    )
    if column_exists('fee_payment', 'temp_term'):
        op.drop_column('fee_payment', 'temp_term')

    # Alter result
    if not column_exists('result', 'temp_term'):
        op.add_column('result', sa.Column('temp_term', sa.String(length=20), nullable=True))
    op.execute("""
        UPDATE result 
        SET temp_term = CASE 
            WHEN UPPER(term) IN ('FIRST', '1', '1ST') THEN 'First'
            WHEN UPPER(term) IN ('SECOND', '2', '2ND') THEN 'Second'
            WHEN UPPER(term) IN ('THIRD', '3', '3RD') THEN 'Third'
            ELSE 'First' END
        WHERE term IS NOT NULL
    """)
    op.execute("""
        DELETE r1 FROM result r1
        INNER JOIN result r2
        WHERE 
            r1.student_id = r2.student_id AND
            r1.subject_id = r2.subject_id AND
            r1.session = r2.session AND
            r1.temp_term = r2.temp_term AND
            r1.id < r2.id
    """)
    op.execute("UPDATE result SET term = temp_term")
    op.alter_column(
        'result',
        'term',
        existing_type=sa.String(length=20),
        type_=sa.Enum(*TERM_ENUM_VALUES, name='termenum'),
        nullable=False
    )
    op.alter_column(
        'result',
        'created_at',
        existing_type=sa.DateTime(),
        nullable=False,
        server_default=sa.func.now()
    )
    if column_exists('result', 'temp_term'):
        op.drop_column('result', 'temp_term')

    # Alter session
    op.alter_column(
        'session',
        'is_current',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default='0'
    )
    op.alter_column(
        'session',
        'current_term',
        existing_type=sa.String(length=20),
        type_=sa.Enum(*TERM_ENUM_VALUES, name='termenum'),
        existing_nullable=True
    )

    # Alter student
    op.alter_column(
        'student',
        'date_registered',
        existing_type=sa.DateTime(),
        nullable=False,
        existing_server_default=sa.text('CURRENT_TIMESTAMP')
    )
    op.alter_column(
        'student',
        'approved',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default='0'
    )

    # Alter student_class_history
    if not column_exists('student_class_history', 'start_term'):
        op.add_column('student_class_history', sa.Column('start_term', sa.Enum(*TERM_ENUM_VALUES, name='termenum'), nullable=False, server_default='First'))
    else:
        op.execute("""
            UPDATE student_class_history 
            SET start_term = CASE 
                WHEN UPPER(start_term) IN ('FIRST', '1', '1ST') THEN 'First'
                WHEN UPPER(start_term) IN ('SECOND', '2', '2ND') THEN 'Second'
                WHEN UPPER(start_term) IN ('THIRD', '3', '3RD') THEN 'Third'
                ELSE 'First' END
            WHERE start_term IS NOT NULL
        """)
        op.alter_column(
            'student_class_history',
            'start_term',
            existing_type=sa.String(length=20),
            type_=sa.Enum(*TERM_ENUM_VALUES, name='termenum'),
            nullable=False,
            server_default='First'
        )

    if not column_exists('student_class_history', 'end_term'):
        op.add_column('student_class_history', sa.Column('end_term', sa.Enum(*TERM_ENUM_VALUES, name='termenum'), nullable=True))

    if not column_exists('student_class_history', 'join_date'):
        op.add_column('student_class_history', sa.Column('join_date', sa.DateTime(), nullable=False, server_default=sa.func.now()))
        op.execute("UPDATE student_class_history SET join_date = NOW() WHERE join_date IS NULL")

    if not column_exists('student_class_history', 'leave_date'):
        op.add_column('student_class_history', sa.Column('leave_date', sa.DateTime(), nullable=True))

    if not column_exists('student_class_history', 'is_active'):
        op.add_column('student_class_history', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'))
        op.execute("UPDATE student_class_history SET is_active = 1 WHERE is_active IS NULL")

    # Alter user
    op.alter_column(
        'user',
        'active',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default='1'
    )
    op.alter_column(
        'user',
        'role',
        existing_type=sa.String(length=50),
        type_=sa.Enum(*ROLE_ENUM_VALUES, name='roleenum'),
        nullable=False
    )
    op.execute("""
        UPDATE user 
        SET role = LOWER(role)
        WHERE role IN ('admin', 'student', 'teacher', 'ADMIN', 'STUDENT', 'TEACHER')
    """)

def downgrade():
    # Downgrade user
    op.alter_column(
        'user',
        'role',
        existing_type=sa.Enum(*ROLE_ENUM_VALUES, name='roleenum'),
        type_=sa.String(length=50),
        nullable=False
    )
    op.alter_column(
        'user',
        'active',
        existing_type=sa.Boolean(),
        nullable=True
    )

    # Downgrade student_class_history
    if column_exists('student_class_history', 'is_active'):
        op.drop_column('student_class_history', 'is_active')
    if column_exists('student_class_history', 'leave_date'):
        op.drop_column('student_class_history', 'leave_date')
    if column_exists('student_class_history', 'join_date'):
        op.drop_column('student_class_history', 'join_date')
    if column_exists('student_class_history', 'end_term'):
        op.drop_column('student_class_history', 'end_term')
    if column_exists('student_class_history', 'start_term'):
        op.alter_column(
            'student_class_history',
            'start_term',
            existing_type=sa.Enum(*TERM_ENUM_VALUES, name='termenum'),
            type_=sa.String(length=20),
            nullable=True
        )

    # Downgrade student
    op.alter_column(
        'student',
        'approved',
        existing_type=sa.Boolean(),
        nullable=True
    )
    op.alter_column(
        'student',
        'date_registered',
        existing_type=sa.DateTime(),
        nullable=True,
        existing_server_default=sa.text('CURRENT_TIMESTAMP')
    )

    # Downgrade session
    op.alter_column(
        'session',
        'current_term',
        existing_type=sa.Enum(*TERM_ENUM_VALUES, name='termenum'),
        type_=sa.String(length=20),
        existing_nullable=True
    )
    op.alter_column(
        'session',
        'is_current',
        existing_type=sa.Boolean(),
        nullable=True
    )

    # Downgrade result
    if not column_exists('result', 'temp_term'):
        op.add_column('result', sa.Column('temp_term', sa.String(length=20), nullable=True))
    op.alter_column(
        'result',
        'created_at',
        existing_type=sa.DateTime(),
        nullable=True
    )
    op.alter_column(
        'result',
        'term',
        existing_type=sa.Enum(*TERM_ENUM_VALUES, name='termenum'),
        type_=sa.String(length=20),
        existing_nullable=False
    )
    if column_exists('result', 'temp_term'):
        op.drop_column('result', 'temp_term')

    # Downgrade fee_payment
    if not column_exists('fee_payment', 'temp_term'):
        op.add_column('fee_payment', sa.Column('temp_term', sa.String(length=20), nullable=True))
    op.alter_column(
        'fee_payment',
        'term',
        existing_type=sa.Enum(*TERM_ENUM_VALUES, name='termenum'),
        type_=sa.String(length=20),
        existing_nullable=False
    )
    if column_exists('fee_payment', 'temp_term'):
        op.drop_column('fee_payment', 'temp_term')

    # Downgrade classes
    op.alter_column(
        'classes',
        'name',
        existing_type=sa.String(length=50),
        nullable=True
    )

    # Downgrade class_teacher
    op.alter_column(
        'class_teacher',
        'is_form_teacher',
        existing_type=sa.Boolean(),
        nullable=True
    )