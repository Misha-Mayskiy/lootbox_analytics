"""Add cs2_investment_amount to User model

Revision ID: beca5d716246
Revises: 2b6bbee074d6
Create Date: 2025-05-24 23:49:15.070649

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'beca5d716246'
down_revision = '2b6bbee074d6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cs2_investment_amount', sa.Float(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('cs2_investment_amount')

    # ### end Alembic commands ###
