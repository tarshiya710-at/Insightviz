
import pandas as pd
from db_connection import get_connection


def execute_sql(sql, database="insightviz"):

    cleaned_sql = sql.strip().rstrip(";")

    if not cleaned_sql.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")

    conn = get_connection(database)

    try:
        cursor = conn.cursor()
        cursor.execute(cleaned_sql)

        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]

        df = pd.DataFrame(rows, columns=columns)

        cursor.close()
        return df

    finally:
        conn.close()
