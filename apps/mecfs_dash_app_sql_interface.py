import sys

import dash  # (version 1.12.0)
from dash.dependencies import Input, Output, State
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto  # pip install dash-cytoscape==0.2.0 or higher
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
from data.clinical_data import ClinicalDataVersionHistory
from data.redcap import Redcap
from data.assay_classes import Proteomic
from data.assay_classes import Cytokine
from data.assay_classes import Metabolomic

from data.scrnaseq_summary import ScRNAseqSummary
from data.biospecimens import Biospecimen
from data.biospecimens import BiospecimenVersionHistory
from data.biospecimens import BiospecimenTubeInfo
from data.users import User
from data.event_log import Event_log

from data.assay_results import AssayResults
from data.data_label_types import DataLabels
from data.data_label_types import DataLabelPathways


def rotate_z(x, y, z, theta):
    w = x + 1j * y
    return np.real(np.exp(1j * theta) * w), np.imag(np.exp(1j * theta) * w), z


def build_display_of_database_schema(tableName):
    attributes = []
    if tableName == 'Demographic data':
        attributes = utilities.attributes(ClinicalData)
    elif tableName == 'Demographic history':
        attributes = utilities.attributes(ClinicalDataVersionHistory)
    elif tableName == 'Users':
        attributes = utilities.attributes(User)
    elif tableName == 'Event log':
        attributes = utilities.attributes(Event_log)
    elif tableName == 'Biospecimen data':
        attributes = utilities.attributes(Biospecimen)
    elif tableName == 'Biospecimen history':
        attributes = utilities.attributes(BiospecimenVersionHistory)
    elif tableName == 'Biospecimen tube info':
        attributes = utilities.attributes(BiospecimenTubeInfo)
    elif tableName == 'Redcap':
        attributes = utilities.attributes(Redcap)
    elif tableName == 'Proteomic':
        attributes = utilities.attributes(Proteomic)
    elif tableName == 'Cytokine':
        attributes = utilities.attributes(Cytokine)
    elif tableName == 'Metabolomic':
        attributes = utilities.attributes(Metabolomic)
    elif tableName == 'Assay results':
        attributes = utilities.attributes(AssayResults)
    elif tableName == 'Data labels':
        attributes = utilities.attributes(DataLabels)
    elif tableName == 'Data label pathways':
        attributes = utilities.attributes(DataLabelPathways)
    elif tableName == 'Gene symbol ref':
        attributes = utilities.attributes(DataLabels)
    elif tableName == 'Ensembl gene ID ref':
        attributes = utilities.attributes(DataLabels)
    elif tableName == 'Cytokine label ref':
        attributes = utilities.attributes(DataLabels)
    elif tableName == 'Metabolomic label ref':
        attributes = utilities.attributes(DataLabels)

    htmlPChildren = []
    for attrib in attributes:
        htmlPChildren.append(attrib)
        htmlPChildren.append(html.Br())

    cardChildren = [html.H4(tableName, className="card-title"),
                    html.Hr(),
                    html.P(htmlPChildren, className="card-text")]

    return cardChildren


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
# data_list = svc.find_clinical_data()
data_list = svc.find_proteomic_data_only()
if data_list is None:
    print(f'No {documentName} data records.')
    sys.exit(2)

df, _ = utilities.create_df_from_object_list(data_list, [Proteomic], ['proteomic'])
print(df.head(5))

# Creating an ID column name gives us more interactive capabilities
df['id'] = df['study_id']
df.set_index('id', inplace=True, drop=False)

# -------------------------------------------------------------------------------------
# App layout
uniqueComponentForApp = '-sql-interface-1'  # Make sure this is different for every app / page
buttonQuestion1ID = 'button-question-1' + uniqueComponentForApp
buttonQuestion2ID = 'button-question-2' + uniqueComponentForApp
buttonQuestion3ID = 'button-question-3' + uniqueComponentForApp
collapse1ID = 'collapse-1' + uniqueComponentForApp
collapse2ID = 'collapse-2' + uniqueComponentForApp
collapse3ID = 'collapse-3' + uniqueComponentForApp
graphComponentID = 'cytoscape-graph' + uniqueComponentForApp
tableDefinitionID = 'table-definition-1' + uniqueComponentForApp
sqlInputID = 'sql-input-1' + uniqueComponentForApp
groupDropdownComponentID = 'group-dropdown' + uniqueComponentForApp
comparison1DropdownComponentID = 'compare-dropdown-1' + uniqueComponentForApp
comparison2DropdownComponentID = 'compare-dropdown-2' + uniqueComponentForApp
comparison3DropdownComponentID = 'compare-dropdown-3' + uniqueComponentForApp
dataTableComponentID = 'datatable-interactivity' + uniqueComponentForApp
card_graph = utilities.spinner_wrapper(dbc.Card(id=graphComponentID, body=True, color="secondary", ))
dataTableComponent = utilities.data_table(dataTableComponentID, df)

clinicalGroupList = ['phenotype', 'site', 'sex', 'ethnicity', 'race', 'mecfs_sudden_gradual',
                     'qmep_sudevent', 'qmep_metimediagnosis', 'vo2change', 'atchange']
clinicalNumericList = ['age', 'height_in', 'weight_lbs', 'bmi', 'mecfs_duration',
                       'vo2peak1', 'vo2peak2', 'at1', 'at2']

# Sorting operators (https://dash.plotly.com/datatable/filtering)
layout = html.Div([

    # Buttons at top of window
    dbc.Row([
        dbc.Col(dbc.Button(
            "Show / hide database schematic",
            id=buttonQuestion1ID,
            className="mb-3",
            color="primary",
        ), width=5),

        dbc.Col(dbc.Button(
            "Show / hide SQL statement entry",
            id=buttonQuestion2ID,
            className="mb-3",
            color="primary",
        ), width=5)
    ], justify="center"),

    # Database schema
    dbc.Collapse(
        dbc.Row([
            dbc.Col(
                cyto.Cytoscape(
                    id=graphComponentID,
                    zoomingEnabled=False,
                    pan={'x': 100, 'y': 100},
                    layout={'name': 'preset'},
                    style={'width': '100%', 'height': '500px'},
                    elements=[
                        # Nodes elements
                        {'data': {'id': 'demographic_data', 'label': 'Demographic data'},
                         'position': {'x': 270, 'y': 10},
                         'selected': True
                         },

                        {'data': {'id': 'demographic_history', 'label': 'Demographic history'},
                         'position': {'x': 20, 'y': 30},
                         },

                        {'data': {'id': 'users', 'label': 'Users'},
                         'position': {'x': 50, 'y': 90},
                         },

                        {'data': {'id': 'event_log', 'label': 'Event log'},
                         'position': {'x': 20, 'y': 150},
                         },

                        {'data': {'id': 'biospecimen_data', 'label': 'Biospecimen data'},
                         'position': {'x': 440, 'y': 10},
                         },

                        {'data': {'id': 'biospecimen_history', 'label': 'Biospecimen history'},
                         'position': {'x': 550, 'y': 30},
                         },

                        {'data': {'id': 'biospecimen_tube_info', 'label': 'Biospecimen tube info'},
                         'position': {'x': 570, 'y': 100},
                         },

                        {'data': {'id': 'redcap', 'label': 'Redcap'},
                         'position': {'x': 120, 'y': 120},
                         },

                        {'data': {'id': 'proteomic', 'label': 'Proteomic'},
                         'position': {'x': 220, 'y': 140},
                         },

                        {'data': {'id': 'cytokine', 'label': 'Cytokine'},
                         'position': {'x': 340, 'y': 150},
                         },

                        {'data': {'id': 'metabolomic', 'label': 'Metabolomic'},
                         'position': {'x': 460, 'y': 160}
                         },

                        {'data': {'id': 'assay_results', 'label': 'Assay results'},
                         'position': {'x': 280, 'y': 250}
                         },

                        {'data': {'id': 'data_labels', 'label': 'Data labels'},
                         'position': {'x': 430, 'y': 260}
                         },

                        {'data': {'id': 'data_label_pathways', 'label': 'Data label pathways'},
                         'position': {'x': 480, 'y': 320}
                         },

                        {'data': {'id': 'gene_symbol_ref', 'label': 'Gene symbol ref'},
                         'position': {'x': 130, 'y': 190}
                         },

                        {'data': {'id': 'ensembl_geneid_ref', 'label': 'Ensembl gene ID ref'},
                         'position': {'x': 50, 'y': 240}
                         },

                        {'data': {'id': 'cytokine_label_ref', 'label': 'Cytokine label ref'},
                         'position': {'x': 20, 'y': 290}
                         },

                        {'data': {'id': 'metabolomic_label_ref', 'label': 'Metabolomic label ref'},
                         'position': {'x': 70, 'y': 340}
                         },

                        # Edge elements
                        {'data': {'source': 'users', 'target': 'event_log'}},
                        {'data': {'source': 'demographic_data', 'target': 'demographic_history'}},
                        {'data': {'source': 'demographic_data', 'target': 'users'}},
                        {'data': {'source': 'demographic_data', 'target': 'redcap'}},
                        {'data': {'source': 'demographic_data', 'target': 'proteomic'}},
                        {'data': {'source': 'demographic_data', 'target': 'cytokine'}},
                        {'data': {'source': 'demographic_data', 'target': 'metabolomic'}},
                        {'data': {'source': 'biospecimen_data', 'target': 'users'}},
                        {'data': {'source': 'biospecimen_data', 'target': 'biospecimen_history'}},
                        {'data': {'source': 'biospecimen_data', 'target': 'biospecimen_tube_info'}},
                        {'data': {'source': 'biospecimen_data', 'target': 'proteomic'}},
                        {'data': {'source': 'biospecimen_data', 'target': 'cytokine'}},
                        {'data': {'source': 'biospecimen_data', 'target': 'metabolomic'}},
                        {'data': {'source': 'proteomic', 'target': 'assay_results'}},
                        {'data': {'source': 'cytokine', 'target': 'assay_results'}},
                        {'data': {'source': 'metabolomic', 'target': 'assay_results'}},
                        {'data': {'source': 'assay_results', 'target': 'data_labels'}},
                        {'data': {'source': 'data_labels', 'target': 'data_label_pathways'}},
                        {'data': {'source': 'assay_results', 'target': 'gene_symbol_ref'}},
                        {'data': {'source': 'assay_results', 'target': 'ensembl_geneid_ref'}},
                        {'data': {'source': 'assay_results', 'target': 'cytokine_label_ref'}},
                        {'data': {'source': 'assay_results', 'target': 'metabolomic_label_ref'}},
                    ]
                ), width=9, align="start"),

            dbc.Col(
                # Show table columns
                dbc.Card(
                    id=tableDefinitionID,
                    body=True
                ),
                width=3,
                align="center",
                style={'width': '100%',
                       'height': '500px',
                       'overflowY': 'scroll',
                       'padding-top': '25px',
                       'padding-bottom': '25px'
                       }
            )
        ], justify="center"),
        id=collapse1ID, is_open=True
    ),

    html.Br(),

    # SQL entry
    dbc.Collapse(
        dbc.Row([
            dbc.Textarea(id=sqlInputID, placeholder="Enter SQL...")
        ]),
        id=collapse2ID, is_open=True
    ),

    # html.Br(),
    # html.Div([
    #     html.Div(dcc.Dropdown(
    #         id=groupDropdownComponentID, value='phenotype', clearable=False,
    #         options=[{'label': x, 'value': x} for x in clinicalGroupList],
    #         multi=False,
    #         searchable=True,
    #         placeholder='Select one',
    #         style={"width": "90%"}
    #     ), className='two columns', style={"width": "15rem"}),
    #
    #     html.Div(dcc.Dropdown(
    #         id=comparison1DropdownComponentID, value='sex', clearable=False,
    #         persistence=True, persistence_type='memory',
    #         options=[{'label': x, 'value': x} for x in clinicalGroupList],
    #         multi=False,
    #         searchable=True,
    #         placeholder='Select one',
    #         style={"width": "90%"}
    #     ), className='two columns', style={"width": "15rem"}),
    #
    #     html.Div(dcc.Dropdown(
    #         id=comparison2DropdownComponentID, value='site', clearable=False,
    #         persistence=True, persistence_type='memory',
    #         options=[{'label': x, 'value': x} for x in ['none'] + clinicalGroupList],
    #         multi=False,
    #         searchable=True,
    #         placeholder='Select one',
    #         style={"width": "90%"}
    #     ), className='two columns', style={"width": "15rem"}),
    #
    #     html.Div(dcc.Dropdown(
    #         id=comparison3DropdownComponentID, value='race', clearable=False,
    #         persistence=True, persistence_type='memory',
    #         options=[{'label': x, 'value': x} for x in ['none'] + clinicalGroupList],
    #         multi=False,
    #         searchable=True,
    #         placeholder='Select one',
    #         style={"width": "90%"}
    #     ), className='two columns', style={"width": "15rem"}),
    # ], className='row'),

    # Data table
    html.Br(),
    html.Div([
        dbc.Row(dbc.Col(dataTableComponent,
                        width=12,
                        style={'width': '100%',
                               'height': '500px',
                               'overflow': 'scroll',
                               # 'padding-top': '25px',
                               # 'padding-bottom': '25px'
                               }
                        ), justify="start"),
    ]),
    html.Br(),
])


# Show / hide regions
@app.callback(
    Output(collapse1ID, "is_open"),
    [Input(buttonQuestion1ID, "n_clicks")],
    [State(collapse1ID, "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


@app.callback(
    Output(collapse2ID, "is_open"),
    [Input(buttonQuestion2ID, "n_clicks")],
    [State(collapse2ID, "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


# Show columns in tables
@app.callback(
    Output(tableDefinitionID, 'children'),
    Input(graphComponentID, 'tapNodeData'),
)
def update_nodes(data):
    print(data)
    if data is None:
        return build_display_of_database_schema('Demographic data')
    else:
        return build_display_of_database_schema(data['label'])


# -------------------------------------------------------------------------------------
# Create scatter plot
@app.callback(
    Output(component_id=graphComponentID, component_property='children'),
    [Input(component_id=groupDropdownComponentID, component_property='value'),
     Input(component_id=comparison1DropdownComponentID, component_property='value'),
     Input(component_id=comparison2DropdownComponentID, component_property='value'),
     Input(component_id=comparison3DropdownComponentID, component_property='value')]
)
def display_value(group_chosen, compare_1_chosen, compare_2_chosen, compare_3_chosen):
    # df_fltrd = df[df['Genre'] == genre_chosen]
    # df_fltrd = df_fltrd.nlargest(10, sales_chosen)
    # fig = px.bar(df_fltrd, x=compare_1_chosen, y=compare_2_chosen, color='Platform')
    # fig = fig.update_yaxes(tickprefix="$", ticksuffix="M")

    print(group_chosen)
    print(compare_1_chosen)
    print(compare_2_chosen)
    print(compare_3_chosen)

    rootBranchesLeaves = [group_chosen, compare_1_chosen]
    if compare_2_chosen.lower() != 'none':
        rootBranchesLeaves.append(compare_2_chosen)
    if compare_3_chosen.lower() != 'none':
        rootBranchesLeaves.append(compare_3_chosen)

    colorSequence = utilities.set_color_sequence(group_chosen)

    # Produce a sunburst plot
    fig = px.sunburst(
        data_frame=df,
        path=rootBranchesLeaves,  # Root, branches, leaves
        color=group_chosen,
        color_discrete_sequence=colorSequence,
        maxdepth=-1,  # set the sectors rendered. -1 will render all levels in the hierarchy
        # color="Victim's age",
        # color_continuous_scale=px.colors.sequential.BuGn,
        # range_color=[10,100],
        branchvalues="total",  # or 'remainder'
        hover_name=group_chosen,
        # hover_data={'Unarmed': False},    # remove column name from tooltip  (Plotly version >= 4.8.0)
        title=documentName.capitalize() + ' Data Sunburst Plot',
        template='ggplot2',  # 'ggplot2', 'seaborn', 'simple_white', 'plotly',
        #                                   # 'plotly_white', 'plotly_dark', 'presentation',
        #                                   # 'xgridoff', 'ygridoff', 'gridon', 'none'
        height=600,
    )

    fig.update_traces(textinfo='label+percent entry')
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))

    return [
        dcc.Graph(id='sunburst_plot' + uniqueComponentForApp, figure=fig)
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
