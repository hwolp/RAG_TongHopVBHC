from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _column_exists(engine: Engine, table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return False
    columns = inspector.get_columns(table_name)
    return any(col["name"] == column_name for col in columns)


def sync_schema(engine: Engine) -> None:
    """Best-effort schema sync for non-migration environments.

    This keeps older databases compatible with newly added ORM fields.
    """
    with engine.begin() as conn:
        if not _column_exists(engine, "users", "full_name"):
            conn.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR(100) NULL"))

        if not _column_exists(engine, "users", "is_locked"):
            conn.execute(text("ALTER TABLE users ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT 0"))

        if not _column_exists(engine, "users", "role_group_id"):
            conn.execute(text("ALTER TABLE users ADD COLUMN role_group_id INT NULL"))
            try:
                conn.execute(
                    text(
                        "ALTER TABLE users "
                        "ADD CONSTRAINT fk_users_role_group "
                        "FOREIGN KEY (role_group_id) REFERENCES role_groups(id)"
                    )
                )
            except Exception:
                # Ignore if FK already exists or DB variant does not support this statement form.
                pass

        if not _column_exists(engine, "documents", "chat_session_id"):
            conn.execute(text("ALTER TABLE documents ADD COLUMN chat_session_id INT NULL"))
            try:
                conn.execute(
                    text(
                        "ALTER TABLE documents "
                        "ADD CONSTRAINT fk_documents_chat_session "
                        "FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id)"
                    )
                )
            except Exception:
                pass

        if not _column_exists(engine, "shared_documents", "shared_with_user_id"):
            conn.execute(text("ALTER TABLE shared_documents ADD COLUMN shared_with_user_id INT NULL"))
            try:
                conn.execute(
                    text(
                        "ALTER TABLE shared_documents "
                        "ADD CONSTRAINT fk_shared_documents_user "
                        "FOREIGN KEY (shared_with_user_id) REFERENCES users(id)"
                    )
                )
            except Exception:
                pass

        # Ensure new session_doc_attachments table is created
        inspector = inspect(engine)
        if "session_doc_attachments" not in inspector.get_table_names():
            conn.execute(text("""
                CREATE TABLE session_doc_attachments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id INT NOT NULL,
                    doc_id INT NOT NULL,
                    attached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """))
