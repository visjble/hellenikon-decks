#!/usr/bin/env python3
"""
Check the decks, build index.json, and build Anki packages.

    python3 tools/decks.py check   validate every deck; fail if index.json is stale
    python3 tools/decks.py index   rewrite index.json from decks/
    python3 tools/decks.py apkg    write build/<id>.apkg for every deck (needs genanki)

`check` and `index` use only the standard library, so a contributor can run
them without installing anything. The format is described in README.md.
"""

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECKS = ROOT / 'decks'
INDEX = ROOT / 'index.json'
BUILD = ROOT / 'build'

FORMAT = 'hellenikon-deck'
VERSION = 1

DECK_REQUIRED = ['format', 'version', 'id', 'title', 'description', 'language',
                 'level', 'author', 'license', 'source', 'updated', 'cards']
DECK_OPTIONAL = ['dialect', 'tags']
LEVELS = ['beginner', 'intermediate', 'advanced']
LICENSES = ['CC-BY-SA-4.0']

# The card fields Hellēnikon generates, and no others: a card exported from the
# app also carries `id`, the verbatim source sentence in `context`, and the
# source document, none of which belong in a shared deck.
CARD_REQUIRED = ['greek', 'english']
CARD_OPTIONAL = ['lemma', 'part_of_speech', 'person', 'number', 'tense', 'voice',
                 'mood', 'case', 'gender', 'example_sentence', 'example_translation']
CARD_FIELDS = CARD_REQUIRED + CARD_OPTIONAL

# The app makes a phrase card from at most three words; an example is a short
# sentence, not a passage.
GREEK_MAX_WORDS = 3
EXAMPLE_MAX_WORDS = 12

# Size limits, so one deck stays something a reviewer can read through
MAX_CARDS = 500
CARD_FIELD_MAX_CHARS = 300
DECK_TEXT_MAX_CHARS = {'title': 120, 'description': 500, 'author': 80, 'source': 300}

SLUG = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
GREEK_LETTER = re.compile(r'[Ͱ-Ͽἀ-῿]')


def deck_files():
    return sorted(DECKS.glob('*.json'))


def is_nfc(text):
    return unicodedata.normalize('NFC', text) == text


def validate(path):
    """Return the problems with one deck file, as readable strings."""
    try:
        deck = json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return [f'not valid UTF-8 JSON: {e}']
    if not isinstance(deck, dict):
        return ['the file must hold one JSON object']

    problems = []
    for key in DECK_REQUIRED:
        if key not in deck:
            problems.append(f'missing "{key}"')
    for key in deck:
        if key not in DECK_REQUIRED + DECK_OPTIONAL:
            problems.append(f'unknown deck field "{key}"')
    if problems:
        return problems

    if deck['format'] != FORMAT:
        problems.append(f'"format" must be "{FORMAT}"')
    if deck['version'] != VERSION:
        problems.append(f'"version" must be {VERSION}')
    if deck['id'] != path.stem:
        problems.append(f'"id" must match the file name ("{path.stem}")')
    if not SLUG.match(path.stem):
        problems.append('file name must be lowercase letters, digits and hyphens')
    for key, limit in DECK_TEXT_MAX_CHARS.items():
        if not isinstance(deck[key], str) or not deck[key].strip():
            problems.append(f'"{key}" must be a non-empty string')
        elif len(deck[key]) > limit:
            problems.append(f'"{key}" is over {limit} characters')
    if deck['language'] != 'grc':
        problems.append('"language" must be "grc"')
    if deck['level'] not in LEVELS:
        problems.append(f'"level" must be one of {", ".join(LEVELS)}')
    if deck['license'] not in LICENSES:
        problems.append(f'"license" must be one of {", ".join(LICENSES)}')
    if not isinstance(deck['updated'], str) or not DATE.match(deck['updated']):
        problems.append('"updated" must be a YYYY-MM-DD date')
    tags = deck.get('tags', [])
    if not isinstance(tags, list) or not all(isinstance(t, str) and SLUG.match(t) for t in tags):
        problems.append('"tags" must be a list of lowercase-hyphenated words')

    cards = deck['cards']
    if not isinstance(cards, list) or not cards:
        return problems + ['"cards" must be a non-empty list']
    if len(cards) > MAX_CARDS:
        problems.append(f'{len(cards)} cards: a deck holds at most {MAX_CARDS}; split it')

    seen = {}
    for n, card in enumerate(cards, 1):
        where = f'card {n}'
        if not isinstance(card, dict):
            problems.append(f'{where}: must be an object')
            continue
        if isinstance(card.get('greek'), str):
            where = f'card {n} ({card["greek"]})'
        for key in CARD_REQUIRED:
            if not isinstance(card.get(key), str) or not card[key].strip():
                problems.append(f'{where}: missing "{key}"')
        for key, value in card.items():
            if key not in CARD_FIELDS:
                problems.append(f'{where}: field "{key}" is not allowed in a shared deck')
            elif not isinstance(value, str):
                problems.append(f'{where}: "{key}" must be a string')
            elif not is_nfc(value):
                problems.append(f'{where}: "{key}" is not Unicode NFC')
            elif len(value) > CARD_FIELD_MAX_CHARS:
                problems.append(f'{where}: "{key}" is over {CARD_FIELD_MAX_CHARS} characters')

        greek = card.get('greek')
        if isinstance(greek, str) and greek.strip():
            if not GREEK_LETTER.search(greek):
                problems.append(f'{where}: "greek" has no Greek letters')
            if len(greek.split()) > GREEK_MAX_WORDS:
                problems.append(f'{where}: "greek" is over {GREEK_MAX_WORDS} words')
            key = unicodedata.normalize('NFC', greek).lower()
            if key in seen:
                problems.append(f'{where}: duplicate of card {seen[key]}')
            seen.setdefault(key, n)
        example = card.get('example_sentence')
        if isinstance(example, str) and len(example.split()) > EXAMPLE_MAX_WORDS:
            problems.append(f'{where}: "example_sentence" is over {EXAMPLE_MAX_WORDS} words')
        if bool(card.get('example_sentence')) != bool(card.get('example_translation')):
            problems.append(f'{where}: an example sentence and its translation go together')
    return problems


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def build_index():
    entries = []
    for path in deck_files():
        deck = load(path)
        entries.append({
            'id': deck['id'],
            'title': deck['title'],
            'description': deck['description'],
            'level': deck['level'],
            'dialect': deck.get('dialect', ''),
            'tags': deck.get('tags', []),
            'author': deck['author'],
            'license': deck['license'],
            'source': deck['source'],
            'updated': deck['updated'],
            'cards': len(deck['cards']),
            'file': f'decks/{path.name}',
        })
    index = {'format': 'hellenikon-deck-index', 'version': VERSION, 'decks': entries}
    return json.dumps(index, ensure_ascii=False, indent=2) + '\n'


def check():
    failed = False
    for path in deck_files():
        problems = validate(path)
        if problems:
            failed = True
            print(f'{path.relative_to(ROOT)}:')
            for p in problems:
                print(f'  - {p}')
    if failed:
        return 1
    current = INDEX.read_text(encoding='utf-8') if INDEX.exists() else ''
    if current != build_index():
        print('index.json is out of date: run  python3 tools/decks.py index')
        return 1
    print(f'{len(deck_files())} deck(s) OK, index.json up to date')
    return 0


def index():
    for path in deck_files():
        if validate(path):
            print(f'{path.relative_to(ROOT)} has problems; run  python3 tools/decks.py check')
            return 1
    INDEX.write_text(build_index(), encoding='utf-8')
    print(f'wrote index.json ({len(deck_files())} deck(s))')
    return 0


def stable_id(text):
    """An Anki id from a name, the same on every build, so re-importing a
    newer package updates the deck instead of adding a second one."""
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], 'big') % (1 << 30) + (1 << 30)


ANKI_CSS = """
.card { font-family: "GFS Didot", "Gentium Plus", "Noto Serif", serif;
        font-size: 20px; text-align: center; color: #222; background: #fdfcf8; }
.nightMode .card, .card.nightMode { color: #eee; background: #1e1e1e; }
.greek { font-size: 2em; }
.english { font-size: 1.3em; margin: .6em 0; }
.grammar { color: #777; font-size: .85em; }
.example { margin-top: 1em; font-style: italic; }
"""

ANKI_FRONT = '<div class="greek">{{Greek}}</div>'

ANKI_BACK = """{{FrontSide}}
<hr id="answer">
<div class="english">{{English}}</div>
<div class="grammar">
{{#Lemma}}{{Lemma}}{{/Lemma}}{{#PartOfSpeech}} · {{PartOfSpeech}}{{/PartOfSpeech}}
{{#Person}} · {{Person}}{{/Person}}{{#Number}} · {{Number}}{{/Number}}
{{#Tense}} · {{Tense}}{{/Tense}}{{#Voice}} · {{Voice}}{{/Voice}}{{#Mood}} · {{Mood}}{{/Mood}}
{{#Case}} · {{Case}}{{/Case}}{{#Gender}} · {{Gender}}{{/Gender}}
</div>
{{#Example}}<div class="example">{{Example}}<br>{{ExampleTranslation}}</div>{{/Example}}
"""

# Anki field name for each deck card field, in note order
ANKI_FIELDS = [('greek', 'Greek'), ('english', 'English'), ('lemma', 'Lemma'),
               ('part_of_speech', 'PartOfSpeech'), ('person', 'Person'), ('number', 'Number'),
               ('tense', 'Tense'), ('voice', 'Voice'), ('mood', 'Mood'), ('case', 'Case'),
               ('gender', 'Gender'), ('example_sentence', 'Example'),
               ('example_translation', 'ExampleTranslation')]


def apkg():
    try:
        import genanki
    except ImportError:
        print('genanki is not installed: pip install -r requirements.txt')
        return 1
    from html import escape

    model = genanki.Model(
        stable_id('hellenikon-deck-model-v1'),
        'Hellēnikon card',
        fields=[{'name': name} for _, name in ANKI_FIELDS],
        templates=[{'name': 'Greek → English', 'qfmt': ANKI_FRONT, 'afmt': ANKI_BACK}],
        css=ANKI_CSS,
    )
    BUILD.mkdir(exist_ok=True)
    for path in deck_files():
        if validate(path):
            print(f'{path.relative_to(ROOT)} has problems; run  python3 tools/decks.py check')
            return 1
        deck = load(path)
        anki_deck = genanki.Deck(stable_id(f'hellenikon-deck:{deck["id"]}'),
                                 f'Hellēnikon::{deck["title"]}',
                                 description=escape(deck['description']))
        for card in deck['cards']:
            anki_deck.add_note(genanki.Note(
                model=model,
                fields=[escape(card.get(key, '')) for key, _ in ANKI_FIELDS],
                guid=genanki.guid_for(deck['id'], card['greek']),
                tags=deck.get('tags', []),
            ))
        out = BUILD / f'{deck["id"]}.apkg'
        genanki.Package(anki_deck).write_to_file(out)
        print(f'wrote {out.relative_to(ROOT)} ({len(deck["cards"])} cards)')
    return 0


COMMANDS = {'check': check, 'index': index, 'apkg': apkg}

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__.strip())
        sys.exit(2)
    sys.exit(COMMANDS[sys.argv[1]]())
