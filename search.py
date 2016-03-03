"""
# FILES
$ python search.py -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results

# OUTPUT
if not found => empty line

# READING
seek read

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


def peek(lst):
    return lst[-1]


def precedence(op):
    return {
        "OR": 0,
        "AND": 1,
        "NOT": 2,
        "(": -1, # never executed as an operation
        }[op]


def op_and(p1, p2):
    result = []

    while p1 and p2:
        if p1[0] == p2[0]:
            result.append(p1[0])
            p1.pop(0)
            p2.pop(0)
        elif p1[0] < p2[0]:
            p1.pop(0)
        else:
            p2.pop(0)

    return result


def op_or(p1, p2):
    result = []

    while p1 and p2:
        if p1[0] == p2[0]:
            result.append(p1[0])
            p1.pop(0)
            p2.pop(0)
        elif p1[0] < p2[0]:
            result.append(p1.pop(0))
        else:
            result.append(p2.pop(0))

    if p1:
        result.extend(p1)
    else:
        result.extend(p2)

    return result


def op_not(p, all_p):
    result = []

    while p and all_p:
        if p[0] == all_p[0]:
            p.pop(0)
            all_p.pop(0)
        else:
            result.append(all_p.pop(0))

    result.extend(all_p)

    return result


def usage():
    print "usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results"


# Here be Dats!
class OpNode:
    op = None # "NOT", "AND" or "OR"
    term = None
    children = None
    postings = []
    expected_postings = 0

    def __init__(self, children, op, term):
        self.children = children
        self.op = op
        self.term = term

    def is_op(self):
        return self.op != None

    def read_postings_of_term(self, postings_file, dictionary):
        if self.term in dictionary:
            term_pointer = dictionary[self.term][0]
            postings_length = dictionary[self.term][1]
            postings_file.seek(term_pointer)
            self.postings = [int(docID) for docID in postings_file.read(postings_length).split()]

    def merge(children_postings):
        if op == "NOT":
            # return not(children_postings[0], all_docIDs)
            pass
        elif op == "OR":
            # return or(children_postings)
            pass
        elif op == "AND":
            # return and(children_postings)
            pass

    def recursive_merge(self):
        if self.op != None:
            children_postings = [child.recursive_merge for child in children]
            return self.merge(children_postings)
        else:
            return self.postings

    def consolidate_ops_recursive(self, required_op):
        if self.op != required_op:
            return [self]
        else:
            grouped_children = []
            for child in self.children:
                grouped_children.extend(child.consolidate_ops_recursive(required_op))
            return grouped_children

    def consolidate_not_recursive(self, effective):
        if self.op != "NOT":
            return (self, effective)
        else:
            return self.children[0].consolidate_not_recursive(not effective)

    def consolidate_ops(self):
        if self.op == None:
            self.expected_postings = len(self.postings)
        elif self.op == "AND":
            self.children = self.consolidate_ops_recursive("AND")
        elif self.op == "OR":
            self.children = self.consolidate_ops_recursive("OR")
        elif self.op == "NOT":
            child, effective = self.consolidate_not_recursive(False)
            if effective:
                self.children = [child]

class OpTree:
    root = None
    op_list = ["NOT", "AND", "OR"]

    def __init__(self, rpn_stack, postings_file, dictionary):
        node_stack = []
        print "--- Nodes ---"
        for token in rpn_stack:
            if token in self.op_list:
                if token != "NOT":
                    right_child = node_stack.pop()
                    left_child = node_stack.pop()
                    node_stack.append(OpNode([left_child, right_child], token, None))
                else:
                    # For a NOT, only child is always on the left
                    only_child = node_stack.pop()
                    node_stack.append(OpNode([child], token, None))
            else:
                token_node = OpNode(None, None, token)
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

    '''
    # tree initialization
    tree = OpTree(['bill', 'gates', 'AND', 'steve', 'jobs', 'AND', 'AND'], None, None)
    print "--- How tree looks like ---"
    root = tree.root
    print root.children[0].children[0].term,
    print root.children[0].op,
    print root.children[0].children[1].term,
    print root.op,
    print root.children[1].children[0].term,
    print root.children[1].op,
    print root.children[1].children[1].term
    '''

    '''
    # nots
    yes = OpNode(None, None, "Hi!")
    no = OpNode([yes], "NOT", None)
    yes1 = OpNode([no], "NOT", None)
    no1 = OpNode([yes1], "NOT", None)
    yes2 = OpNode([no1], "NOT", None)
    no2 = OpNode([yes2], "NOT", None)
    no2.consolidate_ops()
    print no2.children[0].term
    '''

    tree = OpTree(['bill', 'gates', 'AND', 'steve', 'jobs', 'AND', 'AND'], None, None)
    tree.root.consolidate_ops()
    print len(tree.root.children)
    for child in tree.root.children:
        print child.term