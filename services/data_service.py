# Utilities for interaction with the database (creating, reading, updating, and deleting).
# Amoung other things, maintains an event log of anything done to the database (and it's subsequent
# success or failure), and updates version history collections for top-level collections

# Author: Paul Munn, Genomics Innovation Hub, Cornell University

# Version history:
# Created: 10/19/2020


from typing import List, Optional
import datetime

from colorama import Fore
from mongoengine import ValidationError

from data.clinical_data import ClinicalData, ClinicalDataVersionHistory
from data.redcap import Redcap
from data.assay_classes import Proteomic
from data.assay_classes import Cytokine
from data.assay_classes import Metabolomic
from data.scrnaseq_summary import ScRNAseqSummary
from data.biospecimens import Biospecimen, BiospecimenVersionHistory, BiospecimenTubeInfo
from data.users import User
from data.event_log import Event_log
from data.assay_results import AssayResults
from data.data_label_types import GeneSymbols
from data.data_label_types import EnsemblTranscriptIDs
from data.data_label_types import EnsemblGeneIDs
from data.data_label_types import CytokineLabels
from data.data_label_types import GeneSymbolsToEnsemblGeneIDs
from mongoengine.queryset.visitor import Q

import set_up_globals
import utilities


def get_users() -> List[User]:
    users = User.objects().all()

    return list(users)


def create_account(name: str, email: str) -> User:
    user = User()
    user.name = name
    user.email = email

    user.save()

    return user


def find_account_by_email(email: str) -> User:
    return User.objects(email=email).first()


def find_clinical_data_by_study_id(study_id: int) -> ClinicalData:
    return ClinicalData.objects(study_id=study_id).first()


def find_biospecimen_data_by_specimen_id(specimen_id: str) -> Biospecimen:
    return Biospecimen.objects(specimen_id=specimen_id).first()


# def find_biospecimen_data_by_sample_id(sample_id: int) -> Biospecimen:
#     # return Biospecimen.objects(__raw__={biospecimen_tube_info: {sample_id: sample_id}}).first()
#     # return Biospecimen.objects(biospecimen_tube_info.sample_id=sample_id).first()
#     return Biospecimen.objects(__raw__={'specimen_id': specimen_id}).first()


def find_biospecimen_data_by_study_id(study_id: int) -> List[Biospecimen]:
    return list(Biospecimen.objects(study_id=study_id).all())


def find_cytokine_data() -> List[ClinicalData]:
    return list(ClinicalData.objects(cytokine__unique_id__exists=True).all().order_by('phenotype'))


def find_clinical_data_for_user(account: User) -> List[ClinicalData]:
    query = ClinicalData.objects(id__in=account.id).all().order_by('phenotype')
    clinical_data = list(query)

    return clinical_data


def find_clinical_data() -> List[ClinicalData]:
    return list(ClinicalData.objects().all().order_by('phenotype'))


def find_demographic_data_only() -> List[ClinicalData]:
    return list(ClinicalData.demographic_data_only().all().order_by('phenotype'))


def find_proteomic_data_only() -> List[ClinicalData]:
    return list(ClinicalData.proteomic_data_only().all().order_by('phenotype'))


def find_cytokine_data_only() -> List[ClinicalData]:
    return list(ClinicalData.cytokine_data_only().all().order_by('phenotype'))


def find_metabolomic_data_only() -> List[ClinicalData]:
    return list(ClinicalData.metabolomic_data_only().all().order_by('phenotype'))


def find_scrnaseq_summary_data_only() -> List[ClinicalData]:
    return list(ClinicalData.scrnaseq_summary_data_only().all().order_by('phenotype'))
    # return list(
    #     ClinicalData.objects(scrnaseq_summary__sampleid__exists=True).only('study_id', 'phenotype', 'site', 'sex',
    #                                                               'age', 'scrnaseq_summary').order_by('phenotype'))


# Return a string for field that can be either a string or an integer
def convert_to_string(val):
    try:
        number_test = float(val)
        return str(int(number_test))
    except ValueError:
        return str(val)


# def add_clinical_data(active_account: User, biospecimen_data_list, index, row) -> ClinicalData:
def add_clinical_data(active_account: User, df, data_file_name):  # -> ClinicalData:
    documentName = set_up_globals.clinical_document_name

    for index, row in df.iterrows():
        currentVersion = 0
        clinical_data = find_clinical_data_by_study_id(row.study_id)

        if clinical_data:
            # If data exists, save in version history
            #     Update version history before current version
            #     In the case of a failure during save, this will will result in a duplicate record
            #     in the history collection (which is acceptable), rather than a lost record in the
            #     history collection (which is not acceptable).

            # //--- stop after history update to simulate a failure, then
            # //--- run full flow to make sure clean up works correctly

            currentVersion = clinical_data.version_number
            clinical_data_version_history = ClinicalDataVersionHistory()

            attributeList = utilities.attributes(ClinicalData)
            # print(attributeList)
            for attrib in attributeList:
                # print(attrib)
                clinical_data_version_history[attrib] = clinical_data[attrib]

            clinical_data_version_history.save()
        else:
            # If no data exists for this study id, set created info
            clinical_data = ClinicalData()
            clinical_data.created_by = active_account
            clinical_data.created_date = datetime.datetime.now()

        # Get list of biospecimens for this clinical record
        biospecimen_data_list = find_biospecimen_data_by_study_id(index)

        clinical_data.last_modified_by = active_account
        clinical_data.last_modified_date = datetime.datetime.now()
        clinical_data.study_id = index
        clinical_data.data_file_name = row.data_file_name
        clinical_data.version_number = currentVersion + 1
        clinical_data.biospecimen_data_references = biospecimen_data_list
        clinical_data.site = row.site
        clinical_data.sex = row.sex
        clinical_data.phenotype = row.phenotype
        clinical_data.age = int(row.age)
        clinical_data.height_in = float(row.height_in)
        clinical_data.weight_lbs = float(row.weight_lbs)
        clinical_data.bmi = float(row.bmi)
        clinical_data.ethnicity = convert_to_string(row.ethnicity)
        clinical_data.race = convert_to_string(row.race)
        clinical_data.mecfs_sudden_gradual = convert_to_string(row.mecfs_sudden_gradual)
        clinical_data.qmep_sudevent = convert_to_string(row.qmep_sudevent)
        clinical_data.mecfs_duration = convert_to_string(row.mecfs_duration)
        # clinical_data.qmep_mediagnosis = datetime.datetime.strptime(str(row.qmep_mediagnosis), '%Y-%m-%d %H:%M:%S').date()
        # clinical_data.qmep_mesymptoms = datetime.datetime.strptime(str(row.qmep_mesymptoms), '%Y-%m-%d %H:%M:%S').date()
        clinical_data.qmep_metimediagnosis = convert_to_string(row.qmep_metimediagnosis)
        # clinical_data.cpet_d1 = datetime.datetime.strptime(str(row.cpet_d1), '%Y-%m-%d %H:%M:%S').date()
        # clinical_data.cpet_d2 = datetime.datetime.strptime(str(row.cpet_d2), '%Y-%m-%d %H:%M:%S').date()
        clinical_data.vo2peak1 = convert_to_string(row.vo2peak1)
        clinical_data.vo2peak2 = convert_to_string(row.vo2peak2)
        clinical_data.vo2change = convert_to_string(row.vo2change)
        clinical_data.at1 = convert_to_string(row.at1)
        clinical_data.at2 = convert_to_string(row.at2)
        clinical_data.atchange = convert_to_string(row.atchange)

        try:
            clinical_data.save()
        except (ValueError, ValidationError) as e:
            message = f'Save of {documentName} data with id={index} resulted in exception: {e}'
            add_event_log(active_account,
                          message,
                          success=False,
                          event_type='Import',
                          exception_type=e.__class__.__name__,
                          file_name=row.data_file_name,
                          study_id=str(index))
            error_msg(message)
            continue  # Skip the rest of this loop

        message = f'Added / updated {documentName} data for ENID: {clinical_data.study_id} with id {clinical_data.id}.'
        add_event_log(active_account,
                      message,
                      success=True,
                      event_type='Import',
                      file_name=data_file_name,
                      study_id=index,
                      document_id=str(clinical_data.id))
        success_msg(message)

    return  # clinical_data


# Add data that is common to each class (proteomic, cytokines, etc.)
def add_common_data(active_account: User, row, dataClass, metaDataDict):
    dataClass.last_modified_by = active_account
    dataClass.last_modified_date = datetime.datetime.now()
    dataClass.data_file_name = row.data_file_name

    dataClass.timepoint = row.timepoint
    if len(str(row.annot_1).strip()) > 0 and str(row.annot_1).strip().lower() != 'nan':
        dataClass.annot_1 = str(row.annot_1).strip()
    if len(str(row.annot_2).strip()) > 0 and str(row.annot_2).strip().lower() != 'nan':
        dataClass.annot_2 = str(row.annot_2).strip()
    if len(str(row.annot_3).strip()) > 0 and str(row.annot_3).strip().lower() != 'nan':
        dataClass.annot_3 = str(row.annot_3).strip()

    # Add metadata from upload form
    if metaDataDict['submitter_name'] is not None and \
            len(metaDataDict['submitter_name'].strip()) > 0 and \
            metaDataDict['submitter_name'].strip().lower() != 'nan':
        dataClass.submitter_name = metaDataDict['submitter_name'].strip()
    if metaDataDict['submitter_netid'] is not None and \
            len(metaDataDict['submitter_netid'].strip()) > 0 and \
            metaDataDict['submitter_netid'].strip().lower() != 'nan':
        dataClass.submitter_netid = metaDataDict['submitter_netid'].strip()
    if metaDataDict['pi_name'] is not None and \
            len(metaDataDict['pi_name'].strip()) > 0 and \
            metaDataDict['pi_name'].strip().lower() != 'nan':
        dataClass.pi_name = metaDataDict['pi_name'].strip()
    if metaDataDict['assay_type'] is not None and \
            len(metaDataDict['assay_type'].strip()) > 0 and \
            metaDataDict['assay_type'].strip().lower() != 'nan':
        dataClass.assay_type = metaDataDict['assay_type'].strip()
    if metaDataDict['assay_method'] is not None and \
            len(metaDataDict['assay_method'].strip()) > 0 and \
            metaDataDict['assay_method'].strip().lower() != 'nan':
        dataClass.assay_method = metaDataDict['assay_method'].strip()
    if metaDataDict['biospecimen_type'] is not None and \
            len(metaDataDict['biospecimen_type'].strip()) > 0 and \
            metaDataDict['biospecimen_type'].strip().lower() != 'nan':
        dataClass.biospecimen_type = metaDataDict['biospecimen_type'].strip()
    if metaDataDict['dataset_name'] is not None and \
            len(metaDataDict['dataset_name'].strip()) > 0 and \
            metaDataDict['dataset_name'].strip().lower() != 'nan':
        dataClass.dataset_name = metaDataDict['dataset_name'].strip()
    if metaDataDict['dataset_annotation'] is not None and \
            len(metaDataDict['dataset_annotation'].strip()) > 0 and \
            metaDataDict['dataset_annotation'].strip().lower() != 'nan':
        dataClass.dataset_annotation = metaDataDict['dataset_annotation'].strip()
    if metaDataDict['data_label_type'] is not None and \
            len(metaDataDict['data_label_type'].strip()) > 0 and \
            metaDataDict['data_label_type'].strip().lower() != 'nan':
        dataClass.data_label_type = metaDataDict['data_label_type'].strip()
    if metaDataDict['comment'] is not None and \
            len(metaDataDict['comment'].strip()) > 0 and \
            metaDataDict['comment'].strip().lower() != 'nan':
        dataClass.comment = metaDataDict['comment'].strip()
    if metaDataDict['units'] is not None and \
            len(metaDataDict['units'].strip()) > 0 \
            and metaDataDict['units'].strip().lower() != 'nan':
        dataClass.units = metaDataDict['units'].strip()
    if metaDataDict['normalization_method'] is not None and \
            len(metaDataDict['normalization_method'].strip()) > 0 \
            and metaDataDict['normalization_method'].strip().lower() != 'nan':
        dataClass.normalization_method = metaDataDict['normalization_method'].strip()
    if metaDataDict['pipeline'] is not None and \
            len(metaDataDict['pipeline'].strip()) > 0 \
            and metaDataDict['pipeline'].strip().lower() != 'nan':
        dataClass.pipeline = metaDataDict['pipeline'].strip()

    # Add assay results to data as a subdocument
    # Data labels (e.g. gene symbols) start at column 6.
    # Subtract 3 from end to account for data_file_name, study_id, and unique_id
    for i in range(6, len(row) - 3):
        data_label = row.index[i]
        result = row[i]
        # if set_up_globals.testMode:
        #     print(data_label, result)

        # Is this a new or existing assay result for this gene symbol?
        assay_results: Optional[AssayResults] = None
        newAssayResults = True

        for a in dataClass.assay_results:
            if a.data_label == data_label and a.data_label_type == metaDataDict['data_label_type'].strip():
                assay_results = a
                newAssayResults = False
                break

        if not assay_results:
            assay_results = AssayResults()
            assay_results.data_label_type = metaDataDict['data_label_type'].strip()
            assay_results.data_label = data_label

        assay_results.result = result
        if metaDataDict['data_label_type'].strip() == set_up_globals.gene_symbol_data_label_type:
            gene_symbol_reference = find_gene_symbol_reference(data_label)
            if gene_symbol_reference:
                assay_results.gene_symbol_reference = gene_symbol_reference
            else:
                # Flag error if gene symbol does not exist
                message = f"Error in save of assay data: {metaDataDict['data_label_type'].strip()} {data_label} not found"
                add_event_log(active_account,
                              message,
                              success=False,
                              event_type='Import',
                              file_name=row.data_file_name,
                              document_id=str(dataClass.unique_id),
                              sub_document_id=str(data_label))
                error_msg(message)

        # //--- test for other data label types

        if newAssayResults:
            dataClass.assay_results.append(assay_results)

    return dataClass


def get_clinical_data_reference(active_account: User, documentName, study_id, data_file_name):
    clinical_data = find_clinical_data_by_study_id(study_id)
    if not clinical_data:
        message = f'You must import {set_up_globals.clinical_document_name} data for study ID {study_id} before importing {documentName} data.'
        add_event_log(active_account,
                      message,
                      success=False,
                      event_type='Import',
                      file_name=data_file_name,
                      study_id=study_id)
        error_msg(message)

    return clinical_data


def save_clinical_data(active_account: User, clinical_data: ClinicalData, documentName, study_id, data_file_name, sub_document_id):
    try:
        clinical_data.save()
    except (ValueError, ValidationError) as e:
        message = f'Save of {documentName} data with id={sub_document_id} resulted in exception: {e}'
        add_event_log(active_account,
                      message,
                      success=False,
                      event_type='Import',
                      exception_type=e.__class__.__name__,
                      file_name=data_file_name,
                      study_id=study_id,
                      document_id=str(clinical_data.id),
                      sub_document_id=str(sub_document_id))
        error_msg(message)
        return  # Skip the rest of this function

    message = f'Added / updated {documentName} data for ENID: {clinical_data.study_id} with id {sub_document_id}.'
    add_event_log(active_account,
                  message,
                  success=True,
                  event_type='Import',
                  file_name=data_file_name,
                  study_id=study_id,
                  document_id=str(clinical_data.id),
                  sub_document_id=str(sub_document_id))
    success_msg(message)

    return


def add_proteomic_data(active_account: User, df, data_file_name, metaDataDict):  # -> Proteomic:
    documentName = set_up_globals.proteomics_document_name

    for index, row in df.iterrows():
        clinical_data = get_clinical_data_reference(active_account, documentName, row.study_id, data_file_name)
        if not clinical_data:
            continue  # Skip the rest of this loop

        proteomic_data: Optional[Proteomic] = None
        newRow = True

        for b in clinical_data.proteomic:
            if b.unique_id == index:
                proteomic_data = b
                newRow = False
                break

        # If no data exists for this id, set created info
        if not proteomic_data:
            proteomic_data = Proteomic()
            proteomic_data.created_by = active_account
            proteomic_data.created_date = datetime.datetime.now()

        proteomic_data.unique_id = index

        # Find associated biospecimens
        specimen_id = str(int(float(row.study_id))) + '-' + row.timepoint + '-' + metaDataDict['biospecimen_type']
        biospecimen_data = find_biospecimen_data_by_specimen_id(specimen_id)
        if biospecimen_data:
            proteomic_data.biospecimen_data_reference = biospecimen_data

        proteomic_data = add_common_data(active_account, row, proteomic_data, metaDataDict)

        # //--- All of this code moved to add_common_data - remove after testing

        # proteomic_data.last_modified_by = active_account
        # proteomic_data.last_modified_date = datetime.datetime.now()
        # proteomic_data.data_file_name = row.data_file_name
        # # proteomic_data.excel_file_id = index
        # # //--- proteomic_data.biospecimen_data_reference = biospecimen_data
        # # proteomic_data.time = row.time
        # # proteomic_data.cpet_day = row.cpet_day
        # # proteomic_data.pre_post_cpet = row.pre_post_cpet
        # # proteomic_data.run = row.run
        # proteomic_data.timepoint = row.timepoint
        # if len(str(row.annot_1).strip()) > 0 and str(row.annot_1).strip().lower() != 'nan':
        #     proteomic_data.annot_1 = str(row.annot_1).strip()
        # if len(str(row.annot_2).strip()) > 0 and str(row.annot_2).strip().lower() != 'nan':
        #     proteomic_data.annot_2 = str(row.annot_2).strip()
        # if len(str(row.annot_3).strip()) > 0 and str(row.annot_3).strip().lower() != 'nan':
        #     proteomic_data.annot_3 = str(row.annot_3).strip()
        #
        # # Add assay results to data as a subdocument
        # # //--- this should be a separate function, but let's get it working first
        # # Gene symbols start at column 6. Subtract 2 from end to account for data_file_name and study_id
        # for i in range(6, len(row)-2):
        #     gene_symbol = row.index[i]
        #     result = row[i]
        #     # print(gene_symbol, result)
        #
        #     # Is this a new or existing assay result for this gene symbol?
        #     assay_results: Optional[AssayResults] = None
        #     newAssayResults = True
        #     for a in proteomic_data.assay_results:
        #         if a.gene_symbol == gene_symbol:  # //--- field in assay results needs to be passed parameter
        #             assay_results = a
        #             newAssayResults = False
        #             break
        #
        #     if not assay_results:
        #         assay_results = AssayResults()
        #
        #     assay_results.gene_symbol = gene_symbol
        #     assay_results.result = result
        #     if newAssayResults:
        #         proteomic_data.assay_results.append(assay_results)

        # If this a new row, append it to the clinical data (otherwise, the
        # existing row will be updated upon saving of the clinical data)
        if newRow:
            clinical_data.proteomic.append(proteomic_data)

        # Save sub document data
        save_clinical_data(active_account, clinical_data, documentName, row.study_id, row.data_file_name, index)

        # try:
        #     clinical_data.save()
        # except (ValueError, ValidationError) as e:
        #     message = f'Save of {documentName} data with id={index} resulted in exception: {e}'
        #     add_event_log(active_account,
        #                   message,
        #                   success=False,
        #                   event_type='Import',
        #                   exception_type=e.__class__.__name__,
        #                   file_name=row.data_file_name,
        #                   study_id=row.study_id,
        #                   document_id=str(clinical_data.id),
        #                   sub_document_id=str(index))
        #     error_msg(message)
        #     continue  # Skip the rest of this loop
        #
        # message = f'Added / updated {documentName} data for ENID: {clinical_data.study_id} with id {index}.'
        # add_event_log(active_account,
        #               message,
        #               success=True,
        #               event_type='Import',
        #               file_name=data_file_name,
        #               study_id=row.study_id,
        #               document_id=str(clinical_data.id),
        #               sub_document_id=str(index))
        # success_msg(message)

    return  # proteomic_data


def add_cytokine_data(active_account: User, df, data_file_name, metaDataDict):  # -> Cytokine:
    documentName = set_up_globals.cytokines_document_name

    for index, row in df.iterrows():
        clinical_data = get_clinical_data_reference(active_account, documentName, row.study_id, data_file_name)
        if not clinical_data:
            continue  # Skip the rest of this loop

        cytokine_data: Optional[Cytokine] = None
        newRow = True

        for b in clinical_data.cytokine:
            if b.unique_id == index:
                cytokine_data = b
                newRow = False
                break

        # If no data exists for this id, set created info
        if not cytokine_data:
            cytokine_data = Cytokine()
            cytokine_data.created_by = active_account
            cytokine_data.created_date = datetime.datetime.now()

        cytokine_data.unique_id = index

        # Find associated biospecimens
        specimen_id = str(int(float(row.study_id))) + '-' + row.timepoint + '-' + metaDataDict['biospecimen_type']
        biospecimen_data = find_biospecimen_data_by_specimen_id(specimen_id)
        if biospecimen_data:
            cytokine_data.biospecimen_data_reference = biospecimen_data

        cytokine_data = add_common_data(active_account, row, cytokine_data, metaDataDict)

        # If this a new row, append it to the clinical data (otherwise, the
        # existing row will be updated upon saving of the clinical data)
        if newRow:
            clinical_data.cytokine.append(cytokine_data)

        # Save sub document data
        save_clinical_data(active_account, clinical_data, documentName, row.study_id, row.data_file_name, index)

    return  # cytokine_data


def add_metabolomic_data(active_account: User, df, data_file_name, metaDataDict):  # -> Metabolomic:
    documentName = set_up_globals.metabolomics_document_name

    for index, row in df.iterrows():
        clinical_data = get_clinical_data_reference(active_account, documentName, row.study_id, data_file_name)
        if not clinical_data:
            continue  # Skip the rest of this loop

        metabolomic_data: Optional[Metabolomic] = None
        newRow = True

        for b in clinical_data.metabolomic:
            if b.unique_id == index:
                metabolomic_data = b
                newRow = False
                break

        # If no data exists for this id, set created info
        if not metabolomic_data:
            metabolomic_data = Metabolomic()
            metabolomic_data.created_by = active_account
            metabolomic_data.created_date = datetime.datetime.now()

        metabolomic_data.unique_id = index

        # Find associated biospecimens
        specimen_id = str(int(float(row.study_id))) + '-' + row.timepoint + '-' + metaDataDict['biospecimen_type']
        biospecimen_data = find_biospecimen_data_by_specimen_id(specimen_id)
        if biospecimen_data:
            metabolomic_data.biospecimen_data_reference = biospecimen_data

        metabolomic_data = add_common_data(active_account, row, metabolomic_data, metaDataDict)

        # If this a new row, append it to the clinical data (otherwise, the
        # existing row will be updated upon saving of the clinical data)
        if newRow:
            clinical_data.metabolomic.append(metabolomic_data)

        # Save sub document data
        save_clinical_data(active_account, clinical_data, documentName, row.study_id, row.data_file_name, index)

    return  # metabolomic_data


# def add_scrnaseq_summary_data(active_account: User, clinical_data: ClinicalData, biospecimen_data: Biospecimen,
# index, row) -> ScRNAseqSummary:
def add_scrnaseq_summary_data(active_account: User, df, data_file_name):  # -> ScRNAseqSummary:
    documentName = set_up_globals.scrnaseq_summary_document_name

    for index, row in df.iterrows():
        clinical_data = find_clinical_data_by_study_id(row.study_id)
        if not clinical_data:
            message = f'You must import {set_up_globals.clinical_document_name} data for study ID {row.study_id} before importing {documentName} data.'
            add_event_log(active_account,
                          message,
                          success=False,
                          event_type='Import',
                          file_name=data_file_name,
                          study_id=row.study_id)
            error_msg(message)
            continue  # Skip the rest of this loop

        scrnaseq_summary_data: Optional[ScRNAseqSummary] = None
        newRow = True

        for b in clinical_data.scrnaseq_summary:
            if b.sampleid == index:
                scrnaseq_summary_data = b
                newRow = False
                break

        # If no data exists for this id, set created info
        if not scrnaseq_summary_data:
            scrnaseq_summary_data = ScRNAseqSummary()
            scrnaseq_summary_data.created_by = active_account
            scrnaseq_summary_data.created_date = datetime.datetime.now()

        # Find associated biospecimens (first strip tube number off of the sample name)
        valMinusTubeNumberList = row.sample_name.split('-')[0:4]
        specimen_id = '-'.join(valMinusTubeNumberList)
        biospecimen_data = find_biospecimen_data_by_specimen_id(specimen_id)

        scrnaseq_summary_data.last_modified_by = active_account
        scrnaseq_summary_data.last_modified_date = datetime.datetime.now()
        scrnaseq_summary_data.sampleid = index
        scrnaseq_summary_data.data_file_name = row.data_file_name
        scrnaseq_summary_data.biospecimen_data_reference = biospecimen_data
        scrnaseq_summary_data.estimated_number_of_cells = int(row.estimated_number_of_cells)
        scrnaseq_summary_data.mean_reads_per_cell = int(row.mean_reads_per_cell)
        scrnaseq_summary_data.median_genes_per_cell = int(row.median_genes_per_cell)
        scrnaseq_summary_data.number_of_reads = int(row.number_of_reads)
        scrnaseq_summary_data.valid_barcodes = float(row.valid_barcodes)
        scrnaseq_summary_data.sequencing_saturation = float(row.sequencing_saturation)
        scrnaseq_summary_data.q30_bases_in_barcode = float(row.q30_bases_in_barcode)
        scrnaseq_summary_data.q30_bases_in_rna_read = float(row.q30_bases_in_rna_read)
        scrnaseq_summary_data.q30_bases_in_sample_index = float(row.q30_bases_in_sample_index)
        scrnaseq_summary_data.q30_bases_in_umi = float(row.q30_bases_in_umi)
        scrnaseq_summary_data.reads_mapped_to_genome = float(row.reads_mapped_to_genome)
        scrnaseq_summary_data.reads_mapped_confidently_to_genome = float(row.reads_mapped_confidently_to_genome)
        scrnaseq_summary_data.reads_mapped_confidently_to_intergenic_regions = float(
            row.reads_mapped_confidently_to_intergenic_regions)
        scrnaseq_summary_data.reads_mapped_confidently_to_intronic_regions = float(
            row.reads_mapped_confidently_to_intronic_regions)
        scrnaseq_summary_data.reads_mapped_confidently_to_exonic_regions = float(
            row.reads_mapped_confidently_to_exonic_regions)
        scrnaseq_summary_data.reads_mapped_confidently_to_transcriptome = float(
            row.reads_mapped_confidently_to_transcriptome)
        scrnaseq_summary_data.reads_mapped_antisense_to_gene = float(row.reads_mapped_antisense_to_gene)
        scrnaseq_summary_data.fraction_reads_in_cells = float(row.fraction_reads_in_cells)
        scrnaseq_summary_data.total_genes_detected = float(row.total_genes_detected)
        scrnaseq_summary_data.median_umi_counts_per_cell = float(row.median_umi_counts_per_cell)
        scrnaseq_summary_data.ten_x_batch = int(row.ten_x_batch)
        scrnaseq_summary_data.firstpass_nextseq = int(row.firstpass_nextseq)
        scrnaseq_summary_data.secondpass_nextseq = int(row.secondpass_nextseq)
        scrnaseq_summary_data.hiseq_x5 = int(row.hiseq_x5)
        scrnaseq_summary_data.novaseq_s4 = int(row.novaseq_s4)
        scrnaseq_summary_data.nextseq2k = int(row.nextseq2k)
        scrnaseq_summary_data.brc_id = row.brc_id
        scrnaseq_summary_data.enid = int(row.enid)
        scrnaseq_summary_data.sample_name = row.sample_name
        scrnaseq_summary_data.bc = row.bc

        if len(str(row.notes).strip()) > 0 and str(row.notes).strip().lower() != 'nan':
            scrnaseq_summary_data.notes = str(row.notes).strip()

        # If this a new row, append it to the clinical data (otherwise, the
        # existing row will be updated upon saving of the clinical data)
        if newRow:
            clinical_data.scrnaseq_summary.append(scrnaseq_summary_data)

        try:
            clinical_data.save()
        except (ValueError, ValidationError) as e:
            message = f'Save of {documentName} data with id={index} resulted in exception: {e}'
            add_event_log(active_account,
                          message,
                          success=False,
                          event_type='Import',
                          exception_type=e.__class__.__name__,
                          file_name=row.data_file_name,
                          study_id=row.study_id,
                          document_id=str(clinical_data.id),
                          sub_document_id=str(index))
            error_msg(message)
            continue  # Skip the rest of this loop

        message = f'Added / updated {documentName} data for ENID: {clinical_data.study_id} with id {index}.'
        add_event_log(active_account,
                      message,
                      success=True,
                      event_type='Import',
                      file_name=data_file_name,
                      study_id=row.study_id,
                      document_id=str(clinical_data.id),
                      sub_document_id=str(index))
        success_msg(message)

    return  # scrnaseq_summary_data


# def add_redcap_data(active_account: User, clinical_data: ClinicalData, index, row) -> Redcap:
def add_redcap_data(active_account: User, df, data_file_name):  # -> Redcap:
    documentName = set_up_globals.redcap_document_name

    for index, row in df.iterrows():
        clinical_data = find_clinical_data_by_study_id(row.study_id)
        if not clinical_data:
            message = f'You must import {set_up_globals.clinical_document_name} data for study ID {row.study_id} before importing {documentName} data.'
            add_event_log(active_account,
                          message,
                          success=False,
                          event_type='Import',
                          file_name=data_file_name,
                          study_id=row.study_id)
            error_msg(message)
            continue  # Skip the rest of this loop

        redcap_data: Optional[Redcap] = None
        newRow = True

        for b in clinical_data.redcap:
            if b.excel_file_id == index:
                redcap_data = b
                newRow = False
                break

        # If no data exists for this id, set created info
        if not redcap_data:
            biospecimen_data = Redcap()
            biospecimen_data.created_by = active_account
            biospecimen_data.created_date = datetime.datetime.now()

        redcap_data.last_modified_by = active_account
        redcap_data.last_modified_date = datetime.datetime.now()
        redcap_data.excel_file_id = index
        redcap_data.data_file_name = row.data_file_name
        redcap_data.ccc_date = datetime.datetime.strptime(str(row.date_received), '%Y-%m-%d %H:%M:%S').date()
        # //---

        # If this a new row, append it to the clinical data (otherwise, the
        # existing row will be updated upon saving of the clinical data)
        if newRow:
            clinical_data.redcap.append(redcap_data)

        try:
            clinical_data.save()
        except (ValueError, ValidationError) as e:
            message = f'Save of {documentName} data with id={index} resulted in exception: {e}'
            add_event_log(active_account,
                          message,
                          success=False,
                          event_type='Import',
                          exception_type=e.__class__.__name__,
                          file_name=row.data_file_name,
                          study_id=row.study_id,
                          document_id=str(clinical_data.id),
                          sub_document_id=str(index))
            error_msg(message)
            continue  # Skip the rest of this loop

        message = f'Added / updated {documentName} data for ENID: {clinical_data.study_id} with id {index}.'
        add_event_log(active_account,
                      message,
                      success=True,
                      event_type='Import',
                      file_name=data_file_name,
                      study_id=row.study_id,
                      document_id=str(clinical_data.id),
                      sub_document_id=str(index))
        success_msg(message)

    return  # redcap_data


# def add_biospecimen_data(active_account: User, index, row) -> Biospecimen:
def add_biospecimen_data(active_account: User, df, data_file_name):  # -> Biospecimen:
    documentName = set_up_globals.biospecimen_document_name

    for index, row in df.iterrows():
        currentVersion = 0
        biospecimen_data = find_biospecimen_data_by_specimen_id(index)

        if biospecimen_data:
            # If data exists, save in version history
            currentVersion = biospecimen_data.version_number
            biospecimen_data_version_history = BiospecimenVersionHistory()

            attributeList = utilities.attributes(Biospecimen)
            # print(attributeList)
            for attrib in attributeList:
                # print(attrib)
                biospecimen_data_version_history[attrib] = biospecimen_data[attrib]

            biospecimen_data_version_history.save()
        else:
            # If no data exists for this id, set created info
            biospecimen_data = Biospecimen()
            biospecimen_data.created_by = active_account
            biospecimen_data.created_date = datetime.datetime.now()

        biospecimen_data.specimen_id = index  # row.specimen_id
        biospecimen_data.last_modified_by = active_account
        biospecimen_data.last_modified_date = datetime.datetime.now()
        biospecimen_data.version_number = currentVersion + 1
        biospecimen_data.study_id = int(row.study_id)
        # biospecimen_data.clinical_data_reference = clinical_data
        biospecimen_data.cpet_day = row.cpet_day
        biospecimen_data.pre_post_cpet = row.pre_post_cpet
        biospecimen_data.specimen_type = row.specimen_type

        # Add biospecimen tube info to data as a subdocument
        # Is this a new or existing sample for this biospecimen?
        biospecimen_tube_info: Optional[BiospecimenTubeInfo] = None
        newBiospecimenTubeInfo = True
        for a in biospecimen_data.biospecimen_tube_info:
            if a.sample_id == int(row.sample_id):
                biospecimen_tube_info = a
                newBiospecimenTubeInfo = False
                break

        if not biospecimen_tube_info:
            biospecimen_tube_info = BiospecimenTubeInfo()

        biospecimen_tube_info.sample_id = int(row.sample_id)
        biospecimen_tube_info.date_received = datetime.datetime.strptime(str(row.date_received), '%Y-%m-%d %H:%M:%S').date()
        biospecimen_tube_info.data_file_name = row.data_file_name
        biospecimen_tube_info.tube_number = int(row.tube_number)
        biospecimen_tube_info.freezer_id = row.freezer_id
        biospecimen_tube_info.box_number = int(row.box_number)
        biospecimen_tube_info.box_position = int(row.box_position)
        biospecimen_tube_info.analysis_id = row.analysis_id

        if row.is_removed == 'TRUE':
            biospecimen_tube_info.is_removed = True
        else:
            biospecimen_tube_info.is_removed = False

        if len(str(row.comments).strip()) > 0 and str(row.comments).strip().lower() != 'nan':
            biospecimen_tube_info.comments = str(row.comments).strip()

        if newBiospecimenTubeInfo:
            biospecimen_data.biospecimen_tube_info.append(biospecimen_tube_info)

        # biospecimen_data.sample_id = int(row.sample_id)
        # biospecimen_data.date_received = datetime.datetime.strptime(str(row.date_received), '%Y-%m-%d %H:%M:%S').date()
        # biospecimen_data.data_file_name = row.data_file_name
        # biospecimen_data.tube_number = int(row.tube_number)
        # biospecimen_data.freezer_id = row.freezer_id
        # biospecimen_data.box_number = int(row.box_number)
        # biospecimen_data.box_position = int(row.box_position)
        # biospecimen_data.analysis_id = row.analysis_id

        # if row.is_removed == 'TRUE':
        #     biospecimen_data.is_removed = True
        # else:
        #     biospecimen_data.is_removed = False
        #
        # if len(str(row.comments).strip()) > 0 and str(row.comments).strip().lower() != 'nan':
        #     biospecimen_data.comments = str(row.comments).strip()

        try:
            biospecimen_data.save()
        except (ValueError, ValidationError) as e:
            message = f'Save of {documentName} data with id={index} resulted in exception: {e}'
            add_event_log(active_account,
                          message,
                          success=False,
                          event_type='Import',
                          exception_type=e.__class__.__name__,
                          file_name=row.data_file_name,
                          document_id=str(index))
            error_msg(message)
            continue  # Skip the rest of this loop

        message = f'Added / updated {documentName} data for Specimen ID: {index} with id {biospecimen_data.id}.'
        add_event_log(active_account,
                      message,
                      success=True,
                      event_type='Import',
                      file_name=data_file_name,
                      sample_id=row.sample_id,
                      document_id=str(index))
        success_msg(message)

    # //--- this would be a good place to check / update references in each sub-document in the clinical data

    return  # biospecimen_data

def find_gene_symbol_reference(gene_symbol: str) -> GeneSymbols:
    return GeneSymbols.objects(data_label=gene_symbol).first()


def find_ensembl_gene_id_reference(ensembl_gene_id: str) -> EnsemblGeneIDs:
    return EnsemblGeneIDs.objects(data_label=ensembl_gene_id).first()


def find_cytokine_label_reference(cytokine_label: str) -> CytokineLabels:
    return CytokineLabels.objects(data_label=cytokine_label).first()


def find_gene_symbol_to_ensembl_gene_id_reference_in_data_record(gene_symbol_data: GeneSymbols, ensembl_geneid_data: EnsemblGeneIDs):
    return GeneSymbolsToEnsemblGeneIDs.objects(Q(gene_symbol_reference=gene_symbol_data.id) & Q(ensembl_geneid_reference=ensembl_geneid_data.id)).first()


# def find_gene_symbol_reference_in_data_type_class(cls, id):
#     return cls.objects(gene_symbol_references=id).first()


def add_data_label_types(active_account: User, df, data_file_name):
    documentName = set_up_globals.data_label_type_document_name

    gene_symbol_data_label_type = set_up_globals.gene_symbol_data_label_type
    ensembl_gene_id_data_label_type = set_up_globals.ensembl_gene_id_data_label_type
    cytokine_data_label_type = set_up_globals.cytokine_data_label_type

    gene_symbol_to_ensembl_geneid_ref = set_up_globals.gene_symbol_to_ensembl_geneid_ref
    gene_symbol_to_cytokine_label_ref = set_up_globals.gene_symbol_to_cytokine_label_ref

    for index, row in df.iterrows():

        # For testing, only load subset of genes (those starting with 'ACTN')
        if set_up_globals.testMode:
            testGeneList = ['A2M', 'ACTB', 'ACTN4', 'ACTR3', 'AGT', 'ALB', 'ALDOA', 'AMBP', 'APOA1', 'APOA4', 'APOC1',
                            'NGFB', 'FGF2', 'CCL27', 'CCL11', 'CSF3', 'CSF2', 'CXCL1', 'HGF', 'IFNA2', 'IFNG', 'IL10',
                            'IL12B', 'IL12B', 'IL13', 'IL15', 'IL16', 'IL17', 'IL18', 'IL1A', 'IL1B', 'IL1R1', 'IL2',
                            'IL2RA', 'IL3', 'IL4', 'IL5', 'IL6', 'IL7', 'CXCL8', 'IL9', 'CXCL10', 'LIF', 'CSF1',
                            'CCL2', 'CCL7', 'MIF', 'CXCR3', 'CCL3', 'CCL4', 'PDGFB', 'CCL5', 'KITLG', 'SCGF',
                            'CXCL12', 'TNFB', 'TNFA', 'TNFSF10','VEGF',
                            'IL_2ra', 'MIG', 'MIP_1B', 'IL_6', 'IFN_a2', 'IFN_g', 'SDF_1a', 'IL_1ra', 'MCP_3', 'IL_16',
                            'IL_12p40', 'LIF', 'TNF_B', 'IL_5', 'GM_CSF', 'MIF', 'TNFa', 'RANTES', 'IL_2', 'IL_1B',
                            'IL_18', 'Eotaxin', 'bFGF', 'VEGF', 'B_NGF', 'PDGF_BB', 'IP_10', 'IL_13', 'IL_4', 'MCP_1',
                            'IL_8', 'MIP_1a', 'IL_10', 'G_CSF', 'GROa', 'HGF', 'IL_1a', 'IL_3', 'SCF', 'TRAIL', 'M_CSF'
                            'CTACK', 'IL_15', 'IL_7', 'IL_12p70', 'IL_17', 'IL_9', 'SCGF_B']
            if row.gene_name not in testGeneList:
                continue

        # currentVersion = 0
        gene_symbol_data = find_gene_symbol_reference(row.gene_name)
        ensembl_gene_id_data = find_ensembl_gene_id_reference(row.gene_stable_id)
        cytokine_label_data = find_cytokine_label_reference(row.cytokine_label)

        # //--- need to set this up for all data labels
        # //--- need some way of tracking changes - version history maybe

        if gene_symbol_data:
            pass
            # Instead of keeping a version history, maintain a list of prior values for each label
            # currentVersion = gene_symbol_data.version_number
            # gene_symbol_data_version_history = DataLabelTypeVersionHistory()

            # attributeList = utilities.attributes(GeneSymbols)
            # # print(attributeList)
            # for attrib in attributeList:
            #     # print(attrib)
            #     gene_symbol_data_version_history[attrib] = gene_symbol_data[attrib]
            # gene_symbol_data_version_history.save()
        else:
            # If no data exists for this id, set created info
            gene_symbol_data = GeneSymbols()
            # gene_symbol_data.ensembl_geneid_references = []

        if not ensembl_gene_id_data:
            ensembl_gene_id_data = EnsemblGeneIDs()
            # ensembl_gene_id_data.gene_symbol_references = []

        if not cytokine_label_data:
            cytokine_label_data = CytokineLabels()

        # gene_symbol_data.data_label_type = gene_symbol_data_label_type
        # gene_symbol_data.version_number = currentVersion + 1
        gene_symbol_data.data_label = row.gene_name
        ensembl_gene_id_data.data_label = row.gene_stable_id
        cytokine_label_data = row.cytokine_label

        # Save gene symbols
        try:
            gene_symbol_data.save()
        except (ValueError, ValidationError) as e:
            message = f'Save of {documentName} data with {gene_symbol_data_label_type}={row.gene_name} resulted in exception: {e}'
            add_event_log(active_account,
                          message,
                          success=False,
                          event_type='Import',
                          exception_type=e.__class__.__name__,
                          file_name=row.data_file_name,
                          document_id=str(row.gene_name))
            error_msg(message)
            continue  # Skip the rest of this loop

        message = f'Added / updated {documentName} data for {gene_symbol_data_label_type}: {row.gene_name} with id {gene_symbol_data.id}.'
        add_event_log(active_account,
                      message,
                      success=True,
                      event_type='Import',
                      file_name=data_file_name,
                      document_id=str(gene_symbol_data.id))
        success_msg(message)

        # Save cytokine labels
        try:
            cytokine_label_data.save()
        except (ValueError, ValidationError) as e:
            message = f'Save of {documentName} data with {cytokine_data_label_type}={row.cytokine_label} resulted in exception: {e}'
            add_event_log(active_account,
                          message,
                          success=False,
                          event_type='Import',
                          exception_type=e.__class__.__name__,
                          file_name=row.data_file_name,
                          document_id=str(row.cytokine_label))
            error_msg(message)
            continue  # Skip the rest of this loop

        message = f'Added / updated {documentName} data for {cytokine_data_label_type}: {row.cytokine_label} with id {cytokine_label_data.id}.'
        add_event_log(active_account,
                      message,
                      success=True,
                      event_type='Import',
                      file_name=data_file_name,
                      document_id=str(cytokine_label_data.id))
        success_msg(message)

        # Save ensembl gene ids
        try:
            ensembl_gene_id_data.save()
        except (ValueError, ValidationError) as e:
            message = f'Save of {documentName} data with {ensembl_gene_id_data_label_type}={row.gene_stable_id} resulted in exception: {e}'
            add_event_log(active_account,
                          message,
                          success=False,
                          event_type='Import',
                          exception_type=e.__class__.__name__,
                          file_name=row.data_file_name,
                          document_id=str(row.gene_stable_id))
            error_msg(message)
            continue  # Skip the rest of this loop

        message = f'Added / updated {documentName} data for {ensembl_gene_id_data_label_type}: {row.gene_stable_id} with id {ensembl_gene_id_data.id}.'
        add_event_log(active_account,
                      message,
                      success=True,
                      event_type='Import',
                      file_name=data_file_name,
                      document_id=str(ensembl_gene_id_data.id))
        success_msg(message)

        # Set up references to other data label types
        # //---
        gene_symbol_to_ensembl_geneid_data = find_gene_symbol_to_ensembl_gene_id_reference_in_data_record(gene_symbol_data, ensembl_gene_id_data)
        if not gene_symbol_to_ensembl_geneid_data:
            gene_symbol_to_ensembl_geneid_data = GeneSymbolsToEnsemblGeneIDs()
            gene_symbol_to_ensembl_geneid_data.gene_symbol_data_label = row.gene_name
            gene_symbol_to_ensembl_geneid_data.ensembl_geneid_data_label = row.gene_stable_id
            gene_symbol_to_ensembl_geneid_data.gene_symbol_reference = gene_symbol_data
            gene_symbol_to_ensembl_geneid_data.ensembl_geneid_reference = ensembl_gene_id_data

        # if ensembl_gene_id_data.id not in gene_symbol_data.ensembl_geneid_references:
        #     gene_symbol_data.ensembl_geneid_references.append(ensembl_gene_id_data)

        # if gene_symbol_data.id not in ensembl_gene_id_data.gene_symbol_references:
        #     ensembl_gene_id_data.gene_symbol_references.append(gene_symbol_data)

        # Save gene symbols to ensembl gene ids many-to-many relationship
        try:
            gene_symbol_to_ensembl_geneid_data.save()
        except (ValueError, ValidationError) as e:
            message = f'Save of {documentName} data with {gene_symbol_to_ensembl_geneid_ref}={row.gene_name} and {row.gene_stable_id} resulted in exception: {e}'
            add_event_log(active_account,
                          message,
                          success=False,
                          event_type='Import',
                          exception_type=e.__class__.__name__,
                          file_name=row.data_file_name,
                          # document_id=str(row.gene_name)
                          )
            error_msg(message)
            continue  # Skip the rest of this loop

        message = f'Added / updated {documentName} data for {gene_symbol_to_ensembl_geneid_ref}: {row.gene_name} and {row.gene_stable_id} with id {gene_symbol_to_ensembl_geneid_data.id}.'
        add_event_log(active_account,
                      message,
                      success=True,
                      event_type='Import',
                      file_name=data_file_name,
                      document_id=str(gene_symbol_to_ensembl_geneid_data.id))
        success_msg(message)

    return  # data_label_types


def add_event_log(active_account: User,
                  message,
                  event_type='Import',
                  exception_type=None,
                  success=False,
                  file_name=None,
                  study_id=None,
                  sample_id=None,
                  document_id=None,
                  sub_document_id=None,
                  comment=None) -> Event_log:
    # If no data exists for this id, set created info
    event_log_data = Event_log()
    event_log_data.created_by = active_account
    event_log_data.created_date = datetime.datetime.now()

    event_log_data.event_type = event_type
    event_log_data.success = success
    event_log_data.message = message
    if exception_type is not None:
        event_log_data.exception_type = exception_type
    if file_name is not None:
        event_log_data.file_name = file_name
    if study_id is not None:
        event_log_data.study_id = study_id
    if sample_id is not None:
        event_log_data.sample_id = sample_id
    if document_id is not None:
        event_log_data.document_id = document_id
    if sub_document_id is not None:
        event_log_data.sub_document_id = sub_document_id

    if comment is not None:
        if len(str(comment).strip()) > 0 and str(comment).strip().lower() != 'nan':
            event_log_data.comment = str(comment).strip()

    event_log_data.save()

    return event_log_data


def success_msg(text):
    print(Fore.LIGHTGREEN_EX + text + Fore.WHITE)


def error_msg(text):
    print(Fore.LIGHTRED_EX + text + Fore.WHITE)
