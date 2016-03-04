import re
import nltk
import sys
import getopt
import json
import heapq
import time
import math

'''
Removing/Normalizing numbers
Remove stop words (observe change in dict/postings)
'''

def precedence(op):
    """Given operator type, returns the precedence order of operator.

    Higher precedence order is reflected by higher return value. For use with shunting_yard only.

    :param op: Operator type in string.
    :return: An integer reflecting the precedence order of the operator. Higher precedence = higher integer value.
    """
    return {
        "OR": 0,
        "AND": 1,
        "NOT": 2,
        "(": -1, # never executed as an operator
        }[op]


def shunting_yard(query):
    """Returns a list of search tokens and operators in Reverse Polish Notation.

    :param query: A string containing the search query.
    :return: A list of search tokens and operators in Reverse Polish Notation.
    """
    query_tokens = nltk.word_tokenize(query)
    stemmer = nltk.stem.PorterStemmer()
    rpn_stack = []
    op_stack = []
    op_list = ["NOT", "AND", "OR"]

    for token in query_tokens:
        if token not in op_list and token not in ["(", ")"]:
            rpn_stack.append(stemmer.stem(token))
        elif token in op_list:
            while op_stack and precedence(token) <= precedence(op_stack[-1]):
                rpn_stack.append(op_stack.pop())
            op_stack.append(token)
        elif token == "(":
            op_stack.append(token)
        elif token == ")":
            while op_stack and op_stack[-1] != "(":
                rpn_stack.append(op_stack.pop())
            op_stack.pop()

    while op_stack:
        rpn_stack.append(op_stack.pop())

    return rpn_stack

def get_skip_flags(len1, len2):
    skip1 = int(math.sqrt(len1))
    skip2 = int(math.sqrt(len2))
    flags1 = [False] * len1
    flags2 = [False] * len2
    a = 0
    b = 0
    while a < len1:
        flags1[a] = True
        a += skip1
    while b < len2:
        flags2[b] = True
        b += skip2
    return (skip1, skip2, flags1, flags2)

def op_and(p1, p2):
    """Evaluates p1 AND p2 and returns result as list.

    :param p1: A list containing the first postings list.
    :param p2: A list containing the second postings list.
    :return: A list containing the result of p1 AND p2.
    """
    result = []
    i = 0
    j = 0
    skip_dist1, skip_dist2, can_skip1, can_skip2 = get_skip_flags(len(p1), len(p2))

    while i < len(p1) and j < len(p2):
        if p1[i] == p2[j]:
            result.append(p1[i])
            i += 1
            j += 1
        elif p1[i] < p2[j]:
            if can_skip1[i]:
                lookahead = i + skip_dist1
                if lookahead < len(p1) and p1[lookahead] <= p2[j]:
                    i += skip_dist1
                else:
                    i += 1
            else:
                i += 1
        else:
            if can_skip2[j]:
                lookahead = j + skip_dist2
                if lookahead < len(p2) and p2[lookahead] <= p1[i]:
                    j += skip_dist2
                else:
                    j += 1
            else:
                j += 1
                
    return result


def op_multi_and(list_of_postings_lists):
    """Evaluates p1 AND p2 AND ... AND pN and returns result as list.

    :param list_of_postings_lists: A list of postings lists.
    :return: A list containing the result of p1 AND p2 AND ... AND pN.
    """
    list_of_postings_lists.sort(key=len)
    result = list_of_postings_lists[0]

    for p in list_of_postings_lists[1:]:
        result = op_and(result, p)

    return result


def op_and_not(p1, p2):
    """Evaluates p1 AND NOT p2 and returns result as list.

    :param p1: A list containing the first postings list.
    :param p2: A list containing the second postings list.
    :return: A list containing the result of p1 AND NOT p2.
    """
    result = []
    i = 0
    j = 0
    skip_dist1, skip_dist2, can_skip1, can_skip2 = get_skip_flags(len(p1), len(p2))

    while i < len(p1) and j < len(p2):
        if p1[i] == p2[j]:
            i += 1
            j += 1
        elif p1[i] < p2[j]:
            result.append(p1[i])
            i += 1
        else:
            if can_skip2[j]:
                lookahead = j + skip_dist2
                if lookahead < len(p2) and p2[lookahead] <= p1[i]:
                    j += skip_dist2
                else:
                    j += 1
            else:
                j += 1

    result.extend(p1[i:])

    return result


def op_or(p1, p2):
    """Evaluates p1 OR p2 and returns result as list.

    :param p1: A list containing the first postings list.
    :param p2: A list containing the second postings list.
    :return: A list containing the result of p1 OR p2.
    """
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


def op_multi_or(list_of_postings_lists):
    """Evaluates p1 OR p2 OR ... OR pN and returns result as list.

    :param list_of_postings_lists: A list of postings lists.
    :return: A list containing the result of p1 OR p2 OR ... OR pN.
    """
    heap = []
    results = []
    for postings in list_of_postings_lists:
        for docID in postings:
            heapq.heappush(heap, docID)

    while heap:
        smallest = heapq.heappop(heap)
        if results:
            if results[-1] != smallest: results.append(smallest)
        else:
            results.append(smallest)

    return results


def op_not(p, all_p):
    """Evaluates NOT p and returns result as list.

    :param p: A list containing the postings list.
    :param all_p: A list containing the postings list that includes every docID.
    :return: A list containing the result of NOT p.
    """
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
    """Prints the proper format for calling this script."""
    print "usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results"


class OpNode:
    """Nodes for tree used to model a search query in Reverse Polish Notation.

    A node may represent either a search token or an operator.

    Attributes:
        children: A list of OpNode instances. Only operator nodes have children.
        op: A string indicating the node's operator type..
            Possible values: "NOT", "AND", "OR", "AND NOT", None
        term: A string containing the search token value.
        postings: An integer list storing the docIDs from the postings list of a search token node.
        expected_count: An integer storing the expected number of docIDs after an operator node has been fully resolved.
    """

    children = None
    op = None
    term = None
    postings = []
    expected_count = 0

    def __init__(self, children, op, term):
        """Inits OpNode with a list of its child nodes, its operator type, and its search token, where applicable.

        Only operator nodes should have children, and has an operator type: "NOT", "AND", "OR", "AND NOT".HEAD
        Only search token nodes have a search token value, and has an operator type: None.

        :param children: A list of OpNode instances. Only operator nodes have children.
        :param op: A string indicating the node's operator type. Possible values: "NOT", "AND", "OR", "AND NOT", None
        :param term: A string containing the search token value
        """

        self.children = children
        self.op = op
        self.term = term

    def is_op(self):
        """Boolean check if node is a type of operator.

        :return:A boolean value. True if is operator node. False if is search token node.
        """
        return self.op != None

    def read_postings_of_term(self, postings_file, dictionary):
        """ Gets own postings list from file and stores it in its attribute. For search token nodes only.

        :param postings_file: File object referencing the file containing the complete set of postings lists.
        :param dictionary: Dictionary that takes search token keys, and returns a tuple of pointer and length.
            The pointer points to the starting point of the search token's postings list in the file.
            The length refers to the length of the search token's postings list in bytes.
        """

        if self.term in dictionary:
            term_pointer = dictionary[self.term][0]
            postings_length = dictionary[self.term][1]
            postings_file.seek(term_pointer)
            self.postings = [int(docID) for docID in postings_file.read(postings_length).split()]

    def recursive_merge(self, all_docIDs):
        """Recursively resolves self and child operator nodes, and returns a list containing the resulting docIDs.

        For search token nodes, returns its postings list.

        :param all_docIDs: The list of all docIDs possible.
        :return: A list containing resulting docIDs after resolving operators, or postings list for search token nodes
        """
        if self.op != None:
            children_postings = [child.recursive_merge(all_docIDs) for child in self.children]
            return self.merge(children_postings, all_docIDs)
        else:
            return self.postings

    def merge(self, children_postings, all_docIDs):
        """Resolves operator nodes, and returns a list containing the resulting docIDs. For operator nodes only.

        :param children_postings: A list of child search token nodes' postings lists
        :param all_docIDs: The list of all docIDs possible.
        :return: A list containing the resulting docIDs after resolving the operator.
        """
        if self.op == "NOT":
            return op_not(children_postings[0], all_docIDs)
        elif self.op == "OR":
            return op_multi_or(children_postings)
        elif self.op == "AND":
            return op_multi_and(children_postings)
        elif self.op == "AND NOT":
            return op_and_not(children_postings[0], children_postings[1])

    def consolidate_ops_recursive(self, required_op):
        """

        :param required_op: The operator type that is being consolidated.
        :return:
        """
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

    def de_morgans(self, children_nots):
        children_of_nots = [child_not.children[0] for child_not in children_nots]
        center_grandchild = OpNode(children_of_nots, "OR" if self.op == "AND" else "AND", None)
        new_child_not = OpNode([center_grandchild], "NOT", None)
        return new_child_not

    def process_and_not(self, child_not, children_notnots):
        new_child_and = OpNode(children_notnots, "AND", None)
        self.op = "AND NOT"
        self.children = [new_child_and, child_not.children[0]]

    def consolidate_children(self):
        if self.children:
            if self.op == "OR" or self.op == "AND":
                children_nots = [child for child in self.children if child.op == "NOT"]
                if len(children_nots) > 1:
                    if len(children_nots) == len(self.children): # de Morgan's completely wipes out children, so morph into NOT node
                        self.copy_descendant_info(self.de_morgans(children_nots))
                    else: # There are non-NOT children, so maintain current op in current node
                        self.children = [child for child in self.children if child.op != "NOT"]
                        self.children.append(self.de_morgans(children_nots))
            if self.op == "AND":
                children_nots = [child for child in self.children if child.op == "NOT"]
                children_notnots = [child for child in self.children if child.op != "NOT"]
                if children_nots: # There are non-NOT children, and a single NOT child (de Morgan's prevents more NOTs), so morph into AND NOT
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
    """Models a Reverse Polish Notation search query with a tree.

    Nodes in tree represents operators or search tokens, as defined by OpNode class.

    Attributes:
        root: Points to the OpNode that serves as the root node.
    """
    root = None
    op_list = ["NOT", "AND", "OR"]

    def __init__(self, rpn_stack, postings_file, dictionary):
        """Constructs the OpTree as a binary tree. Loads postings into search-token OpNodes immediately.
        """
        node_stack = []
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
        self.root = node_stack.pop()


# TESTS #


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


# END TESTS #

def load_args():
    """Attempts to parse command line arguments fed into the script when it was called.
    Notifies the user of the correct format if parsing failed.
    """
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
    begin = time.time() * 1000.0
    with open(dictionary_file) as dict_file:
        all_docIDs, dictionary = json.load(dict_file)

    # open queries
    postings = file(postings_file)
    output = file(output_file, 'w')
    with open(queries_file) as queries:
        for query in queries:
            rpn_stack = shunting_yard(query)
            if rpn_stack:
                tree = OpTree(rpn_stack, postings, dictionary)
                tree.root.consolidate_ops()
                tree.root.consolidate_children()
                tree.root.calculate_expected(all_docIDs)
                result_IDs = [str(result_ID) for result_ID in tree.root.recursive_merge(all_docIDs)]
                result_IDs.append("\n")
                output.write(" ".join(result_IDs))
            else:
                output.write("\n")
    postings.close()
    output.close()
    after = time.time() * 1000.0
    print after-begin

def and_not_test():
    tree = OpTree(shunting_yard("money AND NOT possibility"), None, {})
    print (tree.root.children[0].op, tree.root.children[0].term)
    print (tree.root.children[1].op, tree.root.children[1].term)
    print (tree.root.children[1].children[0].op, tree.root.children[1].children[0].term)
    tree.root.consolidate_children()
    print tree.root.op

def random_skips_test():
    even = [guy for guy in range(5000000) if guy % 2 == 0]
    # odd = [guy for guy in range(5000000) if guy % 1000 == 0]
    odd = [5000001]

    begin = time.time() * 1000.0
    _ = op_and(even, odd)
    after = time.time() * 1000.0
    print after-begin

def main():
    dictionary_file, postings_file, queries_file, output_file = load_args()

    # tree_initialization_test()
    # nots_test()
    # consolidate_test()
    # and_not_test()
    # random_skips_test()
    process_queries(dictionary_file, postings_file, queries_file, output_file)

if __name__ == "__main__":
    main()