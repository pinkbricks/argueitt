// Turns a transcript into tokens tagged for the four highlight kinds the
// feedback card's legend names.
//
// Fillers and pauses come from what the backend already measured; these two
// lists mirror backend/stats.py so the highlights agree with the counts shown
// beside them. If that file's word sets change, change these too.
const SINGLE_WORD_FILLERS = new Set([
  'um', 'uh', 'uhh', 'umm', 'erm', 'er', 'like', 'basically',
])

const MULTI_WORD_FILLERS = [
  ['you', 'know'],
  ['i', 'mean'],
  ['sort', 'of'],
  ['kind', 'of'],
]

// Repetition is not something the backend reports, so it is counted here.
// Grammar words are excluded: "the" appearing six times is not a finding.
const REPETITION_IGNORED = new Set([
  'the', 'a', 'an', 'and', 'or', 'but', 'to', 'of', 'in', 'on', 'at', 'for',
  'is', 'are', 'was', 'were', 'be', 'been', 'that', 'this', 'with', 'as',
  'so', 'if', 'it', 'i', 'you', 'they', 'we', 'he', 'she',
])

const REPETITION_MIN_COUNT = 3

function normalise(token) {
  return token.toLowerCase().replace(/[^a-z0-9']/g, '')
}

// Splits on whitespace but keeps it, so the transcript can be rebuilt exactly.
function tokenise(transcript) {
  const parts = transcript.split(/(\s+)/)
  const tokens = []
  let offset = 0

  for (const part of parts) {
    if (part.length === 0) continue
    tokens.push({
      text: part,
      space: /^\s+$/.test(part),
      start: offset,
      end: offset + part.length,
      word: normalise(part),
      kind: null,
      pauseAfter: false,
    })
    offset += part.length
  }

  return tokens
}

function markFillers(tokens) {
  const words = tokens.filter((t) => !t.space)

  for (let i = 0; i < words.length; i += 1) {
    for (const phrase of MULTI_WORD_FILLERS) {
      const matches = phrase.every((part, j) => words[i + j]?.word === part)
      if (matches) {
        phrase.forEach((_, j) => {
          words[i + j].kind = 'filler'
        })
      }
    }
    if (!words[i].kind && SINGLE_WORD_FILLERS.has(words[i].word)) {
      words[i].kind = 'filler'
    }
  }
}

function markStrongest(tokens, strongestMoment, transcript) {
  if (!strongestMoment) return

  // The model quotes the moment back, so match loosely: punctuation and
  // spacing often differ from the transcript by a character or two.
  const needle = strongestMoment.toLowerCase().replace(/\s+/g, ' ').trim()
  const haystack = transcript.toLowerCase().replace(/\s+/g, ' ')
  let at = haystack.indexOf(needle)

  if (at === -1) {
    const words = needle.split(' ')
    if (words.length < 4) return
    at = haystack.indexOf(words.slice(0, 6).join(' '))
    if (at === -1) return
  }

  const from = at
  const to = at + needle.length

  for (const token of tokens) {
    if (token.space) continue
    if (token.start < to && token.end > from) token.kind = 'strong'
  }
}

function markRepetitions(tokens) {
  const counts = new Map()
  for (const token of tokens) {
    if (token.space || token.kind || token.word.length < 2) continue
    if (REPETITION_IGNORED.has(token.word)) continue
    counts.set(token.word, (counts.get(token.word) || 0) + 1)
  }

  for (const token of tokens) {
    if (token.space || token.kind) continue
    if ((counts.get(token.word) || 0) >= REPETITION_MIN_COUNT) token.kind = 'repetition'
  }
}

// pause_details arrives in time order and names the word each gap followed, so
// walk the transcript consuming pauses as their word turns up.
function markPauses(tokens, pauseDetails) {
  if (!pauseDetails?.length) return
  const pending = pauseDetails.map((p) => normalise(p.after_word || ''))
  let next = 0

  for (const token of tokens) {
    if (token.space || next >= pending.length) continue
    if (token.word && token.word === pending[next]) {
      token.pauseAfter = true
      next += 1
    }
  }
}

export function buildHighlights(transcript, { strongestMoment, pauseDetails } = {}) {
  if (!transcript) return []

  const tokens = tokenise(transcript)
  markFillers(tokens)
  markStrongest(tokens, strongestMoment, transcript)
  markRepetitions(tokens)
  markPauses(tokens, pauseDetails)

  return tokens
}
