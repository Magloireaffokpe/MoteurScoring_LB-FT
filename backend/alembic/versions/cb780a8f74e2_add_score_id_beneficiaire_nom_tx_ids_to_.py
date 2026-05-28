"""add score_id beneficiaire_nom tx_ids to alerts

Revision ID: cb780a8f74e2
Revises: abc123456789
Create Date: 2026-05-28 12:55:48.923547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'cb780a8f74e2'
down_revision: Union[str, None] = 'abc123456789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('alerts', sa.Column('score_id', sa.UUID(), nullable=True))
    op.add_column('alerts', sa.Column('beneficiaire_nom', sa.String(200), nullable=True))
    op.add_column('alerts', sa.Column('tx_ids', JSONB(), nullable=True))
    op.create_index(op.f('ix_alerts_score_id'), 'alerts', ['score_id'], unique=False)
    op.create_foreign_key('fk_alerts_score_id', 'alerts', 'scores',
                          ['score_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_alerts_score_id', 'alerts', type_='foreignkey')
    op.drop_index(op.f('ix_alerts_score_id'), table_name='alerts')
    op.drop_column('alerts', 'tx_ids')
    op.drop_column('alerts', 'beneficiaire_nom')
    op.drop_column('alerts', 'score_id')
