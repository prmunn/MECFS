# Utilities for interaction with Dash components, plus frequently used python functions

# Author: Paul Munn, Genomics Innovation Hub, Cornell University

# Version history:
# Created: 10/19/2020


import pandas as pd
import dash_table
import dash_core_components as dcc
# import dash_bootstrap_components as dbc


# Get attributes for class that do not start with '_'
def attributes(cls):
    excludeFields = ['objects', 'DoesNotExist', 'MultipleObjectsReturned', 'id']
    return [i for i in cls.__dict__.keys() if not i.startswith('_') and i not in excludeFields]


def create_df_from_object_list(object_list, cls, subDocument):
    columnsFromClinicalData = ['study_id', 'phenotype', 'site', 'sex', 'age']
    attribute_names = attributes(cls)
    # Remove non-JSON serializable objects (of type User, Biospecimen)
    attribute_names.remove('created_by')
    attribute_names.remove('last_modified_by')
    attribute_names.remove('created_date')
    attribute_names.remove('last_modified_date')
    attribute_names.remove('biospecimen_data_reference')
    print(len(attribute_names))

    data = []
    for c in object_list:
        print('Study ID: {} - {}'.format(
            c['study_id'],
            'ME/CFS patient' if c['phenotype'] == 'ME/CFS' else 'Healthy control'))
        for sd in c[subDocument]:
            dataRow = []
            for dataColumn in attribute_names:
                dataRow.append(sd[dataColumn])
            # print(
            #     '      Sample: {}, Freezer ID: {}, {} {} {} {}'.format(
            #         sd['sample_name'],
            #         sd.biospecimen_data_reference.freezer_id,
            #         sd.number_of_reads,
            #         sd.estimated_number_of_cells,
            #         sd.mean_reads_per_cell,
            #         sd.median_genes_per_cell
            #     ))

            # Add clinical data
            for dataColumn in columnsFromClinicalData:
                dataRow.append(c[dataColumn])
            # print('len dataRow:', len(dataRow))
            # print('dataRow:', dataRow)
            data.append(dataRow)

    # Add clinical data column names
    for dataColumn in columnsFromClinicalData:
        attribute_names.append(dataColumn)

    # print('data:', data)
    df = pd.DataFrame(data, columns=attribute_names)

    return df


def spinner_wrapper(component):
    # return dbc.Spinner(children=[component],
    #                    size="lg", color="primary", type="border", fullscreen=True,),
    #                    # spinner_style={"width": "10rem", "height": "10rem"}),
    #                    # type = "none", spinnerClassName="spinner")
    return dcc.Loading(
        children=[component],
        color="#119DFF", type="default", fullscreen=False, )


def data_table(table_id, df):
    return dash_table.DataTable(
        id=table_id,
        columns=[
            {"name": i, "id": i, "deletable": True, "selectable": True, "hideable": True}
            if i == "study_id" or i == "site" or i == "id" or i == "created_date" or i == "last_modified_date"
            else {"name": i, "id": i, "deletable": True, "selectable": True}
            for i in df.columns
        ],
        data=df.to_dict('records'),  # the contents of the table
        editable=False,  # allow editing of data inside all cells
        filter_action="native",  # allow filtering of data by user ('native') or not ('none')
        sort_action="native",  # enables data to be sorted per-column by user or not ('none')
        sort_mode="single",  # sort across 'multi' or 'single' columns
        column_selectable="multi",  # allow users to select 'multi' or 'single' columns
        row_selectable="multi",  # allow users to select 'multi' or 'single' rows
        row_deletable=True,  # choose if user can delete a row (True) or not (False)
        selected_columns=[],  # ids of columns that user selects
        selected_rows=[],  # indices of rows that user selects
        page_action="native",  # all data is passed to the table up-front or not ('none')
        page_current=0,  # page number that user is on
        page_size=9,  # number of rows visible per page
        style_cell={  # ensure adequate header width when text is shorter than cell's text
            'minWidth': 95, 'maxWidth': 95, 'width': 95
        },
        style_cell_conditional=[  # align text columns to left. By default they are aligned to right
            {
                'if': {'column_id': c},
                'textAlign': 'left'
            } for c in ['sex', 'phenotype']
        ],
        style_data={  # overflow cells' content into multiple lines
            'whiteSpace': 'normal',
            'height': 'auto'
        }
    )
