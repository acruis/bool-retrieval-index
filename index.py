'''
Dictionary format:
[
	[1, 2, 3, 4, 5, 11],
	{
		"hi": [0, 2],
		"bye": [3, 1]
	}
]

[] = list
{} = dict
(no tuples)

All docIDs in a list: 				dictionary[0]
Pointer to "retrieval": 			dictionary[1]["retrieval"][0]
Length of postings for "retrieval": dictionary[1]["retrieval"][1]
'''

import getopt
import sys
import nltk
import json
from os import listdir
from os.path import isfile, join
try:
	import cPickle as pickle
except:
	import pickle

def load_all_doc_names(docs_dir):
	sorted_members = sorted([int(dir_member) for dir_member in listdir(docs_dir)])
	# Additional check for only files in directory
	joined_members = [(dir_member, join(docs_dir, str(dir_member))) for dir_member in sorted_members]
	joined_files = [(member_name, member_path) for member_name, member_path in joined_members if isfile(member_path)]
	return joined_files

def index_doc(doc_name, postings_list):
	docID, doc_path = doc_name
	doc_file = file(doc_path)
	doc = doc_file.read()
	# Tokenize to doc content to sentences, then to words.
	sentences = nltk.tokenize.sent_tokenize(doc)
	words = set([word for sentence in sentences for word in nltk.tokenize.word_tokenize(sentence)])
	# Append doc to postings list.
	# No need to sort the list if we call index_doc in sorted docID order.
	for word in words:
		if word in postings_list:
			postings_list[word].append(docID)
		else:
			postings_list[word] = [docID]
	doc_file.close()

def index_all_docs(docs):
	postings_list = {}
	for doc in docs: # slice for smaller postings file
		index_doc(doc, postings_list)
	return postings_list

def write_postings(postings_list, postings_file_name):
	postings_file = file(postings_file_name, 'w')
	dict_terms = {}
	for term, docIDs in postings_list.iteritems():
		posting_pointer = postings_file.tell()
		postings_file.write(" ".join([str(docID) for docID in docIDs]))
		write_length = postings_file.tell() - posting_pointer
		postings_file.write("\n")
		dict_terms[term] = (posting_pointer, write_length)
	postings_file.close()
	return dict_terms

def all_doc_IDs(docs):
	# O(doc_count).
	return [docID for docID, doc_path in docs]

def create_dictionary(docIDs, dict_terms, dict_file_name):
	dict_file = file(dict_file_name, 'w')
	json.dump([docIDs, dict_terms], dict_file)
	dict_file.close()

def usage():
	print "usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file"

def parse_args():
	docs_dir = dict_file = postings_file = None
	try:
	    opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')
	except getopt.GetoptError, err:
	    usage()
	    sys.exit(2)
	for o, a in opts:
	    if o == '-i':
	        docs_dir = a
	    elif o == '-d':
	        dict_file = a
	    elif o == '-p':
	        postings_file = a
	    else:
	        assert False, "unhandled option"
	if docs_dir == None or dict_file == None or postings_file == None:
	    usage()
	    sys.exit(2)
	return (docs_dir, dict_file, postings_file)

def main():
	docs_dir, dict_file, postings_file = parse_args()

	print "Searching all documents in {}...".format(docs_dir),
	docs = load_all_doc_names(docs_dir)
	print "DONE"

	print "Constructing the inverted index...",
	postings_list = index_all_docs(docs)
	print "DONE"

	print "Writing postings to {}...".format(postings_file),
	dict_terms = write_postings(postings_list, postings_file)
	print "DONE"

	print "Writing dictionary to {}...".format(dict_file),
	docIDs = all_doc_IDs(docs)
	create_dictionary(docIDs, dict_terms, dict_file)
	print "DONE"

if __name__ == "__main__":
	main()