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
	joined_contents = [(f, join(docs_dir, f)) for f in listdir(docs_dir)]
	joined_files = [(f, joined_f) for f, joined_f in joined_contents if isfile(joined_f)]
	return joined_files

def updatePostings(doc_name, postings):
	docID, doc_path = doc_name
	doc = file(doc_path).read()
	sentences = nltk.tokenize.sent_tokenize(doc)
	words = set([word for sentence in sentences for word in nltk.tokenize.word_tokenize(sentence)])
	for word in words:
		if word in postings:
			postings[word].append(docID)
		else:
			postings[word] = [docID]

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
print docs[998]
postings = {}
updatePostings(docs[998], postings)
print postings