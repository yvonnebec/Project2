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

    # Any rows with -99 values are deleted in the dataframe
    df = pd.read_csv(comma_path)

    df.replace(-99, pd.NA, inplace=True)
    df.dropna(inplace=True)

    rename_cols(df, prc_col=prc_col)

    # Sort values by ticker, then date
    df = df.sort_values(by=['ticker', 'date'])

    # Absolute values the negative values that seem consistent if they were positive
    df['open'] = np.abs(df['open'])



    # Creates a new file clean_data.dat which has all negative values removed
    df.to_csv(os.path.join(DATADIR, 'clean_data.dat'), index=False)

    return df[['date', 'ticker', 'price']]




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
            if os.path.isfile((os.path.join(DATADIR, f'{tic.lower()}_prc.csv'))):
                df_csv = read_csv(os.path.join(DATADIR, f'{tic.lower()}_prc.csv'), tic, prc_col)
                data = pd.concat([data, df_csv], ignore_index=True)

    # Read from DAT files
    if dat_files is not None:
        for dat in dat_files:
            df_dat = read_dat(os.path.join(DATADIR, f'{dat}'), prc_col)
            data = pd.concat([data, df_dat], ignore_index=True)

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
    # Formatting data types to align with docstring
    df['date'] = pd.to_datetime(df['date'])
    df['ticker'] = df['ticker'].str.upper().str.replace(' ', '').str.replace('"', '')

    # Computing daily returns as 'dret' using percentage change
    df = df.sort_values(by=['ticker', 'date'])
    df['dret'] = df.groupby('ticker')['price'].pct_change()

    df['mdate'] = df['date'].dt.to_period('M').astype(str)
    
    # Grouping by ticker and mdate to get the closing, last price of each month
    close_price = df.groupby(['ticker', 'mdate'])['price'].last().reset_index()

    # Compute the previous month's close, last price for each ticker
    close_price['prev_price'] = close_price.groupby('ticker')['price'].shift(1)

    # Monthly Return = (Closing Price on Last Day of Month / Closing Price on Last Day of Previous Month) - 1
    close_price['mret'] = (close_price['price'] / close_price['prev_price']) - 1

    # Monthly Volatillity = Standard deviation of dret * sqrt(21)
    m_vol = df.groupby(['ticker', 'mdate'])['dret'].agg(lambda x: np.std(x) * np.sqrt(21)).reset_index()
    m_vol.rename(columns={'dret': 'mvol'}, inplace=True)

    # Merge the monthly return and volatility data
    monthly_data = pd.merge(close_price[['ticker', 'mdate', 'mret']], m_vol[['ticker', 'mdate', 'mvol']], on=['ticker', 'mdate'])

    monthly_data = monthly_data[['mdate', 'ticker', 'mret', 'mvol']]

    monthly_data['mret'] = pd.to_numeric(monthly_data['mret'], errors='coerce')
    monthly_data['mvol'] = pd.to_numeric(monthly_data['mvol'], errors='coerce')

    # Remove NaN results
    monthly_data.dropna(inplace=True)

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

    # mret = intercept +  a * lagged_mvol + error
    regression_model = smf.ols(formula='mret ~ lagged_mvol', data=monthly_data).fit()
    print(regression_model.summary())




def test_read_dat():
    data1_path = os.path.join(DATADIR, 'data1.dat')
    df = (read_dat(data1_path, 'adj_close'))
    print(df)

def test_read_csv_tsla():
    # tsla stock data
    tsla_pth = os.path.join(DATADIR, 'tsla_prc.csv')

    print(read_csv(tsla_pth, 'tsla', 'adj_close'))

    # The dataframe should be different when a different prc_col is chosen
    print(read_csv(tsla_pth, 'tsla', 'open'))

def test_read_files():
    # Created two new files, trf.dat, and trf_prc.csv to test the read_files function with multiple files and stocks
    read_files(['TRF', 'TSLA', 'A'], ['trf.dat', 'data1.dat'])

    # Expected Results - will appear in read_files.csv
    # 1.) Include first half of TRF block in trf.dat (Second half of the block overlaps with trf_prc.csv)

    # 2.) Expects result to also add (1900-00-00) data to one of TSLA's result
    # (This data was added to the trf.dat file to test if the function can read from multiple dat files for one TICK)

    # 3.) Expect to see a stock A (does not have an associated csv file, but has data in trf.dat)

def test_read_files_basic():
    print(read_files(csv_tickers=["tsla"], dat_files=["data1"]))

def test_calc_monthly_ret_and_vol():
    data1_path = os.path.join(DATADIR, 'data1.dat')
    df = (read_dat(data1_path, 'adj_close'))
    print(calc_monthly_ret_and_vol(df))

def test_tsla_regression():
    main(csv_tickers=['tsla'], dat_files=['data1.dat'], prc_col='adj_close')

if __name__ == "__main__":
    pass
    #test_read_csv_tsla()
    #test_read_dat()
    #test_read_files()
    #test_read_files_basic()
    #test_calc_monthly_ret_and_vol()
    #test_tsla_regression()
