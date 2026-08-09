"""Small dialogue-act precheck before intent classification."""

from __future__ import annotations


GREETING_WORDS = {"hi", "hello", "hey", "salam", "assalamualaikum"}
ACK_WORDS = {"ok", "okay", "thanks", "thank you", "tnx", "dhonnobad", "done"}


def detect_dialogue_act(text: str) -> str | None:
    normalized = text.strip().lower()

    if normalized in GREETING_WORDS:
        return "greeting"

    if normalized in ACK_WORDS:
        return "acknowledgement"

    return None
