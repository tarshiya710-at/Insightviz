
import mysql.connector

def get_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="mysqlroot@37pass",
        database="insightviz"
    )
    return connection


if __name__ == "__main__":
    conn = get_connection()

    if conn.is_connected():
        print("InsightViz connected to MySQL successfully!")

    conn.close()
