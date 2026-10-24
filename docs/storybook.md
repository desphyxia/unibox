# The storybook

Status as of 2026-10-24. The parent-facing storybook from `docs/concept-state.md` (section 12: "a running life story per creature, egg to guardian, templated, in the parent-gated area, readable and savable as a PDF or image; no accounts or uploads"), cut down to the prototype: one session per child, so the book tells the story of this session.

## What it is

A short picture book behind the grown-ups' gate in the parent area: a cover with the creature and its name, then one page per moment, each with a picture of that moment and a sentence or two. Example pages:

- *Mira hatched at dawn, after four taps on the egg.*
- *Her first meal was an apple from the tree.*
- *Mira tried on a crown, a scarf and a bow.*
- *A friend came to the nest. Hearts, and then an egg!*
- *The baby got Mira's mint coat and Pip's gold glow.*
- *As the sun set, Mira was tucked in under a blanket.*

Rules for the text:
- **Templated, never generated.** Each page has a few fixed wordings, filled in with names, the kind of creature, its colours, its temperament and the island time.
- **Only what happened.** It never says what the child missed or didn't do, and it never scores.
- **Names stay on the device.** The book may show them; the event log still never records them.

## The plan (one PR each)

1. **Record the story** (done, below). The game notes each first moment and takes a picture of it. Nothing changes for the child.
2. **The book in the parent area** (done, below). A Storybook button: the cover, then a page per moment with the picture and the templated text, turned with arrows. "New session" warns that the book will be cleared.
3. **Saving.** A page as a picture, or the whole book as a PDF (the pictures are already JPEGs, which a PDF can hold as they are). The web build saves it as a browser download. Sharing from the app (the iPad share sheet) waits for the store build.

Choices made (the user can still change them): only this session's story (the prototype saves no creatures between sessions); pictures are screenshots of the real moment, not separate illustrations; pictures and PDF, no accounts or uploads.

## Step 1: the record (`game/scripts/story.gd`)

`main.story` notes a moment the first time it happens, with its facts, the island hour, and who it was about:

| Moment | When | Facts |
|---|---|---|
| `hatch` | the first egg hatches | taps, kind, temperament |
| `meal` | the first apple is eaten | from the hand or the ground |
| `dressed` | the first thing is worn; each new thing joins the list and the picture is taken again | items |
| `drink` | the first drink at the pond | |
| `placed` | the first thing is placed at the pond; gathers like `dressed` | items |
| `ball` | the first game with the ball | |
| `rainbow` | the rainbow after the rain (the whole view) | the place in view |
| `bedtime` | the first creature curls up to sleep; a tuck-in takes the picture again with the blanket | hour, who was tucked in |
| `friend` | the second adult reaches the nest | its coat and glow |
| `pair` | the two greet with hearts | |
| `egg` | the child has chosen the first egg's traits | traits, which parent gave each |
| `hatch_baby1`... | each baby hatches | traits, which parent gave each |
| `grown_baby1`... | each baby is grown | |

It also counts pets, apples, drinks, ball games and things worn or placed, for a closing page. Up to 20 pages. Each new page writes `story_page` to the event log; a picture that can't be taken writes `story_no_picture`.

**Pictures.** A picture is taken a moment after the event, when the action is under way (an apple mid-bite, the baby out of its egg), cut out round the creature (560 by 420 meadow units, wider for two creatures), and kept as a 640x480 JPEG, about 60 KB. If the parent area, the trait picker or the 3D check is open, or the creature is in the other place, it tries again every half second for 12 seconds. The sun button and the grown-ups' button are left out of that one frame if they would show. The cut-out and the shrinking happen on the graphics chip, in a small viewport that draws part of the last frame, so only the small picture is read back. On the graphics-chip renderers (the desktop, and the iPad app later) that read-back doesn't wait for the chip; on the web build it is a plain read of the small picture. The JPEG is made on a worker thread.

`tests/autoplay.tscn` saves the story's pictures and a list of its pages to `OUT_DIR/story`.

## Step 2: the book (`game/scripts/parent_ui.gd`, `story_text.gd`)

**Storybook** is the first button in the parent area. Each page is a spread, since the game is always landscape: the picture on the left, framed like a print, and the words on the right, set in Meadow Book (Lora cut down to Latin letters, `game/fonts/`; other letters fall back to the game's own font). Previous and Next turn the page, and so does a swipe across the picture. Pages:

- **Cover:** "Pip's story" ("The little fox's story" before it has a name), "A playful fox, and one day on the island." The picture is the creature dressed up, else its hatch.
- **One page per moment**, in order, with the moment's picture. The text comes from `StoryText`: each moment has one to three wordings, picked by the moment itself so a page keeps its words. Names are read when the book is opened, so a name given later shows everywhere. A page on a new island day starts "The next morning," (or "The next day," after 11:00). The second trait is called the glow (fox), the mane (unicorn) or the markings (collie).
- **The end, for now:** the counts that happened ("Along the way, Pip was petted five times, ate two apples, had one drink at the pond and played ball twice. The family grew by one baby."), with the latest picture.
- Before the egg hatches the book says that the story begins with the hatch.

**New session** now asks first when the book has pages: "This clears Pip's storybook (13 pages). It isn't kept anywhere else." with Keep playing, Open the storybook, and Clear it and start a new session. Log events: `storybook_opened` (pages), `storybook_closed` (pages seen), `storybook_cleared`.

The autoplay run opens the empty book at the start, every page near the end, swipes both ways, shows the warning, and prints every page's text with and without names.
