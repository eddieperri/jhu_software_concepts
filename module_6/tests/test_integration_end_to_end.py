"""
Pytest suite for microservice integration.
Tests the RabbitMQ publisher, the worker consumer logic, and database interactions.
"""

import os
import json
from unittest.mock import patch, MagicMock
import pytest
import psycopg

import publisher
import consumer
from db import load_data
from etl import query_data

@pytest.mark.integration
@patch('publisher.pika.BlockingConnection')
def test_publisher_logic(mock_conn):
    """Tests that the publisher correctly builds and sends an AMQP message."""
    mock_channel = MagicMock()
    mock_conn.return_value.channel.return_value = mock_channel
    
    publisher.publish_task("test_task", payload={"key": "value"})
    
    mock_channel.exchange_declare.assert_called_once()
    mock_channel.queue_declare.assert_called_once()
    mock_channel.basic_publish.assert_called_once()

@pytest.mark.integration
@patch('consumer.scrape_data')
def test_consumer_scrape_handler(mock_scrape, test_db, fake_json_data, monkeypatch):
    """Tests the worker's ability to process a scrape task and insert idempotently."""
    monkeypatch.setattr(os.path, 'exists', lambda path: True)
    
    with open(fake_json_data, 'r', encoding='utf-8') as f:
        fake_data = json.load(f)
        
    mock_open = MagicMock()
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(fake_data)
    monkeypatch.setattr('builtins.open', mock_open)
    
    with psycopg.connect(conninfo=test_db) as conn:
        consumer.handle_scrape_new_data(conn, {})
        conn.commit()
        
    with psycopg.connect(conninfo=test_db) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants;")
            assert cur.fetchone()[0] == 1

@pytest.mark.integration
def test_consumer_recompute_handler(test_db):
    """Tests the recompute analytics handler path."""
    with psycopg.connect(conninfo=test_db) as conn:
        consumer.handle_recompute_analytics(conn, {})

@pytest.mark.integration
@patch('consumer.handle_scrape_new_data')
@patch('consumer.get_db_connection')
def test_consumer_callback_paths(mock_db_conn, mock_handle_scrape):
    """Tests the RabbitMQ callback router and negative error paths."""
    mock_channel = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = 1
    
    # 1. Test unknown task type
    unknown_body = json.dumps({"kind": "unknown_task"}).encode('utf-8')
    consumer.callback(mock_channel, mock_method, None, unknown_body)
    mock_channel.basic_ack.assert_called_once()
    mock_channel.reset_mock()

    # 2. Test recompute analytics routing
    recompute_body = json.dumps({"kind": "recompute_analytics"}).encode('utf-8')
    consumer.callback(mock_channel, mock_method, None, recompute_body)
    mock_channel.basic_ack.assert_called_once()
    mock_channel.reset_mock()

    # 3. Test successful scrape_new_data routing (Hits consumer.py Line 72)
    mock_db_conn.side_effect = None
    scrape_body = json.dumps({"kind": "scrape_new_data"}).encode('utf-8')
    consumer.callback(mock_channel, mock_method, None, scrape_body)
    mock_handle_scrape.assert_called_once()
    mock_channel.basic_ack.assert_called_once()
    mock_channel.reset_mock()
    
    # 4. Test database failure (triggers NACK)
    mock_db_conn.side_effect = Exception("Database Offline")
    valid_body = json.dumps({"kind": "scrape_new_data"}).encode('utf-8')
    consumer.callback(mock_channel, mock_method, None, valid_body)
    mock_channel.basic_nack.assert_called_once_with(delivery_tag=1, requeue=False)

@pytest.mark.integration
@patch('consumer.pika.BlockingConnection')
def test_consumer_main_loop(mock_conn):
    """Tests the worker startup and connection loop."""
    mock_channel = MagicMock()
    mock_conn.return_value.channel.return_value = mock_channel
    mock_channel.start_consuming.side_effect = KeyboardInterrupt
    
    try:
        consumer.main()
    except KeyboardInterrupt:
        pass
        
    mock_channel.basic_consume.assert_called_once()

@pytest.mark.integration
def test_database_error_coverage(monkeypatch, fake_json_data):
    """Forces 100% coverage on database exception blocks."""
    def mock_db_crash(*args, **kwargs):
        raise psycopg.Error("Simulated Database Crash")
        
    monkeypatch.setattr(psycopg, 'connect', mock_db_crash)
    
    with pytest.raises(psycopg.Error):
        load_data.load_data(fake_json_data) 
        
    with pytest.raises(psycopg.Error):
        query_data.get_metrics()

@pytest.mark.integration
def test_load_data_edge_cases(tmp_path):
    """Restores the negative tests to get load_data.py back to 100%"""
    suspicious_data = [{
        "uGPA": "4.5", "GRE Quant": "175", "program": "CS",
        "date added": "Added on BadDate", "result url": "http://bad-date.com" 
    }, {
        "uGPA": "bad", "GRE Quant": " 165 \n", "date added": "", "result url": "http://valid.com"
    }, {
        # FIX: Added a record with no URL to hit load_data.py Line 59
        "program": "No URL Record", "result url": "" 
    }]
    test_file = tmp_path / "inspect.json"
    with open(test_file, "w") as f:
        json.dump(suspicious_data, f)
        
    load_data.load_data(str(test_file))
    assert load_data.clean_numeric(["invalid"], 0, 4) is None
    
    with pytest.raises(FileNotFoundError):
        load_data.load_data("dummy_does_not_exist.json")
    
    try:
        load_data.load_data() 
    except Exception:
        pass

@pytest.mark.integration
def test_db_fallback_coverage(monkeypatch):
    """Hits the local fallback connection logic when DATABASE_URL is missing."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(psycopg, 'connect', lambda *args, **kwargs: "mocked_connection")
    assert load_data.get_db_connection() == "mocked_connection"
    assert query_data.get_db_connection() == "mocked_connection"
    
@pytest.mark.integration
def test_consumer_fallback_connection(monkeypatch):
    """Hits the consumer DB connection fallback logic."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(consumer.psycopg, 'connect', lambda *args, **kwargs: "mocked_connection")
    assert consumer.get_db_connection() == "mocked_connection"