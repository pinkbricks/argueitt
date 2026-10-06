// Shown on the analysing screen while the backend works. Each entry pairs a
// fact with something to do about it, so the panel is never just trivia.
//
// Written against what Argueitt actually scores — the SPONTANEOUS_ANSWER
// functions in backend/framework.py (coherence, answering the real question,
// recovery) and the delivery metrics in backend/stats.py (filler words, time
// to first content word, pace, long pauses) — so a tip is never advice the
// coach contradicts a few seconds later.
//
// Hardcoded for now; the intent is for these to come from the backend, picked
// against the speaker's own weakest function.
export const waitingTips = [
  {
    fact: 'Filler words like "um" often appear while your brain searches for the next phrase.',
    tip: 'Try replacing "um" with a silent pause.',
  },
  {
    fact: 'A listener decides what your answer is from your first sentence, then spends the rest of it checking whether they were right.',
    tip: 'Lead with your position. The reasons can follow it.',
  },
  {
    fact: 'Stumbling costs almost nothing. Stopping to restart the sentence costs much more.',
    tip: 'Finish the sentence you are in, then begin a clean one.',
  },
  {
    fact: 'Under pressure most people drift to a nearby question that is easier to answer than the one they were asked.',
    tip: 'Repeat the question to yourself before your first word.',
  },
  {
    fact: 'Three points mentioned in passing are less convincing than one point argued properly.',
    tip: 'Pick your strongest reason and spend your time there.',
  },
  {
    fact: 'Speakers tend to speed up on the line that matters most to them.',
    tip: 'Slow down on your key sentence. Pace signals importance.',
  },
  {
    fact: 'Hedges like "I think" and "sort of" weaken claims the speaker already believes.',
    tip: 'State the claim once, without the cushion.',
  },
  {
    fact: 'Concrete examples are remembered far longer than the abstractions they illustrate.',
    tip: 'Name one specific case, even a small one.',
  },
  {
    fact: 'Trailing off at the end can undo an otherwise strong answer.',
    tip: 'When you are out of things to say, stop there.',
  },
]
