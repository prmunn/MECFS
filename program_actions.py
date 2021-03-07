# Text based user interface for controlling interactions with ME/CFS database
# This includes setting up user IDs, reading excel files and writing their contents to the database,
# and producing reports from the database

# Author: Paul Munn, Genomics Innovation Hub, Cornell University

# Version history:
# Created: 10/19/2020


import os
# import sys
# import datetime
from colorama import Fore
# from dateutil import parser
from mongoengine import ValidationError

import data.mongo_setup as mongo_setup
from infrastructure.switchlang import switch
import infrastructure.state as state
import services.data_service as svc
from data.assay_classes import Proteomic
from data.assay_classes import Cytokine
from data.assay_classes import Metabolomic

import pandas as pd
import numpy as np

# Set up globals
import set_up_globals
import utilities

MECFSVersion = set_up_globals.MECFSVersion
data_folder = set_up_globals.data_folder


def main():
    mongo_setup.global_init(set_up_globals.database_name)
    print_header()

    while not state.active_account:
        try:
            response = log_into_account()
            if response in set_up_globals.exitResponseList:
                exit_app()

        except KeyboardInterrupt:
            return

    show_commands()

    try:
        while True:
            action = get_action()

            with switch(action) as s:
                s.case('a', import_assay_data)
                s.case('d', import_clinical_data)
                # s.case('r', import_redcap_data)
                s.case('b', import_biospecimen_data)
                # s.case('p', import_proteomics_data)
                s.case('scrna', import_scrnaseq_summary_data)
                s.case('dlt', import_data_label_types)
                s.case('compids', import_compound_ids)
                s.case('pathways', import_pathway_data)
                s.case('cdlt', combine_data_label_types)
                s.case('tp', test_pathway_mapping)
                s.case('vc', list_clinical_data)
                s.case('vb', list_biospecimen_data_for_study_id)
                s.case('vsc', list_biospecimen_data_for_scrnaseq_summary)
                s.case('vosc', list_only_scrnaseq_summary)
                s.case(set_up_globals.exitResponseList, exit_app)  # ['x', 'bye', 'exit', 'exit()']
                s.case('?', show_commands)
                s.case('', lambda: None)
                s.default(unknown_command)

            if action:
                print()

    except KeyboardInterrupt:
        return


def show_commands():
    print('What action would you like to take:')
    print(f'[D] Import {set_up_globals.clinical_document_name} data')
    # print('Import [R]edcap data')
    print('[B] Import biospecimen data')
    print('[A] Import assay data (Proteomics, Cytokines, Metabolomics, etc.)')
    # print('Import [p]roteomics data')
    print('[scRNA] Import scRNA-seq summary data')
    print('[dlt] Import data label types')
    print('[compids] Import compound IDs')
    print('[pathways] Import pathway data')
    print('[cdlt] Combine data label types')
    print('[tp] Test pathway mapping across two assays')
    print(f'[vc] View {set_up_globals.clinical_document_name} data')
    print('[vb] View biospecimen data for a study ID')
    print('[vsc] View biospecimen data for each scRNA-seq summary')
    print('[vosc] View only scRNA-seq summary data')
    # print('Change [M]ode (guest or host)')
    print('e[X]it app')
    print('[?] Help (this info)')
    print()


def create_account():
    print(' ******************** REGISTER ******************** ')

    name = input('What is your name? ')
    email = input('What is your email? ').strip().lower()

    old_account = svc.find_account_by_email(email)
    if old_account:
        error_msg(f"ERROR: Account with email {email} already exists.")
        return

    state.active_account = svc.create_account(name, email)
    success_msg(f"Created new account with id {state.active_account.id}.")


def log_into_account():
    print(' ******************** Select user ******************** ')

    for user_tuple in set_up_globals.users:
        name = user_tuple[0]
        email = user_tuple[1]
        if not svc.find_account_by_email(email):
            svc.create_account(name, email)

    users = svc.get_users()
    print()
    for idx, u in enumerate(users):
        print('{}. {} (email: {})'.format(
            idx + 1,
            u.name,
            u.email
        ))

    message = f"\nPlease enter a number between 1 and {str(len(users))} or 'x' to exit: "
    response = input(message)
    if response in set_up_globals.exitResponseList:
        return response

    try:
        user = users[int(response) - 1]
    except (IndexError, ValueError):
        error_msg(message + '\n')
        return response

    email = user.email
    account = svc.find_account_by_email(email)
    if not account:
        error_msg(f'Could not find account with email {email}.')
        return response

    state.active_account = account
    success_msg('Logged in successfully.')


def modify_df_column_names(column_names, classColumnList=None):
    renamed_columns = []
    for i in range(len(column_names)):
        original_col = str(column_names[i]).strip()
        col = original_col.replace(' ', '_')
        col = col.replace('-', '_')
        col = col.replace('?', '')
        col = col.replace('(', '')
        col = col.replace(')', '')
        col = col.replace('/', '_')
        col = col.replace('#', 'number')
        col = col.replace('10x', 'ten_x')
        col = col.lower()

        # If classColumnsList exists then restrict column names to only those in the class
        # This prevents the changing of gene symbols that are included as columns in th Excel spreadsheet
        if (classColumnList is not None) and (col not in classColumnList):
            renamed_columns.append(original_col)
        else:
            renamed_columns.append(col)

    return renamed_columns


def create_custom_columns(df, documentName, data_file_name, index_column=None):
    #  Acts like pass by reference if I add data to df, rather than
    #  assigning a new value to df, so no need to return a value
    df['data_file_name'] = data_file_name

    if documentName == set_up_globals.scrnaseq_summary_document_name:
        df['study_id'] = df['enid']

    if documentName == set_up_globals.proteomics_document_name or \
            documentName == set_up_globals.cytokines_document_name or \
            documentName == set_up_globals.metabolomics_document_name:
        df['study_id'] = df['ENID']

        validTimePoints = ['D1-PRE', 'D1-POST', 'D2-PRE', 'D2-POST']
        timepoint_list = []
        for val in df['timepoint']:
            if val in validTimePoints:
                timepoint_list.append(val)
            elif val.lower() == 'pre-day1':
                timepoint_list.append('D1-PRE')
            elif val.lower() == 'post-day1':
                timepoint_list.append('D1-POST')
            elif val.lower() == 'pre-day2':
                timepoint_list.append('D2-PRE')
            elif val.lower() == 'post-day2':
                timepoint_list.append('D2-POST')
            else:
                timepoint_list.append('')
        df['timepoint'] = timepoint_list

        # Set up unique_id column
        if index_column == 'AnalysisID':
            # df.dropna(axis=0, subset=[index_column], inplace=True)  # Remove nulls from index
            # //--- flag null value in the event log
            index_names = df[df[index_column] == ''].index
            df.drop(index_names, inplace=True)
            df['unique_id'] = df[index_column]
        elif index_column == 'ENID+Timepoint':
            # //--- flag null values in the event log
            # //--- I'm sure there's a way of doing this in one line, but this way is more readable : )
            unique_id_list = []
            for index, row in df.iterrows():
                unique_id_list.append(svc.convert_to_string(row.study_id) + '-' + row.timepoint + '-' + data_file_name)
            df['unique_id'] = unique_id_list
        # else:
        #     error_msg(f'Error: {index_column} is not a valid sample identifier type')
        #     error_msg('Exiting data load')
        #     return  # None, None

    if documentName == set_up_globals.biospecimen_document_name:
        df['sample_id'] = df['id']
        # Set Specimen ID to ENID, CPET Day, Pre/Post, and Specimen type
        # //--- this may not be needed in biospecimen spread sheet removes tube number from specimen id column
        # //--- I'm sure there's a way of doing this in one line, but this way is more readable : )
        specimen_id_list = []
        for val in df['specimen_id']:
            valMinusTubeNumberList = val.split('-')[0:4]
            specimen_id_list.append('-'.join(valMinusTubeNumberList))
        df['specimen_id'] = specimen_id_list

    if documentName == set_up_globals.clinical_document_name:
        # Make sure study ID is numeric (i.e. strip off 'ENID' if it exists)
        study_id_list = [int(val.strip('ENID')) for val in df['study_id']]
        df['study_id'] = study_id_list

    if documentName == set_up_globals.data_label_type_document_name:
        df['unique_id'] = df.index
        if 'comp_id' not in df.columns:
            df['comp_id'] = ''
            df['biochemical'] = ''
        if 'gene_name' not in df.columns:
            df['gene_name'] = ''
        if 'gene_stable_id' not in df.columns:
            df['gene_stable_id'] = ''
        if 'cytokine_label' not in df.columns:
            df['cytokine_label'] = ''
        # //--- set up remaining data labels - let's do this without the hardcoding


def import_data(documentName, index_column, verifyIntegrityFlag=True, sheet_name=0, skiprows=None):
    print(f' ******************** Import {documentName} data ******************** ')

    # Look up file
    items = os.listdir(data_folder)
    fileList = []
    for names in items:
        if (names.endswith('.xlsx') or names.endswith('.xls')) and not names.startswith('~'):
            fileList.append(names)

    for idx, fileName in enumerate(fileList):
        print('{}. {}'.format(
            idx + 1,
            fileName
        ))

    message = f"\nPlease select a file number between 1 and {str(len(fileList))}: "
    response = input(message)
    # if response in set_up_globals.exitResponseList:
    #     return None, None

    try:
        data_file_name = fileList[int(response) - 1]
    except (IndexError, ValueError):
        error_msg('\nError: You did not make a valid file selection \n')
        return None, None

    engine = 'openpyxl'  # Support for xlxs file format
    if data_file_name.split('.')[1] == 'xls':
        engine = 'xlrd'  # Support for xls file format
    df = pd.read_excel(data_folder + data_file_name,
                       sheet_name=sheet_name, skiprows=skiprows, engine=engine, keep_default_na=False)

    df.columns = modify_df_column_names(df.columns)
    index_names = df[df[index_column] == ''].index
    df.drop(index_names, inplace=True)
    # df.dropna(axis=0, subset=[index_column], inplace=True)  # Remove nulls from index

    # Create custom columns
    create_custom_columns(df, documentName, data_file_name)
    df.set_index(index_column, drop=False, inplace=True, verify_integrity=verifyIntegrityFlag)

    return df, data_file_name


def import_assay_data():
    # Look up file
    items = os.listdir(data_folder)
    fileList = []
    for names in items:
        if (names.endswith('.xlsx') or names.endswith('.xls')) and not names.startswith('~'):
            fileList.append(names)

    for idx, fileName in enumerate(fileList):
        print('{}. {}'.format(
            idx + 1,
            fileName
        ))

    message = f"\nPlease select a file number between 1 and {str(len(fileList))}: "
    response = input(message)
    # //--- need some error checking here
    # if response in set_up_globals.exitResponseList:
    #     return  # None, None

    try:
        data_file_name = fileList[int(response) - 1]
    except (IndexError, ValueError):
        error_msg('\nError: You did not make a valid file selection \n')
        return  # None, None

    # Start by reading metadata sheet
    # Need to know: documentName, index_column, sheet_name, and skiprows before reading data sheet
    metaDataDict = {'submitter_name': None,
                    'submitter_netid': None,
                    'pi_name': None,
                    'assay_type': None,
                    'assay_method': None,
                    'biospecimen_type': None,
                    'sample_identifier_type': None,
                    'dataset_name': None,
                    'dataset_annotation': None,
                    'data_label_type': None,
                    'comment': None,
                    'units': None,
                    'normalization_method': None,
                    'pipeline': None}
    engine = 'openpyxl'  # Support for xlxs file format
    if data_file_name.split('.')[1] == 'xls':
        engine = 'xlrd'  # Support for xls file format
    skiprows = range(0, 3)
    metaDataDF = pd.read_excel(data_folder + data_file_name,
                               sheet_name='Metadata', skiprows=skiprows, engine=engine, keep_default_na=False)
    for i, row in metaDataDF.iterrows():
        metaDataType = modify_df_column_names([str(row[0]).lower()])[0]
        response = str(row[1])
        if metaDataType in metaDataDict and len(response) > 0:
            metaDataDict[metaDataType] = response

    # Display what was just read
    print('')
    for key, val in metaDataDict.items():
        print(key, ':', val)

    # Check assay type
    # //--- replace all these with global references
    validAssayTypes = [set_up_globals.proteomics_document_name,
                       set_up_globals.cytokines_document_name,
                       set_up_globals.metabolomics_document_name,
                       'BDNF', 'CPET', 'LPS', 'miRNA', 'scRNAseq', 'Survey']
    documentName = metaDataDict['assay_type']
    if documentName not in validAssayTypes:
        error_msg(f'Error: {documentName} is not a valid assay type')
        error_msg('Exiting data load')
        return  # None, None

    message = f"\nIs this correct? (y/n): "
    response = input(message)
    if response[0].lower() != 'y':
        return  # None, None

    print(f' ******************** Import {documentName} data ******************** ')

    skiprows = range(0, 1)  # //--- for now, define skiprows as the top row - can adjust this later
    df = pd.read_excel(data_folder + data_file_name,
                       sheet_name='Data Table', skiprows=skiprows, engine=engine, keep_default_na=False)

    # Remove nulls from ENID
    index_names = df[df['ENID'] == ''].index
    df.drop(index_names, inplace=True)
    # df.dropna(axis=0, subset=['ENID'], inplace=True)  # Remove nulls from ENID

    # Remove unnamed columns
    unnamedColList = [colName for colName in df.columns if str(colName).startswith('Unnamed')]
    df.drop(labels=unnamedColList, axis='columns', inplace=True)

    # //--- add remaining assay types
    if documentName == set_up_globals.proteomics_document_name:
        classColumnList = utilities.attributes(Proteomic)
    elif documentName == set_up_globals.cytokines_document_name:
        classColumnList = utilities.attributes(Cytokine)
    elif documentName == set_up_globals.metabolomics_document_name:
        classColumnList = utilities.attributes(Metabolomic)
    else:
        error_msg(f'Error: {documentName} is not a valid assay type')
        error_msg('No data saved')
        return

    df.columns = modify_df_column_names(df.columns, classColumnList)

    # Create custom columns
    create_custom_columns(df, documentName, data_file_name, metaDataDict['sample_identifier_type'])

    try:
        df.set_index('unique_id', drop=False, inplace=True, verify_integrity=True)
    except (ValueError, ValidationError) as e:
        message = f'Create of index for {documentName} data resulted in exception: {e}'
        error_msg(message)
        error_msg('No data saved')
        return  # Skip the rest of this function

    # Assay specific save functions
    # //--- still need svc code for other documents
    if documentName == set_up_globals.proteomics_document_name:
        svc.add_proteomic_data(state.active_account, df, data_file_name, metaDataDict)
    elif documentName == set_up_globals.cytokines_document_name:
        svc.add_cytokine_data(state.active_account, df, data_file_name, metaDataDict)
    elif documentName == set_up_globals.metabolomics_document_name:
        svc.add_metabolomic_data(state.active_account, df, data_file_name, metaDataDict)
    else:
        error_msg(f'Error: {documentName} is not a valid assay type')
        error_msg('No data saved')

    return  # df, data_file_name


def import_data_label_types():
    documentName = set_up_globals.data_label_type_document_name
    df, data_file_name = import_data(documentName, 'gene_name', verifyIntegrityFlag=False)
    svc.add_data_label_types(state.active_account, df, data_file_name)


def combine_data_label_types():
    documentName = set_up_globals.data_label_type_document_name

    # Read two spreadsheets to combine
    df, data_file_name = import_data(documentName, 'gene_name', verifyIntegrityFlag=False)
    cytokine_df, data_file_name = import_data(documentName, 'entrezgenessymbol', verifyIntegrityFlag=False)
    print(df.head(5))
    print(cytokine_df.head(5))

    # Add cytokine column to main df
    geneToCytokineTranslationDict = {}
    for index, row in cytokine_df.iterrows():
        geneToCytokineTranslationDict[row['entrezgenessymbol']] = row['cytokine']
    # print('geneToCytokineTranslationDict', geneToCytokineTranslationDict)
    df['cytokine_label'] = ''
    # print(df.head(5))
    for index, row in df.iterrows():
        if row['gene_name'] in geneToCytokineTranslationDict:
            df.loc[index, 'cytokine_label'] = geneToCytokineTranslationDict[row['gene_name']]
    print(df.head(5))

    # Write combined df to new spreadsheet
    output_data_file_name = 'combined_gene_names_and_cytokines.xlsx'
    df.to_excel(data_folder + output_data_file_name)


def import_compound_ids():
    documentName = set_up_globals.data_label_type_document_name
    df, data_file_name = import_data(documentName, 'comp_id', verifyIntegrityFlag=False)
    svc.add_data_label_types(state.active_account, df, data_file_name)


def import_pathway_data():
    documentName = set_up_globals.data_label_pathway_document_name
    df, data_file_name = import_data(documentName, 'pathway_name', verifyIntegrityFlag=False)
    svc.add_data_label_pathways(state.active_account, df, data_file_name)


def import_clinical_data():
    documentName = set_up_globals.clinical_document_name
    df, data_file_name = import_data(documentName, 'study_id')
    svc.add_clinical_data(state.active_account, df, data_file_name)


def import_biospecimen_data():
    documentName = set_up_globals.biospecimen_document_name
    df, data_file_name = import_data(documentName, 'specimen_id', verifyIntegrityFlag=False)
    svc.add_biospecimen_data(state.active_account, df, data_file_name)

    # data_file_name = set_up_globals.biospecimen_data_file
    # print(f' ******************** Import {documentName} data ******************** ')
    #
    # df = pd.read_excel(data_folder + data_file_name)
    # df['data_file_name'] = data_file_name
    # df.columns = modify_df_column_names(df.columns)
    # df.set_index('id', drop=True, inplace=True, verify_integrity=True)
    #
    # # Create custom columns
    # create_custom_columns(df, documentName)
    #
    # for index, row in df.iterrows():
    #     # clinical_data = svc.find_clinical_data_by_study_id(row.study_id)
    #     # if not clinical_data:
    #     #     error_msg(
    #     #         f'You must import clinical data for study ID {row.study_id} before importing {documentName} data.')
    #     #     error_msg(f'Import of {documentName} data aborted.')
    #     #     return
    #     biospecimen_data = svc.add_biospecimen_data(state.active_account, index, row)
    #     success_msg(f'Added / updated {documentName} data id {biospecimen_data.id}.')


def import_redcap_data():
    documentName = set_up_globals.redcap_document_name
    df, data_file_name = import_data(documentName, 'id')
    svc.add_redcap_data(state.active_account, df, data_file_name)

    # data_file_name = set_up_globals.redcap_data_files
    # print(f' ******************** Import {documentName} data ******************** ')
    #
    # df = pd.read_excel(data_folder + data_file_name)
    # df['data_file_name'] = data_file_name
    # df.columns = modify_df_column_names(df.columns)
    # df.set_index('id', drop=True, inplace=True, verify_integrity=True)  # //--- id ?
    #
    # # Create custom columns
    # create_custom_columns(df, documentName)
    #
    # for index, row in df.iterrows():
    #     clinical_data = svc.find_clinical_data_by_study_id(row.study_id)
    #     if not clinical_data:
    #         error_msg(
    #             f'You must import clinical data for study ID {row.study_id} before importing {documentName} data.')
    #         error_msg(f'Import of {documentName} data aborted.')
    #         return
    #     redcap_data = svc.add_redcap_data(state.active_account, clinical_data, index, row)
    #     success_msg(
    #         f'Added / updated {documentName} data for ENID: {clinical_data.study_id} with id {redcap_data.id}.')


def import_scrnaseq_summary_data():
    documentName = set_up_globals.scrnaseq_summary_document_name
    df, data_file_name = import_data(documentName, 'sampleid', sheet_name=0, skiprows=range(0, 3))
    svc.add_scrnaseq_summary_data(state.active_account, df, data_file_name)

    # data_file_name = set_up_globals.scrnaseq_summary_data_file
    # print(f' ******************** Import {documentName} data ******************** ')
    #
    # df = pd.read_excel(data_folder + data_file_name, sheet_name='final', skiprows=range(0, 3))
    # df['data_file_name'] = data_file_name
    # df.columns = modify_df_column_names(df.columns)
    # df.set_index('sampleid', drop=True, inplace=True, verify_integrity=True)
    #
    # # Create custom columns
    # create_custom_columns(df, documentName)
    #
    # df.sort_values(by='study_id', inplace=True)
    # for index, row in df.iterrows():
    #     clinical_data = svc.find_clinical_data_by_study_id(row.study_id)
    #     if not clinical_data:
    #         error_msg(
    #             f'You must import clinical data for study ID {row.study_id} before importing {documentName} data.')
    #         error_msg(f'Import of {documentName} data aborted.')
    #         return
    #     biospecimen_data = svc.find_biospecimen_data_by_sample_id(index)
    #     scrnaseq_summary = svc.add_scrnaseq_summary_data(state.active_account, clinical_data, biospecimen_data, index,
    #                                                      row)
    #     success_msg(
    #         f'Added / updated {documentName} data for ENID: {clinical_data.study_id} with id {index}.')


def test_pathway_mapping():
    print(' ********************     Test pathway mapping     ******************** ')

    pathway_name = 'Cytokine / proteomic test'
    dataLabelPathwayIDs = svc.find_pathway_data(pathway_name)

    for idx, c in enumerate(dataLabelPathwayIDs.data_label_references):
        print(' {}. {}: {}'.format(idx + 1, c.data_label, c.gene_symbol_references[0].data_label))

    data_list = svc.test_pathway_mapping()
    df, dataGeneSymbolList = utilities.create_df_from_object_list(data_list,
                                                                  [Proteomic, Cytokine],
                                                                  ['proteomic', 'cytokine'],
                                                                  assayResultsFlag=True,
                                                                  dataLabelPathwayIDs=dataLabelPathwayIDs)
    print('dataGeneSymbolList:', dataGeneSymbolList)
    print(df.head(15))
    print(df.columns)

    print(f"There are {len(df)} records.")
    df['aggregated_result'] = 0
    for idx, c in df.iterrows():
        print(' {}. {}: {}'.format(idx + 1, c.study_id,
                                   'ME/CFS patient' if c.phenotype == 'ME/CFS' else 'Healthy control'))
        print('      * Assay summary: {}, {}'.format(c.assay_type, c.timepoint))
        arList = []
        for ar in dataGeneSymbolList:
            if not np.isnan(c[ar]):
                arList.append(c[ar])
            print('            * Results: {}, {}'.format(ar, c[ar]))
        print(np.ma.average(arList))
        df.loc[idx, 'aggregated_result'] = np.ma.average(arList)

    print(df.head(15))

    # results_ave = svc.test_pathway_average(dataLabelPathwayIDs)
    # print('results_ave:', results_ave)


def list_clinical_data(suppress_header=False):
    if not suppress_header:
        print(f' ********************     {set_up_globals.clinical_document_name.capitalize()} data     ******************** ')

    clinical_data_list = svc.find_clinical_data()
    print(f"There are {len(clinical_data_list)} records.")
    for idx, c in enumerate(clinical_data_list):
        print(' {}. {}: {}'.format(idx + 1, c.study_id,
                                   'ME/CFS patient' if c.phenotype == 'ME/CFS' else 'Healthy control'))
        for sc in c.scrnaseq_summary:
            print('      * scRNA-seq summary: {}, {}'.format(
                sc.brc_id,
                sc.sample_name
            ))


def list_biospecimen_data_for_study_id():
    list_clinical_data(suppress_header=True)

    study_id = input("Enter study ID: ")
    if not study_id.strip():
        error_msg('Cancelled')
        print()
        return

    study_id = int(study_id)
    biospecimen_data_list = svc.find_biospecimen_data_by_study_id(study_id)

    print("There are {} biospecimens for study ID {}.".format(len(biospecimen_data_list), study_id))
    print(biospecimen_data_list)
    for idx, b in enumerate(biospecimen_data_list):
        print(' {}. Date received: {}, Tube number: {}, Freezer ID: {}'.format(idx + 1, b.date_received, b.tube_number,
                                                                               b.freezer_id))
        # for sc in c.scrnaseq_summary:
        #     print('      * scRNA-seq summary: {}, {}'.format(
        #         sc.brc_id,
        #         sc.sample_name
        #     ))


def list_biospecimen_data_for_scrnaseq_summary():
    print(' ********************     Biospecimen data for scRNA-seq summaries     ******************** ')

    list_clinical_data(suppress_header=True)

    study_id = input("Enter study ID: ")
    if not study_id.strip():
        error_msg('Cancelled')
        print()
        return

    study_id = int(study_id)
    clinical_data_list = svc.find_clinical_data_by_study_id(study_id)
    print('Study ID: {} - {}'.format(
        clinical_data_list.study_id,
        'ME/CFS patient' if clinical_data_list.phenotype == 'ME/CFS' else 'Healthy control'))
    if clinical_data_list.scrnaseq_summary.count() < 1:
        print(f'No scRNA-seq summary records for study ID {str(study_id)}')
        return
    for sc in clinical_data_list.scrnaseq_summary:
        print(
            '      * scRNA-seq summary: , Sample name: {}, Tube number: {}, Freezer ID: {}, Date received: {}'.format(
                sc.sample_name,
                sc.biospecimen_data_reference.tube_number,
                sc.biospecimen_data_reference.freezer_id,
                sc.biospecimen_data_reference.date_received
            ))


def list_only_scrnaseq_summary():
    print(' ********************     Only scRNA-seq summaries     ******************** ')

    scrnaseq_summary_data_list = svc.find_only_scrnaseq_summary_data()
    if scrnaseq_summary_data_list is None:
        print(f'No scRNA-seq summary records.')
        return

    for c in scrnaseq_summary_data_list:
        print('Study ID: {} - {}'.format(
            c.study_id,
            'ME/CFS patient' if c.phenotype == 'ME/CFS' else 'Healthy control'))
        for sc in c.scrnaseq_summary:
            print(
                '      Sample: {}, Freezer ID: {}, {} {} {} {}'.format(
                    sc['sample_name'],
                    sc.biospecimen_data_reference.freezer_id,
                    sc.number_of_reads,
                    sc.estimated_number_of_cells,
                    sc.mean_reads_per_cell,
                    sc.median_genes_per_cell
                ))


def exit_app():
    print()
    print('bye')
    raise KeyboardInterrupt()


def get_action():
    text = '> '
    if state.active_account:
        text = f'{state.active_account.name}> '

    action = input(Fore.YELLOW + text + Fore.WHITE)
    return action.strip().lower()


def unknown_command():
    print("Sorry we didn't understand that command.")


def success_msg(text):
    print(Fore.LIGHTGREEN_EX + text + Fore.WHITE)


def error_msg(text):
    print(Fore.LIGHTRED_EX + text + Fore.WHITE)


def print_header():
    print(Fore.WHITE + '*********************************************')
    print(Fore.GREEN + '              ME/CFS Import')
    print(Fore.WHITE + '*********************************************')
    print()


if __name__ == '__main__':
    main()
