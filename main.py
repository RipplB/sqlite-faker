#!/usr/bin/env python3
"""
SQLite Faker - Generate SQLite databases with fake data using Faker library.
"""

import argparse
import ast
import json
import sqlite3
import sys
from typing import Any, Dict, List

from faker import Faker


def is_valid_sql_identifier(name: str) -> bool:
    """
    Validate SQL identifier to prevent SQL injection.
    
    Args:
        name: The identifier to validate
    
    Returns:
        True if valid, False otherwise
    """
    # SQL identifiers should only contain alphanumeric characters and underscores
    # and should not start with a number
    if not name:
        return False
    if name[0].isdigit():
        return False
    return all(c.isalnum() or c == '_' for c in name)


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


def parse_faker_arguments(args_string: str) -> Dict[str, Any]:
    """
    Safely parse Faker method arguments from string format.
    
    Args:
        args_string: Arguments in format like "min=1, max=100" or "elements=('a', 'b')"
    
    Returns:
        Dictionary of parsed arguments
    """
    kwargs = {}
    
    # Remove outer parentheses if present
    args_string = args_string.strip()
    
    if not args_string:
        return kwargs
    
    # Parse key=value pairs while respecting nested structures
    i = 0
    while i < len(args_string):
        # Skip whitespace
        while i < len(args_string) and args_string[i].isspace():
            i += 1
        
        if i >= len(args_string):
            break
        
        # Find key
        key_start = i
        while i < len(args_string) and (args_string[i].isalnum() or args_string[i] == '_'):
            i += 1
        key = args_string[key_start:i]
        
        # Skip whitespace and '='
        while i < len(args_string) and (args_string[i].isspace() or args_string[i] == '='):
            i += 1
        
        # Find value (handle nested parentheses)
        value_start = i
        paren_depth = 0
        in_string = False
        string_char = None
        
        while i < len(args_string):
            char = args_string[i]
            
            if not in_string:
                if char in ('"', "'"):
                    in_string = True
                    string_char = char
                elif char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                elif char == ',' and paren_depth == 0:
                    break
            else:
                if char == string_char and (i == 0 or args_string[i-1] != '\\'):
                    in_string = False
                    string_char = None
            
            i += 1
        
        value = args_string[value_start:i].strip()
        
        # Parse the value using ast.literal_eval for safety
        try:
            kwargs[key] = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            # If it fails, treat as string
            kwargs[key] = value.strip('"').strip("'")
        
        # Skip comma
        if i < len(args_string) and args_string[i] == ',':
            i += 1
    
    return kwargs


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
            first_paren = faker_method.index('(')
            last_paren = faker_method.rindex(')')
            method_name = faker_method[:first_paren].strip()
            args_part = faker_method[first_paren + 1:last_paren]
            
            # Get the method
            method = getattr(fake, method_name)
            
            # Parse arguments safely
            kwargs = parse_faker_arguments(args_part)
            
            # Call method with parsed arguments
            return method(**kwargs)
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
    # Validate table name
    if not is_valid_sql_identifier(table_name):
        print(f"Error: Invalid table name '{table_name}'. Table names must contain only alphanumeric characters and underscores, and cannot start with a number.")
        sys.exit(1)
    
    column_definitions = []
    for col in columns:
        col_name = col['name']
        
        # Validate column name
        if not is_valid_sql_identifier(col_name):
            print(f"Error: Invalid column name '{col_name}'. Column names must contain only alphanumeric characters and underscores, and cannot start with a number.")
            sys.exit(1)
        
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
    # Validate table name
    if not is_valid_sql_identifier(table_name):
        print(f"Error: Invalid table name '{table_name}'.")
        sys.exit(1)
    
    # Filter out auto-increment columns and validate column names
    column_names = []
    for col in columns:
        col_name = col['name']
        
        # Validate column name
        if not is_valid_sql_identifier(col_name):
            print(f"Error: Invalid column name '{col_name}'.")
            sys.exit(1)
        
        constraints = col.get('constraints', '').upper()
        if 'AUTOINCREMENT' not in constraints:
            column_names.append(col_name)
    
    placeholders = ', '.join(['?' for _ in column_names])
    insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"
    conn.executemany(insert_sql, data)
    conn.commit()


def generate_database(schema: Dict[str, Any], num_rows: int, output_db: str = "output.db", locale: str = "en_US") -> None:
    """Generate the SQLite database based on the schema."""
    try:
        fake = Faker(locale)
    except AttributeError:
        print(f"Error: Invalid locale '{locale}'. Please use a valid Faker locale (e.g., en_US, es_ES, fr_FR, de_DE, ja_JP).")
        sys.exit(1)
    
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
    
    parser.add_argument(
        '-l', '--locale',
        type=str,
        default='en_US',
        help='Locale for fake data generation (default: en_US). Examples: en_US, es_ES, fr_FR, de_DE, ja_JP'
    )
    
    args = parser.parse_args()
    
    # Validate number of rows
    if args.num_rows <= 0:
        print("Error: Number of rows must be positive.")
        sys.exit(1)
    
    # Load schema
    schema = load_schema(args.schema_file)
    
    # Generate database
    generate_database(schema, args.num_rows, args.output, args.locale)


if __name__ == "__main__":
    main()
