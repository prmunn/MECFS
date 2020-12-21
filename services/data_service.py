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
from data.proteomics import Proteomic
from data.scrnaseq_summary import ScRNAseqSummary
from data.biospecimens import Biospecimen, BiospecimenVersionHistory
from data.users import User
from data.event_log import Event_log

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


def find_biospecimen_data_by_sample_id(sample_id: int) -> Biospecimen:
    return Biospecimen.objects(sample_id=sample_id).first()


def find_biospecimen_data_by_study_id(study_id: int) -> List[Biospecimen]:
    return list(Biospecimen.objects(study_id=study_id).all())


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
        clinical_data.site = int(row.site)
        clinical_data.sex = row.sex
        clinical_data.phenotype = row.phenotype
        clinical_data.age = int(row.age)
        clinical_data.height_in = float(row.height_in)
        clinical_data.weight_lbs = float(row.weight_lbs)
        clinical_data.bmi = float(row.bmi)
        clinical_data.ethnicity = int(row.ethnicity)
        clinical_data.race = int(row.race)
        if str(row.mecfs_sudden_gradual).strip().isnumeric():
            clinical_data.mecfs_sudden_gradual = int(row.mecfs_sudden_gradual)
        if str(row.mecfs_duration).strip().isnumeric():
            clinical_data.mecfs_duration = int(row.mecfs_duration)

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
            continue  # Skip the rest f this loop

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


def add_proteomic_data(active_account: User, df, data_file_name):  # -> Proteomic:
    documentName = set_up_globals.proteomics_document_name

    for index, row in df.iterrows():
        clinical_data = find_clinical_data_by_study_id(row.study_id)
        if not clinical_data:
            message = f'You must import clinical data for study ID {row.study_id} before importing {documentName} data.'
            add_event_log(active_account,
                          message,
                          success=False,
                          event_type='Import',
                          file_name=data_file_name,
                          study_id=row.study_id)
            error_msg(message)
            continue  # Skip the rest of this loop

        proteomic_data: Optional[Proteomic] = None
        newRow = True

        for b in clinical_data.proteomic:
            if b.excel_file_id == index:
                proteomic_data = b
                newRow = False
                break

        # If no data exists for this id, set created info
        if not proteomic_data:
            proteomic_data = Proteomic()
            proteomic_data.created_by = active_account
            proteomic_data.created_date = datetime.datetime.now()

        proteomic_data.last_modified_by = active_account
        proteomic_data.last_modified_date = datetime.datetime.now()
        proteomic_data.data_file_name = row.data_file_name
        proteomic_data.excel_file_id = index
        # //--- proteomic_data.biospecimen_data_reference = biospecimen_data
        proteomic_data.time = row.time
        proteomic_data.cpet_day = row.cpet_day
        proteomic_data.pre_post_cpet = row.pre_post_cpet
        proteomic_data.run = row.run
        proteomic_data.a2m = float(row.a2m)
        proteomic_data.actb = float(row.actb)
        proteomic_data.actn4 = float(row.actn4)
        proteomic_data.actr3 = float(row.actr3)
        proteomic_data.agt = float(row.agt)
        proteomic_data.alb = float(row.alb)
        proteomic_data.aldoa = float(row.aldoa)
        proteomic_data.ambp = float(row.ambp)
        proteomic_data.apoa1 = float(row.apoa1)
        proteomic_data.apoa4 = float(row.apoa4)
        proteomic_data.apoc1 = float(row.apoc1)

        # If this a new row, append it to the clinical data (otherwise, the
        # existing row will be updated upon saving of the clinical data)
        if newRow:
            clinical_data.proteomic.append(proteomic_data)

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

    return  # proteomic_data


# def add_scrnaseq_summary_data(active_account: User, clinical_data: ClinicalData, biospecimen_data: Biospecimen,
# index, row) -> ScRNAseqSummary:
def add_scrnaseq_summary_data(active_account: User, df, data_file_name):  # -> ScRNAseqSummary:
    documentName = set_up_globals.scrnaseq_summary_document_name

    for index, row in df.iterrows():
        clinical_data = find_clinical_data_by_study_id(row.study_id)
        if not clinical_data:
            message = f'You must import clinical data for study ID {row.study_id} before importing {documentName} data.'
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

        # Find associated biospecimens
        biospecimen_data = find_biospecimen_data_by_sample_id(index)

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
            message = f'You must import clinical data for study ID {row.study_id} before importing {documentName} data.'
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
        biospecimen_data = find_biospecimen_data_by_sample_id(index)

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

        biospecimen_data.last_modified_by = active_account
        biospecimen_data.last_modified_date = datetime.datetime.now()
        biospecimen_data.sample_id = index
        biospecimen_data.data_file_name = row.data_file_name
        biospecimen_data.version_number = currentVersion + 1
        biospecimen_data.study_id = int(row.study_id)
        # biospecimen_data.clinical_data_reference = clinical_data
        biospecimen_data.date_received = datetime.datetime.strptime(str(row.date_received), '%Y-%m-%d %H:%M:%S').date()
        biospecimen_data.cpet_day = row.cpet_day
        biospecimen_data.pre_post_cpet = row.pre_post_cpet
        biospecimen_data.specimen_type = row.specimen_type
        biospecimen_data.tube_number = int(row.tube_number)
        biospecimen_data.freezer_id = row.freezer_id
        biospecimen_data.box_number = int(row.box_number)
        biospecimen_data.box_position = int(row.box_position)
        biospecimen_data.specimen_id = row.specimen_id
        biospecimen_data.analysis_id = row.analysis_id

        if row.is_removed == 'TRUE':
            biospecimen_data.is_removed = True
        else:
            biospecimen_data.is_removed = False

        if len(str(row.comments).strip()) > 0 and str(row.comments).strip().lower() != 'nan':
            biospecimen_data.comments = str(row.comments).strip()

        # If this a new row, append it to the clinical data (otherwise, the
        # existing row will be updated upon saving of the clinical data)
        # if newRow:
        #     clinical_data.biospecimens.append(biospecimen_data)

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

        message = f'Added / updated {documentName} data for Sample ID: {index} with id {biospecimen_data.id}.'
        add_event_log(active_account,
                      message,
                      success=True,
                      event_type='Import',
                      file_name=data_file_name,
                      sample_id=index,
                      document_id=str(biospecimen_data.id))
        success_msg(message)

    # //--- this would be a good place to check / update references in each sub-document in the clinical data

    return  # biospecimen_data


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


def find_clinical_data_for_user(account: User) -> List[ClinicalData]:
    query = ClinicalData.objects(id__in=account.id).all()
    clinical_data = list(query)

    return clinical_data


def find_clinical_data() -> List[ClinicalData]:
    return list(ClinicalData.objects())


def find_only_scrnaseq_summary_data() -> List[ClinicalData]:
    return list(
        ClinicalData.objects(scrnaseq_summary__sampleid__exists=True).only('study_id', 'phenotype', 'site', 'sex',
                                                                           'age', 'scrnaseq_summary').order_by(
            'study_id'))


def success_msg(text):
    print(Fore.LIGHTGREEN_EX + text + Fore.WHITE)


def error_msg(text):
    print(Fore.LIGHTRED_EX + text + Fore.WHITE)
