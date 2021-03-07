import sys

import dash  # (version 1.12.0)
from dash.dependencies import Input, Output, State
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from app import app

import data.mongo_setup as mongo_setup
from infrastructure.switchlang import switch
import infrastructure.state as state
import services.data_service as svc

from data.clinical_data import ClinicalData
from data.redcap import Redcap
from data.assay_classes import Proteomic
from data.assay_classes import Cytokine
from data.assay_classes import Metabolomic
from data.scrnaseq_summary import ScRNAseqSummary
from data.biospecimens import Biospecimen
from data.users import User


def rotate_z(x, y, z, theta):
    w = x + 1j * y
    return np.real(np.exp(1j * theta) * w), np.imag(np.exp(1j * theta) * w), z


# Set up globals
import utilities
import set_up_globals

MECFSVersion = set_up_globals.MECFSVersion
data_folder = set_up_globals.data_folder

# Register connection to MongoDB
mongo_setup.global_init(database_name=set_up_globals.database_name)

# -------------------------------------------------------------------------------------
# Import data into pandas
# documentName = set_up_globals.proteomics_document_name

pathwayList = ['Cytokine / proteomic test']
pathway_name = pathwayList[0]
dataLabelPathwayIDs = svc.find_pathway_data(pathway_name)
for idx, c in enumerate(dataLabelPathwayIDs.data_label_references):
    print(' {}. {}: {}'.format(idx + 1, c.data_label, c.gene_symbol_references[0].data_label))

data_list = svc.test_pathway_mapping()
if data_list is None:
    print(f'No data records.')
    sys.exit(2)

df, dataLabelList = utilities.create_df_from_object_list(data_list,
                                                         [Proteomic, Cytokine],
                                                         ['proteomic', 'cytokine'],
                                                         assayResultsFlag=True,
                                                         dataLabelPathwayIDs=dataLabelPathwayIDs)

print('dataLabelList:', dataLabelList)

# Normalize
proteomicIndex = df[df['assay_type'] == set_up_globals.proteomics_document_name].index
cytokineIndex = df[df['assay_type'] == set_up_globals.cytokines_document_name].index
print(df.loc[cytokineIndex].head(10))
for col in dataLabelList:
    proteomicSum = df.loc[proteomicIndex, col].sum()
    if proteomicSum > 0:
        df.loc[proteomicIndex, col] = df.loc[proteomicIndex, col] / proteomicSum
    cytokineSum = df.loc[cytokineIndex, col].sum()
    if cytokineSum > 0:
        df.loc[cytokineIndex, col] = df.loc[cytokineIndex, col] / cytokineSum
print(df.loc[cytokineIndex].head(10))

df['aggregated_result'] = 0
df['proteomic_aggregated_result'] = 0
df['cytokine_aggregated_result'] = 0
for idx, c in df.iterrows():
    # print(' {}. {}: {}'.format(idx + 1, c.study_id,
    #                            'ME/CFS patient' if c.phenotype == 'ME/CFS' else 'Healthy control'))
    # print('      * Assay summary: {}, {}'.format(c.assay_type, c.timepoint))
    arList = []
    for ar in dataLabelList:
        if not np.isnan(c[ar]):
            arList.append(c[ar])
        # print('            * Results: {}, {}'.format(ar, c[ar]))
    # print(np.ma.average(arList))
    df.loc[idx, 'aggregated_result'] = np.ma.average(arList)
    if df.loc[idx, 'assay_type'] == set_up_globals.proteomics_document_name:
        df.loc[idx, 'proteomic_aggregated_result'] = np.ma.average(arList)
    if df.loc[idx, 'assay_type'] == set_up_globals.cytokines_document_name:
        df.loc[idx, 'cytokine_aggregated_result'] = np.ma.average(arList)

for idx, c in df.iterrows():
    # print(' {}. {}: {} {}'.format(idx + 1, c.study_id, c.assay_type, c.timepoint))
    if df.loc[idx, 'assay_type'] == set_up_globals.proteomics_document_name:
        study_id = df.loc[idx, 'study_id']
        timepoint = df.loc[idx, 'timepoint']
        cytokine_aggregated_result = df.loc[
            (df['study_id'] == study_id) & (df['assay_type'] == set_up_globals.cytokines_document_name) & (
                        df['timepoint'] == timepoint), 'cytokine_aggregated_result'].mean()
        df.loc[idx, 'cytokine_aggregated_result'] = cytokine_aggregated_result
    if df.loc[idx, 'assay_type'] == set_up_globals.cytokines_document_name:
        study_id = df.loc[idx, 'study_id']
        timepoint = df.loc[idx, 'timepoint']
        proteomic_aggregated_result = df.loc[
            (df['study_id'] == study_id) & (df['assay_type'] == set_up_globals.proteomics_document_name) & (
                        df['timepoint'] == timepoint), 'proteomic_aggregated_result'].mean()
        df.loc[idx, 'proteomic_aggregated_result'] = proteomic_aggregated_result
print(df.head(5))

# Creating an ID column name gives us more interactive capabilities
df['id'] = df['study_id']
df.set_index('id', inplace=True, drop=False)

# -------------------------------------------------------------------------------------
# App layout
uniqueComponentForApp = '-proteomic-cytokine-1'  # Make sure this is different for every app / page
graphComponentID = 'datatable-interactivity-container' + uniqueComponentForApp
pathwayDropdownComponentID = 'pathway-dropdown' + uniqueComponentForApp
groupDropdownComponentID = 'group-dropdown' + uniqueComponentForApp
comparison1DropdownComponentID = 'compare-dropdown-1' + uniqueComponentForApp
comparison2DropdownComponentID = 'compare-dropdown-2' + uniqueComponentForApp
comparison3DropdownComponentID = 'compare-dropdown-3' + uniqueComponentForApp
filterRadioItemsComponentID = 'filter-radioitems-1' + uniqueComponentForApp
plotRadioItemsComponentID = 'plot-radioitems-1' + uniqueComponentForApp
rangeSliderComponentID = 'range-slider-1' + uniqueComponentForApp
dataTableComponentID = 'datatable-interactivity' + uniqueComponentForApp
card_graph = utilities.spinner_wrapper(dbc.Card(id=graphComponentID, body=True, color="secondary", ))
dataTableComponent = utilities.data_table(dataTableComponentID, df)

clinicalGroupList = ['phenotype', 'site', 'sex', 'ethnicity', 'race', 'mecfs_sudden_gradual',
                     'qmep_sudevent', 'qmep_metimediagnosis', 'vo2change', 'atchange']
clinicalNumericList = ['age', 'height_in', 'weight_lbs', 'bmi', 'mecfs_duration',
                       'vo2peak1', 'vo2peak2', 'at1', 'at2']
xAxisList = ['phenotype', 'site', 'sex', 'ethnicity', 'race', 'mecfs_sudden_gradual', 'timepoint', 'biospecimen_type',
             'assay_type', 'assay_method']

mark_values = {0: '0', 5: '5', 10: '10', 15: '15',
               20: '20', 25: '25', 30: '30', 35: '35',
               40: '40', 45: '45', 50: '50', 55: '55',
               60: '60', 65: '65', 70: '70', 75: '75',
               80: '80', 85: '85', 90: '90', 95: '95',
               100: '100', 105: '105', 110: '110', 115: '115'}

# Sorting operators (https://dash.plotly.com/datatable/filtering)
layout = html.Div([

    html.Div([
        html.P(children="Select type of plot",
               style={"text-align": "left", "font-size": "100%"})
    ]),

    html.Div([
        dbc.Row(dbc.Col(dcc.RadioItems(id=plotRadioItemsComponentID,
                                       options=[
                                           {'label': 'Scatter plot', 'value': 'SCATTER'},
                                           {'label': 'Violin plot', 'value': 'VIOLIN'}
                                       ],
                                       value='VIOLIN',
                                       labelStyle={'display': 'inline-block',
                                                   'padding': '0.5rem 1rem',
                                                   'border-radius': '0.5rem'}
                                       ), width=12), justify="start"),
    ], style={"width": "70%", "position": "absolute", "left": "5%"}),
    html.Br(),
    html.Br(),
    html.Div([
        dbc.Row(dbc.Col(card_graph, width=12), justify="start"),
        # justify="start", "center", "end", "between", "around"
    ]),
    html.Br(),
    html.Div([
        html.Label(['Pathway:',
                    html.Div(dcc.Dropdown(
                        id=pathwayDropdownComponentID, value=pathwayList[0], clearable=False,
                        options=[{'label': x, 'value': x} for x in pathwayList],
                        multi=False,
                        searchable=True,
                        placeholder='Select one',
                        style={"width": "90%"}
                    ), className='two columns', style={"width": "15rem"})]),

        html.Label(['Group By:',
                    html.Div(dcc.Dropdown(
                        id=groupDropdownComponentID, value='phenotype', clearable=False,
                        options=[{'label': x, 'value': x} for x in clinicalGroupList],
                        multi=False,
                        searchable=True,
                        placeholder='Select one',
                        style={"width": "90%"}
                    ), className='two columns', style={"width": "15rem"})]),

        html.Label(['X-Axis:',
                    html.Div(dcc.Dropdown(
                        id=comparison1DropdownComponentID, value='assay_type', clearable=False,
                        persistence=True, persistence_type='memory',
                        options=[{'label': x, 'value': x} for x in xAxisList],
                        multi=False,
                        searchable=True,
                        placeholder='Select one',
                        style={"width": "90%"}
                    ), className='two columns', style={"width": "15rem"})]),

        # html.Label(['Y-Axis:',
        #             html.Div(dcc.Dropdown(
        #                 id=comparison2DropdownComponentID, value=dataLabelList[0], clearable=False,
        #                 persistence=True, persistence_type='memory',
        #                 options=[{'label': x, 'value': x} for x in dataLabelList],
        #                 multi=False,
        #                 searchable=True,
        #                 placeholder='Select one',
        #                 style={"width": "90%"}
        #             ), className='two columns', style={"width": "15rem"})]),

        # html.Div(dcc.Dropdown(
        #     id=comparison3DropdownComponentID, value='none', clearable=False,
        #     persistence=True, persistence_type='memory',
        #     options=[{'label': x, 'value': x} for x in ['none'] + clinicalNumericList],
        #     multi=False,
        #     searchable=True,
        #     placeholder='Select one',
        #     style={"width": "90%"}
        # ), className='two columns', style={"width": "15rem"}),
    ], className='row'),
    html.Br(),
    html.Div([
        html.P(children="Filter by Phenotype and Age",
               style={"text-align": "left", "font-size": "100%"})
    ]),

    html.Div([
        dbc.Row(dbc.Col(dcc.RadioItems(id=filterRadioItemsComponentID,
                                       options=[
                                           {'label': 'ME/CFS', 'value': 'ME/CFS'},
                                           {'label': 'Healthy Control', 'value': 'HC'},
                                           {'label': 'Both', 'value': 'BOTH'}
                                       ],
                                       value='BOTH',
                                       labelStyle={'display': 'inline-block',
                                                   'padding': '0.5rem 1rem',
                                                   'border-radius': '0.5rem'}
                                       ), width=12), justify="start"),
    ], style={"width": "70%", "position": "absolute", "left": "5%"}),
    html.Br(),
    html.Br(),
    html.Div([
        dbc.Row(dbc.Col(dcc.RangeSlider(id=rangeSliderComponentID,
                                        min=0,
                                        max=115,
                                        value=[10, 70],
                                        marks=mark_values,
                                        allowCross=False,
                                        pushable=5,
                                        tooltip={'always visible': False, 'placement': 'bottom'},
                                        step=1), width=12), justify="start"),
    ], style={"width": "70%", "position": "absolute", "left": "5%"}),
    html.Br(),
    html.Br(),
    html.Br(),
    html.Div([
        dbc.Row(dbc.Col(dataTableComponent, width=12), justify="start"),
    ]),
    html.Br(),
])


# -------------------------------------------------------------------------------------
# Create violin plot
@app.callback(
    Output(component_id=graphComponentID, component_property='children'),
    [Input(component_id=pathwayDropdownComponentID, component_property='value'),
     Input(component_id=groupDropdownComponentID, component_property='value'),
     Input(component_id=comparison1DropdownComponentID, component_property='value'),
     Input(component_id=filterRadioItemsComponentID, component_property='value'),
     Input(component_id=plotRadioItemsComponentID, component_property='value'),
     Input(component_id=rangeSliderComponentID, component_property='value')]
)
def display_value(pathway_chosen, group_chosen, compare_1_chosen, filter_radioitems_1, plot_radioitems_1, range_1):
    # df_fltrd = df[df['Genre'] == genre_chosen]
    # df_fltrd = df_fltrd.nlargest(10, sales_chosen)
    # fig = px.bar(df_fltrd, x=compare_1_chosen, y=compare_2_chosen, color='Platform')
    # fig = fig.update_yaxes(tickprefix="$", ticksuffix="M")

    print(pathway_chosen)
    print(group_chosen)
    print(compare_1_chosen)
    print(filter_radioitems_1)
    print(plot_radioitems_1)
    print(range_1)

    colorSequence = utilities.set_color_sequence(group_chosen)

    # Filter based on range slider
    df['numeric_age'] = pd.to_numeric(df['age'], errors='coerce')
    dff = df[(df['numeric_age'] >= range_1[0]) & (df['numeric_age'] <= range_1[1])]

    # Filter based on radio items
    if filter_radioitems_1 != 'BOTH':
        dff2 = dff[dff['phenotype'] == filter_radioitems_1]
    else:
        dff2 = dff

    # Add age to title
    title = 'Proteomic / Cytokine comparison plot for ages ' + str(range_1[0]) + ' to ' + str(range_1[1])

    if plot_radioitems_1 == 'SCATTER':
        fig = px.scatter(
            data_frame=df,
            x='proteomic_aggregated_result',
            y='cytokine_aggregated_result',
            color=group_chosen,
            color_discrete_sequence=colorSequence,
            template='ggplot2',
            title=title,
            # size='size',  # size of bubble
            # size_max=30,  # set the maximum mark size when using size
            hover_name='study_id',  # values appear in bold in the hover tooltip
            hover_data=[group_chosen, 'timepoint'],  # values appear as extra data in the hover tooltip
            height=600)
    else:
        fig = px.violin(
            # data_frame=df.query("State == ['{}','{}']".format('ALABAMA','NEW YORK')),
            data_frame=dff2,
            x=compare_1_chosen,
            y='aggregated_result',
            category_orders={
                'timepoint': ['D1-PRE', 'D1-POST', 'D2-PRE', 'D2-POST']},
            orientation="v",  # vertical 'v' or horizontal 'h'
            points='all',  # 'outliers','suspectedoutliers', 'all', or False
            box=True,  # draw box inside the violins
            color=group_chosen,  # differentiate markers by color
            violinmode="group",  # 'overlay' or 'group'
            color_discrete_sequence=colorSequence,
            # color_discrete_map={"ALABAMA": "blue" ,"NEW YORK":"magenta"}, # map your chosen colors

            hover_name='study_id',  # values appear in bold in the hover tooltip
            hover_data=[group_chosen, 'timepoint'],  # values appear as extra data in the hover tooltip
            # custom_data=['Program'],    # values are extra data to be used in Dash callbacks

            # facet_row='State',          # assign marks to subplots in the vertical direction
            # facet_col='Period',         # assign marks to subplots in the horizontal direction
            # facet_col_wrap=2,           # maximum number of subplot columns. Do not set facet_row

            # log_x=True,                 # x-axis is log-scaled
            # log_y=True,                 # y-axis is log-scaled

            # labels={"State": "STATE"},  # map the labels
            title=title,
            # width=1050,  # figure width in pixels
            height=600,  # igure height in pixels
            template='ggplot2',  # 'ggplot2', 'seaborn', 'simple_white', 'plotly',
            # 'plotly_white', 'plotly_dark', 'presentation',
            # 'xgridoff', 'ygridoff', 'gridon', 'none'

            # animation_frame='Year',     # assign marks to animation frames
            # animation_group='',         # use only when df has multiple rows with same object
            # range_x=[5,50],             # set range of x-axis
            # range_y=[-5,100],           # set range of y-axis
            # category_orders={'Year':[2015,2016,2017,2018,2019]},    # set a specific ordering of values per column
        )

    return [
        dcc.Graph(id='plot' + uniqueComponentForApp, figure=fig)
    ]


# -------------------------------------------------------------------------------------
# Highlight selected column
@app.callback(
    Output(dataTableComponentID, 'style_data_conditional'),
    [Input(dataTableComponentID, 'selected_columns')]
)
def update_styles(selected_columns):
    return [{
        'if': {'column_id': i},
        'background_color': '#D2F3FF'
    } for i in selected_columns]
