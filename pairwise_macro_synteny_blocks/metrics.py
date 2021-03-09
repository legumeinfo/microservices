from array import array


def levenshtein(a, b):

  if a == b: return 0
  la, lb = len(a), len(b)
  if la == 0: return lb
  if lb == 0: return la
  if lb > la: a, b, la, lb = b, a, lb, la

  cost = array('i', range(lb + 1))
  for i in range(1, la + 1):
    cost[0] = i; ls = i-1; mn = ls
    for j in range(1, lb + 1):
      ls, act = cost[j], ls + int(a[i-1] != b[j-1])
      cost[j] = min(ls+1, cost[j-1]+1, act)
      if (ls < mn): mn = ls
  return cost[lb]


METRICS = {
    'levenshtein': levenshtein
  }
