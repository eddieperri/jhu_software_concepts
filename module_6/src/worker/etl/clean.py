"""Utilities for cleaning raw GradCafe JSON into a standardized format.

This module provides small helpers to load/save JSON files and a
`clean_data` entrypoint that formats raw scraped records and invokes the
local LLM standardizer to produce JSONL outputs.
"""

# Module is small; allow a few extra locals in the main cleaner function.
# pylint: disable=too-many-locals

import json
import os
import subprocess
import sys


def load_data(filepath):
    """Load JSON from ``filepath`` returning an empty list if missing."""
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_data(data, filepath):
    """Write `data` as pretty JSON to ``filepath"""
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def clean_data():
    """Discover new raw records, standardize them, and append LLM results.

    The function:
    - loads raw and existing cleaned data
    - finds new records by URL
    - writes a temporary input JSON for the LLM
    - runs the local LLM runner script
    - reads JSONL output and appends to the cleaned dataset
    - removes temporary files
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_path, clean_path, llm_dir, temp_in, temp_out, app_script = _get_paths(
        script_dir
    )

    raw_data = load_data(raw_path)
    clean_data_existing = load_data(clean_path)

    # 1. Create a watchlist of URLs we have already processed through the LLM
    processed_urls = {record["result url"] for record in clean_data_existing}

    # 2. Filter: Only keep raw records whose URL is NOT in our clean list
    new_records = [r for r in raw_data if r.get("url") not in processed_urls]

    if not new_records:
        print("No new records to standardize. Database is up to date.")
        return

    print(f"Found {len(new_records)} new records to process.")

    # 3. Format only the NEW records
    formatted_data = _format_new_records(new_records)

    save_data(formatted_data, temp_in)

    # Trigger LLM (Same as before)
    env = os.environ.copy()
    env["N_THREADS"] = "2"
    cmd = [sys.executable, app_script, "--file", temp_in]
    subprocess.run(cmd, env=env, cwd=llm_dir, check=True)

    # 4. Append new results to existing cleaned file
    with open(temp_out, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                clean_data_existing.append(json.loads(line))

    save_data(clean_data_existing, clean_path)

    if os.path.exists(temp_in):
        os.remove(temp_in)
    if os.path.exists(temp_out):
        os.remove(temp_out)

    print(f"Success! {len(new_records)} records standardized and appended.")


if __name__ == "__main__":
    clean_data()


def _get_paths(base_dir: str):
    """Return common paths used by the cleaner as a tuple.

    Keeps `clean_data`'s local variable count smaller by grouping paths.
    """
    raw_path = os.path.join(base_dir, "raw_data.json")
    clean_path = os.path.join(base_dir, "applicant_data.json")
    llm_dir = os.path.join(base_dir, "llm_hosting")
    temp_in = os.path.join(llm_dir, "temp_in.json")
    temp_out = os.path.join(llm_dir, "temp_in.json.jsonl")
    app_script = os.path.join(llm_dir, "app.py")
    return raw_path, clean_path, llm_dir, temp_in, temp_out, app_script


def _format_new_records(new_records):
    """Format raw records into the cleaned shape expected by the LLM.

    Pulled out of ``clean_data`` to reduce local variable pressure there.
    """
    formatted = []
    for record in new_records:
        clean_record = {
            "program": record.get("raw_program"),
            "comments": record.get("comments"),
            "date added": f"Added on {record.get('added_on')}",
            "result url": record.get("url"),
            "status": record.get("decision"),
            "term": record.get("term"),
            "I/International": record.get("international"),
            "Degree": record.get("degree"),
            "raw_text_traceability": record.get("raw_program"),
        }
        if record.get("gpa"):
            clean_record["uGPA"] = record["gpa"]
        if record.get("gre_quant"):
            clean_record["GRE Quant"] = record["gre_quant"]
        if record.get("gre_verbal"):
            clean_record["GRE Verbal"] = record["gre_verbal"]
        if record.get("gre_aw"):
            clean_record["GRE AW"] = record["gre_aw"]
        formatted.append(clean_record)

    return formatted
