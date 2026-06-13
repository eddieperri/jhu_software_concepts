import pytest
import psycopg
import load_data
import query_data

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
    
    # 3. Verify rows were added and constraints worked
    with psycopg.connect(conninfo=test_db) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants;")
            # Should be exactly 2 rows
            assert cur.fetchone()[0] == 2
            
            # Check that row 2 successfully sanitized the bad data to NULLs
            cur.execute("SELECT gpa, gre FROM applicants WHERE url = 'https://test.com/2';")
            bad_data_row = cur.fetchone()
            assert bad_data_row[0] is None # Bad GPA (4.1) becomes None
            assert bad_data_row[1] is None # Bad GRE ("abc") becomes None

    # 4. Test Idempotency (run it again)
    load_data.load_data(fake_json_data)
    
    # Verify count is STILL 2 (it didn't duplicate)
    with psycopg.connect(conninfo=test_db) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants;")
            assert cur.fetchone()[0] == 2

@pytest.mark.db
def test_simple_query_function(test_db, fake_json_data):
    """
    Test simple query function:
    - You should be able to query your data to return a dict with expected keys.
    """
    # Load data first so queries have something to hit
    load_data.load_data(fake_json_data)
    
    # Execute query logic
    metrics = query_data.get_metrics()
    
    # Verify it returns a dictionary with the required keys
    assert isinstance(metrics, dict)
    expected_keys = ['q1', 'q2', 'q3_gpa', 'q3_gre', 'q3_grev', 'q3_greaw', 
                     'q4', 'q5', 'q6', 'q7', 'q8', 'q9_raw', 'q10', 'q11']
                     
    for key in expected_keys:
        assert key in metrics