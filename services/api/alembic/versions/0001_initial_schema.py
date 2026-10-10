"""Initial database schema for Patchwise

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-09 23:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # 2. repositories
    op.create_table(
        'repositories',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('owner', sa.String(100), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('full_name', sa.String(200), nullable=False),
        sa.Column('default_branch', sa.String(50), server_default='main', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_repositories_full_name', 'repositories', ['full_name'], unique=True)

    # 3. pull_requests
    op.create_table(
        'pull_requests',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('repository_id', sa.CHAR(36), sa.ForeignKey('repositories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pr_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('state', sa.String(20), server_default='open', nullable=False),
        sa.Column('base_commit_sha', sa.String(40), nullable=True),
        sa.Column('head_commit_sha', sa.String(40), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_pull_requests_repository_id', 'pull_requests', ['repository_id'])
    op.create_index('ix_pull_requests_repo_number', 'pull_requests', ['repository_id', 'pr_number'], unique=True)

    # 4. reviews
    op.create_table(
        'reviews',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('repository', sa.String(255), nullable=False),
        sa.Column('pr_number', sa.Integer(), nullable=False),
        sa.Column('pr_title', sa.String(255), nullable=True),
        sa.Column('commit_sha', sa.String(40), nullable=True),
        sa.Column('status', sa.String(30), server_default='queued', nullable=False),
        sa.Column('engine_version', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('pr_id', sa.CHAR(36), sa.ForeignKey('pull_requests.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_reviews_repo_pr', 'reviews', ['repository', 'pr_number'])
    op.create_index('ix_reviews_started_at', 'reviews', ['started_at'])
    op.create_index('ix_reviews_pr_id', 'reviews', ['pr_id'])

    # 5. findings
    op.create_table(
        'findings',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('review_id', sa.CHAR(36), sa.ForeignKey('reviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_id', sa.String(50), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('start_line', sa.Integer(), nullable=True),
        sa.Column('end_line', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('suggested_fix', sa.Text(), nullable=True),
        sa.Column('fingerprint', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_findings_review_id', 'findings', ['review_id'])
    op.create_index('ix_findings_severity', 'findings', ['severity'])
    op.create_index('ix_findings_fingerprint', 'findings', ['fingerprint'])
    op.create_index('ix_findings_review_severity', 'findings', ['review_id', 'severity'])

    # 6. feedback
    op.create_table(
        'feedback',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('finding_id', sa.CHAR(36), sa.ForeignKey('findings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('verdict', sa.String(20), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_feedback_finding_id', 'feedback', ['finding_id'])

    # 7. evaluation_runs
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('dataset_version', sa.String(50), nullable=False),
        sa.Column('engine_version', sa.String(50), nullable=False),
        sa.Column('provider_version', sa.String(50), nullable=False),
        sa.Column('tp', sa.Integer(), nullable=False),
        sa.Column('fp', sa.Integer(), nullable=False),
        sa.Column('fn', sa.Integer(), nullable=False),
        sa.Column('precision', sa.Float(), nullable=True),
        sa.Column('recall', sa.Float(), nullable=True),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 8. evaluation_cases
    op.create_table(
        'evaluation_cases',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('dataset_version', sa.String(50), nullable=False),
        sa.Column('case_name', sa.String(100), nullable=False),
        sa.Column('language', sa.String(50), nullable=False),
        sa.Column('code_diff', sa.Text(), nullable=False),
        sa.Column('expected_findings_json', sa.Text(), nullable=False),
        sa.Column('labels', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('evaluation_cases')
    op.drop_table('evaluation_runs')
    op.drop_table('feedback')
    op.drop_table('findings')
    op.drop_table('reviews')
    op.drop_table('pull_requests')
    op.drop_table('repositories')
    op.drop_table('users')
