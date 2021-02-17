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
documentName = set_up_globals.clinical_document_name
# data_list = svc.find_demographic_data_only()
# for c in data_list:
#     for field in c:
#         print(field, c[field])
#     print('\n')

# data_list = svc.find_clinical_data()
data_list = svc.find_proteomic_data_only()
if data_list is None:
    print(f'No {documentName} data records.')
    sys.exit(2)

df,_ = utilities.create_df_from_object_list(data_list, Proteomic, 'proteomic')
print(df.head(5))

# Creating an ID column name gives us more interactive capabilities
df['id'] = df['study_id']
df.set_index('id', inplace=True, drop=False)

# -------------------------------------------------------------------------------------
# App layout
uniqueComponentForApp = '-clinical-2'  # Make sure this is different for every app / page
graphComponentID = 'datatable-interactivity-container-scatter' + uniqueComponentForApp
groupDropdownComponentID = 'group-dropdown' + uniqueComponentForApp
comparison1DropdownComponentID = 'compare-dropdown-1' + uniqueComponentForApp
comparison2DropdownComponentID = 'compare-dropdown-2' + uniqueComponentForApp
comparison3DropdownComponentID = 'compare-dropdown-3' + uniqueComponentForApp
rangeSliderComponentID = 'range-slider-1' + uniqueComponentForApp
dataTableComponentID = 'datatable-interactivity-scatter' + uniqueComponentForApp
card_graph = utilities.spinner_wrapper(dbc.Card(id=graphComponentID, body=True, color="secondary", ))
dataTableComponent = utilities.data_table(dataTableComponentID, df)

clinicalGroupList = ['phenotype', 'site', 'sex', 'ethnicity', 'race', 'mecfs_sudden_gradual',
                     'qmep_sudevent', 'qmep_metimediagnosis', 'vo2change', 'atchange']
clinicalNumericList = ['age', 'height_in', 'weight_lbs', 'bmi', 'mecfs_duration',
                       'vo2peak1', 'vo2peak2', 'at1', 'at2']

mark_values = {0:'0',5:'5',10:'10',15:'15',
               20:'20',25:'25',30:'30',35:'35',
               40:'40',45:'45',50:'50',55:'55',
               60:'60',65:'65',70:'70',75:'75',
               80:'80',85:'85',90:'90',95:'95',
               100:'100',105:'105',110:'110',115:'115'}

# Sorting operators (https://dash.plotly.com/datatable/filtering)
layout = html.Div([

    html.Div([
        dbc.Row(dbc.Col(card_graph, width=12), justify="start"),
        # justify="start", "center", "end", "between", "around"
    ]),
    html.Br(),
    html.Div([
        html.Div(dcc.Dropdown(
            id=groupDropdownComponentID, value='phenotype', clearable=False,
            options=[{'label': x, 'value': x} for x in clinicalGroupList],
            multi=False,
            searchable=True,
            placeholder='Select one',
            style={"width": "90%"}
        ), className='two columns', style={"width": "15rem"}),

        html.Div(dcc.Dropdown(
            id=comparison1DropdownComponentID, value='weight_lbs', clearable=False,
            persistence=True, persistence_type='memory',
            options=[{'label': x, 'value': x} for x in clinicalNumericList],
            multi=False,
            searchable=True,
            placeholder='Select one',
            style={"width": "90%"}
        ), className='two columns', style={"width": "15rem"}),

        html.Div(dcc.Dropdown(
            id=comparison2DropdownComponentID, value='bmi', clearable=False,
            persistence=True, persistence_type='memory',
            options=[{'label': x, 'value': x} for x in clinicalNumericList],
            multi=False,
            searchable=True,
            placeholder='Select one',
            style={"width": "90%"}
        ), className='two columns', style={"width": "15rem"}),

        html.Div(dcc.Dropdown(
            id=comparison3DropdownComponentID, value='none', clearable=False,
            persistence=True, persistence_type='memory',
            options=[{'label': x, 'value': x} for x in ['none'] + clinicalNumericList],
            multi=False,
            searchable=True,
            placeholder='Select one',
            style={"width": "90%"}
        ), className='two columns', style={"width": "15rem"}),
    ], className='row'),
    html.Br(),
    html.Div([
        dbc.Row(dbc.Col(dcc.RangeSlider(id=rangeSliderComponentID,
                min=0,
                max=115,
                value=[10,70],
                marks=mark_values,
                allowCross=False,
                pushable=5,
                tooltip={'always visible':False, 'placement':'bottom'},
                step=1), width=12), justify="start"),
    ], style={"width": "70%", "position":"absolute", "left":"5%"}),
    html.Br(),
    html.Br(),
    html.Br(),
    html.Div([
        dbc.Row(dbc.Col(dataTableComponent, width=12), justify="start"),
    ]),
    html.Br(),
])


# -------------------------------------------------------------------------------------
# Create scatter plot
@app.callback(
    Output(component_id=graphComponentID, component_property='children'),
    [Input(component_id=groupDropdownComponentID, component_property='value'),
     Input(component_id=comparison1DropdownComponentID, component_property='value'),
     Input(component_id=comparison2DropdownComponentID, component_property='value'),
     Input(component_id=comparison3DropdownComponentID, component_property='value'),
     Input(component_id=rangeSliderComponentID, component_property='value')]
)
def display_value(group_chosen, compare_1_chosen, compare_2_chosen, compare_3_chosen, range_1):
    # df_fltrd = df[df['Genre'] == genre_chosen]
    # df_fltrd = df_fltrd.nlargest(10, sales_chosen)
    # fig = px.bar(df_fltrd, x=compare_1_chosen, y=compare_2_chosen, color='Platform')
    # fig = fig.update_yaxes(tickprefix="$", ticksuffix="M")

    print(group_chosen)
    print(compare_1_chosen)
    print(compare_2_chosen)
    print(compare_3_chosen)
    print(range_1)

    colorSequence = utilities.set_color_sequence(group_chosen)

    # Filter based on range slider
    df['numeric_age'] = pd.to_numeric(df['age'], errors='coerce')
    dff = df[(df['numeric_age']>=range_1[0])&(df['numeric_age']<=range_1[1])]

    # Add age to title
    title = documentName.capitalize() + ' Data Scatter Plot for Ages ' + str(range_1[0]) + ' to ' + str(range_1[1])

    # If the third compare choice is 'none' then produce a
    # 2D scatter plot, otherwise produce a 3D scatter plot
    if compare_3_chosen.lower() == 'none':
        fig = px.scatter(
            data_frame=dff,
            x=compare_1_chosen,
            y=compare_2_chosen,
            color=group_chosen,
            color_discrete_sequence=colorSequence,
            template='ggplot2',
            title=title,
            # size='age',  # size of bubble
            # size_max=15,  # set the maximum mark size when using size
            hover_name='study_id',  # values appear in bold in the hover tooltip
            height=600)
    else:
        # Use for animation rotation at the end
        x_eye = -1.25
        y_eye = 2
        z_eye = 0.5

        fig = px.scatter_3d(
            data_frame=dff,
            x=compare_1_chosen,
            y=compare_2_chosen,
            z=compare_3_chosen,
            color=group_chosen,
            color_discrete_sequence=colorSequence,
            template='ggplot2',
            title=title,
            size='age',  # size of bubble
            size_max=15,  # set the maximum mark size when using size
            hover_name='study_id',  # values appear in bold in the hover tooltip
            height=600
        ).update_layout(scene_camera_eye=dict(x=x_eye, y=y_eye, z=z_eye),
                        updatemenus=[dict(type='buttons',
                                          showactive=False,
                                          y=1,
                                          x=0.8,
                                          xanchor='left',
                                          yanchor='bottom',
                                          pad=dict(t=45, r=10),
                                          buttons=[dict(label='Play',
                                                        method='animate',
                                                        args=[None, dict(frame=dict(duration=250, redraw=True),
                                                                         transition=dict(duration=0),
                                                                         fromcurrent=True,
                                                                         mode='immediate'
                                                                         )]
                                                        )
                                                   ]
                                          )
                                     ]
                        )

        frames = []
        for t in np.arange(0, 6.26, 0.1):
            xe, ye, ze = rotate_z(x_eye, y_eye, z_eye, -t)
            frames.append(go.Frame(layout=dict(scene_camera_eye=dict(x=xe, y=ye, z=ze))))
        fig.frames = frames

    return [
        dcc.Graph(id='scatter_plot' + uniqueComponentForApp, figure=fig)
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
