#

# Version history:

# ME/CFS version 1 (MECFS_V1) - original version:

# Set up globals
MECFSVersion = 'MECFS_V1'
# data_folder = '/workdir/data/'
# data_folder = 'C:/Users/prm88/Documents/Box/genome_innovation_hub/mecfs_code/data/'
data_folder = '../data/'
database_name = 'mecfs_db_test3'
testMode = True

users = [('Paul Munn', 'prm88@cornell.edu'),
         ('Faraz Ahmed', 'fa286@cornell.edu'),
         ('Jen Grenier', 'jgrenier@cornell.edu'),
         ('Carl Franconi', 'carl.franconi@cornell.edu'),
         ('Ludovic Giloteaux', 'lg349@cornell.edu'),
         ]

exitResponseList = ['x', 'bye', 'exit', 'exit()']

import_log_file = 'data_import.log'

clinical_document_name = 'demographic'
redcap_document_name = 'REDCap'
biospecimen_document_name = 'biospecimens'
proteomics_document_name = 'Proteomics'
cytokines_document_name = 'Cytokines'
metabolomics_document_name = 'Metabolomics'
scrnaseq_summary_document_name = 'scRNA-seq summary'

data_label_type_document_name = 'data label type'
gene_symbol_data_label_type = 'Gene Symbol'
ensembl_gene_id_data_label_type = 'Ensembl Gene ID'
cytokine_data_label_type = 'Cytokine Label'

gene_symbol_to_ensembl_geneid_ref = 'Gene Symbol to Ensembl Gene ID'
gene_symbol_to_cytokine_label_ref = 'Gene Symbol to Cytokine Label'

print('ME/CFS version:', MECFSVersion)
print('Data folder:', data_folder)
