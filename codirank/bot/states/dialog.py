from __future__ import annotations
from aiogram.fsm.state import State, StatesGroup


class DialogStates(StatesGroup):
    START = State()
    ELICITING = State()
    RANKING = State()
    FEEDBACK = State()
    REFINING = State()
