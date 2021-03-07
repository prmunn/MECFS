import sys

import dash  # (version 1.12.0)
from dash.dependencies import Input, Output
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.express as px
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from app import app

import data.mongo_setup as mongo_setup
from infrastructure.switchlang import switch
import infrastructure.state as state
import services.data_service as svc

from data.clinical_data import ClinicalData
from data.redcap import Redcap
from data.proteomics import Proteomic
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
scrnaseq_summary_data_list = svc.find_scrnaseq_summary_data_only()
if scrnaseq_summary_data_list is None:
    print(f'No scRNA-seq summary records.')
    sys.exit(2)

df,_ = utilities.create_df_from_object_list(scrnaseq_summary_data_list, [ScRNAseqSummary], ['scrnaseq_summary'])
print(df.head(5))

# Creating an ID column name gives us more interactive capabilities
df['id'] = df['study_id']
df.set_index('id', inplace=True, drop=False)

# -------------------------------------------------------------------------------------
# App layout
graphComponentID = 'datatable-interactivity-container-3dscatter'
dataTableComponentID = 'datatable-interactivity-3dscatter'
card_graph = utilities.spinner_wrapper(dbc.Card(id=graphComponentID, body=True, color="secondary",))
dataTableComponent = utilities.data_table(dataTableComponentID, df)

# Sorting operators (https://dash.plotly.com/datatable/filtering)
layout = html.Div([

    html.Div([
        dbc.Row(dbc.Col(card_graph, width=12), justify="start"),
        # justify="start", "center", "end", "between", "around"
    ]),
    html.Br(),
    html.Div([
        dbc.Row(dbc.Col(dataTableComponent, width=12), justify="start"),
    ]),
    html.Br(),
])


# -------------------------------------------------------------------------------------
# Create 3D scatter charts
@app.callback(
    Output(component_id=graphComponentID, component_property='children'),
    [Input(component_id=dataTableComponentID, component_property="derived_virtual_data"),
     Input(component_id=dataTableComponentID, component_property='derived_virtual_selected_rows'),
     Input(component_id=dataTableComponentID, component_property='derived_virtual_selected_row_ids'),
     Input(component_id=dataTableComponentID, component_property='selected_rows'),
     Input(component_id=dataTableComponentID, component_property='derived_virtual_indices'),
     Input(component_id=dataTableComponentID, component_property='derived_virtual_row_ids'),
     Input(component_id=dataTableComponentID, component_property='active_cell'),
     Input(component_id=dataTableComponentID, component_property='selected_cells'),
     Input(component_id=dataTableComponentID, component_property='selected_columns')]
)
def update_3d_scatter(all_rows_data, slctd_row_indices, slct_rows_names, slctd_rows,
               order_of_rows_indices, order_of_rows_names, actv_cell, slctd_cell, slctd_columns):
    print('***************************************************************************')
    print('Data across all pages pre or post filtering: {}'.format(all_rows_data))
    print('---------------------------------------------')
    print("Indices of selected rows if part of table after filtering:{}".format(slctd_row_indices))
    print("Names of selected rows if part of table after filtering: {}".format(slct_rows_names))
    print("Indices of selected rows regardless of filtering results: {}".format(slctd_rows))
    print('---------------------------------------------')
    print("Indices of all rows pre or post filtering: {}".format(order_of_rows_indices))
    print("Names of all rows pre or post filtering: {}".format(order_of_rows_names))
    print("---------------------------------------------")
    print("Complete data of active cell: {}".format(actv_cell))
    print("Complete data of all selected cells: {}".format(slctd_cell))
    print("---------------------------------------------")
    print("Indices of selected columns regardless of filtering results: {}".format(slctd_columns))

    if slctd_row_indices is None:
        slctd_row_indices = []

    dff = df if all_rows_data is None else pd.DataFrame(all_rows_data)
    dff['size'] = dff['age'] / 4

    # data = []
    # for index, row in dff_all.iterrows():
    #     for col in slctd_columns:
    #         dataRow = []
    #         dataRow.append(row['sample_name'])
    #         dataRow.append(col)
    #         dataRow.append(row[col])
    #         data.append(dataRow)
    # dff = pd.DataFrame(data, columns=['sample_name', 'column_name', 'value'])

    # used to highlight selected countries on bar chart
    # colors = ['#7FDBFF' if i in slctd_row_indices else '#0074D9'
    #           for i in range(len(dff))]

    if len(slctd_columns) < 3:
        slctd_columns = ['valid_barcodes', 'sequencing_saturation', 'q30_bases_in_barcode']

    # Use for animation rotation at the end
    x_eye = -1.25
    y_eye = 2
    z_eye = 0.5

    group_chosen = 'phenotype'
    colorSequence = utilities.set_color_sequence(group_chosen)

    fig = px.scatter_3d(
        data_frame=dff,
        x=slctd_columns[0],
        y=slctd_columns[1],
        z=slctd_columns[2],
        color=group_chosen,
        color_discrete_sequence=colorSequence,
        template='ggplot2',
        title='scRNA-seq Summary 3D Scatter Plot',
        size='size',  # size of bubble
        size_max=30,  # set the maximum mark size when using size
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
        dcc.Graph(id='3d_scatter_plot', figure=fig)
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
