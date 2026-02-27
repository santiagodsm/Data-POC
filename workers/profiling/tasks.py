import json
import os
import uuid
from io import BytesIO

import psycopg2
import psycopg2.extras
from minio import Minio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db_conn():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "db"),
        port=int(os.environ.get("PGPORT", 5432)),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )


def _minio_client():
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    secure = endpoint.startswith("https")
    host = endpoint.replace("https://", "").replace("http://", "")
    return Minio(
        host,
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=secure,
    )


def _validate_table(cur, table: str):
    cur.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    )
    if not cur.fetchone():
        raise ValueError(f"Table '{table}' not found in public schema")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def _compute_stats(conn, table: str) -> dict:
    stats = {"table": table, "columns": []}

    with conn.cursor() as cur:
        _validate_table(cur, table)

        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        row_count = cur.fetchone()[0]
        stats["row_count"] = row_count

        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        columns = cur.fetchall()

        for col_name, data_type in columns:
            cur.execute(
                f"""
                SELECT
                    COUNT(*) FILTER (WHERE "{col_name}" IS NULL) AS null_count,
                    COUNT(DISTINCT "{col_name}") AS distinct_count
                FROM "{table}"
                """,
            )
            null_count, distinct_count = cur.fetchone()
            stats["columns"].append({
                "name": col_name,
                "type": data_type,
                "null_count": null_count,
                "null_pct": round(null_count / row_count * 100, 2) if row_count > 0 else 0,
                "distinct_count": distinct_count,
            })

    return stats


# ---------------------------------------------------------------------------
# Task entry point (called by RQ)
# ---------------------------------------------------------------------------

def run_profile(run_id: str, table: str):
    conn = _db_conn()
    try:
        # Mark running
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE profile_run SET status = 'running' WHERE id = %s",
                (run_id,),
            )
        conn.commit()

        # Compute stats
        summary = _compute_stats(conn, table)

        # Upload JSON artifact to MinIO
        bucket = os.environ.get("MINIO_BUCKET_ARTIFACTS", "artifacts")
        artifact_key = f"profiling/{run_id}/{table}.json"
        payload = json.dumps(summary, default=str, indent=2).encode()

        client = _minio_client()
        client.put_object(
            bucket,
            artifact_key,
            BytesIO(payload),
            length=len(payload),
            content_type="application/json",
        )

        # Persist artifact + result rows, mark done
        artifact_id = str(uuid.uuid4())
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO artifact (id, name, bucket, key, content_type, size_bytes)
                VALUES (%s, %s, %s, %s, 'application/json', %s)
                """,
                (artifact_id, f"{table}_profile.json", bucket, artifact_key, len(payload)),
            )
            cur.execute(
                """
                INSERT INTO profile_result (run_id, artifact_id, summary)
                VALUES (%s, %s, %s)
                """,
                (run_id, artifact_id, psycopg2.extras.Json(summary)),
            )
            cur.execute(
                "UPDATE profile_run SET status = 'done', finished_at = now() WHERE id = %s",
                (run_id,),
            )
        conn.commit()

    except Exception:
        # Best-effort: mark failed
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE profile_run SET status = 'failed', finished_at = now() WHERE id = %s",
                    (run_id,),
                )
            conn.commit()
        except Exception:
            pass
        raise
    finally:
        conn.close()
