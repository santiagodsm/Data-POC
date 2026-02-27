"""
Seed the database with sample projects, subfolders, threads, and turns.
Run via: docker exec dc_api python /scripts/seed.py
"""
import os
import sys
import psycopg2

conn = psycopg2.connect(
    host=os.environ.get("PGHOST", "db"),
    port=int(os.environ.get("PGPORT", 5432)),
    dbname=os.environ["PGDATABASE"],
    user=os.environ["PGUSER"],
    password=os.environ["PGPASSWORD"],
)

with conn.cursor() as cur:
    # ── Projects ───────────────────────────────────────────────────────────
    cur.execute("""
        INSERT INTO project (name, description) VALUES
          ('Sales Analytics',   'Monthly sales data from CRM and ERP systems'),
          ('HR Dataset',        'Employee headcount and payroll exports'),
          ('Product Catalogue', 'SKU inventory and pricing sheets')
        ON CONFLICT DO NOTHING
        RETURNING id, name
    """)
    projects = cur.fetchall()
    print(f"Inserted {len(projects)} projects")

    if not projects:
        print("Projects already seeded — nothing to do.")
        conn.close()
        sys.exit(0)

    p_sales, p_hr, p_product = [p[0] for p in projects]

    # ── Subfolders ─────────────────────────────────────────────────────────
    cur.execute("""
        INSERT INTO subfolder (project_id, name, path) VALUES
          (%s, 'Q1 2025', 'sales/q1_2025'),
          (%s, 'Q2 2025', 'sales/q2_2025'),
          (%s, 'Headcount', 'hr/headcount'),
          (%s, 'Payroll',   'hr/payroll'),
          (%s, 'Electronics', 'catalogue/electronics'),
          (%s, 'Apparel',     'catalogue/apparel')
    """, (p_sales, p_sales, p_hr, p_hr, p_product, p_product))
    print("Inserted 6 subfolders")

    # ── Threads + turns ────────────────────────────────────────────────────
    cur.execute("""
        INSERT INTO thread (project_id, title) VALUES (%s, %s) RETURNING id
    """, (p_sales, "Revenue trend questions"))
    thread_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO turn (thread_id, role, content) VALUES
          (%s, 'user',      'What was total revenue in Q1?'),
          (%s, 'assistant', 'Based on the Q1 2025 data, total revenue was $4.2M across 1,840 orders.'),
          (%s, 'user',      'How does that compare to Q2?'),
          (%s, 'assistant', 'Q2 revenue was $5.1M, a 21%% increase driven by the spring promotion.')
    """, (thread_id, thread_id, thread_id, thread_id))
    print("Inserted 1 thread with 4 turns")

conn.commit()
conn.close()
print("✓ Seed complete")
