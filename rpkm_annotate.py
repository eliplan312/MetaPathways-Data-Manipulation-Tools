""" rpkm_annotate.py : Library / script to combine pathway information, RPKM data, and annotation information into output data"""

__author__ = "Eli Kaplan"
__email__ = "eli.kaplan@alumni.ubc.ca"
__license__ = "CC0 - No rights reserved. See LICENSE"

import csv
import sys

from os import listdir
from os.path import join

from rpkm_correlate import loadPathwayInfoFromFile, loadORFDataFromFile, correlatePathwayInfoWithData


def loadAnnotationsFromFile(filename, sample_name, csv_separator):
	anno_data=[sample_name, {}]

	try:
		with open(filename, 'r') as anno_file:
			anno_reader = csv.reader(anno_file, delimiter=csv_separator)

			for row in anno_reader:
				anno_query = 'O_' + row[0].replace(sample_name,'')[1:] # Generate the proper corresponding ORF ID

				# Only take the first annotation result from each ORF
				if anno_query in anno_data[1]:
					continue

				anno_hit = row[9].split('[')[0] # Grab only the name of the gene as the 'hit'
				anno_q_length = row[2] 	# 'q_length' column
				anno_bitscore = row[3] 	# 'bitscore' column
				anno_bsr = row[4] 		# 'bsr' column
				anno_expect = row[5]	# 'expect' column
				anno_identity = row[7] 	# 'identity' column
				anno_ec = row[8] 		# 'ec' column

				anno_data[1][anno_query] = (anno_hit, anno_q_length, anno_bitscore, anno_bsr, anno_expect, anno_identity, anno_ec)

	except Exception as e:
		print("Error reading annotation file - exiting.")
		print("Exception: " + str(e))
		quit()


	return anno_data


def batchCorrelateAnnotate(file_dir, output_filename = 'pwy_anno.tsv', csv_separator='\t', pwy_file_suffix='.pwy.txt', data_file_suffix='.orf_rpkm.txt', anno_file_suffix='.metacyc-2016-10-31.lastout.parsed.txt'):

	# Create a list of all files in the target directory
	all_files = [join(file_dir, f) for f in listdir(file_dir)]

	# Split the list of all the files into three lists: pathway files, data files, and annotation files
	pwy_files = []
	data_files = []
	anno_files = []

	for file in all_files:
		if pwy_file_suffix in file:
			pwy_files.append(file)
		elif data_file_suffix in file:
			data_files.append(file)
		elif anno_file_suffix in file:
			anno_files.append(file)
		else:
			print("Unknown file in batch directory: " + file)


	# Match each pathway information file with its corresponding RPKM data file and annotation file
	file_pairs = []

	for pwy_file in pwy_files:
		# Generate the name of the corresponding data file based on the name of the pathway info file
		corresponding_data_file = pwy_file.replace(pwy_file_suffix, data_file_suffix)

		# Generate the name of the corresponding annotation file, using the same technique
		corresponding_anno_file = pwy_file.replace(pwy_file_suffix, anno_file_suffix)
	
		# If the necessary files exist, pair them with the pathway file. Otherwise, don't process anything for this set of pathway data.
		if corresponding_data_file in data_files:
			if corresponding_anno_file in anno_files:
				file_pairs.append((pwy_file, corresponding_data_file, corresponding_anno_file))

			else:
				print("Missing annotation file: " + corresponding_anno_file)

		else:
			print("Missing data file: " + corresponding_data_file)


	output_data = []
	n_total_pathways = 0
	n_total_datapoints = 0
	n_total_annotations = 0

	for (pathway_file, data_file, anno_file) in file_pairs:
		# Load pathway information from the given file
		pathway_info = loadPathwayInfoFromFile(pathway_file, csv_separator)
		cur_sample = pathway_info[0]

		# Load RPKM data from the file corresponding to the pathway info file
		rpkm_data = loadORFDataFromFile(data_file, cur_sample, csv_separator)

		anno_data = loadAnnotationsFromFile(anno_file, cur_sample, csv_separator)

		data_dict = dict(rpkm_data[1])

		n_missing_annotations = 0
		n_missing_rpkm = 0

		for pwy, pwy_cname, pwy_orfs in pathway_info[1]:
			n_total_pathways += 1
			for orf in pwy_orfs:
				if orf in data_dict:
					n_total_datapoints += 1
					if orf in anno_data[1]:
						n_total_annotations += 1
						orf_anno = anno_data[1][orf]


						output_data.append((cur_sample, # SAMPLE
							pwy,			# PWY_NAME
							orf,			# ORF
							orf_anno[0], 	# HIT
							data_dict[orf], # RPKM
							orf_anno[1], 	# Q_LENGTH
							orf_anno[2],	# BITSCORE
							orf_anno[3],	# BSR
							orf_anno[4],	# EXPECT
							orf_anno[5],	# IDENTITY
							orf_anno[6]))	# EC


					else:
						n_missing_annotations += 1

				else:
					n_missing_rpkm += 1

		print('Loaded sample: ' + cur_sample + ' - ORFS with no annotations: ' + str(n_missing_annotations) + ' - missing rpkm data points: ' + str(n_missing_rpkm))
				

	print('Processed ' + str(n_total_pathways) + ' pathways, ' + str(n_total_datapoints) + ' RPKM data points, ' + str(n_total_annotations) + ' total annotations.')


	
	# Generate a header for the output tabulated file 
	output_file_header = ['SAMPLE', 'PWY_NAME', 'ORF', 'HIT', 'RPKM', 'Q_LENGTH', 'BITSCORE', 'BSR', 'EXPECT', 'IDENTITY', 'EC']



	# Output the resulting data to the chosen file
	try:
		with open(output_filename, 'w') as output_file:
			output_writer = csv.writer(output_file, delimiter=csv_separator)

			# Write the header to the output file as the first line.
			output_writer.writerow(output_file_header)

			for row in output_data:
				output_writer.writerow(row)

	
	except Exception as e: # If an error occurred while writing out the results, exit.
		print("ERORR: File output failed - exiting.")
		print("Exception: " + str(e))
		quit()


	




# Allow the script to be run stand-alone (and prevent the following code from running when imported)
if __name__ == "__main__":

	def printUsage():
		"""Prints usage information for this script."""
		print('\nPathway/RPKM Batch Data Correlator')

	target_folder = ""

	args = list(sys.argv)

	# If --help is specified, print usage information and exit.
	if '--help' in args:
		print('Printing usage information.')
		printUsage()
		quit()


	if len(args) == 2: # Output file not specified
		target_folder = args[1]
		output_filename = 'pwy_anno.tsv'

	elif len(args) == 3: # Output file specified
		target_folder = args[1]
		output_filename = args[2]

	else: # If command-line arguments are not well-formed, print usage information and exit.
		printUsage()
		quit()


	batchCorrelateAnnotate(target_folder, output_filename)
