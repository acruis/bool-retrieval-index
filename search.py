import re
import nltk
import sys
import getopt
import json

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
    i = 0
    j = 0

    while i < len(p1) and j < len(p2):
        if p1[i] == p2[j]:
            result.append(p1[i])
            i += 1
            j += 1
        elif p1[i] < p2[j]:
            i += 1
        else:
            j += 1

    return result


def op_multi_and(list_of_postings_lists):
    list_of_postings_lists.sort(key=len)
    result = list_of_postings_lists[0]

    for p in list_of_postings_lists[1:]:
        result = op_and(result, p)

    return result


def op_and_not(p1, p2):
    result = []
    i = 0
    j = 0

    while i < len(p1) and j < len(p2):
        if p1[i] == p2[j]:
            i += 1
            j += 1
        elif p1[i] < p2[j]:
            result.append(p1[i])
            i += 1
        else:
            j += 1

    result.extend(p1[i:])

    return result


def op_or(p1, p2):
    result = []
    i = 0
    j = 0

    while i < len(p1) and j < len(p2):
        if p1[i] == p2[j]:
            result.append(p1[i])
            i += 1
            j += 1
        elif p1[i] < p2[j]:
            result.append(p1[i])
            i += 1
        else:
            result.append(p2[j])
            j += 1

    if i < len(p1):
        result.extend(p1[i:])
    else:
        result.extend(p2[j:])

    return result


def op_not(p, all_p):
    result = []
    i = 0
    j = 0

    while i < len(p) and j < len(all_p):
        if p[i] == all_p[j]:
            i += 1
            j += 1
        else:
            result.append(all_p[j])
            j += 1

    result.extend(all_p[j:])

    return result


def usage():
    print "usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results"


# Here be Dats!
class OpNode:
    op = None # "NOT", "AND", "OR" or "AND NOT"
    term = None
    children = None
    postings = []
    expected_count = 0

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

    def merge(self, children_postings, all_docIDs):
        if self.op == "NOT":
            return op_not(children_postings[0], all_docIDs)
        elif self.op == "OR":
            return op_or(children_postings[0], children_postings[1])
        elif self.op == "AND":
            return op_multi_and(children_postings)
        elif self.op == "AND NOT":
            return op_and_not(children_postings[0], children_postings[1])

    def recursive_merge(self, all_docIDs):
        if self.op != None:
            children_postings = [child.recursive_merge(all_docIDs) for child in self.children]
            return self.merge(children_postings, all_docIDs)
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
        if self.op == "AND":
            self.children = self.consolidate_ops_recursive("AND")
        elif self.op == "OR":
            self.children = self.consolidate_ops_recursive("OR")
        elif self.op == "NOT":
            descendant, effective = self.consolidate_not_recursive(False)
            if effective:
                self.children = [descendant]
            else:
                self.copy_descendant_info(descendant)
        
        if self.op != None:
            for child in self.children:
                child.consolidate_ops()

    def copy_descendant_info(self, descendant):
        self.op = descendant.op
        self.term = descendant.term
        self.expected_count = descendant.expected_count
        self.children = descendant.children
        self.postings = descendant.postings

    def deMorgans(self, children_nots):
        children_of_nots = [child_not.children[0] for child_not in children_nots]
        center_grandchild = OpNode(children_of_nots, "OR" if self.op == "AND" else "AND", None)
        new_child_not = OpNode([center_grandchild], "NOT", None)
        self.children.append(new_child_not)

    def process_and_not(self, child_not, children_notnots):
        new_child_and = OpNode([children_notnots], "AND", None)
        self.op = "AND NOT"
        self.children = [new_child_and, child_not.children[0]]

    def consolidate_children(self):
        if self.children:
            if self.op == "OR" or self.op == "AND":
                children_nots = [child for child in self.children if child.op == "NOT"]
                self.children = [child for child in self.children if child.op != "NOT"]
                if len(children_nots) > 1:
                    self.deMorgans(children_nots)
            if self.op == "AND":
                children_nots = [child for child in self.children if child.op == "NOT"]
                children_notnots = [child for child in self.children if child.op != "NOT"]
                if children_nots:
                    assert(len(children_nots) == 1)
                    self.process_and_not(children_nots[0], children_notnots)
            for child in self.children:
                child.consolidate_children()

    def calculate_expected(self, all_docIDs):
        if self.op == None:
            self.expected_count = len(self.postings)
        elif self.op == "AND":
            for child in self.children: child.calculate_expected(all_docIDs)
            self.expected_count = min([child.expected_count for child in self.children])
        elif self.op == "OR":
            for child in self.children: child.calculate_expected(all_docIDs)
            self.expected_count = sum([child.expected_count for child in self.children])
        elif self.op == "NOT":
            self.children[0].calculate_expected(all_docIDs)
            self.expected_count = len(all_docIDs) - self.children[0].expected_count

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
                    node_stack.append(OpNode([only_child], token, None))
            else:
                token_node = OpNode(None, None, token)
                token_node.read_postings_of_term(postings_file, dictionary)
                node_stack.append(token_node)
            print [(node.op, node.term) for node in node_stack]
        self.root = node_stack.pop()
# Dat end tho

def tree_initialization_test():
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

def nots_test():
    yes = OpNode(None, None, "Hi!")
    no = OpNode([yes], "NOT", None)
    yes1 = OpNode([no], "NOT", None)
    no1 = OpNode([yes1], "NOT", None)
    yes2 = OpNode([no1], "NOT", None)
    no2 = OpNode([yes2], "NOT", None)
    yes3 = OpNode([no2], "NOT", None)
    yes3.consolidate_ops()
    print yes3.term

def consolidate_test():
    tree = OpTree(['bill', 'gates', 'AND', 'steve', 'jobs', 'AND', 'AND'], None, None)
    tree.root.consolidate_ops()
    print len(tree.root.children)
    for child in tree.root.children:
        print child.term

def load_args():
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
    return (dictionary_file, postings_file, queries_file, output_file)

def process_queries(dictionary_file, postings_file, queries_file, output_file):
    # load dictionary
    with open(dictionary_file) as dict_file:
        all_docIDs, dictionary = json.load(dict_file)

    # open queries
    postings = file(postings_file)
    output = file(output_file, 'w')
    with open(queries_file) as queries:
        for query in queries:
            tree = OpTree(shunting_yard(query), postings, dictionary)
            tree.root.consolidate_ops()
            tree.root.consolidate_children()
            tree.root.calculate_expected(all_docIDs)
            result_IDs = [str(result_ID) for result_ID in tree.root.recursive_merge(all_docIDs)]
            result_IDs.append("\n")
            output.write(" ".join(result_IDs))
    postings.close()
    output.close()

def main():
    dictionary_file, postings_file, queries_file, output_file = load_args()

    # tree_initialization_test()
    # nots_test()
    # consolidate_test()
    process_queries(dictionary_file, postings_file, queries_file, output_file)

if __name__ == "__main__":
    main()