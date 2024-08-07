""" scaffold for project2
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


from project2 import config as cfg
from project2 import util
from project2.config import DATADIR

#from config import DATADIR


# Helper Functions
def normalise(name):

    # Remove leading and trailing whitespaces
    name = name.strip()

    if name.isupper():
        name = name.lower()


    # Convert Camel to Snake Case
    cased_name = ''
    for i, ch in enumerate(name):
        if ch.isupper() and i != 0:
            cased_name += '_' + ch.lower()
        else:
            cased_name += ch.lower()

    # Replace alphanumerics with underscores
    new = ''
    for ch in cased_name:
        if ch.isalnum():
            new += ch
        else:
            new += '_'

    # Replace many underscores with single one
    final = ''
    prev = None
    for ch in new:
        if ch == '_' and prev == '_':
            continue
        final += ch
        prev = ch

    return final


def rename_cols(
        df: pd.DataFrame,
        prc_col: str = 'adj_close',
        ) -> None:
    """ Rename the columns of `df` in place.

    Normalise the names of columns in a dataframe such that they are in
    snake case with no leading or trailing white spaces. The prc_col
    parameter indicates which column should be renamed to 'price'.
    This function should be used in read_dat and read_csv.

    Parameters
    ----------
    df: frame
        A data frame with daily prices (open, close, etc...) for different
        tickers. 

    prc_col: str
        Which price to use (close, open, etc...). 


    """
    normalised_cols = []
    for col in df.columns:
        normalised_cols.append(normalise(col))
    df.columns = normalised_cols

    if prc_col in df.columns: 
        df.rename(columns={prc_col: 'price'}, inplace=True)




def read_dat(
        pth,
        prc_col: str = 'adj_close',
        ) -> pd.DataFrame:
    """ Returns a data frame with the relevant information from the .dat file
    `pah`


    Parameters
    ----------
    pth: str
        Location of the .dat file to be read

    prc_col: str
        Which price column to use (close, open, etc...)



    Returns
    -------
    frame: 
        A dataframe with columns:
    
         #   Column   
        ---  ------   
         0   date     
         1   ticker   
         2   price    



    """
    # Creates a new file comma_dat which has commas separating all values and tickers with no quotations
    new_lines = []
    if os.path.exists(pth):
        with open(pth, 'r') as file:
            content = file.readlines()
            for line in content:
                new_lines.append(" ".join(line.replace("'", "").split()))
    comma_path = os.path.join(DATADIR, 'comma_dat.csv')

    with open(comma_path, 'w') as new_file:
        for line in new_lines:
            changed_line = line.replace(' ', ',') + '\n'
            changed_line = changed_line.replace(',,', ',')
            new_file.write(changed_line)

    # Creates a new dataframe where any lines with negative values are deleted
    df = pd.read_csv(comma_path)

    rename_cols(df, prc_col=prc_col)

    numeric_columns = df.select_dtypes(include=[np.number])
    filtered_df = df[numeric_columns.ge(0).all(axis=1)]
    filtered_df = filtered_df.sort_values(by=['ticker', 'date'])

    # Creates a new file clean_data.dat which has all negative values removed

    filtered_df.to_csv(os.path.join(DATADIR, 'clean_data.dat'), index=False)

    return filtered_df[['date', 'ticker', 'price']]




def read_csv(
        pth,
        ticker: str,
        prc_col: str = 'adj_close',
        ) -> pd.DataFrame:
    """ Returns a DF with the relevant information from the CSV file `pth`

    Parameters
    ----------
    pth: str
        Location of the CSV file to be read

    ticker:
        Relevant ticker

    prc_col: str
        Which price column to use (close, open, etc...)



    Returns
    -------
    frame: 
        A dataframe with columns:
    
         #   Column   
        ---  ------   
         0   date     
         1   ticker   
         2   price    


    """
    df = pd.read_csv(pth)
    rename_cols(df, prc_col=prc_col)
    df['ticker'] = ticker.upper()
    df = df.sort_values(by=['ticker', 'date'])

    return df[['date', 'ticker', 'price']]


def read_files(
        csv_tickers: list | None = None,
        dat_files: list | None = None,
        prc_col: str = 'adj_close',
        ):
    """ Read CSV and DAT files. If an observation [ticker, price] is
    present in both files, prioritize CSV

    Parameters
    ----------
    csv_ticker: list, str, optional

    dat_files: list, str, optional

    prc_col: str
        Which price to use (close, open, etc...). 

    Returns
    -------
    frame: 
        A dataframe with columns:
    
         #   Column   
        ---  ------   
         0   date     
         1   ticker   
         2   price    
    """
    data = pd.DataFrame(columns=['date', 'ticker', 'price'])

    # Read from CSV files
    if csv_tickers is not None:
        for tic in csv_tickers:
            df_csv = read_csv(os.path.join(DATADIR, f'{tic}_prc.csv'), tic, prc_col)
            data = pd.concat([data, df_csv], ignore_index=True)

            # Read from DAT files
            if dat_files is not None:
                for dat in dat_files:
                    df_dat = read_dat(os.path.join(DATADIR, f'{dat}.dat'), prc_col)
                    df_tick_dat = df_dat[df_dat['ticker'] == tic.upper()]
                    data = pd.concat([data, df_tick_dat], ignore_index=True)

    data.drop_duplicates(subset=['date', 'ticker'], keep='first', inplace=True)
    data = data.sort_values(by=['ticker', 'date'])

    # Creates a new file for the output
    data.to_csv(os.path.join(DATADIR, 'read_files.csv'), index=False)

    return data



def calc_monthly_ret_and_vol(df):
    """ Compute monthly returns and volatility for each ticker in `df`.

    Parameters
    ----------
    df: frame
        A data frame with columns

         #   Column
        ---  ------
         0   date
         1   ticker
         2   price


    Returns
    -------
    frame:
        A data frame with columns

         #   Column
        ---  ------
         0   mdate
         1   ticker
         2   mret
         3   mvol

        where
            mdate is a string with format YYYY-MM

            ticker is the ticker (uppercase, no spaces, no quotes)

            mret is the monthly return

            mvol is the monthly volatility. Computed as the
                standard deviation of daily returns * sqrt(21)


    Notes
    -----
    Assume no gaps in the daily time series of each ticker



    """
    # Formatting data types
    df['date'] = pd.to_datetime(df['date'])
    df['price'] = pd.to_numeric(df['price'])
    df['ticker'] = df['ticker'].str.upper().str.replace(' ', '').str.replace('"', '')


    # Computing daily returns
    df = df.sort_values(by=['ticker', 'date'])
    df['dret'] = df.groupby('ticker')['price'].pct_change()

    df['mdate'] = df['date'].dt.to_period('M').astype(str)
    #print(df)
    monthly_data = df.groupby(['ticker', 'mdate']).agg(
        #mret=('dret', 'sum'),
        mret=('price', lambda x: (x.iloc[-1] / x.iloc[0]) - 1),
        mvol=('dret', lambda x: np.std(x) * np.sqrt(21))
    ).reset_index()

    monthly_data = monthly_data[['mdate', 'ticker', 'mret', 'mvol']] 
    #print(monthly_data)   
    #monthly_data.rename(columns={'mdate': 'mdate', 'ticker': 'ticker', 'mret': 'mret', 'mvol': 'mvol'}, inplace=True)

    return monthly_data

def main(
        csv_tickers: list | None = None,
        dat_files: list | None = None,
        prc_col: str = 'adj_close',
        ):
    """ Perform the main analysis. Regressing month returns on lagged monthly
    volatility.

    Parameters
    ----------
    csv_tickers: list
        A list of strings, where each string is the ticker of a stock for which
        the data is in a CSV file.

    dat_files: list
        A list of strings, where each string is the name of a dat file.

    prc_col: str
        The name of the column in which price data is to be read.

    Returns
    -------
    None

    Notes
    -----
    The function should print the summary results of a linear regression provided by
    the statsmodels package.
    """
    df = read_files(csv_tickers=csv_tickers, dat_files=dat_files, prc_col=prc_col)
    monthly_data = calc_monthly_ret_and_vol(df)

    monthly_data['lagged_mvol'] = monthly_data.groupby('ticker')['mvol'].shift(1)
    monthly_data.dropna(inplace=True)
    #print(monthly_data)

    # mret = intercept +  a * lagged_mvol + error
    regression_model = smf.ols(formula='mret ~ lagged_mvol', data=monthly_data).fit()
    print(regression_model.summary())



def test_read_dat():
    data1_path = os.path.join(DATADIR, 'data1.dat')
    df = (read_dat(data1_path, 'adj_close'))
    print(df)
    print(calc_monthly_ret_and_vol(df))

def test_read_csv():
    #tsla stock data
    tsla_pth = os.path.join(DATADIR, 'tsla_prc.csv')

    print(read_csv(tsla_pth, 'tsla', 'adj_close'))

    #The dataframe should be different when a different prc_col is chosen
    print(read_csv(tsla_pth, 'tsla', 'open'))

def test_step_1_2():

    result = pd.read_csv(os.path.join(DATADIR, 'res.csv')).equals(pd.read_csv(os.path.join(DATADIR, 'sample.csv')))
    print(f'Dataframes are the same: {result}')

if __name__ == "__main__":
    pass
    #test_read_csv()
    #test_read_dat()
    #print(read_files(csv_tickers=["tsla"], dat_files=["data1"]))
    #res = calc_monthly_ret_and_vol(read_files(csv_tickers=["tsla"], dat_files=["data1"])).to_csv(os.path.join(DATADIR, 'res.csv'), index=False)
    #print(res)
    #test_step_1_2()
    #main(csv_tickers=["tsla"], dat_files=["data1"], prc_col='adj_close')





