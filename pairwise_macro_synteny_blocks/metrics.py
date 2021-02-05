def _levenshteinRecurrence(a, i, b, j, t, mask):
  # use memoized data if possible
  if t[i][j] is None:
    # base case: empty strings
    if i == 0:
      t[i][j] = j
    elif j == 0:
      t[i][j] = i
    # test if last characters of the strings match
    else:
      cost = 0 if a[i-1] == b[j-1] and a[i-1] not in mask else 1
      # return minimum of delete char from a, delete char from b, and delete
      # char from both
      t[i][j] = min(_levenshteinRecurrence(a, i-1, b, j, t, mask)+1,
                    _levenshteinRecurrence(a, i, b, j-1, t, mask)+1,
                    _levenshteinRecurrence(a, i-1, b, j-1, t, mask)+cost)
  return t[i][j]


def levenshtein(a, b, mask=set()):
  i = len(a)
  j = len(b)
  t = [[None for n in range(j+1)] for m in range(i+1)]
  return _levenshteinRecurrence(a, i, b, j, t, mask)


METRICS = {
    'levenshtein': levenshtein
  }
