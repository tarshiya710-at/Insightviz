
import pandas as pd
from db_connection import get_connection


def execute_sql(sql):

    # Allow only SELECT queries for safety
    cleaned_sql = sql.strip().rstrip(";")

    if not cleaned_sql.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")

    conn = get_connection()

    try:
        df = pd.read_sql_query(cleaned_sql, conn)
        return df

    finally:
        conn.close()


if __name__ == "__main__":

    query = """
    SELECT category,
           SUM(quantity * price) AS total_sales
    FROM demo_sales
    GROUP BY category
    """

    result = execute_sql(query)

    print("\nQuery Results:")
    print(result)
