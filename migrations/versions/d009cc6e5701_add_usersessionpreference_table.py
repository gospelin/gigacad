"""Add UserSessionPreference table

Revision ID: d009cc6e5701
Revises: 42fc94b51579
Create Date: 2025-02-25 09:47:16.714311

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd009cc6e5701'
down_revision = '42fc94b51579'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('admin_privilege',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('can_manage_users', sa.Boolean(), nullable=True),
    sa.Column('can_manage_sessions', sa.Boolean(), nullable=True),
    sa.Column('can_manage_classes', sa.Boolean(), nullable=True),
    sa.Column('can_manage_results', sa.Boolean(), nullable=True),
    sa.Column('can_manage_teachers', sa.Boolean(), nullable=True),
    sa.Column('can_view_reports', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_session_preference',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('current_term', sa.Enum('First', 'Second', 'Third', name='termenum'), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['session.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_session_preference')
    op.drop_table('admin_privilege')
    # ### end Alembic commands ###
