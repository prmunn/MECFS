import datetime
import mongoengine
from data.biospecimens import Biospecimen
from data.users import User


time_choices = ('t1', 't2', 't3')
cpet_day_choice = ('D1', 'D2')
pre_post_cpet_choice = ('PRE', 'POST')


class Proteomic(mongoengine.EmbeddedDocument):
    created_by = mongoengine.ReferenceField(User, required=True)
    created_date = mongoengine.DateTimeField(required=True)
    last_modified_by = mongoengine.ReferenceField(User, required=True)
    last_modified_date = mongoengine.DateTimeField(default=datetime.datetime.now)

    excel_file_id = mongoengine.IntField(required=True)
    data_file_name = mongoengine.StringField(required=True)
    biospecimen_data_reference = mongoengine.ReferenceField(Biospecimen)
    time = mongoengine.StringField(required=True, choices=time_choices)
    cpet_day = mongoengine.StringField(choices=cpet_day_choice)
    pre_post_cpet = mongoengine.StringField(choices=pre_post_cpet_choice)
    run = mongoengine.StringField(required=True)
    a2m = mongoengine.FloatField()
    actb = mongoengine.FloatField()
    actn4 = mongoengine.FloatField()
    actr3 = mongoengine.FloatField()
    agt = mongoengine.FloatField()
    alb = mongoengine.FloatField()
    aldoa = mongoengine.FloatField()
    ambp = mongoengine.FloatField()
    apoa1 = mongoengine.FloatField()
    apoa4 = mongoengine.FloatField()
    apoc1 = mongoengine.FloatField()
