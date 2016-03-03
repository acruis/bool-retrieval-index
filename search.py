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

# Here be Dats!
class OpNode:
    op = None # "NOT", "AND" or "OR"
    term = None
    left_child = None
    right_child = None
    postings = []
    expected_postings = 0

    def __init__(self, left, right, op, term):
        self.left_child = left
        self.right_child = right
        self.op = op
        self.term = term

    def is_op(self):
        return self.op != None

    def read_postings_of_term(self, postings_file, dictionary):
        term_pointer = dictionary[self.term][0]
        postings_length = dictionary[self.term][1]
        postings_file.seek(term_pointer)
        self.postings = postings_file.read(postings_length).split()
        self.expected_postings = len(self.postings)

class OpTree:
    root = None
    op_list = ["NOT", "AND", "OR"]

    def __init__(self, rpn_stack, postings_file, dictionary):
        node_stack = []
        print "--- Nodes ---"
        for token in rpn_stack:
            if token in self.op_list:
                right_child = node_stack.pop()
                left_child = node_stack.pop()
                node_stack.append(OpNode(left_child, right_child, token, None))
            else:
                token_node = OpNode(None, None, None, token)
                # token_node.read_postings_of_term(postings_file, dictionary)
                node_stack.append(token_node)
            print [(node.op, node.term) for node in node_stack]
        self.root = node_stack.pop()
# Dat end tho

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

    tree = OpTree(['bill', 'gates', 'AND', 'steve', 'jobs', 'AND', 'AND'], None, None)
    print "--- How tree looks like ---"
    root = tree.root
    print root.left_child.left_child.term,
    print root.left_child.op,
    print root.left_child.right_child.term,
    print root.op,
    print root.right_child.left_child.term,
    print root.right_child.op,
    print root.right_child.right_child.term