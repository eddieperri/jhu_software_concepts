import os
import json
from datetime import datetime, timezone
import pika

EXCHANGE = "tasks"
QUEUE = "tasks_q"
ROUTING_KEY = "tasks"

def _open_channel():
    """Opens a connection and channel to RabbitMQ."""
    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    params = pika.URLParameters(url)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    
    # Durable exchange & queue; bind once per process (idempotent)
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    ch.queue_declare(queue=QUEUE, durable=True)
    ch.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=ROUTING_KEY)
    
    return conn, ch

def publish_task(kind: str, payload: dict | None = None, headers: dict | None = None) -> None:
    """Builds a JSON message and publishes it to the tasks queue."""
    body = json.dumps(
        {"kind": kind, "ts": datetime.now(timezone.utc).isoformat(), "payload": payload or {}},
        separators=(",", ":")
    ).encode("utf-8")
    
    conn, ch = _open_channel()
    try:
        ch.basic_publish(
            exchange=EXCHANGE,
            routing_key=ROUTING_KEY,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2, # Persistent message
                headers=headers or {}
            ),
            mandatory=False,
        )
    finally:
        conn.close()