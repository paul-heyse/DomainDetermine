"""Text normalization utilities for mapping inputs."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Mapping

try:
    import spacy
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    spacy = None  # type: ignore[assignment]


@dataclass(slots=True)
class NormalizedText:
    """Represents normalized text and basic linguistic signals."""

    original: str
    normalized: str
    language: str
    tokens: tuple[str, ...]


class TextNormalizer:
    """Applies Unicode normalization, case folding, and tokenization."""

    _STOPWORD_PATTERN = re.compile(r"\b(\w{1,2})\b", re.IGNORECASE)

    def __init__(self, language_model: str = "en_core_web_sm", acronym_maps: Mapping[str, Mapping[str, str]] | None = None) -> None:
        self._nlp = self._load_pipeline(language_model)
        self._acronym_maps = acronym_maps or {}

    @staticmethod
    def _load_pipeline(language_model: str):
        if spacy is None:
            return None
        try:
            return spacy.load(language_model, disable=("ner", "parser"))
        except OSError:  # pragma: no cover - model missing
            return spacy.blank("en")

    @staticmethod
    def _remove_control_characters(text: str) -> str:
        return "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")

    @staticmethod
    def _case_fold(text: str) -> str:
        return text.casefold()

    @classmethod
    def _strip_short_tokens(cls, text: str) -> str:
        return cls._STOPWORD_PATTERN.sub(" ", text)

    def normalize(self, text: str) -> NormalizedText:
        """Normalize text and provide token information."""

        clean_text = self._remove_control_characters(text)
        clean_text = unicodedata.normalize("NFC", clean_text)
        folded_text = self._case_fold(clean_text)
        stripped_text = self._strip_short_tokens(folded_text)
        language, tokens = self._tokenize(stripped_text)
        expanded_text = self._expand_acronyms(stripped_text, language)
        language, tokens = self._tokenize(expanded_text)
        return NormalizedText(
            original=text,
            normalized=expanded_text.strip(),
            language=language,
            tokens=tokens,
        )

    def detect_language(self, text: str) -> str:
        """Detect language without full normalization."""

        language, _ = self._tokenize(text)
        if language != "und":
            return language
        normalized = self.normalize(text)
        return normalized.language

    def normalize_batch(self, texts: Iterable[str]) -> tuple[NormalizedText, ...]:
        """Normalize a batch of texts."""

        return tuple(self.normalize(text) for text in texts)

    def _tokenize(self, text: str) -> tuple[str, tuple[str, ...]]:
        if self._nlp is None:
            tokens = tuple(token for token in re.split(r"\W+", text) if token)
            return ("und", tokens)
        doc = self._nlp(text)
        language = getattr(doc, "lang_", None) or "und"
        tokens = tuple(token.lemma_ for token in doc if not token.is_stop)
        return (language, tokens)

    def _expand_acronyms(self, text: str, language: str) -> str:
        mappings = self._acronym_maps.get(language, {})
        if not mappings:
            return text
        pattern = re.compile(r"\b(" + "|".join(map(re.escape, mappings)) + r")\b", re.IGNORECASE)

        def _replace(match: re.Match[str]) -> str:
            key = match.group(0).upper()
            return mappings.get(key, match.group(0))

        return pattern.sub(_replace, text)

