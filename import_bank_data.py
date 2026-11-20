
import pandas as pd
import mysql.connector

# Read CSV
df = pd.read_csv(
    r"C:\Users\Lenovo\Downloads\bank.csv",
    sep=";"
)

# Connect to MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="mysqlroot@37pass",
    database="insightviz_bank_marketing"
)

cursor = conn.cursor()

# Insert records into existing table
columns = list(df.columns)
column_names = ", ".join(f"`{col}`" for col in columns)
placeholders = ", ".join(["%s"] * len(columns))

query = f"""
INSERT INTO bank_marketing ({column_names})
VALUES ({placeholders})
"""

data = [
    tuple(None if pd.isna(value) else value for value in row)
    for row in df.itertuples(index=False, name=None)
]

cursor.executemany(query, data)
conn.commit()

print("Rows imported:", cursor.rowcount)

cursor.close()
conn.close()
