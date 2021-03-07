import datetime
import mongoengine

from data.biospecimens import Biospecimen
from data.redcap import Redcap
from data.assay_classes import Proteomic
from data.assay_classes import Cytokine
from data.assay_classes import Metabolomic
from data.scrnaseq_summary import ScRNAseqSummary
from data.users import User

site_choices = ('ITH',
                'LA',
                'NYC')
sex_choices = (('F', 'Female'),
               ('M', 'Male'),
               ('Mt', 'Trans-male'),
               ('Ft', 'Trans-female'))
phenotype_choices = (('HC', 'Healthy control'), ('ME/CFS', 'ME/CFS participant'))
ethnicity_choice = (('1', 'Hispanic or Latino'),
                    ('2', 'Not Hispanic or Latino'),
                    ('3', 'Unknown'),
                    ('NA', 'Not applicable'))
race_choice = (('1', 'American Indian or Alaska Native'),
               ('2', 'Asian'),
               ('3', 'Black or African American'),
               ('4', 'Native Hawaiian or other Pacific Islander'),
               ('5', 'White'),
               ('6', 'Unknown'),
               ('NA', 'Not applicable'))
mecfs_sudden_gradual_choice = (('1', 'Sudden'), ('2', 'Gradual'), ('NA', 'Not applicable'))
qmep_sudevent_choice = (('1', 'Viral illness'),
                        ('2', 'Viral-like illness'),
                        ('3', 'Food poisoning'),
                        ('4', 'Physical trauma'),
                        ('5', 'Life stress event'),
                        ('6', 'Vaccine'),
                        ('7', 'Other'),
                        ('8', 'Multiple'),
                        ('NA', 'Not applicable'))
change_choice = (('1', '(-.499 to 4.99%)'),
                 ('2', '(>=5%)'),
                 ('3', '(=<5%)'),
                 ('NA', 'Not applicable'))


class ClinicalData(mongoengine.Document):
    created_by = mongoengine.ReferenceField(User, required=True)
    created_date = mongoengine.DateTimeField(required=True)
    last_modified_by = mongoengine.ReferenceField(User, required=True)
    last_modified_date = mongoengine.DateTimeField(default=datetime.datetime.now)

    data_file_name = mongoengine.StringField(required=True)
    version_number = mongoengine.IntField(required=True)
    study_id = mongoengine.IntField(required=True)
    biospecimen_data_references = mongoengine.ListField(mongoengine.ReferenceField(Biospecimen))
    site = mongoengine.StringField(choices=site_choices)
    sex = mongoengine.StringField(choices=sex_choices)
    phenotype = mongoengine.StringField(required=True, choices=phenotype_choices)
    age = mongoengine.IntField()
    height_in = mongoengine.FloatField()
    weight_lbs = mongoengine.FloatField()
    bmi = mongoengine.FloatField()
    ethnicity = mongoengine.StringField(choices=ethnicity_choice)
    race = mongoengine.StringField(choices=race_choice)
    mecfs_sudden_gradual = mongoengine.StringField(choices=mecfs_sudden_gradual_choice)
    qmep_sudevent = mongoengine.StringField(choices=qmep_sudevent_choice)
    mecfs_duration = mongoengine.StringField()
    # qmep_mediagnosis = mongoengine.StringField()
    # qmep_mesymptoms = mongoengine.StringField()
    qmep_metimediagnosis = mongoengine.StringField()
    # cpet_d1 = mongoengine.StringField()
    # cpet_d2 = mongoengine.StringField()
    vo2peak1 = mongoengine.StringField()
    vo2peak2 = mongoengine.StringField()
    vo2change = mongoengine.StringField(choices=change_choice)
    at1 = mongoengine.StringField()
    at2 = mongoengine.StringField()
    atchange = mongoengine.StringField(choices=change_choice)

    # biospecimens = mongoengine.EmbeddedDocumentListField(Biospecimen)
    redcap = mongoengine.EmbeddedDocumentListField(Redcap)
    proteomic = mongoengine.EmbeddedDocumentListField(Proteomic)
    cytokine = mongoengine.EmbeddedDocumentListField(Cytokine)
    metabolomic = mongoengine.EmbeddedDocumentListField(Metabolomic)
    scrnaseq_summary = mongoengine.EmbeddedDocumentListField(ScRNAseqSummary)

    @classmethod
    def get_demographic_attributes(cls):
        # Remove non-JSON serializable objects
        excludeFields = ['objects', 'DoesNotExist', 'MultipleObjectsReturned', 'id',
                         'biospecimen_data_references', 'redcap', 'proteomic', 'cytokine', 'metabolomic',
                         'scrnaseq_summary', 'get_demographic_attributes', 'demographic_data_only',
                         'redcap_data_only', 'proteomic_data_only', 'cytokine_data_only',
                         'metabolomic_data_only', 'scrnaseq_summary_data_only']
        return [i for i in cls.__dict__.keys() if not i.startswith('_') and i not in excludeFields]

    @mongoengine.queryset_manager
    def demographic_data_only(doc_cls, queryset):
        return queryset.exclude('biospecimen_data_references',
                                'redcap',
                                'proteomic',
                                'cytokine',
                                'metabolomic',
                                'scrnaseq_summary').order_by('phenotype')

    @mongoengine.queryset_manager
    def redcap_data_only(doc_cls, queryset):
        return queryset.exclude('biospecimen_data_references',
                                'proteomic',
                                'cytokine',
                                'metabolomic',
                                'scrnaseq_summary').order_by('phenotype')

    @mongoengine.queryset_manager
    def proteomic_data_only(doc_cls, queryset):
        return queryset.exclude('biospecimen_data_references',
                                'redcap',
                                'cytokine',
                                'metabolomic',
                                'scrnaseq_summary').order_by('phenotype')

    @mongoengine.queryset_manager
    def cytokine_data_only(doc_cls, queryset):
        return queryset.exclude('biospecimen_data_references',
                                'redcap',
                                'proteomic',
                                'metabolomic',
                                'scrnaseq_summary').order_by('phenotype')

    @mongoengine.queryset_manager
    def metabolomic_data_only(doc_cls, queryset):
        return queryset.exclude('biospecimen_data_references',
                                'redcap',
                                'proteomic',
                                'cytokine',
                                'scrnaseq_summary').order_by('phenotype')

    @mongoengine.queryset_manager
    def scrnaseq_summary_data_only(doc_cls, queryset):
        return queryset.exclude('biospecimen_data_references',
                                'redcap',
                                'proteomic',
                                'cytokine',
                                'metabolomic').order_by('phenotype')

    meta = {
        'db_alias': 'core',
        'collection': 'demographic_data',
        'ordering': ['-study_id'],
        'indexes': ['study_id',
                    '$phenotype',
                    'proteomic.unique_id',
                    'cytokine.unique_id',
                    'metabolomic.unique_id']
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
    site = mongoengine.StringField(choices=site_choices)
    sex = mongoengine.StringField(choices=sex_choices)
    phenotype = mongoengine.StringField(required=True, choices=phenotype_choices)
    age = mongoengine.IntField()
    height_in = mongoengine.FloatField()
    weight_lbs = mongoengine.FloatField()
    bmi = mongoengine.FloatField()
    ethnicity = mongoengine.StringField(choices=ethnicity_choice)
    race = mongoengine.StringField(choices=race_choice)
    mecfs_sudden_gradual = mongoengine.StringField(choices=mecfs_sudden_gradual_choice)
    qmep_sudevent = mongoengine.StringField(choices=qmep_sudevent_choice)
    mecfs_duration = mongoengine.StringField()
    # qmep_mediagnosis = mongoengine.StringField()
    # qmep_mesymptoms = mongoengine.StringField()
    qmep_metimediagnosis = mongoengine.StringField()
    # cpet_d1 = mongoengine.StringField()
    # cpet_d2 = mongoengine.StringField()
    vo2peak1 = mongoengine.StringField()
    vo2peak2 = mongoengine.StringField()
    vo2change = mongoengine.StringField(choices=change_choice)
    at1 = mongoengine.StringField()
    at2 = mongoengine.StringField()
    atchange = mongoengine.StringField(choices=change_choice)

    # biospecimens = mongoengine.EmbeddedDocumentListField(Biospecimen)
    redcap = mongoengine.EmbeddedDocumentListField(Redcap)
    proteomic = mongoengine.EmbeddedDocumentListField(Proteomic)
    cytokine = mongoengine.EmbeddedDocumentListField(Cytokine)
    scrnaseq_summary = mongoengine.EmbeddedDocumentListField(ScRNAseqSummary)

    meta = {
        'db_alias': 'core',
        'collection': 'demographic_data_version_history'
    }
