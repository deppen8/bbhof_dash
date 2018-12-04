import pandas as pd
import altair as alt
alt.renderers.enable('notebook')
from colors import player_colors

def hof_theme():
    return {
        "config": {
            "title": {
                "fontSize": 18,
            },
            "axisX": {
                "domain": True,
                "domainWidth": 1,
                "grid": True,
                "gridWidth": 0.5,
                "labelFontSize": 14,
                "labelAngle": 0,
                "ticks": False, 
                "tickSize": 5,
                "titleFontSize": 16,
            },
            "axisY": {
                "domain": True,
                "grid": False,
                "gridWidth": 0.5,
                "labelFontSize": 14,
                "labelAngle": 0, 
                "ticks": True,
                "titleFontSize": 16,
            },
            "header": {
                "labelFontSize": 16,
                "titleFontSize": 16
            },
            "legend": {
                "labelFontSize": 12,
                "symbolSize": 100, # default,
                "titleFontSize": 12,
            }
        }
    }

alt.themes.register("hof_theme", hof_theme)
alt.themes.enable("hof_theme")


def read_votes(excel_file='data.xlsx', sheet_name='ballots'):
    '''import data from excel file
    
    Parameters
    ----------
    excel_file : str, optional
        path to the data file
    sheet_name : str, optional
        excel sheet with vote data
    
    Returns
    -------
    ballots : pandas DataFrame
        cleaned and order set of vote data
    '''

    raw = pd.read_excel(excel_file, sheet=sheet_name, dtype={'date':'datetime64'})  # read data from excel
    ballots = raw.replace(to_replace='x', value=1).fillna(0)  # replace x with 1, fill NaN to 0
    
    ballots['ballot_id'] = range(1, ballots.shape[0]+1)
    
    col_order = ['ballot_id', 'voter', 'date', 'n_votes', 'source'] + ballots.columns.tolist()[1:-4]
    ballots = ballots[col_order]
    ballots.iloc[:,5:] = ballots.iloc[:,5:].astype(int)  # set player columns to int dtype
    
    return ballots


def calculate_benchmarks(ballots, expected_total_ballots=412):
    '''find values for some key vote landmarks
    
    Parameters
    ----------
    ballots : pandas DataFrame
        DataFrame in the form returned by `read_votes()`
    expected_total_ballots : int, optional
        number of ballots expected to be submitted
    
    Returns
    -------
    pandas DataFrame
        DataFrame of with one row
    '''

    n_ballots = ballots['ballot_id'].max()
    pacemark = n_ballots * .75
    expected_threshold = expected_total_ballots * .75
    percent_submitted = n_ballots / expected_total_ballots * 100

    return pd.DataFrame({'induction_pace': [pacemark],
                         'expected_threshold': [expected_threshold],
                         'expected_total_ballots': [expected_total_ballots],
                         'percent_submitted': [percent_submitted],
                         'n_ballots': [n_ballots]
                         })


def tidy_ballots(ballots):
    '''Turn vote data into a 'tidy' dataset
    
    Parameters
    ----------
    ballots : pandas DataFrame
        DataFrame in the form returned by `read_votes()`
    
    Returns
    -------
    pandas DataFrame
        Tidy version of the ballot data
    '''
    
    return pd.melt(ballots, 
                   id_vars=['ballot_id', 'voter', 'date', 'n_votes', 'source'], 
                   var_name='player', value_name='votes')


def remove_no_votes(tidy_ballots_df):
    '''limit data to only players receiving votes
    
    Parameters
    ----------
    tidy_ballots_df : pandas DataFrame
        DataFrame of the form produced by `tidy_ballots()`
    
    Returns
    -------
    pandas DataFrame
        equivalent to the input with some players' data removed
    '''

    vote_sums = tidy_ballots_df.groupby('player')['votes'].sum().reset_index()
    zeros = vote_sums[vote_sums['votes']==0]
    return tidy_ballots_df[~tidy_ballots_df['player'].isin(zeros['player'])]


def calculate_cumsum_votes(tidy_ballots_df):
    '''find cumulative sum through time per player
    
    Parameters
    ----------
    tidy_ballots_df : pandas DataFrame
        DataFrame of the form produced by `tidy_ballots()`
    
    Returns
    -------
    pandas DataFrame
        same as input with new `cumulative_votes` column
    '''

    date_sums = tidy_ballots_df.groupby(['player', 'date'])['votes'].sum().reset_index()
    date_cumsums = date_sums.groupby(['player'])['votes'].cumsum()
    date_sums['cumulative_votes'] = date_cumsums
    return date_sums


def make_plots(tidy_ballots_df, benchmarks_df, colors):
    '''create two linked output plots
    
    Parameters
    ----------
    tidy_ballots_df : pandas DataFrame
        DataFrame of the form produced by tidy_ballots()
    benchmarks_df : pandas DataFrame
        DataFrame of the form produced by `calculate_benchmarks()`
    colors : dict
        Dictionary of the form `'player name': 'hex_color'`
    
    Returns
    -------
    altair Chart object
        An altair chart consisting of a horizontal bar plot and a linked line plot
    '''

    selection = alt.selection_multi(fields=['player'])

    top = alt.Chart().mark_bar().encode(
        x = alt.X('sum(votes):Q', scale=alt.Scale(domain=(0, 412)), axis=alt.Axis(title='total votes')),
        y = alt.Y('player:N', sort=alt.EncodingSortField(field='votes', op='sum', order='descending'), axis=alt.Axis(title=None)),
        tooltip = alt.Tooltip('sum(votes):Q', title='votes'),
        color=alt.condition(selection, 
                            alt.Color('player:N', legend=None, scale=colors),
                            alt.value('lightgray'))
    ).properties(
        width=600, height=300,
        selection=selection
    )
    
    bottom = alt.Chart().mark_line(point=True).encode(
        x = alt.X('yearmonthdate(date):T', axis=alt.Axis(title='date')),
        y = alt.Y('cumulative_votes:Q', axis = alt.Axis(title='cumulative votes')),
        color = alt.Color('player:N', legend=None, scale=colors),
        tooltip = alt.Tooltip('player:N', title='null')
    ).properties(
        width=600, height=200
    ).transform_filter(
        selection
    )

    current_pace_bars = alt.Chart(benchmarks_df).mark_rule(color='orangered').encode(
        x='induction_pace:Q',
        tooltip=alt.Tooltip('induction_pace:Q')
    )

    expected_threshold = alt.Chart(benchmarks_df).mark_rule(color='goldenrod', size=4).encode(
        x='expected_threshold:Q',
        tooltip=alt.Tooltip('expected_threshold:Q')
    )

    current_pace_lines = alt.Chart(benchmarks_df).mark_rule(color='orangered').encode(
        y='induction_pace:Q',
        tooltip=alt.Tooltip('induction_pace:Q')
    )

    return alt.vconcat((top + current_pace_bars + expected_threshold), (bottom + current_pace_lines), data=tidy_ballots_df)


df = read_votes()
benchmarks = calculate_benchmarks(df)

current_ballots = tidy_ballots(df)

vote_getters = remove_no_votes(current_ballots)

cumsums = calculate_cumsum_votes(vote_getters)

vote_getters_cumsums = vote_getters.merge(cumsums.drop(columns=['votes']), how='left', on=['date', 'player'])

player_names = list(player_colors.keys())
symbol_colors = list(player_colors.values())

color_scale = alt.Scale(
            domain=player_names,
            range=symbol_colors
        )

dashboard = make_plots(vote_getters_cumsums, benchmarks, color_scale)

dashboard.save('_includes/ballot_viz.html')
