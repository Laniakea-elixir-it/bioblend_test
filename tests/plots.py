#!/usr/bin/env python3
"""
Module containing functions for preprocessing and visualization of disk I/O metrics generated with the
run_workflow.py script.
Once data is collected with the test_disk_encryption.sh script on two Galaxy VMs (one with disk encryption and one
without), it should be divided into two directories: metrics_encrypted, the directory containing metrics measured from
the encrypted VM and metrics, the directory containing metrics measured on the non encrypted VM.
The main function in this module will produce three plots:
1. Boxplot comparing the workflow runtime
2. Boxplot comparing the averaged read speed
3. Boxplot comparing the averaged write speed (3).  
"""

# Dependencies
import argparse
import pandas as pd
import json
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os
import re
from statannotations.Annotator import Annotator



################################################################################
# COMMAND LINE OPTIONS

def cli_options():
    parser = argparse.ArgumentParser(description='Plot disk metrics of workflow')
    parser.add_argument('-i', '--input-dir', dest='basedir', help='Base directory containing metrics and metrics_encrypted directory, each with metrics inside')
    parser.add_argument('--title', dest='main_title', help='Main title')
    parser.add_argument('--font-scale', default=2.8, dest='font_scale', help='Plot font scale')
    parser.add_argument('--notch', default=False, dest='notch', action='store_true', help='If set, notches are shown in boxplots')
    parser.add_argument('--pvalues', default=False, dest='pvalues', action='store_true', help='If set, pvalues are shown in boxplots')
    parser.add_argument('--all-plots', default=False, dest='all_plots', action='store_true', help='If set, all the plots will be produced (also histograms for plain disk I/O metrics)')
    parser.add_argument('-o', '--output', dest='output_file', help='Output file')
    return parser.parse_args()



################################################################################
# DATA PREPROCESSING FUNCTIONS

def filter_time(df, metrics_path):
    """Filter the dstat output dataframe removing measurements outside the time range in which the workflow run

    :param df: Pandas dataframe to be filtered
    :type df: pd.DataFrame
    :param metrics_path: Path to the .json runtime metrics of the workflow
    :type metrics_path: str
    :return: Filtered pandas dataframe
    :rtype: pd.DataFrame
    """
    
    # Set column names
    df.set_axis(['read_tps', 'write_tps', 'rMB/s', 'wMB/s', 'time'], axis=1, inplace=True)
    
    # Convert time to datetime object
    df.loc[:,('time')] = df['time'].apply(lambda x: datetime.strptime(x,'%d-%m %H:%M:%S').replace(year=datetime.now().year))
    
    # Load jobs metrics
    with open(metrics_path,'r') as f:
        jobs_info = json.load(f)

    # Take start and end time
    start_times = []
    end_times = []
    for k,v in jobs_info.items():
        start_times.append(datetime.strptime(v['start'], '%Y-%m-%d %H:%M:%S'))
        end_times.append(datetime.strptime(v['end'], '%Y-%m-%d %H:%M:%S'))
    start_time = min(start_times)
    end_time = max(end_times)
    
    # Filter dstat
    df = df[(df['time'] <= end_time) & (df['time'] >= start_time)].copy(deep=True)

    # Use relative time
    df.loc[:,('time')] = list(range(0,len(df)))
    
    return df


def get_metrics(basedir, encrypted, time_metrics_file='wf_jobs_metrics.json', dstat_metrics_file='dstat_out_wf.csv'):
    """Import all the dstat outputs contained inside 'basedir', preprocess them and return three preprocessed dataframes:
    
    1. Pandas serie containing runtime of the workflow at each iteration.
    2. Dataframe containing plain disk metrics (from dstat output).
    3. Dataframe containing disk metrics averaged at each iteration of the workflow.

    :param basedir: Base directory in which there are the subdirectories containing the metrics.
    :type basedir: str
    :param encrypted: String to be placed in the 'Encrypted' column of the dataframe, should be either 'Encrypted' or 'Non encrypted'
    :type encrypted: str
    :param time_metrics_file: Name of the file inside each subdirectory containing time metrics, defaults to 'wf_jobs_metrics.json'
    :type time_metrics_file: str, optional
    :param dstat_metrics_file: Name of the file inside each subdirectory containing dstat output, defaults to 'dstat_out_wf.csv'
    :type dstat_metrics_file: str, optional
    :return: The three dataframes containing runtime, plain and averaged disk metrics
    :rtype: Tuple of pd.DataFrame
    """
    
    times = []
    list_of_metrics = []
    list_of_avg_metrics = []

    for directory in os.listdir(basedir):
        
        # get interation number
        index = re.findall(r'\d+', directory)[0]
        
        # times
        directory = f'{basedir}/{directory}'
        try:
            with open(f'{directory}/{time_metrics_file}','r') as f:
                jobs_info = json.load(f)
                time = [float(v['runtime_raw_value']) for k,v in jobs_info.items()]
                times += time

            # read/write velocity
            dstat_df = pd.read_csv(f'{directory}/dstat_out{index}/{dstat_metrics_file}',header=[0,1],skiprows=5)
            dstat_df = filter_time(dstat_df, f'{directory}/{time_metrics_file}')
            
            dstat_df['rMB/s'] = dstat_df['rMB/s'].div(1000000)
            dstat_df['wMB/s'] = dstat_df['wMB/s'].div(1000000)

            # Build plain data
            dstat_df['encrypted'] = [encrypted]*len(dstat_df)
            list_of_metrics.append(dstat_df)
            
            # Build averaged data
            means = dstat_df.describe().loc['mean',:]
            means['encrypted'] = encrypted
            list_of_avg_metrics.append(means)

        except FileNotFoundError as e:
            print(e)
    
    avg_df = pd.DataFrame(list_of_avg_metrics)
    plain_df = pd.concat(list_of_metrics)
            
    return times, plain_df, avg_df


def build_time_df(encrypted_time, nonencrypted_time):
    """Merge two pandas series coming from 'get_metrics' containing time metrics

    :param encrypted_time: Pandas serie containing runtimes for the encrypted VM
    :type encrypted_time: pd.Series
    :param nonencrypted_time: Pandas serie containing runtimes for the non encrypted VM
    :type nonencrypted_time: pd.Series
    :return: Pandas dataframe containing the runtimes with the type of VM (encrypted or non encrypted) specified
    :rtype: pd.DataFrame
    """
    time_df = pd.DataFrame({
        'time (s)': encrypted_time + nonencrypted_time,
        'encrypted':['Encrypted']*len(encrypted_time) + ['Non encrypted']*len(nonencrypted_time)
    })
    return time_df


def build_dataframes(basedir, time_metrics_file='wf_jobs_metrics.json', dstat_metrics_file='dstat_out_wf.csv'):
    """Main function for data preprocessing, build metrics dataframes used to plot data.

    :param basedir: Main base directory in which all the metrics are stored.
    :type basedir: str
    :param time_metrics_file: Name of the file containing time metrics, defaults to 'wf_jobs_metrics.json'
    :type time_metrics_file: str, optional
    :param dstat_metrics_file: Name of the file containing the dstat output, defaults to 'dstat_out_wf.csv'
    :type dstat_metrics_file: str, optional
    :return: Three dataframes containing runtime, plain and averaged disk metrics used to plot data
    :rtype: tuple of pd.DataFrames
    """
    
    encrypted_time, encrypted_df, avg_encrypted_df = get_metrics(basedir=f'{basedir}/metrics_encrypted',
                                                                 encrypted='Encrypted',
                                                                 time_metrics_file=time_metrics_file,
                                                                 dstat_metrics_file=dstat_metrics_file)
    nonencrypted_time, nonencrypted_df, avg_nonencrypted_df = get_metrics(basedir=f'{basedir}/metrics',
                                                                          encrypted='Non encrypted',
                                                                          time_metrics_file=time_metrics_file,
                                                                          dstat_metrics_file=dstat_metrics_file)
    
    # runtime dataframe
    time_df = build_time_df(encrypted_time, nonencrypted_time)

    # Disk metrics dataframe
    dstat_df = pd.concat([encrypted_df, nonencrypted_df])

    # Average disk metrics dataframe
    avg_dstat_df = pd.concat([avg_encrypted_df, avg_nonencrypted_df])
    
    return time_df, dstat_df, avg_dstat_df



################################################################################
# DATA VISUALIZATION FUNCTIONS

def boxplot(data, column, ax=0, title='', title_fontsize=40, figsize=None, showfliers=False, notch=True, xlabel=None, pvalues=True):
    """Boxplot to compare metrics between encrypted and non encrypted VMs

    :param data: Dataframe
    :type data: pd.DataFrame
    :param column: Column used for the Y axis
    :type column: str
    :param ax: Axis to put the boxplot in a subplot, defaults to 0
    :type ax: int, optional
    :param title: Plot main title, defaults to ''
    :type title: str, optional
    :param title_fontsize: Main title font size, defaults to 40
    :type title_fontsize: int, optional
    :param figsize: Plot figure size (e.g. (15,10) ), defaults to None
    :type figsize: Tuple, optional
    :param showfliers: Whether to show outliers, defaults to False
    :type showfliers: bool, optional
    :param notch: Whether to show boxplot notches, defaults to True
    :type notch: bool, optional
    :param xlabel: Label of the x axis, defaults to None
    :type xlabel: str, optional
    :param pvalues: Whether to show significance of the difference between the two boxplots, defaults to True
    :type pvalues: bool, optional
    """
    if figsize is not None:
        plt.figure(figsize=figsize)

    # Plot data
    sns.boxplot(ax=ax, data=data, x='encrypted', y=column, showfliers=showfliers, notch=notch)
    
    if pvalues:
        order = ['Encrypted', 'Non encrypted']
        pairs = [tuple(order)]
        annotator = Annotator(ax=ax, pairs=pairs, data=data, x='encrypted', y=column, order=order)
        annotator.configure(test='t-test_ind', text_format='star', loc='inside')
        annotator.apply_and_annotate()
    
    ax.set(xlabel=xlabel)
    ax.set_title(title, fontsize=title_fontsize, pad=40)    


def hist(data, column, ax=0, title='', title_fontsize=40, figsize=None, bins=50, logscale=True, stat='probability'):
    """Histogram to compare metrics between encrypted and non encrypted VMs

    :param data: Dataframe
    :type data: pd.DataFrame
    :param column: Column used for the X axis
    :type column: str
    :param ax: Axis to put histogram in a subplot, defaults to 0
    :type ax: int, optional
    :param title: Plot main title, defaults to ''
    :type title: str, optional
    :param title_fontsize: Main title font size, defaults to 40
    :type title_fontsize: int, optional
    :param figsize: Plot figure size (e.g. (15,10) ), defaults to None
    :type figsize: Tuple, optional
    :param bins: Number of bins in the histogram, defaults to 50
    :type bins: int, optional
    :param logscale: Whether to use log scale for the Y axis, defaults to True
    :type logscale: bool, optional
    :param stat: Stat used to compute the Y axis, defaults to 'probability'
    :type stat: str, optional
    """
    if figsize is not None:
        plt.figure(figsize=figsize)
    
    binrange = (min(data[column]), max(data[column]))
    
    sns.histplot(ax=ax, data=data[data['encrypted']=='Encrypted'][column], bins=bins, binrange=binrange,
                 stat=stat, color=sns.color_palette()[0])
    sns.histplot(ax=ax, data=data[data['encrypted']=='Non encrypted'][column], bins=bins, binrange=binrange,
                 stat=stat, color=sns.color_palette()[1])
    
    ax.set_title(title, fontsize=title_fontsize, pad=40)
    
    if logscale:
        ax.set_yscale('log')
        
    ax.legend(labels=["Encrypted","Non encrypted"])


def all_plots(time_df, dstat_df, avg_dstat_df, main_title='', figsize=(40, 25), wspace=0.2, hspace=0.4, main_title_fontsize=50):
    """Produce main figure with all the subplots:

    1. Boxplots of the workflow runtimes
    2. Histograms of the read speed
    3. Histograms of the write speed
    4. Boxplots of the averaged read speed
    5. Boxplots of the averaged write speed

    :param time_df: Dataframe containing runtimes of encrypted and non encrypted VM.
    :type time_df: pd.DataFrame
    :param dstat_df: Dataframe containing plain dstat output of encrypted and non encrypted VM.
    :type dstat_df: pd.DataFrame
    :param avg_dstat_df: Dataframe containing dstat output averaged for each iteration of encrypted and non encrypted VM.
    :type avg_dstat_df: pd.DataFrame
    :param main_title: Main title of the figure, defaults to ''
    :type main_title: str, optional
    :param figsize: Figure size, defaults to (40, 25)
    :type figsize: tuple, optional
    :param wspace: Width of the space between each subplot, defaults to 0.2
    :type wspace: float, optional
    :param hspace: Height of the space between each subplot, defaults to 0.4
    :type hspace: float, optional
    :param main_title_fontsize: Size of the main title, defaults to 50
    :type main_title_fontsize: int, optional
    :return: Figure object containing the plots
    :rtype: matplotlib.figure.Figure
    """

    # Set figure settings
    fig, axes = plt.subplots(2, 3, figsize=figsize)
    fig.delaxes(axes[1,2])
    fig.subplots_adjust(wspace=wspace, hspace=hspace)
    fig.suptitle(main_title,fontsize=main_title_fontsize)

    # TIME
    boxplot(time_df, 'time (s)', ax=axes[0,0], title='Runtime')

    # READ SPEED
    hist(dstat_df, 'rMB/s', ax=axes[0,1], title='Read speed')

    # WRITE SPEED
    hist(dstat_df, 'wMB/s', ax=axes[0,2], title='Write speed')

    # AVERGE READ SPEED
    boxplot(avg_dstat_df, 'rMB/s', ax=axes[1,0], title='Average read speed')

    # AVERAGE WRITE SPEED
    boxplot(avg_dstat_df, 'wMB/s', ax=axes[1,1], title='Average write speed')

    return fig


def main_plots(time_df, avg_dstat_df, main_title='', figsize=(40, 15), wspace=0.2, hspace=0.4, main_title_fontsize=50,
               notch=False, pvalues=False):
    """Function displaying the main plots:

    :param time_df: Dataframe containing runtimes of encrypted and non encrypted VM.
    :type time_df: pd.DataFrame
    :param dstat_df: Dataframe containing plain dstat output of encrypted and non encrypted VM.
    :type dstat_df: pd.DataFrame
    :param avg_dstat_df: Dataframe containing dstat output averaged for each iteration of encrypted and non encrypted VM.
    :type avg_dstat_df: pd.DataFrame
    :param main_title: Main title of the figure, defaults to ''
    :type main_title: str, optional
    :param figsize: Figure size, defaults to (40, 25)
    :type figsize: tuple, optional
    :param wspace: Width of the space between each subplot, defaults to 0.2
    :type wspace: float, optional
    :param hspace: Height of the space between each subplot, defaults to 0.4
    :type hspace: float, optional
    :param main_title_fontsize: Size of the main title, defaults to 50
    :type main_title_fontsize: int, optional
    :param notch: Whether to show notches in boxplots, defaults to False
    :type notch: bool, optional
    :param pvalues: Whether to show significance of the difference between the two boxplots, defaults to False
    :type pvalues: bool, optional
    :return: Figure object containing the plots
    :rtype: matplotlib.figure.Figure
    """

    fig, axes = plt.subplots(1, 3, figsize=figsize)
    fig.subplots_adjust(wspace=wspace, hspace=hspace)
    fig.suptitle(main_title,fontsize=main_title_fontsize, y=1.05)

    # TIME
    boxplot(time_df, 'time (s)', ax=axes[0], title='Runtime', notch=notch, pvalues=pvalues)
    axes[0].set(ylabel='Time (s)')

    # AVERGE READ SPEED
    boxplot(avg_dstat_df, 'rMB/s', ax=axes[1], title='Average read speed', notch=notch, pvalues=pvalues)
    axes[1].set(ylabel='Read speed (MB/s)')

    # AVERAGE WRITE SPEED
    boxplot(avg_dstat_df, 'wMB/s', ax=axes[2], title='Average write speed', notch=notch, pvalues=pvalues)
    axes[2].set(ylabel='Write speed (MB/s)')

    return fig



if __name__=='__main__':

    # Get CLI options
    options = cli_options()
    options.basedir = options.basedir.rstrip('/')

    # Build dataframes
    time_df, dstat_df, avg_dstat_df = build_dataframes(basedir=options.basedir)

    sns.set(font_scale=options.font_scale)

    if options.all_plots:
        # Build figure containing all plots
        fig = all_plots(time_df, dstat_df, avg_dstat_df, main_title=options.main_title)
    
    else:
        # Build figure containing main plots
        fig = main_plots(time_df, avg_dstat_df, main_title=options.main_title, notch=options.notch, pvalues=options.pvalues)

    # Save figure to output
    fig.savefig(options.output_file, bbox_inches='tight')