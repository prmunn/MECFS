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
documentName = set_up_globals.metabolomics_document_name

data_list = svc.find_metabolomic_data_only()
if data_list is None:
    print(f'No {documentName} data records.')
    sys.exit(2)

df, dataLabelList = utilities.create_df_from_object_list(data_list, [Metabolomic], ['metabolomic'],
                                                         assayResultsFlag=True)
print(df.head(5))

# Creating an ID column name gives us more interactive capabilities
df['id'] = df['study_id']
df.set_index('id', inplace=True, drop=False)

# -------------------------------------------------------------------------------------
# App layout
uniqueComponentForApp = '-metabolomic-1'  # Make sure this is different for every app / page
graphComponentID = 'datatable-interactivity-container-violin' + uniqueComponentForApp
groupDropdownComponentID = 'group-dropdown' + uniqueComponentForApp
comparison1DropdownComponentID = 'compare-dropdown-1' + uniqueComponentForApp
comparison2DropdownComponentID = 'compare-dropdown-2' + uniqueComponentForApp
comparison3DropdownComponentID = 'compare-dropdown-3' + uniqueComponentForApp
radioItemsComponentID = 'radioitems-1' + uniqueComponentForApp
rangeSliderComponentID = 'range-slider-1' + uniqueComponentForApp
dataTableComponentID = 'datatable-interactivity-violin' + uniqueComponentForApp
card_graph = utilities.spinner_wrapper(dbc.Card(id=graphComponentID, body=True, color="secondary", ))
dataTableComponent = utilities.data_table(dataTableComponentID, df)

clinicalGroupList = ['phenotype', 'site', 'sex', 'ethnicity', 'race', 'mecfs_sudden_gradual',
                     'qmep_sudevent', 'qmep_metimediagnosis', 'vo2change', 'atchange']
clinicalNumericList = ['age', 'height_in', 'weight_lbs', 'bmi', 'mecfs_duration',
                       'vo2peak1', 'vo2peak2', 'at1', 'at2']
xAxisList = ['phenotype', 'site', 'sex', 'ethnicity', 'race', 'mecfs_sudden_gradual', 'timepoint', 'biospecimen_type']

mark_values = {0: '0', 5: '5', 10: '10', 15: '15',
               20: '20', 25: '25', 30: '30', 35: '35',
               40: '40', 45: '45', 50: '50', 55: '55',
               60: '60', 65: '65', 70: '70', 75: '75',
               80: '80', 85: '85', 90: '90', 95: '95',
               100: '100', 105: '105', 110: '110', 115: '115'}

# Sorting operators (https://dash.plotly.com/datatable/filtering)
layout = html.Div([

    html.Div([
        dbc.Row(dbc.Col(card_graph, width=12), justify="start"),
        # justify="start", "center", "end", "between", "around"
    ]),
    html.Br(),
    html.Div([
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
                        id=comparison1DropdownComponentID, value='timepoint', clearable=False,
                        persistence=True, persistence_type='memory',
                        options=[{'label': x, 'value': x} for x in xAxisList],
                        multi=False,
                        searchable=True,
                        placeholder='Select one',
                        style={"width": "90%"}
                    ), className='two columns', style={"width": "15rem"})]),

        html.Label(['Y-Axis:',
                    html.Div(dcc.Dropdown(
                        id=comparison2DropdownComponentID, value=dataLabelList[0], clearable=False,
                        persistence=True, persistence_type='memory',
                        options=[{'label': x, 'value': x} for x in dataLabelList],
                        multi=False,
                        searchable=True,
                        placeholder='Select one',
                        style={"width": "90%"}
                    ), className='two columns', style={"width": "15rem"})]),

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
        dbc.Row(dbc.Col(dcc.RadioItems(id=radioItemsComponentID,
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
    [Input(component_id=groupDropdownComponentID, component_property='value'),
     Input(component_id=comparison1DropdownComponentID, component_property='value'),
     Input(component_id=comparison2DropdownComponentID, component_property='value'),
     Input(component_id=radioItemsComponentID, component_property='value'),
     Input(component_id=rangeSliderComponentID, component_property='value')]
)
def display_value(group_chosen, compare_1_chosen, compare_2_chosen, radioitems_1, range_1):
    # df_fltrd = df[df['Genre'] == genre_chosen]
    # df_fltrd = df_fltrd.nlargest(10, sales_chosen)
    # fig = px.bar(df_fltrd, x=compare_1_chosen, y=compare_2_chosen, color='Platform')
    # fig = fig.update_yaxes(tickprefix="$", ticksuffix="M")

    print(group_chosen)
    print(compare_1_chosen)
    print(compare_2_chosen)
    print(radioitems_1)
    print(range_1)

    colorSequence = utilities.set_color_sequence(group_chosen)

    # Filter based on range slider
    df['numeric_age'] = pd.to_numeric(df['age'], errors='coerce')
    dff = df[(df['numeric_age'] >= range_1[0]) & (df['numeric_age'] <= range_1[1])]

    # Filter based on radio items
    if radioitems_1 != 'BOTH':
        dff2 = dff[dff['phenotype'] == radioitems_1]
    else:
        dff2 = dff

    # Add age to title
    title = documentName.capitalize() + ' Violin Plot for Ages ' + str(range_1[0]) + ' to ' + str(range_1[1])

    fig = px.violin(
        # data_frame=df.query("State == ['{}','{}']".format('ALABAMA','NEW YORK')),
        data_frame=dff2,
        x=compare_1_chosen,
        y=compare_2_chosen,
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
        dcc.Graph(id='violin_plot' + uniqueComponentForApp, figure=fig)
    ]


# @app.callback(
#     Output(component_id=graphComponentID, component_property='children'),
#     [Input(component_id=dataTableComponentID, component_property="derived_virtual_data"),
#      Input(component_id=dataTableComponentID, component_property='derived_virtual_selected_rows'),
#      Input(component_id=dataTableComponentID, component_property='derived_virtual_selected_row_ids'),
#      Input(component_id=dataTableComponentID, component_property='selected_rows'),
#      Input(component_id=dataTableComponentID, component_property='derived_virtual_indices'),
#      Input(component_id=dataTableComponentID, component_property='derived_virtual_row_ids'),
#      Input(component_id=dataTableComponentID, component_property='active_cell'),
#      Input(component_id=dataTableComponentID, component_property='selected_cells'),
#      Input(component_id=dataTableComponentID, component_property='selected_columns')]
# )
# def update_line(all_rows_data, slctd_row_indices, slct_rows_names, slctd_rows,
#                 order_of_rows_indices, order_of_rows_names, actv_cell, slctd_cell, slctd_columns):
#     print('***************************************************************************')
#     print('Data across all pages pre or post filtering: {}'.format(all_rows_data))
#     print('---------------------------------------------')
#     print("Indices of selected rows if part of table after filtering:{}".format(slctd_row_indices))
#     print("Names of selected rows if part of table after filtering: {}".format(slct_rows_names))
#     print("Indices of selected rows regardless of filtering results: {}".format(slctd_rows))
#     print('---------------------------------------------')
#     print("Indices of all rows pre or post filtering: {}".format(order_of_rows_indices))
#     print("Names of all rows pre or post filtering: {}".format(order_of_rows_names))
#     print("---------------------------------------------")
#     print("Complete data of active cell: {}".format(actv_cell))
#     print("Complete data of all selected cells: {}".format(slctd_cell))
#     print("---------------------------------------------")
#     print("Indices of selected columns regardless of filtering results: {}".format(slctd_columns))
#
#     if slctd_row_indices is None:
#         slctd_row_indices = []
#
#     if len(slctd_columns) < 1:
#         slctd_columns = ['age', 'weight_lbs']
#
#     dff_all = df if all_rows_data is None else pd.DataFrame(all_rows_data)
#     data = []
#     for index, row in dff_all.iterrows():
#         for col in slctd_columns:
#             dataRow = [row['unique_id'], col, row[col]]
#             data.append(dataRow)
#     dff = pd.DataFrame(data, columns=['unique_id', 'column_name', 'value'])
#
#     # used to highlight selected countries on bar chart
#     colors = ['#7FDBFF' if i in slctd_row_indices else '#0074D9'
#               for i in range(len(dff))]
#
#     return [
#         dcc.Graph(id='line_plot',
#                   figure=px.line(
#                       data_frame=dff,
#                       x='unique_id',
#                       y='value',
#                       color='column_name'
#                   ).update_layout(showlegend=True,
#                                   # xaxis={'categoryorder': 'total ascending'},
#                                   yaxis={'title': 'Values'},
#                                   title={'text': 'Clinical Data Line Plot', 'font': {'size': 28}, 'x': 0.5,
#                                          'xanchor': 'center'})
#                   .update_traces(marker_color=colors, hovertemplate="<b>%{y}%</b><extra></extra>")
#                   )
#     ]


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
