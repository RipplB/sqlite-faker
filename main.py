#!/usr/bin/env python3
"""
SQLite Faker - Generate SQLite databases with fake data using Faker library.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

from faker import Faker


def load_schema(schema_path: str) -> Dict[str, Any]:
    """Load and parse the JSON schema file."""
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        return schema
    except FileNotFoundError:
        print(f"Error: Schema file '{schema_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in schema file: {e}")
        sys.exit(1)


def get_faker_value(fake: Faker, faker_method: str) -> Any:
    """
    Get a value from Faker using the specified method.
    
    Args:
        fake: Faker instance
        faker_method: Method name or method with args as string (e.g., "name" or "random_int(min=1, max=100)")
    
    Returns:
        Generated fake value
    """
    try:
        # Check if method has arguments
        if '(' in faker_method:
            # Extract method name and arguments
            method_name = faker_method.split('(')[0]
            # Get the method
            method = getattr(fake, method_name)
            # Execute the method string as code (with arguments)
            # This is safe because we control the input
            result = eval(f"method({faker_method.split('(', 1)[1]}")
            return result
        else:
            # Simple method call without arguments
            method = getattr(fake, faker_method)
            return method()
    except AttributeError:
        print(f"Error: Faker method '{faker_method}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error calling Faker method '{faker_method}': {e}")
        sys.exit(1)


def get_sql_type(column_type: str) -> str:
    """Map generic types to SQLite types."""
    type_mapping = {
        'integer': 'INTEGER',
        'int': 'INTEGER',
        'text': 'TEXT',
        'string': 'TEXT',
        'real': 'REAL',
        'float': 'REAL',
        'blob': 'BLOB',
        'boolean': 'INTEGER',
        'bool': 'INTEGER',
        'date': 'TEXT',
        'datetime': 'TEXT',
        'timestamp': 'TEXT',
    }
    return type_mapping.get(column_type.lower(), 'TEXT')


def create_table(conn: sqlite3.Connection, table_name: str, columns: List[Dict[str, Any]]) -> None:
    """Create a table in the SQLite database."""
    column_definitions = []
    for col in columns:
        col_name = col['name']
        col_type = get_sql_type(col.get('type', 'TEXT'))
        constraints = col.get('constraints', '')
        column_def = f"{col_name} {col_type}"
        if constraints:
            column_def += f" {constraints}"
        column_definitions.append(column_def)
    
    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_definitions)})"
    conn.execute(create_sql)
    conn.commit()


def generate_data(fake: Faker, columns: List[Dict[str, Any]], num_rows: int) -> List[tuple]:
    """Generate fake data for the specified columns."""
    data = []
    for _ in range(num_rows):
        row = []
        for col in columns:
            # Skip auto-increment columns
            constraints = col.get('constraints', '').upper()
            if 'AUTOINCREMENT' in constraints:
                continue
            
            faker_method = col.get('faker', 'word')
            value = get_faker_value(fake, faker_method)
            row.append(value)
        data.append(tuple(row))
    return data


def insert_data(conn: sqlite3.Connection, table_name: str, columns: List[Dict[str, Any]], data: List[tuple]) -> None:
    """Insert generated data into the table."""
    # Filter out auto-increment columns
    column_names = []
    for col in columns:
        constraints = col.get('constraints', '').upper()
        if 'AUTOINCREMENT' not in constraints:
            column_names.append(col['name'])
    
    placeholders = ', '.join(['?' for _ in column_names])
    insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"
    conn.executemany(insert_sql, data)
    conn.commit()


def generate_database(schema: Dict[str, Any], num_rows: int, output_db: str = "output.db") -> None:
    """Generate the SQLite database based on the schema."""
    fake = Faker()
    
    # Create or connect to database
    conn = sqlite3.connect(output_db)
    
    try:
        # Process each table in the schema
        tables = schema.get('tables', [])
        if not tables:
            print("Error: No tables defined in schema.")
            sys.exit(1)
        
        for table in tables:
            table_name = table.get('name')
            columns = table.get('columns', [])
            
            if not table_name:
                print("Error: Table name is required.")
                sys.exit(1)
            
            if not columns:
                print(f"Warning: No columns defined for table '{table_name}'. Skipping.")
                continue
            
            print(f"Creating table: {table_name}")
            create_table(conn, table_name, columns)
            
            print(f"Generating {num_rows} rows of fake data...")
            data = generate_data(fake, columns, num_rows)
            
            print(f"Inserting data into {table_name}...")
            insert_data(conn, table_name, columns, data)
            
            print(f"✓ Table '{table_name}' created with {num_rows} rows\n")
        
        print(f"✓ Database generated successfully: {output_db}")
    
    finally:
        conn.close()


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description='Generate SQLite databases with fake data using Faker library.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example schema JSON:
{
  "tables": [
    {
      "name": "users",
      "columns": [
        {"name": "id", "type": "INTEGER", "constraints": "PRIMARY KEY AUTOINCREMENT"},
        {"name": "username", "type": "TEXT", "faker": "user_name"},
        {"name": "email", "type": "TEXT", "faker": "email"},
        {"name": "age", "type": "INTEGER", "faker": "random_int(min=18, max=100)"}
      ]
    }
  ]
}
        """
    )
    
    parser.add_argument(
        'schema_file',
        type=str,
        help='Path to JSON file describing the database schema'
    )
    
    parser.add_argument(
        '-n', '--num-rows',
        type=int,
        default=10,
        help='Number of rows to generate for each table (default: 10)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='output.db',
        help='Output database file path (default: output.db)'
    )
    
    args = parser.parse_args()
    
    # Validate number of rows
    if args.num_rows <= 0:
        print("Error: Number of rows must be positive.")
        sys.exit(1)
    
    # Load schema
    schema = load_schema(args.schema_file)
    
    # Generate database
    generate_database(schema, args.num_rows, args.output)


if __name__ == "__main__":
    main()
