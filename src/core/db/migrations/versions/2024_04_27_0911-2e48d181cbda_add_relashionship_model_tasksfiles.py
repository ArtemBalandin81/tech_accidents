"""Add relashionship model TasksFiles

Revision ID: 2e48d181cbda
Revises: 8b45b75e5c7e
Create Date: 2024-04-27 09:11:56.032569

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2e48d181cbda'
down_revision = '8b45b75e5c7e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('files',
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('tasks_files',
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('file_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
    sa.PrimaryKeyConstraint('task_id', 'file_id')
    )
    # op.alter_column('user', 'created_at',
    #            existing_type=sa.DATE(),
    #            type_=sa.TIMESTAMP(),
    #            existing_nullable=False,
    #            existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))
    # op.alter_column('user', 'updated_at',
    #            existing_type=sa.DATE(),
    #            type_=sa.TIMESTAMP(),
    #            existing_nullable=False,
    #            existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # op.alter_column('user', 'updated_at',
    #            existing_type=sa.TIMESTAMP(),
    #            type_=sa.DATE(),
    #            existing_nullable=False,
    #            existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))
    # op.alter_column('user', 'created_at',
    #            existing_type=sa.TIMESTAMP(),
    #            type_=sa.DATE(),
    #            existing_nullable=False,
    #            existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))
    op.drop_table('tasks_files')
    op.drop_table('files')
    # ### end Alembic commands ###
