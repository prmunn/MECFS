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

import data.mongo_setup as mongo_setup
from infrastructure.switchlang import switch
import infrastructure.state as state
import services.data_service as svc

import pandas as pd

# Set up globals
import set_up_globals

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
                # s.case('c', create_account)
                # s.case('a', create_account)
                # s.case('l', log_into_account)
                s.case('i', import_clinical_data)
                s.case('r', import_redcap_data)
                s.case('b', import_biospecimen_data)
                s.case('p', import_proteomics_data)
                s.case('s', import_scrnaseq_summary_data)
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
    # print('[C]reate an [a]ccount')
    # print('[L]ogin to your account')
    print('[I]mport clinical data')
    print('Import [R]edcap data')
    print('Import [b]iospeciment data')
    print('Import [p]roteomics data')
    print('Import [s]cRNA-seq summary data')
    print('[vc] View clinical data')
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


def modify_df_column_names(df):
    column_names = df.columns
    renamed_columns = []
    for i in range(len(column_names)):
        col = column_names[i].strip()
        col = col.replace(' ', '_')
        col = col.replace('-', '_')
        col = col.replace('?', '')
        col = col.replace('(', '')
        col = col.replace(')', '')
        col = col.replace('/', '_')
        col = col.replace('#', 'number')
        col = col.replace('10x', 'ten_x')
        col = col.lower()
        renamed_columns.append(col)

    return renamed_columns


def create_custom_columns(df, documentName):
    #  Acts like pass by reference if I add data to df, rather than
    #  assigning a new value to df, so no need to return a value
    if documentName == set_up_globals.proteomics_document_name or \
            documentName == set_up_globals.cytokines_document_name:
        cpet_day_list = []
        pre_post_cpet_list = []
        for val in df['time']:
            if val == 't1':
                cpet_day_list.append('D1')
                pre_post_cpet_list.append('PRE')
            elif val == 't2':
                cpet_day_list.append('D1')
                pre_post_cpet_list.append('POST')
            elif val == 't3':
                cpet_day_list.append('D2')
                pre_post_cpet_list.append('PRE')
            elif val == 't4':
                cpet_day_list.append('D2')
                pre_post_cpet_list.append('POST')
            else:
                cpet_day_list.append('')
                pre_post_cpet_list.append('')
        df['cpet_day'] = cpet_day_list
        df['pre_post_cpet'] = pre_post_cpet_list

    if documentName == set_up_globals.scrnaseq_summary_document_name:
        df['study_id'] = df['enid']

    if documentName == set_up_globals.biospecimen_document_name:
        df['sample_id'] = df.index


def import_data(documentName, index_column, sheet_name=0, skiprows=None):
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

    df = pd.read_excel(data_folder + data_file_name, sheet_name=sheet_name, skiprows=skiprows)
    df['data_file_name'] = data_file_name
    df.columns = modify_df_column_names(df)
    df.set_index(index_column, drop=False, inplace=True, verify_integrity=True)

    # Create custom columns
    create_custom_columns(df, documentName)

    return df, data_file_name


def import_clinical_data():
    documentName = set_up_globals.clinical_document_name
    df, data_file_name = import_data(documentName, 'study_id')
    svc.add_clinical_data(state.active_account, df, data_file_name)


def import_proteomics_data():
    documentName = set_up_globals.proteomics_document_name
    df, data_file_name = import_data(documentName, 'id')
    svc.add_proteomic_data(state.active_account, df, data_file_name)


def import_biospecimen_data():
    documentName = set_up_globals.biospecimen_document_name
    df, data_file_name = import_data(documentName, 'id')
    svc.add_biospecimen_data(state.active_account, df, data_file_name)

    # data_file_name = set_up_globals.biospecimen_data_file
    # print(f' ******************** Import {documentName} data ******************** ')
    #
    # df = pd.read_excel(data_folder + data_file_name)
    # df['data_file_name'] = data_file_name
    # df.columns = modify_df_column_names(df)
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
    # df.columns = modify_df_column_names(df)
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
    # df.columns = modify_df_column_names(df)
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


def list_clinical_data(suppress_header=False):
    if not suppress_header:
        print(' ********************     Clinical data     ******************** ')

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
