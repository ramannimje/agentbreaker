"""Initial schema migration

Revision ID: 001_initial
Revises: 
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # run the schema.sql
    with open(op.get_context().script.directory + '/../../schema.sql') as f:
        sql = f.read()
    conn.execute(sa.text(sql))


def downgrade():
    # Drop tables
    op.execute("DROP TABLE IF EXISTS alerts CASCADE")
    op.execute("DROP TABLE IF EXISTS tool_call_log CASCADE")
    op.execute("DROP TABLE IF EXISTS sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS teams CASCADE")
