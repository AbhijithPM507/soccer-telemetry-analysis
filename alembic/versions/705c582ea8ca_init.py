from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '705c582ea8ca'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "matches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("home_team", sa.String(), nullable=False),
        sa.Column("away_team", sa.String(), nullable=False),
    )
    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("match_id", sa.String(), sa.ForeignKey("matches.id"), nullable=False, index=True),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False, index=True),
        sa.Column("coord_x", sa.Float(), nullable=False),
        sa.Column("coord_y", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("telemetry_events")
    op.drop_table("matches")
