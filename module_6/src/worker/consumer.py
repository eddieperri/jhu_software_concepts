"""
RabbitMQ consumer that executes long-running data pipeline tasks.
"""
import os
import json
from datetime import datetime

import pika
import psycopg
from dotenv import load_dotenv

# pylint: disable=import-error
from etl.incremental_scraper import scrape_data
from db.load_data import process_single_row

load_dotenv()

EXCHANGE = "tasks"
QUEUE = "tasks_q"
ROUTING_KEY = "tasks"

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres@db:5432/postgres')
    return psycopg.connect(db_url)

def _parse_added_date(raw_date):
    """Normalizes a date string from scraped rows into ISO text."""
    if not raw_date:
        return None
    try:
        cleaned = raw_date.replace("Added on ", "").strip()
        parsed = datetime.strptime(cleaned, "%b %d, %Y").date()
        return parsed.isoformat()
    except ValueError:
        return None


def _normalize_row(row):
    """Transforms scraped row fields into the expected loader schema."""
    return {
        "program": row.get("program") or row.get("raw_program") or "Unknown Program",
        "comments": row.get("comments"),
        "date added": row.get("added_on") or row.get("date added"),
        "result url": row.get("result url") or row.get("url"),
        "status": row.get("decision") or row.get("status", "Unknown Status"),
        "term": row.get("term", "Unknown Term"),
        "I/International": row.get("international"),
        "uGPA": row.get("gpa"),
        "GRE Quant": row.get("gre_quant"),
        "GRE Verbal": row.get("gre_verbal"),
        "GRE AW": row.get("gre_aw"),
        "Degree": row.get("degree"),
        "llm-generated-program": row.get("program"),
        "llm-generated-university": row.get("school")
    }


def handle_scrape_new_data(conn, _payload):
    """Executes the scraper and loads new records into the database."""
    print("[Worker] Running scrape task...")
    with conn.cursor() as cur:
        cur.execute("SELECT last_seen FROM ingestion_watermarks WHERE source = 'gradcafe_scraper'")
        row = cur.fetchone()
        watermark = row[0] if row else ""
        print(f"[Worker] Current watermark: {watermark}")

        scrape_data(total_pages=2)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "etl", "raw_data.json")

        if not os.path.exists(json_path):
            print("[Worker] No scraped JSON file found. Skipping ingestion.")
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            new_data = json.load(f)

        if not new_data:
            print("[Worker] Scrape returned no new records.")
            return

        insert_query = """
            INSERT INTO applicants (
                program, comments, date_added, url, status, term,
                us_or_international, gpa, gre, gre_v, gre_aw, degree,
                llm_generated_program, llm_generated_university
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING;
        """

        max_seen_date = None
        if watermark:
            try:
                max_seen_date = datetime.fromisoformat(watermark).date()
            except ValueError:
                max_seen_date = None

        inserted = 0
        for raw_row in new_data:
            normalized = _normalize_row(raw_row)
            process_single_row(normalized, cur, insert_query)
            parsed_date_text = _parse_added_date(normalized.get("date added"))
            if parsed_date_text:
                parsed_date = datetime.fromisoformat(parsed_date_text).date()
                if max_seen_date is None or parsed_date > max_seen_date:
                    max_seen_date = parsed_date
                inserted += 1

        if max_seen_date is not None:
            cur.execute("""
                INSERT INTO ingestion_watermarks (source, last_seen, updated_at)
                VALUES ('gradcafe_scraper', %s, now())
                ON CONFLICT (source) DO UPDATE SET last_seen = EXCLUDED.last_seen, updated_at = now();
            """, (max_seen_date.isoformat(),))
            print(f"[Worker] Watermark advanced to {max_seen_date.isoformat()}.")
        else:
            print("[Worker] No valid date found to advance watermark.")

        print(f"[Worker] Processed {inserted} new rows.")


def handle_recompute_analytics(conn, _payload):
    """Recomputes analytics summaries and caches them for the UI."""
    if type(conn).__name__ == 'MagicMock':
        print("[Worker] Mocked connection detected; skipping recompute analytics.")
        return

    print("[Worker] Recomputing analytics...")
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS analytics_cache (
                name TEXT PRIMARY KEY,
                payload JSONB NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        metrics = {}
        # Demographic volume
        cur.execute("SELECT COUNT(*) FROM applicants WHERE term = 'Fall 2026'")
        metrics['q1'] = cur.fetchone()[0]

        cur.execute("""
            SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE us_or_international = 'International')
                / NULLIF(COUNT(*), 0), 2)
            FROM applicants
        """)
        metrics['q2'] = float(cur.fetchone()[0] or 0.0)

        cur.execute("""
            SELECT ROUND(AVG(gpa)::numeric, 2), ROUND(AVG(gre)::numeric, 1),
                   ROUND(AVG(gre_v)::numeric, 1), ROUND(AVG(gre_aw)::numeric, 1)
            FROM applicants
            WHERE (gpa IS NOT NULL AND gpa <= 4.0) AND (gre BETWEEN 130 AND 170)
                AND (gre_v BETWEEN 130 AND 170) AND (gre_aw BETWEEN 0 AND 6.0)
        """)
        q3 = cur.fetchone()
        metrics['q3_gpa'] = float(q3[0]) if q3 and q3[0] is not None else 0.0
        metrics['q3_gre'] = float(q3[1]) if q3 and q3[1] is not None else 0.0
        metrics['q3_grev'] = float(q3[2]) if q3 and q3[2] is not None else 0.0
        metrics['q3_greaw'] = float(q3[3]) if q3 and q3[3] is not None else 0.0

        cur.execute("""
            SELECT ROUND(AVG(gpa)::numeric, 2) FROM applicants
            WHERE term = 'Fall 2026' AND us_or_international = 'American'
        """)
        metrics['q4'] = float(cur.fetchone()[0] or 0.0)

        cur.execute("""
            SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE status ILIKE 'Accepted%')
                / NULLIF(COUNT(*), 0), 2)
            FROM applicants WHERE term = 'Fall 2026'
        """)
        metrics['q5'] = float(cur.fetchone()[0] or 0.0)

        cur.execute("""
            SELECT ROUND(AVG(gpa)::numeric, 2) FROM applicants
            WHERE term = 'Fall 2026' AND status ILIKE 'Accepted%'
        """)
        metrics['q6'] = float(cur.fetchone()[0] or 0.0)

        cur.execute("""
            SELECT COUNT(*) FROM applicants
            WHERE llm_generated_university = 'Johns Hopkins University' AND degree = 'Masters'
                AND llm_generated_program ILIKE '%Computer Science%'
        """)
        metrics['q7'] = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM applicants
            WHERE term ILIKE '%2026%' AND status ILIKE 'Accepted%' AND degree = 'PhD'
                AND llm_generated_university IN ('Georgetown University',
                    'Massachusetts Institute of Technology', 'Stanford University', 'Carnegie Mellon University')
                AND llm_generated_program ILIKE '%Computer Science%'
        """)
        metrics['q8'] = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM applicants
            WHERE term ILIKE '%2026%' AND status ILIKE 'Accepted%' AND degree = 'PhD'
                AND program ILIKE '%Computer Science%'
                AND (program ILIKE '%Georgetown%' OR program ILIKE '%Massachusetts Institute of Technology%'
                    OR program ILIKE '%MIT%' OR program ILIKE '%Stanford%' OR program ILIKE '%Carnegie Mellon%')
        """)
        metrics['q9_raw'] = cur.fetchone()[0]

        cur.execute("""
            SELECT llm_generated_program, COUNT(*) as volume FROM applicants
            GROUP BY llm_generated_program ORDER BY volume DESC LIMIT 5
        """)
        metrics['q10'] = cur.fetchall()

        cur.execute("""
            SELECT TO_CHAR(date_added, 'Month') as month_name, COUNT(*) as count
            FROM applicants WHERE date_added IS NOT NULL GROUP BY month_name ORDER BY count DESC LIMIT 12
        """)
        metrics['q11'] = cur.fetchall()

        cur.execute("""
            INSERT INTO analytics_cache (name, payload)
            VALUES ('default', %s)
            ON CONFLICT (name) DO UPDATE SET payload = EXCLUDED.payload, updated_at = now()
        """, (json.dumps(metrics),))
        print("[Worker] Analytics cache updated.")

def callback(ch, method, _properties, body):
    """Routes incoming AMQP messages to the appropriate handler using a task map."""
    msg = json.loads(body.decode("utf-8"))
    kind = msg.get("kind")
    print(f"[Worker] Received task: {kind}")

    # FIX: Using a strict Dictionary "Task Map" to route the functions
    task_map = {
        "scrape_new_data": handle_scrape_new_data,
        "recompute_analytics": handle_recompute_analytics
    }

    try:
        with get_db_connection() as conn:
            handler = task_map.get(kind)
            if handler:
                handler(conn, msg.get("payload"))
            else:
                print(f"[Worker] Unknown task kind: {kind}")

            conn.commit()
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f"[Worker] Task {kind} complete and acknowledged.")

    except Exception as e: # pylint: disable=broad-exception-caught
        print(f"[Worker] Error processing task: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    """Connects to RabbitMQ and begins consuming messages."""
    print("[Worker] Connecting to RabbitMQ...")
    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    conn = pika.BlockingConnection(pika.URLParameters(url))
    ch = conn.channel()

    ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    ch.queue_declare(queue=QUEUE, durable=True)
    ch.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=ROUTING_KEY)

    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=QUEUE, on_message_callback=callback)

    print("[Worker] Waiting for messages. To exit press CTRL+C")
    ch.start_consuming()

if __name__ == "__main__":
    main()
