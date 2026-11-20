
from db_connection import get_connection


def get_schema(database="insightviz"):

    conn = get_connection(database)

    try:
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            DATA_TYPE,
            COLUMN_KEY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """

        cursor.execute(query, (database,))
        rows = cursor.fetchall()

        schema = {}

        for row in rows:
            table = row["TABLE_NAME"]

            if table not in schema:
                schema[table] = []

            schema[table].append({
                "column": row["COLUMN_NAME"],
                "type": row["DATA_TYPE"],
                "key": row["COLUMN_KEY"]
            })

        cursor.close()
        return schema

    finally:
        conn.close()


if __name__ == "__main__":

    for database in ["insightviz", "insightviz_test"]:

        print(f"\nDATABASE: {database}")

        result = get_schema(database)

        if not result:
            print("No tables found.")
        else:
            for table, columns in result.items():
                print(f"\nTable: {table}")

                for col in columns:
                    print(col)
