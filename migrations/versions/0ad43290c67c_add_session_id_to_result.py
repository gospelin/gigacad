"""Add session_id to result

Revision ID: 0ad43290c67c
Revises: 67965a197b92
Create Date: 2025-03-09 09:51:01.914959

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '0ad43290c67c'
down_revision = '67965a197b92'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Step 1: Ensure at least one session exists
    session_count = conn.execute(text("SELECT COUNT(*) FROM session")).scalar()
    if session_count == 0:
        conn.execute(text("INSERT INTO session (year, is_current, current_term) VALUES ('2023/2024', 1, 'Third')"))
        default_session_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
    else:
        default_session_id = conn.execute(text("SELECT id FROM session ORDER BY id LIMIT 1")).scalar()

    # Step 2: Check if 'result' table exists and prepare to rename it
    result_exists = conn.execute(text("SHOW TABLES LIKE 'result'")).scalar() is not None
    # if result_exists:
    #     # Drop existing foreign key constraints
    #     constraints = ['fk_result_class_id', 'fk_result_session_id', 'result_ibfk_1', 'result_ibfk_2']
    #     for constraint in constraints:
    #         try:
    #             conn.execute(text(f"ALTER TABLE result DROP FOREIGN KEY {constraint}"))
    #         except Exception:
    #             pass  # Ignore if the constraint doesn't exist

    #     # Rename the existing 'result' table
    #     # op.rename_table('result', 'result_old')

    # # Step 3: Create the new 'result' table
    # op.create_table(
    #     'result',
    #     sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
    #     sa.Column('student_id', sa.Integer(), nullable=False),
    #     sa.Column('subject_id', sa.Integer(), nullable=False),
    #     sa.Column('term', sa.Enum('First', 'Second', 'Third'), nullable=True),
    #     sa.Column('class_assessment', sa.Integer(), nullable=True),
    #     sa.Column('summative_test', sa.Integer(), nullable=True),
    #     sa.Column('exam', sa.Integer(), nullable=True),
    #     sa.Column('total', sa.Integer(), nullable=True),
    #     sa.Column('grade', sa.String(length=5), nullable=True),
    #     sa.Column('remark', sa.String(length=100), nullable=True),
    #     sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    #     sa.Column('next_term_begins', sa.String(length=100), nullable=True),
    #     sa.Column('last_term_average', sa.Float(), nullable=True),
    #     sa.Column('position', sa.String(length=10), nullable=True),
    #     sa.Column('date_issued', sa.String(length=100), nullable=True),
    #     sa.Column('subjects_offered', sa.Integer(), nullable=True),
    #     sa.Column('grand_total', sa.Integer(), nullable=True),
    #     sa.Column('term_average', sa.Float(), nullable=True),
    #     sa.Column('cumulative_average', sa.Float(), nullable=True),
    #     sa.Column('principal_remark', sa.String(length=100), nullable=True),
    #     sa.Column('teacher_remark', sa.String(length=100), nullable=True),
    #     sa.Column('class_id', sa.Integer(), nullable=False),
    #     sa.Column('session_id', sa.Integer(), nullable=True),
    #     sa.PrimaryKeyConstraint('id'),
    #     sa.UniqueConstraint('student_id', 'subject_id', 'class_id', 'term', 'session_id', name='unique_result'),
    #     sa.ForeignKeyConstraint(['student_id'], ['student.id'], name='fk_result_student_id'),
    #     sa.ForeignKeyConstraint(['subject_id'], ['subject.id'], name='fk_result_subject_id'),
    #     sa.ForeignKeyConstraint(['class_id'], ['classes.id'], name='fk_result_class_id_new'),
    #     sa.ForeignKeyConstraint(['session_id'], ['session.id'], name='fk_result_session_id_new'),
    #     mysql_engine='InnoDB',
    #     mysql_charset='utf8mb3'
    # )

    # Step 4: Migrate data from 'result_old' to the new 'result' table (if it existed)
    if result_exists:
        conn.execute(text(f"""
            INSERT INTO result (
                id, student_id, subject_id, term, class_assessment, summative_test, exam, total, grade, remark,
                created_at, next_term_begins, last_term_average, position, date_issued, subjects_offered,
                grand_total, term_average, cumulative_average, principal_remark, teacher_remark, class_id, session_id
            )
            SELECT
                ro.id, ro.student_id, ro.subject_id, ro.term, ro.class_assessment, ro.summative_test, ro.exam, ro.total,
                ro.grade, ro.remark, ro.created_at, ro.next_term_begins, ro.last_term_average, ro.position,
                ro.date_issued, ro.subjects_offered, ro.grand_total, ro.term_average, ro.cumulative_average,
                ro.principal_remark, ro.teacher_remark, ro.class_id, {default_session_id} as session_id
            FROM result_old ro
        """))

        # Step 5: Drop the old table
        # op.drop_table('result_old')

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('result_old',
    sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('student_id', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('subject_id', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('term', mysql.ENUM('First', 'Second', 'Third'), nullable=False),
    sa.Column('session', mysql.VARCHAR(length=20), nullable=False),
    sa.Column('class_assessment', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('summative_test', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('exam', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('total', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('grade', mysql.VARCHAR(length=5), nullable=True),
    sa.Column('remark', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('next_term_begins', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('last_term_average', mysql.FLOAT(), nullable=True),
    sa.Column('position', mysql.VARCHAR(length=10), nullable=True),
    sa.Column('date_issued', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('subjects_offered', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('grand_total', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('term_average', mysql.FLOAT(), nullable=True),
    sa.Column('cumulative_average', mysql.FLOAT(), nullable=True),
    sa.Column('principal_remark', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('teacher_remark', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('class_id', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('session_id', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['class_id'], ['classes.id'], name='fk_result_class_id'),
    sa.ForeignKeyConstraint(['session_id'], ['session.id'], name='fk_result_session_id'),
    sa.ForeignKeyConstraint(['student_id'], ['student.id'], name='result_old_ibfk_1'),
    sa.ForeignKeyConstraint(['subject_id'], ['subject.id'], name='result_old_ibfk_2'),
    sa.PrimaryKeyConstraint('id'),
    mysql_default_charset='utf8mb3',
    mysql_engine='InnoDB'
    )
    with op.batch_alter_table('result_old', schema=None) as batch_op:
        batch_op.create_index('unique_result', ['student_id', 'subject_id', 'term', 'session'], unique=True)

    # ### end Alembic commands ###
