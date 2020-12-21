#

# Version history:

# ME/CFS version 1 (MECFS_V1) - original version:

# Set up globals
MECFSVersion = 'MECFS_V1'
# data_folder = '/workdir/data/'
data_folder = 'C:/Users/prm88/Documents/Box/genome_innovation_hub/mecfs_code/data/'
database_name = 'mecfs_db_test2'

users = [('Paul Munn', 'prm88@cornell.edu'),
         ('Faraz Ahmed', 'fa286@cornell.edu'),
         ('Jen Grenier', 'jgrenier@cornell.edu'),
         ('Carl Franconi', 'carl.franconi@cornell.edu'),
         ('Ludovic Giloteaux', 'lg349@cornell.edu'),
         ]

exitResponseList = ['x', 'bye', 'exit', 'exit()']

import_log_file = 'data_import.log'

clinical_document_name = 'clinical'
clinical_data_file = r'Clinical_data_table_test_1.xlsx'

redcap_document_name = 'REDCap'
redcap_data_files = r'xxx'

biospecimen_document_name = 'biospecimens'
biospecimen_data_file = r'Biospecimens_table.xlsx'

proteomics_document_name = 'proteomics'
proteomics_data_file = r'example_proteomics_test_1.xls'

cytokines_document_name = 'cytokines'
cytokines_data_files = r'xxx'

scrnaseq_summary_document_name = 'scRNA-seq summary'
scrnaseq_summary_data_file = r'MECFS_10x_scRNAseq_metrics_summary_final_Oct2020.xlsx'

print('ME/CFS version:', MECFSVersion)
print('Data folder:', data_folder)
