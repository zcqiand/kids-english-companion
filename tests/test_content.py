"""content.py / characters.py：种子内容完整性——树锚点 M03.F01 / M02.F02。"""
from __future__ import annotations

from kids_english.characters import CHARACTERS, get_character
from kids_english.content import seed_stories, seed_words


def test_word_texts_unique():
    texts = [w["text"] for w in seed_words()]
    assert len(texts) == len(set(texts))


def test_word_fields_present():
    for w in seed_words():
        assert w["id"] == "w_" + w["text"].replace(" ", "_")
        assert w["phonetic"].startswith("/")
        assert w["meaning_cn"]
        assert w["theme"]
        assert w["level"] in (1, 2)


def test_story_words_exist_in_lexicon():
    lex = {w["text"] for w in seed_words()}
    for s in seed_stories():
        for page in s["pages"]:
            for word in page["words"]:
                assert word in lex, f"{s['id']} 引用了词库外的词: {word}"


def test_story_sentences_short_and_bilingual():
    for s in seed_stories():
        for page in s["pages"]:
            assert len(page["en"].split()) <= 9, f"{s['id']} 句子过长: {page['en']}"
            assert page["cn"].strip()


def test_story_characters_exist():
    ids = {c["id"] for c in CHARACTERS}
    for s in seed_stories():
        assert s["character_id"] in ids


def test_get_character():
    maisy = get_character("maisy")
    assert maisy is not None
    assert maisy["name_cn"] == "小鼠波波"
    assert get_character("nobody") is None
    assert len(CHARACTERS) == 4
