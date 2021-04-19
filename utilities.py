# Utilities for interaction with Dash components, plus frequently used python functions

# Author: Paul Munn, Genomics Innovation Hub, Cornell University

# Version history:
# Created: 10/19/2020


import numpy as np
import pandas as pd
import dash_table
import dash_core_components as dcc
# import dash_bootstrap_components as dbc
import plotly.express as px

from data.clinical_data import ClinicalData


# Get attributes for class that do not start with '_'
def attributes(cls):
    excludeFields = ['objects', 'DoesNotExist', 'MultipleObjectsReturned', 'id']
    return [i for i in cls.__dict__.keys() if not i.startswith('_') and i not in excludeFields]


def create_df_from_object_list(object_list, clsList, subDocumentList, assayResultsFlag=False, dataLabelPathwayIDs=None):
    # columnsFromClinicalData = ['study_id', 'phenotype', 'site', 'sex', 'age',
    #                            'height_in', 'weight_lbs', 'bmi', 'ethnicity',
    #                            'race', 'mecfs_sudden_gradual', 'mecfs_duration',
    #                            'qmep_sudevent', 'qmep_metimediagnosis', 'vo2peak1', 'vo2peak2',
    #                            'vo2change', 'at1', 'at2', 'atchange']
    columnsFromClinicalData = ClinicalData.get_demographic_attributes()
    attribute_names = attributes(clsList[0])  # Use attributes from first class (should match other classes)
    # Remove non-JSON serializable objects (of type User, Biospecimen, etc.)
    itemsToRemove = ['created_by', 'last_modified_by', 'created_date', 'last_modified_date',
                     'biospecimen_data_reference', 'biospecimen_data_references', 'assay_results']
    for item in itemsToRemove:
        if item in attribute_names:
            attribute_names.remove(item)
        if item in columnsFromClinicalData:
            columnsFromClinicalData.remove(item)
    print('Length of attribute list:', len(attribute_names))
    print('Attributes:', attribute_names)
    print('columnsFromClinicalData:', columnsFromClinicalData)

    # Build list of data labels up front - this means looping thru
    # the object list twice, but I don't see a better way to do it
    dataLabelsList = []
    for c in object_list:
        for subDocument in subDocumentList:
            for sd in c[subDocument]:
                if assayResultsFlag:
                    for assayResult in sd.assay_results:
                        # If dataLabelPathwayIDs is empty then get all data labels,
                        # otherwise, only get those in dataLabelPathwayIDs
                        if dataLabelPathwayIDs is None:
                            if assayResult['data_label'] not in dataLabelsList:
                                dataLabelsList.append(assayResult['data_label'])
                        else:
                            if assayResult.data_label_reference is None:
                                # print('assayResult.data_label:', assayResult.data_label, 'is missing a data label reference')
                                continue
                            # print('assayResult.data_label_reference.gene_symbol_references:', assayResult.data_label_reference.gene_symbol_references[0].data_label)
                            if assayResult['data_label'] not in dataLabelsList and \
                                    assayResult.data_label_reference.gene_symbol_references[
                                        0] in dataLabelPathwayIDs.data_label_references:
                                dataLabelsList.append(assayResult['data_label'])
    # print('dataLabelsList:', dataLabelsList)

    data = []
    for c in object_list:
        # print('Study ID: {} - {}, {}, {}'.format(
        #     c['study_id'],
        #     'ME/CFS patient' if c['phenotype'] == 'ME/CFS' else 'Healthy control',
        #     c['sex'],
        #     c['proteomic']))
        for subDocument in subDocumentList:
            if not c[subDocument]:
                dataRow = []
                # Add clinical data
                for dataColumn in columnsFromClinicalData:
                    dataRow.append(c[dataColumn])

                attributeNameList = np.repeat(None, len(attribute_names)).tolist()
                for val in attributeNameList:
                    dataRow.append(val)

                if assayResultsFlag:
                    resultList = np.repeat(None, len(dataLabelsList)).tolist()
                    for val in resultList:
                        dataRow.append(val)

                data.append(dataRow)
            else:
                for sd in c[subDocument]:
                    dataRow = []
                    # Add clinical data
                    for dataColumn in columnsFromClinicalData:
                        dataRow.append(c[dataColumn])

                    for dataColumn in attribute_names:
                        dataRow.append(sd[dataColumn])

                    if assayResultsFlag:
                        # So that we keep all data labels in the correct order and position (for assays with different
                        # symbols), first build a list of 'None' and then insert the result in the appropriate position
                        resultList = np.repeat(None, len(dataLabelsList)).tolist()
                        for assayResult in sd.assay_results:
                            # If dataLabelPathwayIDs is empty then get all data labels,
                            # otherwise, only get those in dataLabelPathwayIDs
                            dataLabel = assayResult['data_label']
                            if dataLabel not in dataLabelsList:
                                continue  # These are not the labels you are looking for...
                            # Get position in dataLabelsList
                            dataLabelIndex = dataLabelsList.index(dataLabel)
                            # Insert result into that position in resultList
                            resultList[dataLabelIndex] = assayResult['result']
                        for val in resultList:
                            dataRow.append(val)

                    # print('len dataRow:', len(dataRow))
                    # print('dataRow:', dataRow)
                    data.append(dataRow)
    # print('data:', data)

    # Build list of column names
    colNamesList = []
    for dataColumn in columnsFromClinicalData:
        colNamesList.append(dataColumn)
    for dataColumn in attribute_names:
        colNamesList.append(dataColumn)
    for dataColumn in dataLabelsList:
        colNamesList.append(dataColumn)

    # print('data:', data)
    df = pd.DataFrame(data, columns=colNamesList)

    return df, dataLabelsList


def set_color_sequence(group_selection=None):
    colorSequence = px.colors.qualitative.Pastel
    if group_selection == 'phenotype':
        colorSequence = ['red', 'blue']

    return colorSequence


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
        # page_size=9,  # number of rows visible per page
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
