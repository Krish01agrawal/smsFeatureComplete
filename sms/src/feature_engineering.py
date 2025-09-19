import pandas as pd

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
    df['day_of_week'] = df['transaction_date'].dt.day_name()
    df['month'] = df['transaction_date'].dt.month
    df['hour'] = df['transaction_date'].dt.hour
    df['is_weekend'] = df['day_of_week'].isin(['Saturday', 'Sunday'])
    df['is_high_value'] = df['amount'] > 3000
    return df
