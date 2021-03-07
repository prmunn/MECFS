import sys

import dash  # (version 1.12.0)
from dash.dependencies import Input, Output
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
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
graphComponentID = 'datatable-interactivity-container-line'
dataTableComponentID = 'datatable-interactivity-line'
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
# Create line charts
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
def update_line(all_rows_data, slctd_row_indices, slct_rows_names, slctd_rows,
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

    dff_all = df if all_rows_data is None else pd.DataFrame(all_rows_data)
    data = []
    for index, row in dff_all.iterrows():
        for col in slctd_columns:
            dataRow = []
            dataRow.append(row['sample_name'])
            dataRow.append(col)
            dataRow.append(row[col])
            data.append(dataRow)
    dff = pd.DataFrame(data, columns=['sample_name', 'column_name', 'value'])

    colorSequence = utilities.set_color_sequence()

    # used to highlight selected countries on bar chart
    colors = ['#7FDBFF' if i in slctd_row_indices else '#0074D9'
              for i in range(len(dff))]

    return [
        dcc.Graph(id='line_plot',
                  figure=px.line(
                      data_frame=dff,
                      x='sample_name',
                      y='value',
                      color='column_name',
                      color_discrete_sequence=colorSequence
                  ).update_layout(showlegend=True,
                                  # xaxis={'categoryorder': 'total ascending'},
                                  yaxis={'title': 'Values'},
                                  title={'text': 'scRNA-seq Summary Line Plot', 'font': {'size': 28}, 'x': 0.5, 'xanchor': 'center'})
                  .update_traces(marker_color=colors, hovertemplate="<b>%{y}%</b><extra></extra>")
                  )
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
