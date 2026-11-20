import pandas as pd
import mysql.connector
from mysql.connector import Error
from getpass import getpass
from pathlib import Path

# ---------------- CONFIGURATION ----------------

AIR_DATABASE = "insightviz_air_quality"
AIR_TABLE = "air_quality"

RETAIL_DATABASE = "insightviz_retail"
RETAIL_TABLE = "online_retail"

BATCH_SIZE = 1000


# ---------------- MYSQL CONNECTION ----------------

def connect_mysql():
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user=input("MySQL username [root]: ").strip() or "root",
        password=getpass("MySQL password: ")
    )


# ---------------- DATA PREPARATION ----------------

def prepare_air_quality(file_path):
    df = pd.read_csv(file_path)

    df.columns = [
    col.strip().replace(" ", "_").replace(".", "_")
    for col in df.columns
]

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date

    for col in df.columns:
        if col not in ["City", "Date", "AQI_Bucket"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def prepare_retail(file_path):
    df = pd.read_excel(file_path)

    df.columns = [col.strip().replace(" ", "_") for col in df.columns]

    df["InvoiceNo"] = df["InvoiceNo"].astype("string")
    df["StockCode"] = df["StockCode"].astype("string")
    df["CustomerID"] = df["CustomerID"].astype("Int64").astype("string")
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")

    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")

    # Derived revenue amount. The original source does not provide profit.
    df["Sales_Amount"] = df["Quantity"] * df["UnitPrice"]

    return df


# ---------------- TABLE CREATION ----------------

def create_air_table(cursor):
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{AIR_DATABASE}`")
    cursor.execute(f"USE `{AIR_DATABASE}`")

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS `{AIR_TABLE}` (
            City VARCHAR(100),
            `Date` DATE,
            `PM2_5` DOUBLE NULL,
            PM10 DOUBLE NULL,
            NO DOUBLE NULL,
            NO2 DOUBLE NULL,
            NOx DOUBLE NULL,
            NH3 DOUBLE NULL,
            CO DOUBLE NULL,
            SO2 DOUBLE NULL,
            O3 DOUBLE NULL,
            Benzene DOUBLE NULL,
            Toluene DOUBLE NULL,
            Xylene DOUBLE NULL,
            AQI DOUBLE NULL,
            AQI_Bucket VARCHAR(50)
        )
    """)


def create_retail_table(cursor):
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{RETAIL_DATABASE}`")
    cursor.execute(f"USE `{RETAIL_DATABASE}`")

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS `{RETAIL_TABLE}` (
            InvoiceNo VARCHAR(20),
            StockCode VARCHAR(20),
            Description TEXT,
            Quantity INT,
            InvoiceDate DATETIME,
            UnitPrice DOUBLE,
            CustomerID VARCHAR(30),
            Country VARCHAR(100),
            Sales_Amount DOUBLE
        )
    """)


# ---------------- BATCH INSERT ----------------

def insert_dataframe(cursor, connection, database, table, df):
    cursor.execute(f"USE `{database}`")

    # Ask before replacing rows from an earlier import.
    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
    existing_rows = cursor.fetchone()[0]

    if existing_rows > 0:
        answer = input(
            f"{database}.{table} already has {existing_rows} rows. "
            "Replace them? Type YES to continue: "
        )
        if answer != "YES":
            print(f"Skipping {table}.")
            return 0
        cursor.execute(f"TRUNCATE TABLE `{table}`")
        connection.commit()

    columns = list(df.columns)
    column_sql = ", ".join(f"`{col}`" for col in columns)
    placeholders = ", ".join(["%s"] * len(columns))

    query = f"""
        INSERT INTO `{table}` ({column_sql})
        VALUES ({placeholders})
    """

    inserted = 0

    for start in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[start:start + BATCH_SIZE]
        records = []

        for row in batch.itertuples(index=False, name=None):
            values = []
            for value in row:
                if pd.isna(value):
                    values.append(None)
                elif hasattr(value, "to_pydatetime"):
                    values.append(value.to_pydatetime())
                else:
                    values.append(value)
            records.append(tuple(values))

        cursor.executemany(query, records)
        connection.commit()
        inserted += len(records)
        print(f"{table}: {inserted:,}/{len(df):,} rows inserted")

    return inserted


# ---------------- MAIN PROGRAM ----------------

def main():
    print("\n===== InsightViz: Import Air Quality + Retail =====\n")

    air_path = input("Full path of city_day.csv: ").strip().strip('"')
    retail_path = input("Full path of Online Retail.xlsx: ").strip().strip('"')

    if not Path(air_path).is_file():
        print("Air Quality file not found. Check the path.")
        return

    if not Path(retail_path).is_file():
        print("Retail Excel file not found. Check the path.")
        return

    print("\nReading Air Quality CSV...")
    air_df = prepare_air_quality(air_path)

    print("Reading Retail Excel file...")
    retail_df = prepare_retail(retail_path)

    print("\nFiles loaded:")
    print(f"Air Quality: {len(air_df):,} rows")
    print(f"Retail:      {len(retail_df):,} rows")

    print("\nConnecting to MySQL...")
    connection = connect_mysql()
    cursor = connection.cursor()

    try:
        print("\nCreating Air Quality database/table...")
        create_air_table(cursor)
        connection.commit()

        print("Creating Retail database/table...")
        create_retail_table(cursor)
        connection.commit()

        print("\nImporting Air Quality...")
        air_inserted = insert_dataframe(
            cursor, connection, AIR_DATABASE, AIR_TABLE, air_df
        )

        print("\nImporting Retail...")
        retail_inserted = insert_dataframe(
            cursor, connection, RETAIL_DATABASE, RETAIL_TABLE, retail_df
        )

        print("\n========== IMPORT SUMMARY ==========")
        print(f"Air Quality rows inserted: {air_inserted:,}")
        print(f"Retail rows inserted:      {retail_inserted:,}")
        print("\nDatabases:")
        print(f"{AIR_DATABASE}.{AIR_TABLE}")
        print(f"{RETAIL_DATABASE}.{RETAIL_TABLE}")
        print("\nVerify in MySQL Workbench with:")
        print(f"SELECT COUNT(*) FROM {AIR_DATABASE}.{AIR_TABLE};")
        print(f"SELECT COUNT(*) FROM {RETAIL_DATABASE}.{RETAIL_TABLE};")

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except (Error, Exception) as error:
        print("\nIMPORT ERROR:", error)
