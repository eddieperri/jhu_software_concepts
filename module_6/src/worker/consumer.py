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

def handle_scrape_new_data(conn, _payload):
    """Executes the scraper and loads new records into the database."""
    print("[Worker] Running scrape task...")
    with conn.cursor() as cur:
        cur.execute("SELECT last_seen FROM ingestion_watermarks WHERE source = 'gradcafe_scraper'")
        watermark = cur.fetchone()[0]
        print(f"[Worker] Current watermark: {watermark}")

        scrape_data(total_pages=2)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "etl", "raw_data.json")

        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                new_data = json.load(f)

            insert_query = psycopg.sql.SQL("""
                INSERT INTO applicants (
                    program, comments, date_added, url, status, term,
                    us_or_international, gpa, gre, gre_v, gre_aw, degree,
                    llm_generated_program, llm_generated_university
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING;
            """)

            for row in new_data:
                process_single_row(row, cur, insert_query)

            cur.execute("""
                UPDATE ingestion_watermarks 
                SET last_seen = %s, updated_at = now() 
                WHERE source = 'gradcafe_scraper'
            """, (datetime.now().isoformat(),))

def handle_recompute_analytics(_conn, _payload):
    """Refreshes any materialized views or summary tables."""
    print("[Worker] Recomputing analytics...")

def callback(ch, method, _properties, body):
    """Routes incoming AMQP messages to the appropriate handler."""
    msg = json.loads(body.decode("utf-8"))
    kind = msg.get("kind")
    print(f"[Worker] Received task: {kind}")

    try:
        with get_db_connection() as conn:
            if kind == "scrape_new_data":
                handle_scrape_new_data(conn, msg.get("payload"))
            elif kind == "recompute_analytics":
                handle_recompute_analytics(conn, msg.get("payload"))
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
