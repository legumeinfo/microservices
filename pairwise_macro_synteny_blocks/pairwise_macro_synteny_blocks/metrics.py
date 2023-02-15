from array import array
from itertools import chain
from collections import Counter


def jaccard(a, b, n=1, reversals=False, multiset=False):
    # parse args that may have come from string
    if isinstance(n, str):
        n = int(n)
    if isinstance(reversals, str):
        reversals = bool(reversals)

    # base case
    la, lb = len(a), len(b)
    if n > la or n > lb:
        return 1

    # convert input to n-gram lists
    def nGram(s):
        return [tuple(s[i : i + n]) for i in range(len(s) - n + 1)]

    na, nb = nGram(a), nGram(b)

    # assign n-grams unique IDs
    ids = {}
    i = 0
    for g in chain(na, nb):
        if g not in ids:
            r = g[::-1]
            if reversals and r in ids:
                ids[g] = ids[r]
            else:
                ids[g] = i
                i += 1

    # convert n-gram lists to id sets
    def gramID(g):
        return ids[g]

    aIDs, bIDs = map(gramID, na), map(gramID, nb)

    # generate a count map for each list
    def multiSet(l):
        if not multiset:
            return Counter({e: 1 for e in l})
        return Counter(l)

    sa, sb = multiSet(aIDs), multiSet(bIDs)

    # compute the Jaccard index
    intersection = sa & sb
    union = sa | sb
    numerator = sum(intersection.values())
    denominator = sum(union.values())
    if denominator == 0:
        denominator = 1

    # return the distance
    return 1 - numerator / denominator


def levenshtein(a, b):
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    if lb > la:
        a, b, la, lb = b, a, lb, la

    cost = array("i", range(lb + 1))
    for i in range(1, la + 1):
        cost[0] = i
        ls = i - 1
        mn = ls
        for j in range(1, lb + 1):
            ls, act = cost[j], ls + int(a[i - 1] != b[j - 1])
            cost[j] = min(ls + 1, cost[j - 1] + 1, act)
            if ls < mn:
                mn = ls
    return cost[lb]


METRICS = {"jaccard": jaccard, "levenshtein": levenshtein}
