import mongoengine
from data.data_label_types import GeneSymbols
from data.data_label_types import EnsemblTranscriptIDs
from data.data_label_types import EnsemblGeneIDs
from data.data_label_types import CytokineLabels

data_label_type_choices = ('Gene Symbol',
                           'NCBI GeneID',
                           'NCBI RefSeq ID',
                           'Ensembl GeneID',
                           'Ensembl TranscriptID',
                           'Cytokine'
                           'Other')


class AssayResults(mongoengine.EmbeddedDocument):
    data_label_type = mongoengine.StringField(required=True, choices=data_label_type_choices)
    data_label = mongoengine.StringField(required=True)
    result = mongoengine.FloatField()
    gene_symbol_reference = mongoengine.ReferenceField(GeneSymbols)
    ensembl_transcriptid_reference = mongoengine.ReferenceField(EnsemblTranscriptIDs)
    ensembl_geneid_reference = mongoengine.ReferenceField(EnsemblGeneIDs)
    cytokine_label_reference = mongoengine.ReferenceField(CytokineLabels)

    # //--- set up references for each of the other data label types


# class AssayResultsOld(mongoengine.EmbeddedDocument):
#     gene_symbol = mongoengine.StringField()
#     gene_name = mongoengine.StringField()
#     accession_number = mongoengine.StringField()
#     ensembl_id = mongoengine.StringField()
#     result = mongoengine.FloatField()
#
#     # GENCODE
#     # NCBI RefSeq
#     # UCSC RefSeq
#     # UCSC Gene ID
