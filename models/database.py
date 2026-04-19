# =============================================================
#  models/database.py  —  Pixel Pro schema
#  Uses expire_on_commit=False + eager loading to prevent
#  DetachedInstanceError throughout the app
# =============================================================
from sqlalchemy import (create_engine, Column, Integer, String,
                        Boolean, DateTime, Text, ForeignKey)
from sqlalchemy.orm import (declarative_base, sessionmaker,
                             relationship, joinedload)
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Use PIXELPRO_DATA_DIR if set by app.py (installed/frozen mode).
# Fall back to project root for development.
_data_dir = os.environ.get("PIXELPRO_DATA_DIR", BASE_DIR)
DB_PATH   = os.path.join(_data_dir, "pixelpro.db")

engine  = create_engine(
    f"sqlite:///{DB_PATH}", echo=False,
    connect_args={"check_same_thread": False}
)
# expire_on_commit=False keeps objects usable after session.close()
Session = sessionmaker(bind=engine, expire_on_commit=False)
Base    = declarative_base()


class User(Base):
    __tablename__ = "users"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    username       = Column(String(100), nullable=False, unique=True)
    password       = Column(String(255), nullable=False)
    email          = Column(String(255), nullable=True)
    specialization = Column(String(255), nullable=True)
    is_active      = Column(Boolean, default=True)
    is_deleted     = Column(Boolean, default=False)


class Patient(Base):
    __tablename__ = "patients"
    id                   = Column(Integer, primary_key=True, autoincrement=True)
    patient_id           = Column(String(20),  unique=True)
    first_name           = Column(String(100))
    last_name            = Column(String(100))
    dob                  = Column(DateTime,    nullable=True)
    gender               = Column(String(20))
    phone                = Column(String(30))
    address              = Column(Text)
    ref_doc              = Column(String(255))
    notes                = Column(Text)
    blood_group          = Column(String(10),  nullable=True)
    current_medication   = Column(Text,        nullable=True)
    existing_medical     = Column(Text,        nullable=True)
    past_medical_history = Column(Text,        nullable=True)
    allergies            = Column(Text,        nullable=True)
    email_id             = Column(String(255), nullable=True)
    created_at           = Column(DateTime,    default=datetime.now)
    is_active            = Column(Boolean,     default=True)
    is_deleted           = Column(Boolean,     default=False)
    visits               = relationship(
        "Visit", back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(Visit.visit_date)",
        lazy="select"
    )


class Visit(Base):
    __tablename__ = "visits"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    visit_id       = Column(String(20), unique=True)
    patient_id     = Column(Integer, ForeignKey("patients.id"), nullable=False)
    visit_date     = Column(DateTime, default=datetime.now)
    doctor         = Column(String(255))
    department     = Column(String(255))
    clinical_notes = Column(Text)
    is_deleted     = Column(Boolean, default=False)
    patient        = relationship("Patient", back_populates="visits", lazy="select")
    images         = relationship(
        "CapturedImage", back_populates="visit",
        cascade="all, delete-orphan",
        order_by="CapturedImage.sort_order",
        lazy="select"
    )


class CapturedImage(Base):
    __tablename__ = "captured_images"
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    visit_id            = Column(Integer, ForeignKey("visits.id"), nullable=False)
    file_path           = Column(String(1000))
    annotated_path      = Column(String(1000), nullable=True)
    annotation_data     = Column(Text,         nullable=True)
    selected_for_report = Column(Boolean,      default=False)
    sort_order          = Column(Integer,      default=0)
    captured_at         = Column(DateTime,     default=datetime.now)
    camera_source       = Column(String(50))
    is_deleted          = Column(Boolean,      default=False)
    visit               = relationship("Visit", back_populates="images", lazy="select")


class PACSConfig(Base):
    __tablename__ = "pacs_config"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    name           = Column(String(100), default="Default PACS")
    pacs_ip        = Column(String(100))
    pacs_port      = Column(Integer, default=104)
    ae_title       = Column(String(50))
    local_ae_title = Column(String(50), default="PIXELPRO")
    institution    = Column(String(255))
    modality       = Column(String(20), default="ES")
    is_active      = Column(Boolean, default=True)


class SavedReport(Base):
    __tablename__ = "saved_reports"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    visit_id      = Column(Integer, ForeignKey("visits.id"), nullable=False)
    hospital      = Column(String(255), default="")
    department    = Column(String(255), default="")
    doctor        = Column(String(255), default="")
    address       = Column(String(500), default="")
    observations  = Column(Text, default="")
    diagnosis     = Column(Text, default="")
    notes         = Column(Text, default="")
    signature     = Column(String(255), default="")
    report_html   = Column(Text, default="")     # last rendered HTML
    saved_at      = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted    = Column(Boolean, default=False)
    visit         = relationship("Visit", lazy="select")


class HospitalProfile(Base):
    """Single global row — hospital identity that persists across all reports."""
    __tablename__ = "hospital_profile"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(255), default="")
    address    = Column(Text,        default="")
    email      = Column(String(255), default="")
    phone      = Column(String(100), default="")
    logo_path  = Column(String(1000), default="")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ── Convenience query helpers (always load relations eagerly) ──

def get_patient_with_visits(session, patient_id: int) -> Patient:
    return (session.query(Patient)
            .options(joinedload(Patient.visits).joinedload(Visit.images))
            .filter_by(id=patient_id).first())

def get_visit_with_images(session, visit_id: int) -> Visit:
    return (session.query(Visit)
            .options(joinedload(Visit.images), joinedload(Visit.patient))
            .filter_by(id=visit_id).first())

def get_all_patients(session):
    return (session.query(Patient)
            .options(joinedload(Patient.visits).joinedload(Visit.images))
            .filter(Patient.is_deleted!=True)
            .order_by(Patient.created_at.desc())
            .all())

def get_recent_visits(session, limit=10):
    return (session.query(Visit)
            .options(joinedload(Visit.patient), joinedload(Visit.images))
            .filter(Visit.is_deleted!=True)
            .order_by(Visit.visit_date.desc())
            .limit(limit).all())


def gen_patient_id(session) -> str:
    n = session.query(Patient).count()
    return f"PT-{n+1:04d}"

def gen_visit_id(session) -> str:
    n = session.query(Visit).count()
    return f"VS-{n+1:04d}"


def _add_missing_columns():
    required = {
        "patients": [
            ("patient_id",           "VARCHAR(20)"),
            ("notes",                "TEXT"),
            ("blood_group",          "VARCHAR(10)"),
            ("current_medication",   "TEXT"),
            ("existing_medical",     "TEXT"),
            ("past_medical_history", "TEXT"),
            ("allergies",            "TEXT"),
            ("email_id",             "VARCHAR(255)"),
            ("created_at",           "DATETIME"),
            ("phone",                "VARCHAR(30)"),
            ("address",              "TEXT"),
            ("ref_doc",              "VARCHAR(255)"),
        ],
        "visits": [
            ("visit_id",       "VARCHAR(20)"),
            ("department",     "VARCHAR(255)"),
            ("clinical_notes", "TEXT"),
            ("is_deleted",     "INTEGER DEFAULT 0"),
        ],
        "captured_images": [
            ("annotated_path",      "VARCHAR(1000)"),
            ("annotation_data",     "TEXT"),
            ("selected_for_report", "INTEGER DEFAULT 0"),
            ("sort_order",          "INTEGER DEFAULT 0"),
            ("camera_source",       "VARCHAR(50)"),
            ("is_deleted",          "INTEGER DEFAULT 0"),
        ],
        "saved_reports": [
            ("hospital",     "VARCHAR(255)"),
            ("department",   "VARCHAR(255)"),
            ("doctor",       "VARCHAR(255)"),
            ("address",      "VARCHAR(500)"),
            ("observations", "TEXT"),
            ("diagnosis",    "TEXT"),
            ("notes",        "TEXT"),
            ("signature",    "VARCHAR(255)"),
            ("report_html",  "TEXT"),
            ("saved_at",     "DATETIME"),
            ("is_deleted",   "INTEGER DEFAULT 0"),
        ],
        "hospital_profile": [
            ("name",       "VARCHAR(255)"),
            ("address",    "TEXT"),
            ("email",      "VARCHAR(255)"),
            ("phone",      "VARCHAR(100)"),
            ("logo_path",  "VARCHAR(1000)"),
            ("updated_at", "DATETIME"),
        ],
    }
    from sqlalchemy import text
    with engine.connect() as conn:
        for table, cols in required.items():
            try:
                rows     = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                existing = {r[1] for r in rows}
            except Exception:
                continue
            for col_name, col_type in cols:
                if col_name not in existing:
                    try:
                        conn.execute(text(
                            f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"
                        ))
                        print(f"[DB] Added column: {table}.{col_name}")
                    except Exception as e:
                        print(f"[DB] Could not add {table}.{col_name}: {e}")
        conn.commit()


def _fix_null_booleans():
    """
    SQLite ALTER TABLE adds new columns as NULL for existing rows,
    even with DEFAULT 0. This causes filter_by(is_deleted=False) to
    silently exclude those rows. Fix by setting NULL → 0 for all
    boolean columns on every startup (safe, idempotent).
    """
    fixes = [
        "UPDATE users           SET is_deleted=0 WHERE is_deleted IS NULL",
        "UPDATE users           SET is_active=1  WHERE is_active  IS NULL",
        "UPDATE patients        SET is_deleted=0 WHERE is_deleted IS NULL",
        "UPDATE patients        SET is_active=1  WHERE is_active  IS NULL",
        "UPDATE visits          SET is_deleted=0 WHERE is_deleted IS NULL",
        "UPDATE captured_images SET is_deleted=0 WHERE is_deleted IS NULL",
        "UPDATE captured_images SET selected_for_report=0 WHERE selected_for_report IS NULL",
    ]
    with engine.connect() as conn:
        for sql in fixes:
            try:
                from sqlalchemy import text
                conn.execute(text(sql))
            except Exception:
                pass
        conn.commit()


def init_db():
    Base.metadata.create_all(engine)
    _add_missing_columns()
    _fix_null_booleans()
    _migrate_legacy()


def _migrate_legacy():
    old_path = os.path.join(BASE_DIR, "medcam.db")
    if not os.path.exists(old_path):
        return
    try:
        from sqlalchemy import create_engine as ce, text
        old_engine = ce(f"sqlite:///{old_path}",
                        connect_args={"check_same_thread": False})
        with old_engine.connect() as old_conn:
            tbls = old_conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='patients'"
            )).fetchall()
            if not tbls:
                return
            old_patients = old_conn.execute(text("SELECT * FROM patients")).fetchall()
            cols         = old_conn.execute(text("PRAGMA table_info(patients)")).fetchall()
            col_names    = [c[1] for c in cols]

        sess     = Session()
        migrated = 0

        for row in old_patients:
            p_data = dict(zip(col_names, row))
            fn = (p_data.get("first_name") or "").strip()
            ln = (p_data.get("last_name")  or "").strip()
            if not fn and not ln:
                continue

            from sqlalchemy import text as tx
            existing = sess.execute(tx(
                "SELECT id FROM patients WHERE first_name=:fn AND last_name=:ln "
                "AND is_deleted=0 LIMIT 1"
            ), {"fn": fn, "ln": ln}).fetchone()
            if existing:
                continue

            p = Patient(
                patient_id           = gen_patient_id(sess),
                first_name           = fn,
                last_name            = ln,
                gender               = p_data.get("gender"),
                phone                = p_data.get("contact_number"),
                address              = p_data.get("address"),
                ref_doc              = p_data.get("ref_doc"),
                blood_group          = p_data.get("blood_group"),
                current_medication   = p_data.get("current_medication"),
                existing_medical     = p_data.get("existing_medical"),
                past_medical_history = p_data.get("past_medical_history"),
                allergies            = p_data.get("allergies"),
                email_id             = p_data.get("email_id"),
                is_active            = bool(p_data.get("is_active", True)),
                is_deleted           = bool(p_data.get("is_deleted", False)),
            )
            dob_val = p_data.get("dob")
            if dob_val:
                try:
                    p.dob = (datetime.fromisoformat(str(dob_val))
                             if isinstance(dob_val, str) else dob_val)
                except Exception:
                    pass

            sess.add(p); sess.flush()

            legacy = [p_data.get(f"path_image{i}") for i in range(1, 6)]
            legacy = [x for x in legacy if x and os.path.exists(x)]

            v = Visit(
                visit_id       = gen_visit_id(sess),
                patient_id     = p.id,
                doctor         = p_data.get("ref_doc") or "Migrated",
                department     = "Migrated from MedCamPy",
                clinical_notes = "Auto-migrated from previous session.",
                visit_date     = datetime.now(),
            )
            sess.add(v); sess.flush()

            for idx, path in enumerate(legacy):
                sess.add(CapturedImage(
                    visit_id            = v.id,
                    file_path           = path,
                    sort_order          = idx,
                    camera_source       = "migrated",
                    selected_for_report = True,
                ))
            migrated += 1

        sess.commit(); sess.close()
        if migrated:
            print(f"[Migration] Migrated {migrated} patient(s) from medcam.db")

    except Exception as e:
        print(f"[Migration] Warning: {e}")


def get_session():
    return Session()
