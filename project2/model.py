from __future__ import annotations

import os
import pandas as pd
import numpy as np
from project2.main import calc_monthly_ret_and_vol
from project2.main import read_files
import matplotlib.pyplot as plt
import seaborn as sns
from project2.config import DATADIR

if __name__ == "__main__":

    df = read_files(csv_tickers=["tsla"], dat_files=["data1"], prc_col='adj_close')
    monthly_data = calc_monthly_ret_and_vol(df)
    monthly_data['lagged_mvol'] = monthly_data.groupby('ticker')['mvol'].shift(1)

    monthly_data.dropna(inplace=True)


    print(monthly_data.head())

    sns.regplot(x='lagged_mvol', y='mret', data=monthly_data)
    plt.xlabel('Lagged Monthly Volatility')
    plt.ylabel('Monthly Returns')
    plt.title('Regression of Monthly Returns on Lagged Volatility')
    plt.show()