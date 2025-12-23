# sqlite-faker

A Python application that generates SQLite databases filled with realistic fake data using the [Faker](https://github.com/joke2k/faker) library.

## Features

- 🎲 Generate SQLite databases with fake data
- 📋 Define database schema using simple JSON files
- 🔧 Support for multiple tables and various data types
- 🎯 Flexible Faker method integration with parameters
- ⚡ Built with `uv` for fast dependency management

## Installation

This project uses `uv` for dependency management. If you don't have `uv` installed:

```bash
pip install uv
```

Then install the project dependencies:

```bash
uv sync
```

## Usage

```bash
uv run python main.py <schema_file> -n <num_rows> -o <output_db>
```

### Arguments

- `schema_file` (required): Path to JSON file describing the database schema
- `-n, --num-rows` (optional): Number of rows to generate for each table (default: 10)
- `-o, --output` (optional): Output database file path (default: output.db)

### Example

```bash
uv run python main.py example_schema.json -n 100 -o mydata.db
```

## Schema File Format

The schema file is a JSON file that defines the structure of your database:

```json
{
  "tables": [
    {
      "name": "users",
      "columns": [
        {
          "name": "id",
          "type": "INTEGER",
          "constraints": "PRIMARY KEY AUTOINCREMENT"
        },
        {
          "name": "username",
          "type": "TEXT",
          "faker": "user_name"
        },
        {
          "name": "email",
          "type": "TEXT",
          "faker": "email"
        },
        {
          "name": "age",
          "type": "INTEGER",
          "faker": "random_int(min=18, max=100)"
        }
      ]
    }
  ]
}
```

### Schema Structure

- **tables**: Array of table definitions
  - **name**: Table name
  - **columns**: Array of column definitions
    - **name**: Column name
    - **type**: Data type (INTEGER, TEXT, REAL, BLOB, etc.)
    - **constraints** (optional): SQL constraints (e.g., "PRIMARY KEY AUTOINCREMENT", "NOT NULL")
    - **faker**: Faker method to generate data (e.g., "name", "email", "random_int(min=1, max=100)")

### Supported Data Types

The following data types are mapped to SQLite types:

- `integer`, `int` → INTEGER
- `text`, `string` → TEXT
- `real`, `float` → REAL
- `blob` → BLOB
- `boolean`, `bool` → INTEGER
- `date`, `datetime`, `timestamp` → TEXT

### Faker Methods

You can use any [Faker method](https://faker.readthedocs.io/en/master/providers.html) in the `faker` field:

- Simple methods: `"name"`, `"email"`, `"address"`, `"phone_number"`
- Methods with parameters: `"random_int(min=1, max=100)"`, `"random_element(elements=('a', 'b', 'c'))"`

### Example Schema

See `example_schema.json` for a complete example with two tables (users and products).

## Examples

### Generate a small test database

```bash
uv run python main.py example_schema.json -n 10 -o test.db
```

### Generate a larger database

```bash
uv run python main.py example_schema.json -n 1000 -o production.db
```

### Query the generated database

```bash
sqlite3 test.db "SELECT * FROM users LIMIT 5;"
```

## Development

This project uses `uv` for dependency management. The main dependencies are:

- Python >= 3.12
- faker >= 39.0.0

## License

This project is open source and available under the MIT License.
