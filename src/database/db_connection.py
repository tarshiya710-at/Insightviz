import mysql.connector

# MySQL server connection settings
HOST = "localhost"
USER = "root"
PASSWORD = "mysqlroot@37pass"


def get_connection(database="insightviz"):
    """
    Connect to a MySQL database.
    Uses insightviz as the default database.
    """

    connection = mysql.connector.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=database
    )

    return connection


def get_available_databases():
    """
    Return all available user databases.
    """

    connection = get_connection(database=None)

    try:
        cursor = connection.cursor()
        cursor.execute("SHOW DATABASES")

        databases = [row[0] for row in cursor.fetchall()]

        cursor.close()

        system_databases = [
            "information_schema",
            "mysql",
            "performance_schema",
            "sys"
        ]

        return [
            db for db in databases
            if db not in system_databases
        ]

    finally:
        connection.close()


if __name__ == "__main__":

    try:
        databases = get_available_databases()

        print("Available databases:")
        for db in databases:
            print(db)

        connection = get_connection()

        if connection.is_connected():
            print("\nInsightViz connected successfully!")

        connection.close()

    except mysql.connector.Error as error:
        print("Database connection failed:", error)