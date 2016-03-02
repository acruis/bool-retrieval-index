"""
# FILES
$ python search.py -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results
after indexing => dictionary-file (literal_eval, tuple of list and dict) postings-file (space delimited numbers)
IN: file-of-queries, one query occupies one line
OUT: output-file-of-results

# LITERAL EVALUATION
import ast
x = ast.literal_eval("[1,2]")
The value of x becomes [1,2] (as a list)

# OUTPUT
answer to a query should contain a list of document IDs that match the query in increasing order, in one line
if not found => empty line
document IDs should follow the filenames
Reuters doc IDs are unique integers, they are not necessary sequential

# READING
should not read whole postings file into RAM
use pointers in dictionary to load postings lists from postings file
seek read

# 0 NOTs
AND
OR

# 1 NOT
a AND NOT b => copy a, but avoid b
a OR NOT b => a OR (docs - b)

# De morgan's, 2 NOTs
(NOT a) AND (NOT b) => NOT(a OR b)
(NOT a) OR (NOT b) => NOT(a AND b)
"""

import re
import nltk
import sys
import getopt

def magic(queries_file, out_file):
    with open(queries_file) as queries_data, open(out_file, 'w+') as results_data:
        for line in queries_file:
            pass

# queries: ( ) NOT AND OR, in decreasing order of precedence
# single words conjoined with boolean ops in CAPS
# no nested parantheses
# returns a stack in Reverse Polish Notation
def shunting_yard(query):
    query_tokens = nltk.word_tokenize(query)
    rpn_stack = []
    op_stack = []
    op_list = ["NOT", "AND", "OR"]

    for token in query_tokens:
        if token not in op_list and token not in ["(", ")"]: # is search token
            rpn_stack.append(token)
        elif token in op_list:
            while op_stack and precedence(token) <= precedence(peek(op_stack)):
                rpn_stack.append(op_stack.pop())
            op_stack.append(token)
        elif token == "(":
            op_stack.append(token)
        elif token == ")":
            while op_stack and peek(op_stack) != "(":
                rpn_stack.append(op_stack.pop())
            op_stack.pop()

    while op_stack:
        rpn_stack.append(op_stack.pop())

    return rpn_stack

# TODO implement stack class
def peek(lst):
    return lst[-1]

def precedence(op):
    return {
        "OR": 0,
        "AND": 1,
        "NOT": 2,
        "(" : -1, # never executed as an operation
        }[op]

def usage():
    print "usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results"

if __name__ == "__main__":
    dictionary_file = postings_file = queries_file = output_file = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
    except getopt.GetoptError, err:
        usage()
        sys.exit(2)
    for o, a in opts:
        if o == '-d':
            dictionary_file = a
        elif o == '-p':
            postings_file = a
        elif o == '-q':
            queries_file = a
        elif o == '-o':
            output_file = a
        else:
            assert False, "unhandled option"
    if dictionary_file == None or postings_file == None or queries_file == None or output_file == None:
        usage()
        sys.exit(2)