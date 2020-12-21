import datetime
import mongoengine

from data.biospecimens import Biospecimen
from data.redcap import Redcap
from data.proteomics import Proteomic
from data.scrnaseq_summary import ScRNAseqSummary
from data.users import User

site_choices = ((1, 'ITH'),
                (2, 'LA'),
                (3, 'NYC'))
sex_choices = (('F', 'Female'),
               ('M', 'Male'),
               ('Mt', 'Trans-male'),
               ('Ft', 'Trans-female'))
phenotype_choices = (('HC', 'Healthy control'), ('ME/CFS', 'ME/CFS participant'))
ethnicity_choice = ((1, 'Hispanic or Latino'),
                    (2, 'Not Hispanic or Latino'),
                    (3, 'Unknown'))
race_choice = ((1, 'American Indian or Alaska Native'),
               (2, 'Asian'),
               (3, 'Black or African American'),
               (4, 'Native Hawaiian or other Pacific Islander'),
               (5, 'White'),
               (6, 'Unknown'))
mecfs_sudden_gradual_choice = ((1, 'Sudden'), (2, 'Gradual'))


class ClinicalData(mongoengine.Document):
    created_by = mongoengine.ReferenceField(User, required=True)
    created_date = mongoengine.DateTimeField(required=True)
    last_modified_by = mongoengine.ReferenceField(User, required=True)
    last_modified_date = mongoengine.DateTimeField(default=datetime.datetime.now)

    data_file_name = mongoengine.StringField(required=True)
    version_number = mongoengine.IntField(required=True)
    study_id = mongoengine.IntField(required=True)
    biospecimen_data_references = mongoengine.ListField(mongoengine.ReferenceField(Biospecimen))
    site = mongoengine.IntField(choices=site_choices)
    sex = mongoengine.StringField(choices=sex_choices)
    phenotype = mongoengine.StringField(required=True, choices=phenotype_choices)
    # site = mongoengine.IntField()
    # sex = mongoengine.StringField()
    # phenotype = mongoengine.StringField(required=True)
    age = mongoengine.IntField()
    height_in = mongoengine.FloatField()
    weight_lbs = mongoengine.FloatField()
    bmi = mongoengine.FloatField()
    ethnicity = mongoengine.IntField(choices=ethnicity_choice)
    race = mongoengine.IntField(choices=race_choice)
    mecfs_sudden_gradual = mongoengine.IntField(choices=mecfs_sudden_gradual_choice)
    # ethnicity = mongoengine.IntField()
    # race = mongoengine.IntField()
    # mecfs_sudden_gradual = mongoengine.IntField()
    mecfs_duration = mongoengine.IntField()

    # biospecimens = mongoengine.EmbeddedDocumentListField(Biospecimen)
    redcap = mongoengine.EmbeddedDocumentListField(Redcap)
    proteomic = mongoengine.EmbeddedDocumentListField(Proteomic)
    scrnaseq_summary = mongoengine.EmbeddedDocumentListField(ScRNAseqSummary)

    meta = {
        'db_alias': 'core',
        'collection': 'clinical_data',
        # 'allow_inheritance': True,
        # 'indexes': ['study_id', 'site', '$phenotype']
    }


class ClinicalDataVersionHistory(mongoengine.Document):
    # This class should be an exact copy of the the above class with only the collection name
    # changed in the meta data. I know this is what inheritance is for, but for some reason
    # mongoengine won't allow the setting of a collection in a sub-class
    created_by = mongoengine.ReferenceField(User, required=True)
    created_date = mongoengine.DateTimeField(required=True)
    last_modified_by = mongoengine.ReferenceField(User, required=True)
    last_modified_date = mongoengine.DateTimeField(default=datetime.datetime.now)

    data_file_name = mongoengine.StringField(required=True)
    version_number = mongoengine.IntField(required=True)
    study_id = mongoengine.IntField(required=True)
    biospecimen_data_references = mongoengine.ListField(mongoengine.ReferenceField(Biospecimen))
    site = mongoengine.IntField(choices=site_choices)
    sex = mongoengine.StringField(choices=sex_choices)
    phenotype = mongoengine.StringField(required=True, choices=phenotype_choices)
    age = mongoengine.IntField()
    height_in = mongoengine.FloatField()
    weight_lbs = mongoengine.FloatField()
    bmi = mongoengine.FloatField()
    ethnicity = mongoengine.IntField(choices=ethnicity_choice)
    race = mongoengine.IntField(choices=race_choice)
    mecfs_sudden_gradual = mongoengine.IntField(choices=mecfs_sudden_gradual_choice)
    # ethnicity = mongoengine.IntField()
    # race = mongoengine.IntField()
    # mecfs_sudden_gradual = mongoengine.IntField()
    mecfs_duration = mongoengine.IntField()

    # biospecimens = mongoengine.EmbeddedDocumentListField(Biospecimen)
    redcap = mongoengine.EmbeddedDocumentListField(Redcap)
    proteomic = mongoengine.EmbeddedDocumentListField(Proteomic)
    scrnaseq_summary = mongoengine.EmbeddedDocumentListField(ScRNAseqSummary)

    meta = {
        'db_alias': 'core',
        'collection': 'clinical_data_version_history'
    }
