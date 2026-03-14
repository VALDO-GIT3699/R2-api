from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.settings import settings

is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if is_sqlite else {},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

from app.models import user
from app.models import memory
from app.models import couple
from app.models import invitation
from app.models import appointment
from app.models import couple_note


def apply_lightweight_migrations() -> None:
    inspector = inspect(engine)

    if not inspector.has_table("users"):
        return

    columns = {column["name"] for column in inspector.get_columns("users")}

    memory_columns = set()
    if inspector.has_table("memories"):
        memory_columns = {column["name"] for column in inspector.get_columns("memories")}

    with engine.begin() as conn:
        if "apple_sub" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN apple_sub VARCHAR"))

        if "is_email_verified" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_email_verified BOOLEAN DEFAULT 0"))

        if "couple_id" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN couple_id INTEGER"))

        conn.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_apple_sub ON users (apple_sub)")
        )

        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_users_couple_id ON users (couple_id)")
        )

        if inspector.has_table("memories"):
            if "couple_id" not in memory_columns:
                conn.execute(text("ALTER TABLE memories ADD COLUMN couple_id INTEGER"))

            if "occurred_at" not in memory_columns:
                conn.execute(text("ALTER TABLE memories ADD COLUMN occurred_at DATETIME"))

            if "created_at" not in memory_columns:
                conn.execute(text("ALTER TABLE memories ADD COLUMN created_at DATETIME"))

            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_memories_couple_id ON memories (couple_id)")
            )

            # Fill null timestamps for legacy rows to keep reminder logic safe.
            conn.execute(
                text(
                    "UPDATE memories "
                    "SET occurred_at = COALESCE(occurred_at, CURRENT_TIMESTAMP), "
                    "created_at = COALESCE(created_at, CURRENT_TIMESTAMP)"
                )
            )

        if not inspector.has_table("appointments"):
            conn.execute(
                text(
                    "CREATE TABLE appointments ("
                    "id INTEGER PRIMARY KEY, "
                    "couple_id INTEGER NOT NULL, "
                    "creator_user_id INTEGER NOT NULL, "
                    "title VARCHAR NOT NULL, "
                    "notes VARCHAR, "
                    "scheduled_for DATETIME NOT NULL, "
                    "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )

        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_appointments_couple_id ON appointments (couple_id)")
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_appointments_scheduled_for ON appointments (scheduled_for)"
            )
        )

        if not inspector.has_table("couple_notes"):
            conn.execute(
                text(
                    "CREATE TABLE couple_notes ("
                    "id INTEGER PRIMARY KEY, "
                    "couple_id INTEGER NOT NULL, "
                    "author_user_id INTEGER NOT NULL, "
                    "content VARCHAR NOT NULL, "
                    "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )

        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_couple_notes_couple_id ON couple_notes (couple_id)")
        )
