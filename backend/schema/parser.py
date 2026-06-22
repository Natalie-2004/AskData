# parse SQLlite schema to get Schema JSON
import sys
import os
# no matter where we run this script, 
# we want to make sure the project root is in the path for imports to work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import sqlite3
import json
from typing import List, Dict, Any
from config import DB_PATH

def get_table_names(conn: sqlite3.Connection) -> List[str]:
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    return [table[0] for table in tables]

def get_cols(conn: sqlite3.Connection, table_name: str) -> List[Dict]:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info('{table_name}');")
    cols = []
    for row in cursor:
        cols.append({
            "column_id": row[0],
            "field_name": row[1],
            "field_type": row[2],
            "is_primary_key": bool(row[5])
        })
    return cols

def get_foreign_keys(conn: sqlite3.Connection, table_name: str) -> List[Dict]:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA foreign_key_list('{table_name}');")
    fks = []
    for row in cursor:
        fks.append({
            "from_field": row[3],
            "to_table": row[2],
            "to_field": row[4]
        })
    return fks
    
def get_sample_values(
        conn: sqlite3.Connection,
        table_name: str,
        field_name: str,
        limit: int=5
) -> List[Any]:
    try: 
        cursor = conn.cursor()
        cursor.execute(f"SELECT {field_name} FROM {table_name} WHERE {field_name} IS NOT NULL LIMIT {limit};")
        values = cursor.fetchall()
        return [value[0] for value in values]
    except Exception:
        return []

def parse_db(db_path: str=DB_PATH) -> Dict[str, Any]:
    """
    parse the entire db, return a list of field-level schema, 
    each element represents a field with its table info and sample values
    """
    conn = sqlite3.connect(db_path)
    tables = get_table_names(conn)
    schema_entries = []
    fid = 0
    for table_name in tables:
        cols = get_cols(conn, table_name)
        fks = get_foreign_keys(conn, table_name)
        fk_map = {fk['from_field']: fk for fk in fks}
        for col in cols:
            field_name = col["field_name"]
            samples = get_sample_values(conn, table_name, field_name)
            field_desc = (
                f"Field '{field_name}' in table '{table_name}'. "
                f"Type: {col['field_type']}."
                f"Sample values: {samples}."
            )

            if col["is_primary_key"]:
                field_desc += "This field is the primary key."
            
            if field_name in fk_map:
                fk = fk_map[field_name]
                field_desc += (
                    f"Foreign key referencing "
                    f"{fk['to_table']}.{fk['to_field']}."
                )

            keyword_text = (
                f"{field_name} {table_name} "
                f"{col['field_type']} "
                f"{' '.join(str(s) for s in samples)}"
            )

            schema_entries.append({
                "field_id": str(fid),
                "database_name": "chinook",
                "table_name": table_name,
                "field_name": field_name,
                "field_type": col["field_type"],
                "is_primary_key": col["is_primary_key"],
                "foreign_key": fk_map.get(field_name),
                "sample_values": samples,
                # for vector indexing and retrieval
                "field_description": field_desc,   
                "keyword_text": keyword_text,
                # for reranking
                "rerank_text": field_desc,
            })

            fid += 1

    conn.close()
    return schema_entries

if __name__ == "__main__":
    entries = parse_db()
    print(f"Total fields parsed: {len(entries)}")
    print(json.dumps(entries, indent=2))