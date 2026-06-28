"""
Pytest suite for verifying database operations.
Tests schema constraints, data loading idempotency, and query functionality.
"""

import os
import json
from unittest.mock import MagicMock

import pytest
import psycopg

from db import load_data
from etl import query_data
import consumer

@pytest.mark.db
def test_load_data_and_constraints(test_db, fake_json_data):
    """
    Test database writes:
    - Target table starts empty.
    - After load, new rows exist with non-null fields.
    - Idempotency: Duplicate pulls do not duplicate rows.
    """
    # 1. Verify table is initially empty
    with psycopg.connect(conninfo=test_db) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants;")
            assert cur.fetchone()[0] == 0
            
    # 2. Run the load script using our fake JSON
    load_data.load_data(fake_json_data)
    
    # 3. Verify rows were added and constraints worked (Expecting 1 record based on new fixture)
    with psycopg.connect(conninfo=test_db) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants;")
            assert cur.fetchone()[0] == 1

    # 4. Test idempotency (run it again!)
    load_data.load_data(fake_json_data)
        
    with psycopg.connect(conninfo=test_db) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants;")
            # Should still be exactly 1 record
            assert cur.fetchone()[0] == 1

@pytest.mark.db
def test_simple_query_function(test_db, fake_json_data):
    """
    Test simple query function returns a dict with expected keys.
    """
    load_data.load_data(fake_json_data)
    metrics = query_data.get_metrics()
    
    assert isinstance(metrics, dict)
    expected_keys = ['q1', 'q2', 'q3_gpa', 'q3_gre', 'q3_grev', 'q3_greaw', 
                     'q4', 'q5', 'q6', 'q7', 'q8', 'q9_raw', 'q10', 'q11']
                     
    for key in expected_keys:
        assert key in metrics


def test_parse_added_date_invalid_values():
    """Cover the worker date parsing error path."""
    assert consumer._parse_added_date('') is None
    assert consumer._parse_added_date(None) is None
    assert consumer._parse_added_date('Added on BadDate') is None


def test_consumer_scrape_handler_database_branches(monkeypatch, test_db):
    """Cover worker branches for missing JSON and empty scrape results."""
    monkeypatch.setattr(consumer, 'scrape_data', lambda total_pages=2: None)
    monkeypatch.setattr(consumer.os.path, 'exists', lambda path: False)

    with psycopg.connect(conninfo=test_db) as conn:
        consumer.handle_scrape_new_data(conn, {})

    monkeypatch.setattr(consumer.os.path, 'exists', lambda path: True)
    fake_empty = json.dumps([])
    mock_open = MagicMock()
    mock_open.return_value.__enter__.return_value.read.return_value = fake_empty
    monkeypatch.setattr('builtins.open', mock_open)

    with psycopg.connect(conninfo=test_db) as conn:
        consumer.handle_scrape_new_data(conn, {})


def test_consumer_scrape_handler_invalid_watermark(monkeypatch, test_db):
    """Cover the worker branch where watermark parsing fails and no update occurs."""
    monkeypatch.setattr(consumer, 'scrape_data', lambda total_pages=2: None)
    monkeypatch.setattr(os.path, 'exists', lambda path: True)

    with psycopg.connect(conninfo=test_db) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE ingestion_watermarks SET last_seen = 'BadDate' WHERE source = 'gradcafe_scraper';")
        conn.commit()

    invalid_record = [{
        "program": "Test", "uGPA": "3.5", "GRE Quant": "160",
        "GRE Verbal": "155", "GRE AW": "4.0", "date added": "Added on BadDate",
        "result url": "https://test.com/invalid", "status": "Accepted", "term": "Fall 2026",
        "I/International": "American", "Degree": "Masters",
        "llm-generated-program": "Computer Science",
        "llm-generated-university": "Johns Hopkins University"
    }]
    fake_json = json.dumps(invalid_record)
    mock_open = MagicMock()
    mock_open.return_value.__enter__.return_value.read.return_value = fake_json
    monkeypatch.setattr('builtins.open', mock_open)

    with psycopg.connect(conninfo=test_db) as conn:
        consumer.handle_scrape_new_data(conn, {})


def test_consumer_scrape_handler_invalid_watermark_directly(monkeypatch):
    """Cover the consumer watermark ValueError path with a dummy DB cursor."""
    class DummyCursor:
        def __init__(self):
            self.calls = 0
            self.data = [
                ("BadDate",),
                (None,),
            ]

        def execute(self, query, *args, **kwargs):
            self.calls += 1

        def fetchone(self):
            return self.data[min(self.calls - 1, len(self.data) - 1)]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyConn:
        def cursor(self):
            return DummyCursor()

    monkeypatch.setattr(consumer, 'scrape_data', lambda total_pages=2: None)
    monkeypatch.setattr(consumer.os.path, 'exists', lambda path: False)

    consumer.handle_scrape_new_data(DummyConn(), {})


def test_query_data_helpers_and_metrics(monkeypatch):
    """Cover query_data helper branches and fallback metrics generation."""
    class DummyCursor:
        def __init__(self):
            self.call = 0

        def execute(self, query, *args, **kwargs):
            self.call += 1

        def fetchone(self):
            responses = [
                (1,), (0.0,), (0.0, 0.0, 0.0, 0.0), (0.0,), (0.0,), (1,),
                (1,), (1,)
            ]
            return responses[min(self.call - 1, len(responses) - 1)]

        def fetchall(self):
            return [("Dummy", 1)]

    cursor = DummyCursor()
    metrics = {}
    query_data.get_demographic_metrics(cursor, metrics)
    query_data.get_academic_metrics(cursor, metrics)
    query_data.get_program_metrics(cursor, metrics)

    assert metrics['q1'] == 1
    assert metrics['q2'] == 0.0
    assert metrics['q10'] == [("Dummy", 1)]
    assert metrics['q11'] == [("Dummy", 1)]

    class DummyCursor:
        def __init__(self):
            self.call = 0

        def execute(self, query, *args, **kwargs):
            self.call += 1

        def fetchone(self):
            responses = [
                (1,), (0.0,), (0.0, 0.0, 0.0, 0.0), (0.0,), (0.0,), (1,),
                (1,), (1,)
            ]
            return responses[min(self.call - 1, len(responses) - 1)]

        def fetchall(self):
            return [("Dummy", 1)]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    cursor = DummyCursor()
    metrics = {}
    query_data.get_demographic_metrics(cursor, metrics)
    query_data.get_academic_metrics(cursor, metrics)
    query_data.get_program_metrics(cursor, metrics)

    assert metrics['q1'] == 1
    assert metrics['q2'] == 0.0
    assert metrics['q10'] == [("Dummy", 1)]
    assert metrics['q11'] == [("Dummy", 1)]

    class JsonCursor(DummyCursor):
        def __init__(self):
            super().__init__()
            self.fetchone_calls = 0

        def fetchone(self):
            self.fetchone_calls += 1
            if self.fetchone_calls == 1:
                return ('{"q1": 1}',)
            return super().fetchone()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    cursor = JsonCursor()

    class DummyConn:
        def cursor(self):
            return cursor

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(query_data, 'get_db_connection', lambda: DummyConn())
    json_metrics = query_data.get_metrics()
    assert isinstance(json_metrics, dict)
    assert json_metrics['q1'] == 1


def test_query_data_get_metrics_undefined_table(monkeypatch):
    """Cover the UndefinedTable fallback branch in get_metrics."""
    class DummyCursor:
        def __init__(self):
            self.execute_count = 0
            self.fetchone_count = 0
            self.responses = [
                (1,), (0.0,), (0.0, 0.0, 0.0, 0.0), (0.0,), (0.0,),
                (1,), (1,), (1,)
            ]

        def execute(self, query, *args, **kwargs):
            self.execute_count += 1
            if self.execute_count == 1:
                raise query_data.psycopg.errors.UndefinedTable('no table')

        def fetchone(self):
            self.fetchone_count += 1
            return self.responses[min(self.fetchone_count - 1, len(self.responses) - 1)]

        def fetchall(self):
            return [("Dummy", 1)]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyConn:
        def __init__(self):
            self.cursor_obj = DummyCursor()

        def cursor(self):
            return self.cursor_obj

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(query_data, 'get_db_connection', lambda: DummyConn())
    result = query_data.get_metrics()
    assert isinstance(result, dict)
    assert result['q1'] == 1
    assert result['q10'] == [("Dummy", 1)]



def test_query_data_helper_functions_direct_coverage():
    """Execute helper metric functions to cover safe SQL composition paths."""
    class DummyCursor:
        def __init__(self):
            self.query_index = 0

        def execute(self, query, *args, **kwargs):
            self.query_index += 1

        def fetchone(self):
            responses = [
                (1,),
                (0.0,),
                (0.0, 0.0, 0.0, 0.0),
                (0.0,),
                (0.0,),
                (1,),
                (1,),
                (1,)
            ]
            return responses[min(self.query_index - 1, len(responses) - 1)]

        def fetchall(self):
            return [("Dummy", 1)]

    cursor = DummyCursor()
    metrics = {}
    query_data.get_demographic_metrics(cursor, metrics)
    query_data.get_academic_metrics(cursor, metrics)
    query_data.get_program_metrics(cursor, metrics)

    assert metrics['q1'] == 1
    assert metrics['q2'] == 0.0
    assert metrics['q10'] == [("Dummy", 1)]
    assert metrics['q11'] == [("Dummy", 1)]


def test_query_data_cache_string_payload(monkeypatch):
    """Cover the JSON string payload branch in get_metrics."""
    class DummyCursor:
        def execute(self, query, *args, **kwargs):
            pass

        def fetchone(self):
            return ('{"q1": 42}',)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyConn:
        def cursor(self):
            return DummyCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(query_data, 'get_db_connection', lambda: DummyConn())
    metrics = query_data.get_metrics()
    assert metrics['q1'] == 42


def test_consumer_scrape_handler_invalid_watermark_value_error(monkeypatch):
    """Cover the worker watermark ValueError branch."""
    class DummyCursor:
        def __init__(self):
            self.calls = 0

        def execute(self, query, *args, **kwargs):
            self.calls += 1

        def fetchone(self):
            if self.calls == 1:
                return ("BadDate",)
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyConn:
        def cursor(self):
            return DummyCursor()

    monkeypatch.setattr(consumer, 'scrape_data', lambda total_pages=2: None)
    monkeypatch.setattr(consumer.os.path, 'exists', lambda path: False)

    consumer.handle_scrape_new_data(DummyConn(), {})
