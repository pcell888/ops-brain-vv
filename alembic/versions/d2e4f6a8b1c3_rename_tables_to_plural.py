"""rename all tables to plural form

Revision ID: d2e4f6a8b1c3
Revises: c8d1f3a5e9b2
Create Date: 2026-04-25
"""

from alembic import op

revision = "d2e4f6a8b1c3"
down_revision = "c8d1f3a5e9b2"
branch_labels = None
depends_on = None

RENAMES = [
    ("tenant_registry", "tenant_registries"),
    ("ai_diagnosis_report", "diag_reports"),
    ("ai_push_log", "push_logs"),
    ("ai_exec_task", "exec_tasks"),
    ("ai_effect_tracking", "effect_trackings"),
    ("ai_pending_review", "pending_reviews"),
    ("ai_effect_snapshot", "effect_snapshots"),
    ("ai_solution_knowledge", "solution_knowledges"),
    ("ai_review_report", "review_reports"),
    ("ai_async_job_meta", "async_job_metas"),
    ("ai_diagnosis_session", "diag_sessions"),
]

INDEX_RENAMES = [
    ("ix_ai_diagnosis_report_tenant_store", "ix_diag_reports_tenant_store"),
    ("ix_ai_diagnosis_report_created_at", "ix_diag_reports_created_at"),
    ("ix_ai_push_log_thread", "ix_push_logs_thread"),
    ("ix_ai_push_log_tenant_store", "ix_push_logs_tenant_store"),
    ("ix_ai_push_log_created_at", "ix_push_logs_created_at"),
    ("ix_ai_exec_task_thread", "ix_exec_tasks_thread"),
    ("ix_ai_exec_task_tenant_store", "ix_exec_tasks_tenant_store"),
    ("ix_ai_exec_task_plan", "ix_exec_tasks_plan"),
    ("ix_ai_exec_task_created_at", "ix_exec_tasks_created_at"),
    ("ix_ai_effect_tracking_tenant_store", "ix_effect_trackings_tenant_store"),
    ("ix_ai_pending_review_due", "ix_pending_reviews_due"),
    ("ix_ai_pending_review_tenant_store", "ix_pending_reviews_tenant_store"),
    ("ix_ai_effect_snapshot_thread", "ix_effect_snapshots_thread"),
    ("ix_ai_solution_knowledge_indicators", "ix_solution_knowledges_indicators"),
    ("ix_ai_solution_knowledge_industry", "ix_solution_knowledges_industry"),
    ("ix_ai_solution_knowledge_achievement", "ix_solution_knowledges_achievement"),
    ("ix_ai_solution_knowledge_tenant", "ix_solution_knowledges_tenant"),
    ("ix_ai_review_report_tenant_store", "ix_review_reports_tenant_store"),
    ("ix_ai_async_job_meta_thread", "ix_async_job_metas_thread"),
    ("ix_ai_async_job_meta_status", "ix_async_job_metas_status"),
    ("ix_ai_async_job_meta_updated", "ix_async_job_metas_updated"),
    ("ux_ai_async_job_meta_thread_active", "ux_async_job_metas_thread_active"),
    ("ix_diagnosis_session_tenant", "ix_diag_sessions_tenant"),
    ("ix_diagnosis_session_phase", "ix_diag_sessions_phase"),
    ("ix_diagnosis_session_created_at", "ix_diag_sessions_created_at"),
]


def upgrade() -> None:
    for old_name, new_name in RENAMES:
        op.rename_table(old_name, new_name)
    for old_idx, new_idx in INDEX_RENAMES:
        op.execute(f"ALTER INDEX {old_idx} RENAME TO {new_idx}")


def downgrade() -> None:
    for old_idx, new_idx in INDEX_RENAMES:
        op.execute(f"ALTER INDEX {new_idx} RENAME TO {old_idx}")
    for old_name, new_name in RENAMES:
        op.rename_table(new_name, old_name)
