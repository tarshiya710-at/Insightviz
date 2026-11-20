import os
import re
import math
import torch
import torch.nn as nn
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL
from google import genai
from google.genai import types

load_dotenv(override=True)

device = torch.device(
    "mps" if torch.backends.mps.is_available()
    else ("cuda" if torch.cuda.is_available() else "cpu")
)


class TokenEmbedding(nn.Module):
    def __init__(self, vocab_size, d_model, padding_idx=0):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model, padding_idx=padding_idx)
        self.d_model = d_model

    def forward(self, x):
        return self.embedding(x) * math.sqrt(self.d_model)


class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=1000, dropout=0.2):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term[:pe[:, 1::2].shape[1]])
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return self.dropout(x + self.pe[:, :x.size(1), :])


class TextToSQLTransformer(nn.Module):
    def __init__(self, vocab_size, d_model=256, nhead=8, num_encoder_layers=3, num_decoder_layers=3, dim_feedforward=512, dropout=0.2, padding_idx=0):
        super().__init__()
        self.embedding = TokenEmbedding(vocab_size, d_model, padding_idx)
        self.positional_encoding = PositionalEncoding(d_model, max_len=1000, dropout=dropout)
        self.transformer = nn.Transformer(
            d_model=d_model,
            nhead=nhead,
            num_encoder_layers=num_encoder_layers,
            num_decoder_layers=num_decoder_layers,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        self.output_layer = nn.Linear(d_model, vocab_size)
        self.padding_idx = padding_idx

    def forward(self, src, tgt):
        src_padding_mask = src.eq(self.padding_idx)
        tgt_padding_mask = tgt.eq(self.padding_idx)
        tgt_len = tgt.size(1)
        tgt_mask = torch.triu(torch.ones(tgt_len, tgt_len, device=tgt.device, dtype=torch.bool), diagonal=1)
        src_emb = self.positional_encoding(self.embedding(src))
        tgt_emb = self.positional_encoding(self.embedding(tgt))
        output = self.transformer(
            src=src_emb,
            tgt=tgt_emb,
            tgt_mask=tgt_mask,
            src_key_padding_mask=src_padding_mask,
            tgt_key_padding_mask=tgt_padding_mask,
            memory_key_padding_mask=src_padding_mask
        )
        return self.output_layer(output)


state_dict = torch.load("best_text2sql_model.pth", map_location=device, weights_only=True)
vocab_size, d_model = state_dict["embedding.embedding.weight"].shape

model = TextToSQLTransformer(vocab_size=vocab_size, d_model=d_model).to(device)
model.load_state_dict(state_dict)
model.eval()
print(f"Loaded best_text2sql_model.pth successfully! (vocab_size={vocab_size}, d_model={d_model})")


url = URL.create(
    "mysql+pymysql",
    username=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "1234"),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    database="regional_sales_data",
)
engine = create_engine(url, pool_pre_ping=True)

TABLE_NOTES = """
Notes:
- Column names have spaces, so always use backticks, e.g. `Line Total`.
- `Line Total` = `Order Quantity` * `Unit Price`.
- sales_order.`Customer Name Index` -> customers.`Customer Index`
- sales_order.`Delivery Region Index` -> regions.`id`
- sales_order.`Product Description Index` -> products.`Index`
- regions.`State Code` -> state_regions.`State Code`
- The `2017_budgets` table name starts with a number, so backticks are required.
- Dates are DATE type (YYYY-MM-DD).
"""


def get_schema() -> str:
    inspector = inspect(engine)
    schema_lines = []
    for table in inspector.get_table_names():
        cols = [f"`{c['name']}` ({c['type']})" for c in inspector.get_columns(table)]
        schema_lines.append(f"Table `{table}`: {', '.join(cols)}")
    return "\n".join(schema_lines) + "\n" + TABLE_NOTES


client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def generate_sql(schema: str, question: str) -> str:
    prompt = f"""Based on the MySQL database schema below, write a single-line valid MySQL SELECT query that answers the question.
Rules:
- Output ONLY the raw SQL query, nothing else.
- No markdown backticks, no explanations, no line breaks.
- Use backticks (`) around table or column names with spaces or leading numbers.

Database Schema:
{schema}

Question: {question}
SQL:"""

    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=256),
    )

    sql = response.text.strip()
    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql, flags=re.IGNORECASE)
    return sql.strip().rstrip(";")


if __name__ == "__main__":
    db_schema = get_schema()
    question = "show me the total sales of every product"

    sql_query = generate_sql(db_schema, question)
    print("\nDatabase :", "regional_sales_data")
    print("Question :", question)
    print("SQL Query:", sql_query)