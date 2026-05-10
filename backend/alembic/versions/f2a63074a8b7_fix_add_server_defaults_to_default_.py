"""fix: add server_defaults to default columns

Revision ID: f2a63074a8b7
Revises: 77b8481de8a2
Create Date: 2026-05-10 09:16:57.504059

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a63074a8b7'
down_revision: Union[str, None] = '77b8481de8a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # customers
    op.alter_column('customers', 'statut_pep',
        existing_type=sa.BOOLEAN(), server_default=sa.text('false'))
    op.alter_column('customers', 'kyc_level',
        existing_type=sa.VARCHAR(length=10), server_default='LOW')
    op.alter_column('customers', 'kyc_completion',
        existing_type=sa.INTEGER(), server_default=sa.text('0'))
    op.alter_column('customers', 'status',
        existing_type=sa.VARCHAR(length=20), server_default='ACTIVE')

    # customer_accounts
    op.alter_column('customer_accounts', 'solde_moyen',
        existing_type=sa.NUMERIC(precision=15, scale=2), server_default=sa.text('0'))
    op.alter_column('customer_accounts', 'status',
        existing_type=sa.VARCHAR(length=50), server_default='ACTIF')

    # transactions
    op.alter_column('transactions', 'devise',
        existing_type=sa.VARCHAR(length=5), server_default='XOF')

    # users
    op.alter_column('users', 'is_active',
        existing_type=sa.BOOLEAN(), server_default=sa.text('true'))


def downgrade() -> None:
    op.alter_column('users', 'is_active',
        existing_type=sa.BOOLEAN(), server_default=None)
    op.alter_column('transactions', 'devise',
        existing_type=sa.VARCHAR(length=5), server_default=None)
    op.alter_column('customer_accounts', 'status',
        existing_type=sa.VARCHAR(length=50), server_default=None)
    op.alter_column('customer_accounts', 'solde_moyen',
        existing_type=sa.NUMERIC(precision=15, scale=2), server_default=None)
    op.alter_column('customers', 'status',
        existing_type=sa.VARCHAR(length=20), server_default=None)
    op.alter_column('customers', 'kyc_completion',
        existing_type=sa.INTEGER(), server_default=None)
    op.alter_column('customers', 'kyc_level',
        existing_type=sa.VARCHAR(length=10), server_default=None)
    op.alter_column('customers', 'statut_pep',
        existing_type=sa.BOOLEAN(), server_default=None)