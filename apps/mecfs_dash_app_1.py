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

# import mongo_utilities

# Set up globals
import utilities
import set_up_globals

MECFSVersion = set_up_globals.MECFSVersion
data_folder = set_up_globals.data_folder

# Register connection to MongoDB
mongo_setup.global_init()

# -------------------------------------------------------------------------------------
# Import data into pandas
scrnaseq_summary_data_list = svc.find_only_scrnaseq_summary_data()
if scrnaseq_summary_data_list is None:
    print(f'No scRNA-seq summary records.')
    sys.exit(2)

# property_names = [p for p in dir(ScRNAseqSummary) if isinstance(getattr(ScRNAseqSummary, p), property)]
# attribute_names = [i for i in ScRNAseqSummary.__dict__.keys() if i[:1] != '_']
# attribute_names = utilities.attributes(ScRNAseqSummary)
# print(attribute_names)

# dataList = []
# for c in scrnaseq_summary_data_list:
#     print('Study ID: {} - {}'.format(
#         c.study_id,
#         'ME/CFS patient' if c.phenotype == 'ME/CFS' else 'Healthy control'))
#     dataRow = []
#     for sc in c.scrnaseq_summary:
#         for dataColumn in attribute_names:
#             dataRow.append(sc[dataColumn])
#         print(
#             '      Sample: {}, Freezer ID: {}, {} {} {} {}'.format(
#                 sc['sample_name'],
#                 sc.biospecimen_data_reference.freezer_id,
#                 sc.number_of_reads,
#                 sc.estimated_number_of_cells,
#                 sc.mean_reads_per_cell,
#                 sc.median_genes_per_cell
#             ))
#     dataList.append(dataRow)
#
# df = pd.DataFrame(dataList, columns=attribute_names)

df = utilities.create_df_from_object_list(scrnaseq_summary_data_list, ScRNAseqSummary, 'scrnaseq_summary')
print(df.head(5))

# db = 'mecfs_db_test1'
# collection = 'mecfs_collection'
# df = mongo_utilities.read_mongo(db, collection, query={}, host='localhost', port=27017, username=None, password=None, no_id=True)
# # df = df[df['year'] == 2019]

# Creating an ID column name gives us more interactive capabilities
df['id'] = df['study_id']
df.set_index('id', inplace=True, drop=False)

# -------------------------------------------------------------------------------------
# App layout
# bootstrapTheme = 'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css'
# app = dash.Dash(__name__, prevent_initial_callbacks=True)  # this was introduced in Dash version 1.12.0
# external_stylesheets=[dbc.themes.CYBORG])
# server = app.server

# layout = html.Div([dbc.Button("Success", color="success", className="mr-1")])

# card_graph = dbc.Card(
#         dcc.Graph(id='datatable-interactivity-container', figure={}), body=True, color="secondary",
# )

# card_table = dbc.Card(html.Div([
#     dash_table.DataTable(
#         id='datatable-interactivity',
#         columns=[
#             {"name": i, "id": i, "deletable": True, "selectable": True, "hideable": True}
#             if i == "study_id" or i == "site" or i == "id" or i == "created_date" or i == "last_modified_date"
#             else {"name": i, "id": i, "deletable": True, "selectable": True}
#             for i in df.columns
#         ],
#         data=df.to_dict('records'),  # the contents of the table
#         editable=False,  # allow editing of data inside all cells
#         filter_action="native",  # allow filtering of data by user ('native') or not ('none')
#         sort_action="native",  # enables data to be sorted per-column by user or not ('none')
#         sort_mode="single",  # sort across 'multi' or 'single' columns
#         column_selectable="multi",  # allow users to select 'multi' or 'single' columns
#         row_selectable="multi",  # allow users to select 'multi' or 'single' rows
#         row_deletable=True,  # choose if user can delete a row (True) or not (False)
#         selected_columns=[],  # ids of columns that user selects
#         selected_rows=[],  # indices of rows that user selects
#         page_action="native",  # all data is passed to the table up-front or not ('none')
#         page_current=0,  # page number that user is on
#         page_size=6,  # number of rows visible per page
#         style_cell={  # ensure adequate header width when text is shorter than cell's text
#             'minWidth': 95, 'maxWidth': 95, 'width': 95
#         },
#         style_cell_conditional=[  # align text columns to left. By default they are aligned to right
#             {
#                 'if': {'column_id': c},
#                 'textAlign': 'left'
#             } for c in ['sex', 'phenotype']
#         ],
#         style_data={  # overflow cells' content into multiple lines
#             'whiteSpace': 'normal',
#             'height': 'auto'
#         }
#     )]),
#     color="dark",  # https://bootswatch.com/default/ for more card colors
#     inverse=True,  # change color of text (black or white)
#     outline=False,  # True = remove the block colors from the background and header
# )

card_graph = utilities.spinner_wrapper(dbc.Card(id='datatable-interactivity-container', body=True, color="secondary",))
dataTableComponent = utilities.data_table('datatable-interactivity', df)

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
    # dash_table.DataTable(
    #     id='datatable-interactivity',
    #     columns=[
    #         {"name": i, "id": i, "deletable": True, "selectable": True, "hideable": True}
    #         if i == "study_id" or i == "site" or i == "id" or i == "created_date" or i == "last_modified_date"
    #         else {"name": i, "id": i, "deletable": True, "selectable": True}
    #         for i in df.columns
    #     ],
    #     data=df.to_dict('records'),  # the contents of the table
    #     editable=False,  # allow editing of data inside all cells
    #     filter_action="native",  # allow filtering of data by user ('native') or not ('none')
    #     sort_action="native",  # enables data to be sorted per-column by user or not ('none')
    #     sort_mode="single",  # sort across 'multi' or 'single' columns
    #     column_selectable="multi",  # allow users to select 'multi' or 'single' columns
    #     row_selectable="multi",  # allow users to select 'multi' or 'single' rows
    #     row_deletable=True,  # choose if user can delete a row (True) or not (False)
    #     selected_columns=[],  # ids of columns that user selects
    #     selected_rows=[],  # indices of rows that user selects
    #     page_action="native",  # all data is passed to the table up-front or not ('none')
    #     page_current=0,  # page number that user is on
    #     page_size=9,  # number of rows visible per page
    #     style_cell={  # ensure adequate header width when text is shorter than cell's text
    #         'minWidth': 95, 'maxWidth': 95, 'width': 95
    #     },
    #     style_cell_conditional=[  # align text columns to left. By default they are aligned to right
    #         {
    #             'if': {'column_id': c},
    #             'textAlign': 'left'
    #         } for c in ['sex', 'phenotype']
    #     ],
    #     style_data={  # overflow cells' content into multiple lines
    #         'whiteSpace': 'normal',
    #         'height': 'auto'
    #     }
    # ),
    # dbc.Row(dbc.Col(card_table, width=12), justify="start"),

    html.Br(),
    # html.Div(id='datatable-interactivity-container')
    # html.Div(id='bar-container')
    # html.Div(id='choromap-container')

])

# -------------------------------------------------------------------------------------
# Create bar charts
@app.callback(
    Output(component_id='datatable-interactivity-container', component_property='children'),
    [Input(component_id='datatable-interactivity', component_property="derived_virtual_data"),
     Input(component_id='datatable-interactivity', component_property='derived_virtual_selected_rows'),
     Input(component_id='datatable-interactivity', component_property='derived_virtual_selected_row_ids'),
     Input(component_id='datatable-interactivity', component_property='selected_rows'),
     Input(component_id='datatable-interactivity', component_property='derived_virtual_indices'),
     Input(component_id='datatable-interactivity', component_property='derived_virtual_row_ids'),
     Input(component_id='datatable-interactivity', component_property='active_cell'),
     Input(component_id='datatable-interactivity', component_property='selected_cells'),
     Input(component_id='datatable-interactivity', component_property='selected_columns')]
)
def update_bar(all_rows_data, slctd_row_indices, slct_rows_names, slctd_rows,
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
    # dff = pd.DataFrame(all_rows_data)

    # used to highlight selected countries on bar chart
    colors = ['#7FDBFF' if i in slctd_row_indices else '#0074D9'
              for i in range(len(dff))]

    return [
        dcc.Graph(id=column,
                  figure=px.bar(
                      data_frame=dff,
                      x="sample_name",
                      y=dff[column],
                      labels={"age": "Number of reads"}
                  ).update_layout(showlegend=False, xaxis={'categoryorder': 'total ascending'})
                  .update_traces(marker_color=colors, hovertemplate="<b>%{y}%</b><extra></extra>")
                  )
                  # check if column exists - user may have deleted it
                  # If `column.deletable=False`, then you don't
                  # need to do this check.
                  for column in slctd_columns if column in dff
    ]


# # -------------------------------------------------------------------------------------
# # Create choropleth map
# @app.callback(
#     Output(component_id='choromap-container', component_property='children'),
#     [Input(component_id='datatable-interactivity', component_property="derived_virtual_data"),
#      Input(component_id='datatable-interactivity', component_property='derived_virtual_selected_rows')]
# )
# def update_map(all_rows_data, slctd_row_indices):
#     dff = pd.DataFrame(all_rows_data)
#
#     # highlight selected countries on map
#     borders = [5 if i in slctd_row_indices else 1
#                for i in range(len(dff))]
#
#     if "site" in dff and "age" in dff and "country" in dff:
#         return [
#             dcc.Graph(id='choropleth',
#                       style={'height': 700},
#                       figure=px.choropleth(
#                           data_frame=dff,
#                           locations="site",
#                           scope="america",
#                           color="age",
#                           title="% of Pop",
#                           template='plotly_dark',
#                           hover_data=['site', 'age'],
#                       ).update_layout(showlegend=False, title=dict(font=dict(size=28), x=0.5, xanchor='center'))
#                       .update_traces(marker_line_width=borders, hovertemplate="<b>%{customdata[0]}</b><br><br>" +
#                                                                               "%{customdata[1]}" + "%")
#                       )
#         ]


# -------------------------------------------------------------------------------------
# Highlight selected column
@app.callback(
    Output('datatable-interactivity', 'style_data_conditional'),
    [Input('datatable-interactivity', 'selected_columns')]
)
def update_styles(selected_columns):
    return [{
        'if': {'column_id': i},
        'background_color': '#D2F3FF'
    } for i in selected_columns]


# -------------------------------------------------------------------------------------


# if __name__ == '__main__':
#     app.run_server(debug=True)
