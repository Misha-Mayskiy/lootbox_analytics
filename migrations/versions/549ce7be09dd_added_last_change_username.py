"""Added last change username

Revision ID: 549ce7be09dd
Revises: 396dfb968082
Create Date: 2025-05-27 00:24:59.649343

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '549ce7be09dd'
down_revision = '396dfb968082'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username_last_changed_at', sa.DateTime(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('username_last_changed_at')

    # ### end Alembic commands ###
