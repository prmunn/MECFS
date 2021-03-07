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
documentName = set_up_globals.cytokines_document_name
# data_list = svc.find_cytokine_data()
data_list = svc.find_cytokine_data_only()
if data_list is None:
    print(f'No {documentName} data records.')
    sys.exit(2)

df, dataGeneSymbolList = utilities.create_df_from_object_list(data_list, [Cytokine], ['cytokine'], assayResultsFlag=True)
print(df.head(5))

# Creating an ID column name gives us more interactive capabilities
df['id'] = df['study_id']
df.set_index('id', inplace=True, drop=False)

# -------------------------------------------------------------------------------------
# App layout
uniqueComponentForApp = '-cytokine-1'  # Make sure this is different for every app / page
graphComponentID = 'datatable-interactivity-container-scatter' + uniqueComponentForApp
groupDropdownComponentID = 'group-dropdown' + uniqueComponentForApp
comparison1DropdownComponentID = 'compare-dropdown-1' + uniqueComponentForApp
comparison2DropdownComponentID = 'compare-dropdown-2' + uniqueComponentForApp
comparison3DropdownComponentID = 'compare-dropdown-3' + uniqueComponentForApp
dataTableComponentID = 'datatable-interactivity-scatter' + uniqueComponentForApp
card_graph = utilities.spinner_wrapper(dbc.Card(id=graphComponentID, body=True, color="secondary", ))
dataTableComponent = utilities.data_table(dataTableComponentID, df)

dataGroupList = ['phenotype', 'site', 'sex', 'ethnicity', 'race', 'mecfs_sudden_gradual', 'timepoint', 'biospecimen_type']

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
            options=[{'label': x, 'value': x} for x in dataGroupList],
            multi=False,
            searchable=True,
            placeholder='Select one',
            style={"width": "90%"}
        ), className='two columns', style={"width": "15rem"}),

        html.Div(dcc.Dropdown(
            id=comparison1DropdownComponentID, value=dataGeneSymbolList[0], clearable=False,
            persistence=True, persistence_type='memory',
            options=[{'label': x, 'value': x} for x in dataGeneSymbolList],
            multi=False,
            searchable=True,
            placeholder='Select one',
            style={"width": "90%"}
        ), className='two columns', style={"width": "15rem"}),

        html.Div(dcc.Dropdown(
            id=comparison2DropdownComponentID, value=dataGeneSymbolList[1], clearable=False,
            persistence=True, persistence_type='memory',
            options=[{'label': x, 'value': x} for x in dataGeneSymbolList],
            multi=False,
            searchable=True,
            placeholder='Select one',
            style={"width": "90%"}
        ), className='two columns', style={"width": "15rem"}),

        html.Div(dcc.Dropdown(
            id=comparison3DropdownComponentID, value='none', clearable=False,
            persistence=True, persistence_type='memory',
            options=[{'label': x, 'value': x} for x in ['none'] + dataGeneSymbolList],
            multi=False,
            searchable=True,
            placeholder='Select one',
            style={"width": "90%"}
        ), className='two columns', style={"width": "15rem"}),
    ], className='row'),
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
     Input(component_id=comparison3DropdownComponentID, component_property='value')]
)
def display_value(group_chosen, compare_1_chosen, compare_2_chosen, compare_3_chosen):
    print(group_chosen)
    print(compare_1_chosen)
    print(compare_2_chosen)
    print(compare_3_chosen)

    colorSequence = utilities.set_color_sequence(group_chosen)

    # If the third compare choice is 'none' then produce a
    # 2D scatter plot, otherwise produce a 3D scatter plot
    if compare_3_chosen.lower() == 'none':
        fig = px.scatter(
            data_frame=df,
            x=compare_1_chosen,
            y=compare_2_chosen,
            color=group_chosen,
            color_discrete_sequence=colorSequence,
            template='ggplot2',
            title=documentName + ' Data Scatter Plot',
            # size='size',  # size of bubble
            # size_max=30,  # set the maximum mark size when using size
            hover_name='study_id',  # values appear in bold in the hover tooltip
            height=600)
    else:
        # Use for animation rotation at the end
        x_eye = -1.25
        y_eye = 2
        z_eye = 0.5

        fig = px.scatter_3d(
            data_frame=df,
            x=compare_1_chosen,
            y=compare_2_chosen,
            z=compare_3_chosen,
            color=group_chosen,
            color_discrete_sequence=colorSequence,
            template='ggplot2',
            title=documentName + ' Data 3D Scatter Plot',
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
