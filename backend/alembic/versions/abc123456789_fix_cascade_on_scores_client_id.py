"""fix: add CASCADE on scores.client_id FK

Revision ID: abc123456789
Revises: 395261316418
Create Date: 2026-05-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abc123456789'
down_revision: Union[str, None] = '395261316418'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('ALTER TABLE scores DROP CONSTRAINT IF EXISTS scores_client_id_fkey')
    op.execute('ALTER TABLE scores DROP CONSTRAINT IF EXISTS fk_scores_client_id')
    op.execute('ALTER TABLE scores ADD CONSTRAINT fk_scores_client_id FOREIGN KEY (client_id) REFERENCES customers(id) ON DELETE CASCADE')


def downgrade() -> None:
    op.drop_constraint('fk_scores_client_id', 'scores', type_='foreignkey')
    op.create_foreign_key(
        'scores_client_id_fkey', 'scores', 'customers',
        ['client_id'], ['id'],
    )
