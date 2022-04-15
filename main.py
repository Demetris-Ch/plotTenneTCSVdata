import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

""" Data types:

Prices of Reserved Balancing Reserves: 
    By TSO, all types ar for Automatic frequency restoration reserve.Prices paid by the TSO per type of procured 
    balancing reserve and per procurement period (Currency/MW/period). The information shall be published as soon as 
    possible but no later than one hour after the procurement process ends.
    https://transparency.entsoe.eu/content/static_content/Static%20content/knowledge%20base/data-views/balancing/Data-view%20Price%20of%20Reserved%20Balancing%20Reserves.html

    
"""
day_ahead_prices = False
reserved_balancing_reserve_prices = False
activation_balancing_energy = False
average_total_imbalance = True


def read_csv_info(name):
    return pd.read_csv(f'CSVfiles/{name}.csv')


def read_xl_info(name):
    return pd.read_excel(f'CSVfiles/{name}.xlsx')


def year_to_hour(csv_pd, year=2020):
    if year % 4 == 0:
        per_hour_array = np.zeros((366, 24))
    else:
        per_hour_array = np.zeros((365, 24))
    for index, row in csv_pd.iterrows():
        begin_date_time = row['MTU (CET/CEST)'].split(' - ')[0]
        time_of_datapoint = int(begin_date_time.split(':')[0][-2:])
        date_int = date_to_int(begin_date_time.split(" ")[0])
        try:
            val = float(row['Day-ahead Price [EUR/MWh]'])
        except:
            val = float('nan')
        per_hour_array[date_int-1, time_of_datapoint] = val
    per_hour_array = per_hour_array[~np.isnan(per_hour_array).any(axis=1), :]
    return per_hour_array


def balance_activation(csv_pd):
    per_quarter_up_array = np.zeros((365, 24*4))
    per_quarter_down_array = np.zeros((365, 24*4))
    for index, row in csv_pd.iterrows():
        begin_date_time = row['ISP (UTC)'].split(' - ')[0]
        hour_of_datapoint = int(begin_date_time.split(':')[0][-2:])
        minutes_of_datapoint = int(begin_date_time.split(':')[1][-2:])
        quarter = quarter_of_day(hour_of_datapoint, minutes_of_datapoint)
        date_int = date_to_int(begin_date_time.split(" ")[0])
        per_quarter_up_array[date_int-1, quarter] = float(row['Not specified Up Price [EUR/MWh] - SCA|NL'])
        per_quarter_down_array[date_int-1, quarter] = float(row['Not specified Down Price [EUR/MWh] - SCA|NL'])
    return per_quarter_up_array, per_quarter_down_array


def imbalance(csv_pd, year):
    if year % 4 == 0:
        per_quarter_mw_array = np.zeros((366, 24*4))
    else:
        per_quarter_mw_array = np.zeros((365, 24*4))
    for index, row in csv_pd.iterrows():
        begin_date_time = row['Imbalance settlement period CET/CEST'].split(' - ')[0]
        hour_of_datapoint = int(begin_date_time.split(':')[0][-2:])
        minutes_of_datapoint = int(begin_date_time.split(':')[1][-2:])
        quarter = quarter_of_day(hour_of_datapoint, minutes_of_datapoint)
        date_int = date_to_int(begin_date_time.split(" ")[0])
        try:
            val = float(row['Total Imbalance [MWh] - SCA|DE(TenneT GER)'])
        except:
            val = float('nan')
        per_quarter_mw_array[date_int-1, quarter] = val
    per_quarter_mw_array = per_quarter_mw_array[~np.isnan(per_quarter_mw_array).any(axis=1), :]
    return per_quarter_mw_array


def quarter_of_day(hour, minutes):
    if minutes < 10:
        quarter = hour*4
    elif minutes < 20:
        quarter = hour*4 + 1
    elif minutes < 40:
        quarter = hour*4 + 2
    else:
        quarter = hour*4 + 3
    return quarter


def analyse_matrix(mat, per_hour=True):
    mean_list = []
    std_list = []
    if per_hour:
        for i in range(0, len(mat[0])):
            mean_list.append(np.mean(mat[:, i]))
            std_list.append(np.std(mat[:, i]))
    else:
        for i in range(0, len(mat)):
            mean_list.append(np.mean(mat[i, :]))
            std_list.append(np.std(mat[i, :]))
    return mean_list, std_list


def date_to_int(date_str):
    date_list = date_str.split(".")
    day = int(date_list[0])
    month = int(date_list[1])
    year = int(date_list[2])
    year_list = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if year%4 == 0:
        year_list[1] = 29
    return day + sum(year_list[:month-1])


def hour_to_idx(hour, date_int):
    return (date_int-1)*24+hour


def create_up_down(df):
    up = np.zeros(int(len(df)/2))
    down = np.zeros(int(len(df)/2))
    for index, row in df.iterrows():
        day_str = row['Contracted time period'].split(' ')[0]
        day = date_to_int(day_str)

        if row['Direction'] == 'Down':
            down[day-1] = float(row['Regulation Price [EUR / MW / ISP]'])
        elif row['Direction'] == 'Up':
            up[day-1] = float(row['Regulation Price [EUR / MW / ISP]'])
        else:
            print(f"ERROR: Check UP/DOWN, found direction {row['Direction']}")
    return up, down


def plot_means(mean_list, std_list, year_list):
    plt.rcParams['axes.axisbelow'] = True
    plt.figure(figsize=(15, 5))
    fig = plt.figure()
    x = np.arange(0, 24)
    x_labels = [f'{st}-{st+1}' for st in x]
    for i in range(0, len(mean_list)):
        plt.errorbar(x, mean_list[i], std_list[i], linestyle='None', label=year_list[i], fmt='o', capsize=5)
    plt.xticks(ticks=x, labels=x_labels, rotation=45)
    plt.title("Netherlands Market Day Ahead Prices")
    plt.xlabel("Hour")
    plt.ylabel("Eur/MWh")
    plt.legend()
    plt.grid()
    fig.tight_layout()
    t = time.localtime()
    timestamp = time.strftime('%b-%d-%Y_%H%M%S', t)
    plt.savefig(f'plots/DayAheadPrices{timestamp}.png', bbox_inches='tight', pad_inches=0.5, dpi=500)
    return


def plot_balance_means(mean_list, std_list, legends):
    plt.rcParams['axes.axisbelow'] = True
    plt.figure(figsize=(15, 5))
    fig = plt.figure()
    x = np.arange(0, 24*4)
    for i in range(0, len(mean_list)):
        plt.errorbar(x, mean_list[i], std_list[i], linestyle='None', label=legends[i], fmt='o', capsize=5)
    plt.title("Netherlands TSO Costs for Balancing Activations")
    plt.xlabel("Day Quarter")
    plt.ylabel("Average Eur/MWh")
    plt.legend()
    plt.grid()
    fig.tight_layout()
    t = time.localtime()
    timestamp = time.strftime('%b-%d-%Y_%H%M%S', t)
    plt.savefig(f'plots/BalancingActivationPrices{timestamp}.png', bbox_inches='tight', pad_inches=0.5, dpi=500)
    return


def plot_imbalance(mean_list, std_list, year_list):
    plt.rcParams['axes.axisbelow'] = True
    plt.figure(figsize=(15, 5))
    fig = plt.figure()
    x = np.arange(0, 24*4)
    for i in range(0, len(mean_list)):
        plt.errorbar(x, mean_list[i], std_list[i], linestyle='None', label=year_list[i], fmt='o', capsize=5)
    plt.title("TenneT Germany per Quarter Total Imbalance in MWh")
    plt.xlabel("Quarter of day")
    plt.ylabel("Average Total Imbalance [MWh]")
    plt.legend()
    plt.grid()
    fig.tight_layout()
    t = time.localtime()
    timestamp = time.strftime('%b-%d-%Y_%H%M%S', t)
    plt.savefig(f'plots/Imbalance{timestamp}.png', bbox_inches='tight', pad_inches=0.5, dpi=500)
    return


def plot_reserve_bars(up, down):
    plt.rcParams['axes.axisbelow'] = True
    plt.figure(figsize=(15, 5))
    fig = plt.figure()
    x = np.arange(1, len(up)+1)
    plt.bar(x, up, label='Direction=Up')
    plt.bar(x, down, bottom=up, label='Total (Direction=Down+Up)')
    plt.title("Netherlands TSO Prices from Reserving Balancing for Automatic Frequency Restoration Reserve ")
    plt.xlabel("Day of 2021")
    plt.ylabel("Regulation Price [Eur/MW/ISP]")
    plt.legend()
    plt.grid()
    fig.tight_layout()
    t = time.localtime()
    timestamp = time.strftime('%b-%d-%Y_%H%M%S', t)
    plt.savefig(f'plots/BalancingReservePrices{timestamp}.png', bbox_inches='tight', pad_inches=0.5, dpi=500)
    return


if __name__ == '__main__':
    if day_ahead_prices:
        mean_lists = []
        std_lists = []
        name_lists = ['Day-ahead Prices_202001010000-202101010000', 'Day-ahead Prices_202101010000-202201010000',
                      'Day-ahead Prices_202201010000-202301010000']
        year_lists = [2020, 2021, 2022]
        for i in range(0, len(name_lists)):
            csv_pd = read_csv_info(name_lists[i])
            per_hour_array = year_to_hour(csv_pd, year_lists[i])
            mean_lst, std_lst = analyse_matrix(per_hour_array)
            mean_lists.append(mean_lst)
            std_lists.append(std_lst)
        plot_means(mean_lists, std_lists, year_lists)
    if reserved_balancing_reserve_prices:
        xl_pd = read_xl_info('Prices of Reserved Balancing Reserves 2021')
        up, down = create_up_down(xl_pd)
        plot_reserve_bars(up, down)
    if activation_balancing_energy:
        csv_pd = read_csv_info('Prices of Activated Balancing Energy_202101010000-202201010000')
        per_quarter_up_array, per_quarter_down_array = balance_activation(csv_pd)
        mean_up_lst, std_up_lst = analyse_matrix(per_quarter_up_array)
        mean_down_lst, std_down_lst = analyse_matrix(per_quarter_down_array)
        mean_total_lst, std_total_lst = analyse_matrix(per_quarter_down_array+per_quarter_up_array)
        plot_balance_means([mean_up_lst, mean_down_lst, mean_total_lst], [std_up_lst, std_down_lst, std_total_lst],
                           ['Direction: Up','Direction: Down', 'Total'])
    if average_total_imbalance:
        mean_lists = []
        std_lists = []
        name_lists = ['Imbalance_202001010000-202101010000', 'Imbalance_202101010000-202201010000',
                      'Imbalance_202201010000-202301010000']
        year_lists = [2020, 2021, 2022]
        for i in range(0, len(name_lists)):
            csv_pd = read_csv_info(name_lists[i])
            per_quarter_mw_array = imbalance(csv_pd, year_lists[i])
            mean_lst, std_lst = analyse_matrix(per_quarter_mw_array)
            mean_lists.append(mean_lst)
            std_lists.append(std_lst)
        plot_imbalance(mean_lists, std_lists, year_lists)