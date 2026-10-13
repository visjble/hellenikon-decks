# Hellēnikon Decks

Free Ancient Greek flashcard decks for [Hellēnikon](https://hellenikon.netlify.app)
and [Anki](https://apps.ankiweb.net), shared under CC BY-SA 4.0.

Each deck is one JSON file in `decks/`. On every change a GitHub Action
validates the decks and rebuilds an Anki package for each one.

## Using a deck

**In Anki:** download the deck's `.apkg` from the
[`anki` release](../../releases/tag/anki), then in Anki choose File → Import.
Importing a newer copy of the same deck updates its cards and keeps your review
history.

**In Hellēnikon:** in Flashcards, open 📚 Deck Library and choose Import. The
deck's cards appear as their own group; words you already have cards for are
left as they are. Import it again later to pick up cards added since. A deck
file saved from here can also be opened with 📤 Import JSON.

The index and decks can also be fetched straight from jsDelivr, for example:

    https://cdn.jsdelivr.net/gh/visjble/hellenikon-decks@main/index.json
    https://cdn.jsdelivr.net/gh/visjble/hellenikon-decks@main/decks/attic-particles.json

jsDelivr caches a branch for up to 12 hours, so a change can take that long to
show there.

## What may go in a deck

Everything here is published under CC BY-SA 4.0, so a deck may only contain
material you are free to share:

- **Glosses and grammar notes in your own words.**
- **Example sentences that are original, or quoted from ancient texts** (which
  are public domain). Keep them short: 12 words at most.
- **No text copied from copyrighted books:** textbooks (Athenaze, Reading Greek,
  JACT, Hansen & Quinn …), modern translations, commentaries or dictionaries. A
  deck may *follow* a textbook's chapter, but its sentences and glosses must
  not come from it.

Cards made in Hellēnikon carry the full sentence of the text you were reading
when you queued the word, in a hidden `context` field. The checker rejects that
field, along with the other app-only fields (`id`, `sourceDocumentId`,
`sourceDocumentTitle`), so a raw app export cannot be added by mistake.

## Adding a deck

1. In Hellēnikon, choose Export → "Deck for sharing…", pick the cards, and fill
   in the deck's details; the file it saves already fits the format below and
   leaves out everything private. Put it in `decks/`. (Or copy
   `decks/attic-particles.json` and edit it by hand.)
2. Run the checker and rebuild the index (Python 3, nothing to install):

       python3 tools/decks.py check
       python3 tools/decks.py index

3. Commit the deck together with `index.json` and open a pull request.

To build the Anki packages locally as well:

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/python tools/decks.py apkg     # writes build/<id>.apkg

## Deck format (`hellenikon-deck`, version 1)

A deck keeps the same `cards` list as a Hellēnikon JSON export, so the app's
existing Import JSON already reads it.

| Deck field | Required | Notes |
|---|---|---|
| `format` | yes | `"hellenikon-deck"` |
| `version` | yes | `1` |
| `id` | yes | Same as the file name: lowercase letters, digits, hyphens |
| `title` | yes | |
| `description` | yes | One or two sentences |
| `language` | yes | `"grc"` |
| `dialect` | no | e.g. `"Attic"`, `"Ionic"`, `"Koine"` |
| `level` | yes | `beginner`, `intermediate` or `advanced` |
| `author` | yes | |
| `license` | yes | `"CC-BY-SA-4.0"` |
| `source` | yes | Where the material comes from, e.g. "Original" or "Vocabulary of Xenophon, Anabasis 1.1–1.3" |
| `tags` | no | List of lowercase-hyphenated words |
| `updated` | yes | `YYYY-MM-DD` |
| `cards` | yes | At least one card |

| Card field | Required | Notes |
|---|---|---|
| `greek` | yes | The word or phrase on the front; at most 3 words |
| `english` | yes | The meaning |
| `lemma` | no | Dictionary form; for a phrase, a short parse of each word |
| `part_of_speech` | no | `noun`, `verb`, `particle`, `phrase` … |
| `person`, `number`, `tense`, `voice`, `mood`, `case`, `gender` | no | Parsing, where it applies |
| `example_sentence` | no | At most 12 words; needs `example_translation` |
| `example_translation` | no | Needs `example_sentence` |

All text must be Unicode NFC, and no two cards in a deck may have the same
`greek` (ignoring case).

## License

The decks and the rest of this repository's content are licensed under
[CC BY-SA 4.0](LICENSE). The code in `tools/` and `.github/` is under the
[MIT license](LICENSE-tools).
