from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:Preserved28/4@localhost:5432/GlonetechManagementSuiteDataBase"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("ALTER TYPE status_enum RENAME VALUE 'in-progress' TO 'in_progress';"))
    conn.commit()

print("Enum updated successfully")