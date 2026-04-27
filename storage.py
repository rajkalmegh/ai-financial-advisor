import pandas as pd
import os

FILE = "data.csv"

def load_data():
    if os.path.exists(FILE):
        return pd.read_csv(FILE)
    else:
        return pd.DataFrame(columns=["Date", "Category", "Amount"])

def save_data(df):
    df.to_csv(FILE, index=False)