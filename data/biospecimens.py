import datetime
import mongoengine
from data.users import User
# from data.clinical_data import ClinicalData

cpet_day_choice = ('D1', 'D2')
pre_post_cpet_choice = ('PRE', 'POST')
specimen_type_choice = ('PAXgene',
                        'Whole Blood',
                        'Serum',
                        'Urine',
                        'Plasma',
                        'PBMC')


class Biospecimen(mongoengine.Document):
    created_by = mongoengine.ReferenceField(User, required=True)
    created_date = mongoengine.DateTimeField(required=True)
    last_modified_by = mongoengine.ReferenceField(User, required=True)
    last_modified_date = mongoengine.DateTimeField(default=datetime.datetime.now)

    data_file_name = mongoengine.StringField(required=True)
    version_number = mongoengine.IntField(required=True)
    sample_id = mongoengine.IntField(required=True)
    date_received = mongoengine.DateTimeField(required=True)
    study_id = mongoengine.IntField(required=True)
    # clinical_data_reference = mongoengine.ReferenceField(ClinicalData, required=True)
    cpet_day = mongoengine.StringField(choices=cpet_day_choice)
    pre_post_cpet = mongoengine.StringField(choices=pre_post_cpet_choice)
    specimen_type = mongoengine.StringField(choices=specimen_type_choice)
    # cpet_day = mongoengine.StringField()
    # pre_post_cpet = mongoengine.StringField()
    # specimen_type = mongoengine.StringField()
    tube_number = mongoengine.IntField()
    freezer_id = mongoengine.StringField()
    box_number = mongoengine.IntField()
    box_position = mongoengine.IntField()
    specimen_id = mongoengine.StringField()
    analysis_id = mongoengine.StringField()
    is_removed = mongoengine.BooleanField()
    comments = mongoengine.StringField()

    @property
    def days_since_received(self):
        dt = datetime.datetime.now() - self.date_received
        return dt.days
    meta = {
        'db_alias': 'core',
        'collection': 'biospecimen_data'
        # 'indexes': ['study_id', 'site', '$phenotype']
    }


class BiospecimenVersionHistory(mongoengine.Document):
    created_by = mongoengine.ReferenceField(User, required=True)
    created_date = mongoengine.DateTimeField(required=True)
    last_modified_by = mongoengine.ReferenceField(User, required=True)
    last_modified_date = mongoengine.DateTimeField(default=datetime.datetime.now)

    data_file_name = mongoengine.StringField(required=True)
    version_number = mongoengine.IntField(required=True)
    sample_id = mongoengine.IntField(required=True)
    date_received = mongoengine.DateTimeField(required=True)
    study_id = mongoengine.IntField(required=True)
    # clinical_data_reference = mongoengine.ReferenceField(ClinicalData, required=True)
    cpet_day = mongoengine.StringField(choices=cpet_day_choice)
    pre_post_cpet = mongoengine.StringField(choices=pre_post_cpet_choice)
    specimen_type = mongoengine.StringField(choices=specimen_type_choice)
    # cpet_day = mongoengine.StringField()
    # pre_post_cpet = mongoengine.StringField()
    # specimen_type = mongoengine.StringField()
    tube_number = mongoengine.IntField()
    freezer_id = mongoengine.StringField()
    box_number = mongoengine.IntField()
    box_position = mongoengine.IntField()
    specimen_id = mongoengine.StringField()
    analysis_id = mongoengine.StringField()
    is_removed = mongoengine.BooleanField()
    comments = mongoengine.StringField()

    meta = {
        'db_alias': 'core',
        'collection': 'biospecimen_data_version_history'
    }
