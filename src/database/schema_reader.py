
from db_connection import get_connection

def get_schema():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT
        TABLE_NAME,
        COLUMN_NAME,
        DATA_TYPE,
        COLUMN_KEY
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'insightviz'
    ORDER BY TABLE_NAME, ORDINAL_POSITION
    """

    cursor.execute(query)
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
    conn.close()

    return schema


if __name__ == "__main__":
    result = get_schema()

    if not result:
        print("No tables found in InsightViz database.")
    else:
        for table, columns in result.items():
            print(f"\nTable: {table}")

            for col in columns:
                print(col)
