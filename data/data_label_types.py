import mongoengine


class EnsemblTranscriptIDs(mongoengine.Document):
    data_label = mongoengine.StringField(required=True)

    meta = {
        'db_alias': 'core',
        'collection': 'ensembl_transcriptids',
        'ordering': ['-data_label'],
        'indexes': ['data_label']
    }


class EnsemblGeneIDs(mongoengine.Document):
    data_label = mongoengine.StringField(required=True)

    meta = {
        'db_alias': 'core',
        'collection': 'ensembl_geneids',
        'ordering': ['-data_label'],
        'indexes': ['data_label']
    }


class GeneSymbols(mongoengine.Document):
    data_label = mongoengine.StringField(required=True)

    meta = {
        'db_alias': 'core',
        'collection': 'gene_symbols',
        'ordering': ['-data_label'],
        'indexes': ['data_label']
    }


class CytokineLabels(mongoengine.Document):
    data_label = mongoengine.StringField(required=True)

    meta = {
        'db_alias': 'core',
        'collection': 'cytokine_labels',
        'ordering': ['-data_label'],
        'indexes': ['data_label']
    }


# Now that all classes have been defined, set up each of the reference lists:
# Each data label type should have references to every other data label type,
# allowing us to set up many-to-many relationships between each data label type
class GeneSymbolsToEnsemblGeneIDs(mongoengine.Document):
    gene_symbol_data_label = mongoengine.StringField()
    ensembl_geneid_data_label = mongoengine.StringField()
    gene_symbol_reference = mongoengine.ReferenceField(GeneSymbols)
    ensembl_geneid_reference = mongoengine.ReferenceField(EnsemblGeneIDs)

    meta = {
        'db_alias': 'core',
        'collection': 'gene_symbols_to_ensembl_gene_ids',
        'ordering': ['-gene_symbol_data_label'],
        'indexes': ['gene_symbol_data_label', 'ensembl_geneid_data_label']
    }


class GeneSymbolsToCytokineLabels(mongoengine.Document):
    gene_symbol_data_label = mongoengine.StringField()
    cytokine_data_label = mongoengine.StringField()
    gene_symbol_reference = mongoengine.ReferenceField(GeneSymbols)
    cytokine_label_reference = mongoengine.ReferenceField(CytokineLabels)

    meta = {
        'db_alias': 'core',
        'collection': 'gene_symbols_to_cytokine_labels',
        'ordering': ['-gene_symbol_data_label'],
        'indexes': ['gene_symbol_data_label', 'cytokine_data_label']
    }


# Attributes for gene symbols
# GeneSymbols.data_label = mongoengine.StringField(required=True)
# GeneSymbols.meta = {'db_alias': 'core', 'collection': 'gene_symbols'}

# GeneSymbols.ensembl_transcriptid_references = mongoengine.ListField(mongoengine.ReferenceField(EnsemblTranscriptIDs))
# GeneSymbols.ensembl_geneid_references = mongoengine.ListField(mongoengine.ReferenceField(EnsemblGeneIDs))

# Attributes for ensembl transcript ids
# EnsemblTranscriptIDs.data_label = mongoengine.StringField(required=True)
# EnsemblTranscriptIDs.meta = {'db_alias': 'core', 'collection': 'ensembl_transcriptids'}

# EnsemblTranscriptIDs.gene_symbol_references = mongoengine.ListField(mongoengine.ReferenceField(GeneSymbols))
# EnsemblTranscriptIDs.ensembl_geneid_references = mongoengine.ListField(mongoengine.ReferenceField(EnsemblGeneIDs))

# Attributes for ensembl gene ids
# EnsemblGeneIDs.data_label = mongoengine.StringField(required=True)
# EnsemblGeneIDs.meta = {'db_alias': 'core', 'collection': 'ensembl_geneids'}

# EnsemblGeneIDs.gene_symbol_references = mongoengine.ListField(mongoengine.ReferenceField(GeneSymbols))
# EnsemblGeneIDs.ensembl_transcriptid_references = mongoengine.ListField(mongoengine.ReferenceField(EnsemblTranscriptIDs))

# setattr(EnsemblTranscriptIDs, 'ensembl_geneid_references',
#         mongoengine.ListField(mongoengine.ReferenceField(EnsemblGeneIDs)))
