"""
persistence.py — JSON file-based persistence for all in-memory stores.

Serializes every in-memory dict to a single `store.json` file after each
mutation and reloads the full state on startup.  No external packages required.

Configure the file location via the STORE_PATH environment variable
(default: store.json next to wherever the process runs, or /data/store.json
on Railway if you mount a volume there).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ── store path ────────────────────────────────────────────────────────────────
STORE_PATH = Path(os.getenv("STORE_PATH", "store.json"))


# ── save ──────────────────────────────────────────────────────────────────────

def save_store() -> None:
    """Serialize all in-memory stores to STORE_PATH (atomic write)."""
    try:
        from app import classroom as cls
        from app import auth as auth_mod

        data = {
            # ── classroom stores ──────────────────────────────────────────
            "classrooms": {
                k: v.model_dump(mode="json")
                for k, v in cls._classrooms.items()
            },
            "quizzes": {
                k: v.model_dump(mode="json")
                for k, v in cls._quizzes.items()
            },
            "submissions": {
                k: v.model_dump(mode="json")
                for k, v in cls._submissions.items()
            },
            "polls": {
                k: v.model_dump(mode="json")
                for k, v in cls._polls.items()
            },
            "announcements": {
                k: v.model_dump(mode="json")
                for k, v in cls._announcements.items()
            },
            "chat_history": {
                k: [m.model_dump(mode="json") for m in msgs]
                for k, msgs in cls._chat_history.items()
            },
            "notifications": {
                k: [n.model_dump(mode="json") for n in notes]
                for k, notes in cls._notifications.items()
            },
            "projects": {
                k: v.model_dump(mode="json")
                for k, v in cls._projects.items()
            },
            "project_submissions": {
                k: v.model_dump(mode="json")
                for k, v in cls._project_submissions.items()
            },
            "project_chat": {
                k: [m.model_dump(mode="json") for m in msgs]
                for k, msgs in cls._project_chat.items()
            },
            "lectures": {
                k: v.model_dump(mode="json")
                for k, v in cls._lectures.items()
            },
            "summary_submissions": {
                k: v.model_dump(mode="json")
                for k, v in cls._summary_submissions.items()
            },
            # ── auth stores (bytes stored as hex strings) ─────────────────
            "users_by_email": {
                email: {
                    "record": entry["record"].model_dump(mode="json"),
                    "salt":   entry["salt"].hex(),
                    "hash":   entry["hash"].hex(),
                }
                for email, entry in auth_mod._users_by_email.items()
            },
        }

        # Atomic write: write to .tmp then rename so a crash mid-write
        # never corrupts the existing store.
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STORE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, default=str), encoding="utf-8")
        tmp.replace(STORE_PATH)
        logger.debug("Store saved → %s", STORE_PATH)

    except Exception:
        logger.exception("save_store() failed — data NOT written to disk")


# ── load ──────────────────────────────────────────────────────────────────────

def load_store() -> bool:
    """
    Load all stores from STORE_PATH.
    Returns True if a store was found and loaded, False if starting fresh.
    """
    if not STORE_PATH.exists():
        logger.info("No store file at %s — will seed fresh data.", STORE_PATH)
        return False

    try:
        raw = STORE_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as e:
        logger.error("Failed to read store file (%s) — starting fresh: %s", STORE_PATH, e)
        return False

    try:
        from app import classroom as cls
        from app import auth as auth_mod
        from app.classroom import (
            Classroom, Quiz, Submission, Poll, Announcement, ChatMessage,
            Notification, Project, ProjectSubmission, Lecture, SummarySubmission,
        )
        from app.auth import UserRecord

        # ── classroom stores ──────────────────────────────────────────────
        cls._classrooms = {
            k: Classroom.model_validate(v)
            for k, v in data.get("classrooms", {}).items()
        }
        cls._quizzes = {
            k: Quiz.model_validate(v)
            for k, v in data.get("quizzes", {}).items()
        }
        cls._submissions = {
            k: Submission.model_validate(v)
            for k, v in data.get("submissions", {}).items()
        }
        cls._polls = {
            k: Poll.model_validate(v)
            for k, v in data.get("polls", {}).items()
        }
        cls._announcements = {
            k: Announcement.model_validate(v)
            for k, v in data.get("announcements", {}).items()
        }
        cls._chat_history = {
            k: [ChatMessage.model_validate(m) for m in msgs]
            for k, msgs in data.get("chat_history", {}).items()
        }
        cls._notifications = {
            k: [Notification.model_validate(n) for n in notes]
            for k, notes in data.get("notifications", {}).items()
        }
        cls._projects = {
            k: Project.model_validate(v)
            for k, v in data.get("projects", {}).items()
        }
        cls._project_submissions = {
            k: ProjectSubmission.model_validate(v)
            for k, v in data.get("project_submissions", {}).items()
        }
        cls._project_chat = {
            k: [ChatMessage.model_validate(m) for m in msgs]
            for k, msgs in data.get("project_chat", {}).items()
        }
        cls._lectures = {
            k: Lecture.model_validate(v)
            for k, v in data.get("lectures", {}).items()
        }
        cls._summary_submissions = {
            k: SummarySubmission.model_validate(v)
            for k, v in data.get("summary_submissions", {}).items()
        }

        # ── auth stores — convert hex strings back to bytes ───────────────
        for email, entry in data.get("users_by_email", {}).items():
            record = UserRecord.model_validate(entry["record"])
            auth_entry = {
                "record": record,
                "salt":   bytes.fromhex(entry["salt"]),
                "hash":   bytes.fromhex(entry["hash"]),
            }
            auth_mod._users_by_email[email]      = auth_entry
            auth_mod._users_by_id[record.id]     = auth_entry

        logger.info(
            "Store loaded from %s — %d classes, %d lectures, %d users",
            STORE_PATH,
            len(cls._classrooms),
            len(cls._lectures),
            len(auth_mod._users_by_email),
        )
        return True

    except Exception as e:
        logger.error("Failed to deserialize store: %s — starting fresh.", e)
        return False
