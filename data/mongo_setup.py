import mongoengine


def global_init(database_name):
    mongoengine.register_connection(alias='core', name=database_name)
