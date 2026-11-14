"""The app's texts, in English (the default) and Portuguese.

The language follows the device: Portuguese if the device's main language is
Portuguese (any country), English otherwise.
"""

from dataclasses import dataclass
from typing import Sequence

import flet as ft


@dataclass(frozen=True)
class Texts:
    # Header blocks (short: they must fit the blocks).
    score: str
    best: str
    level: str
    restart: str
    level_names: tuple[str, str, str]  # BEGINNER, MIDDLE, MASTER
    # The message under the color blocks.
    play: str
    game_over: str
    unlocked: str
    # Above the color blocks when the game is over.
    final_score: str  # with {points}
    # Tooltips.
    restart_tip: str
    level_tip: str
    starting_color: str
    unlocks_at: str  # with {points}
    # The question before losing the current game.
    restart_question: str
    change_level_question: str  # with {level}
    lose_game: str
    cancel: str
    change: str
    # How to play: the button, then the tutorial's 3 steps (title, text each).
    how_to_play: str
    tutorial_titles: tuple[str, str, str]
    tutorial_texts: tuple[str, str, str]
    skip: str
    next: str
    start: str


ENGLISH = Texts(
    score="SCORE",
    best="BEST",
    level="LEVEL",
    restart="RESTART",
    level_names=("BEGINNER", "MIDDLE", "MASTER"),
    play="Line up 3 or more squares of the same color.",
    game_over="GAME OVER",
    unlocked="New color unlocked!",
    final_score="You scored {points} points!",
    restart_tip="Restart",
    level_tip="Change level (starts a new game)",
    starting_color="Starting color",
    unlocks_at="Unlocks at {points} points",
    restart_question="Restart the game?",
    change_level_question="Change to {level}?",
    lose_game="You will lose the current game.",
    cancel="CANCEL",
    change="CHANGE",
    how_to_play="HOW TO PLAY",
    tutorial_titles=("Swipe to move", "A new square", "Line up 3"),
    tutorial_texts=(
        "Swipe left, right, up, or down: all the squares slide that way, as far as they can.",
        "After each move, a new square appears on the opposite side.",
        "Line up 3 or more squares of the same color: they disappear and you score."
        " Every 50 points unlocks a new color. The game ends when the board is full.",
    ),
    skip="SKIP",
    next="NEXT",
    start="PLAY!",
)

PORTUGUESE = Texts(
    score="PONTOS",
    best="RECORDE",
    level="NÍVEL",
    restart="REINICIAR",
    level_names=("INICIANTE", "MÉDIO", "MESTRE"),
    play="Alinhe 3 ou mais quadrados da mesma cor.",
    game_over="FIM DE JOGO",
    unlocked="Nova cor desbloqueada!",
    final_score="Você fez {points} pontos!",
    restart_tip="Reiniciar",
    level_tip="Mudar de nível (começa um novo jogo)",
    starting_color="Cor inicial",
    unlocks_at="Desbloqueia com {points} pontos",
    restart_question="Reiniciar o jogo?",
    change_level_question="Mudar para {level}?",
    lose_game="Você vai perder o jogo atual.",
    cancel="CANCELAR",
    change="MUDAR",
    how_to_play="COMO JOGAR",
    tutorial_titles=("Deslize para mover", "Um novo quadrado", "Alinhe 3"),
    tutorial_texts=(
        "Deslize para a esquerda, direita, cima ou baixo: todos os quadrados deslizam"
        " para esse lado, até onde der.",
        "Depois de cada movimento, um novo quadrado aparece no lado oposto.",
        "Alinhe 3 ou mais quadrados da mesma cor: eles somem e você ganha pontos."
        " A cada 50 pontos, uma nova cor é desbloqueada. O jogo acaba quando o tabuleiro enche.",
    ),
    skip="PULAR",
    next="PRÓXIMO",
    start="JOGAR!",
)

LANGUAGES = {"en": ENGLISH, "pt": PORTUGUESE}
DEFAULT_LANGUAGE = "en"


def language_for(locales: Sequence[ft.Locale]) -> str:
    """The language to use for a device's locales (most preferred first)."""
    if locales:
        main = (locales[0].language_code or "").lower()
        if main in LANGUAGES:
            return main
    return DEFAULT_LANGUAGE
