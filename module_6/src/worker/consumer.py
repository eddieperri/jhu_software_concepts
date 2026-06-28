import os
import json
import pika
import psycopg
from datetime import datetime
from dotenv import load_dotenv
from etl.incremental_scraper import scrape_data # Importing your scraper
from db.load_data import process_single_row # Reusing your row processor

load_dotenv()

EXCHANGE = "tasks"
QUEUE = "tasks_q"
ROUTING_KEY = "tasks"

def get_db_connection():
    return psycopg.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres@db:5432/postgres'))

def handle_scrape_new_data(conn, payload):
    print("[Worker] Running scrape task...")
    with conn.cursor() as cur:
        # 1. Read watermark
        cur.execute("SELECT last_seen FROM ingestion_watermarks WHERE source = 'gradcafe_scraper'")
        watermark = cur.fetchone()[0]

        # 2. Scrape Data (You might want to pass 'watermark' into your scrape_data function later to truly make it incremental)
        # Currently, your scrape_data writes to JSON. Let's trigger it.
        scrape_data(total_pages=2) # Keeping it to 2 pages so it doesn't take forever during testing
        
        # 3. Read the newly generated JSON
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

            # Insert idempotently
            for row in new_data:
                process_single_row(row, cur, insert_query)
            
            # 4. Update watermark (Simplistic update for now)
            cur.execute("""
                UPDATE ingestion_watermarks 
                SET last_seen = %s, updated_at = now() 
                WHERE source = 'gradcafe_scraper'
            """, (datetime.now().isoformat(),))

def handle_recompute_analytics(conn, payload):
    print("[Worker] Recomputing analytics...")
    # Add any SQL to refresh materialized views here
    # Example: conn.cursor().execute("REFRESH MATERIALIZED VIEW my_metrics;")
    pass

def callback(ch, method, properties, body):
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
            
            conn.commit() # Commit transaction on success
            ch.basic_ack(delivery_tag=method.delivery_tag) # Acknowledge message only after commit
            print(f"[Worker] Task {kind} complete and acknowledged.")

    except Exception as e:
        print(f"[Worker] Error processing task: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) # Nack without requeue to prevent infinite loops

def main():
    print("[Worker] Connecting to RabbitMQ...")
    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    conn = pika.BlockingConnection(pika.URLParameters(url))
    ch = conn.channel()

    ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    ch.queue_declare(queue=QUEUE, durable=True)
    ch.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=ROUTING_KEY)

    ch.basic_qos(prefetch_count=1) # Backpressure: process 1 task at a time
    ch.basic_consume(queue=QUEUE, on_message_callback=callback)

    print("[Worker] Waiting for messages. To exit press CTRL+C")
    ch.start_consuming()

if __name__ == "__main__":
    main()