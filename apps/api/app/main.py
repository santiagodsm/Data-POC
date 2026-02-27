import csv
import io
import re
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db
from .models import Artifact, ProfileResult, ProfileRun
from .queue import profiling_queue
from .storage import get_minio

app = FastAPI(title="Data CoPilot API")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def _safe_name(raw: str) -> str:
    """Turn any string into a safe lowercase identifier."""
    return re.sub(r'[^a-z0-9_]', '_', raw.strip().lower()) or "col"


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    # Parse CSV
    text_content = content.decode("utf-8-sig")  # strip BOM if present
    reader = csv.reader(io.StringIO(text_content))
    rows = list(reader)
    if len(rows) < 1:
        raise HTTPException(status_code=400, detail="CSV has no headers")

    # Sanitize column names
    raw_headers = rows[0]
    headers = [_safe_name(h) or f"col_{i}" for i, h in enumerate(raw_headers)]
    data_rows = rows[1:]

    # Derive table name from filename: csv_<name>
    base = re.sub(r'\.csv$', '', file.filename, flags=re.IGNORECASE)
    table_name = "csv_" + _safe_name(base)[:50]

    # Create (or replace) the table — all columns are TEXT for simplicity
    cols_ddl = ", ".join(f'"{h}" TEXT' for h in headers)
    col_list  = ", ".join(f'"{h}"' for h in headers)
    placeholders = ", ".join(f":p{i}" for i in range(len(headers)))

    db.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
    db.execute(text(f'CREATE TABLE "{table_name}" ({cols_ddl})'))

    # Bulk insert
    if data_rows:
        insert_sql = text(f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})')
        for row in data_rows:
            # Pad/trim row to match header count
            padded = (row + [""] * len(headers))[: len(headers)]
            db.execute(insert_sql, {f"p{i}": padded[i] for i in range(len(headers))})

    db.commit()

    # Save original CSV to MinIO uploads bucket
    bucket = "uploads"
    minio_key = f"csv/{table_name}/{file.filename}"
    try:
        client = get_minio()
        client.put_object(
            bucket,
            minio_key,
            io.BytesIO(content),
            length=len(content),
            content_type="text/csv",
        )
    except Exception:
        pass  # MinIO upload is best-effort; don't fail the whole request

    return {
        "table": table_name,
        "row_count": len(data_rows),
        "columns": headers,
    }


# ---------------------------------------------------------------------------
# Profiling
# ---------------------------------------------------------------------------

class ProfilingRunRequest(BaseModel):
    table: str
    project_id: Optional[uuid.UUID] = None


@app.post("/profiling/run", status_code=202)
def create_profiling_run(body: ProfilingRunRequest, db: Session = Depends(get_db)):
    run = ProfileRun(project_id=body.project_id)
    db.add(run)
    db.commit()
    db.refresh(run)

    profiling_queue.enqueue(
        "tasks.run_profile",
        str(run.id),
        body.table,
    )

    return {"run_id": str(run.id), "status": run.status}


@app.get("/profiling/runs/{run_id}")
def get_profiling_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.get(ProfileRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    result = None
    if run.status == "done":
        pr = db.query(ProfileResult).filter(ProfileResult.run_id == run.id).first()
        if pr:
            result = pr.summary

    return {
        "run_id": str(run.id),
        "status": run.status,
        "created_at": run.created_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "result": result,
    }


@app.get("/profiling/runs/{run_id}/download")
def download_artifact(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.get(ProfileRun, run_id)
    if not run or run.status != "done":
        raise HTTPException(status_code=404, detail="Run not found or not complete")

    pr = db.query(ProfileResult).filter(ProfileResult.run_id == run.id).first()
    if not pr or not pr.artifact_id:
        raise HTTPException(status_code=404, detail="No artifact for this run")

    artifact = db.get(Artifact, pr.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact record not found")

    client = get_minio()
    response = client.get_object(artifact.bucket, artifact.key)
    return StreamingResponse(
        response,
        media_type=artifact.content_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.name}"'},
    )
