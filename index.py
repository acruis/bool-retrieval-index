# Do indexing!

import getopt
import sys
import nltk
from os import listdir
from os.path import isfile, join
try:
	import cPickle as pickle
except:
	import pickle

def loadAllDocNames(docs_dir):
	sorted_members = sorted([int(dir_member) for dir_member in listdir(docs_dir)])
	# Additional check for only files in directory
	joined_members = [(dir_member, join(docs_dir, str(dir_member))) for dir_member in sorted_members]
	joined_files = [(member_name, member_path) for member_name, member_path in joined_members if isfile(member_path)]
	return joined_files

def indexDoc(doc_name, postings):
	docID, doc_path = doc_name
	doc = file(doc_path).read()
	sentences = nltk.tokenize.sent_tokenize(doc)
	words = set([word for sentence in sentences for word in nltk.tokenize.word_tokenize(sentence)])
	for word in words:
		if word in postings:
			postings[word].append(docID)
		else:
			postings[word] = [docID]

def indexAllDocs(docs):
	postings = {}
	for doc in docs[:10]:
		indexDoc(doc, postings)
	return postings

def usage():
	print "usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file"

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

print docs_dir
print dict_file
print postings_file
docs = loadAllDocNames(docs_dir)
postings = indexAllDocs(docs)