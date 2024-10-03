import psycopg
import os

# Database connection parameters
db_params = {
    'dbname': 'multi_tenant_inventory',
    'user': 'user',
    'password': 'password',
    'host': '172.18.0.2',
    'port': '5432'
}

def check_db_setup():
    try:
        # Connect to the database
        with psycopg.connect(**db_params) as conn:
            with conn.cursor() as cur:
                # List schemas
                cur.execute("SELECT schema_name FROM information_schema.schemata;")
                schemas = cur.fetchall()
                print("Schemas:")
                for schema in schemas:
                    print(f"- {schema[0]}")

                print("\nTables in each schema:")
                # List tables in each schema
                for schema in schemas:
                    schema_name = schema[0]
                    cur.execute(f"""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = %s;
                    """, (schema_name,))
                    tables = cur.fetchall()
                    print(f"\nSchema: {schema_name}")
                    for table in tables:
                        print(f"- {table[0]}")

                # Check for specific tables
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'licenses'
                    );
                """)
                licenses_table_exists = cur.fetchone()[0]
                print(f"\n'licenses' table exists in public schema: {licenses_table_exists}")

    except psycopg.Error as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    check_db_setup()
