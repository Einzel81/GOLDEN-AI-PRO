"""
آلة الحالات
Trading State Machine
"""

from enum import Enum, auto
from typing import Optional, Callable
from dataclasses import dataclass
from loguru import logger


class TradingState(Enum):
    """حالات التداول"""
    IDLE = auto()
    ANALYZING = auto()
    SIGNAL_DETECTED = auto()
    VALIDATING = auto()
    ENTERING_POSITION = auto()
    IN_POSITION = auto()
    MANAGING_POSITION = auto()
    EXITING_POSITION = auto()
    ERROR = auto()


@dataclass
class StateTransition:
    """انتقال الحالة"""
    from_state: TradingState
    to_state: TradingState
    condition: str


class TradingStateMachine:
    """
    آلة حالات التداول
    """
    
    def __init__(self):
        self.state = TradingState.IDLE
        self.previous_state: Optional[TradingState] = None
        self.transitions: list[StateTransition] = []
        self.on_state_change: Optional[Callable] = None
        
        self._setup_transitions()
        
    def _setup_transitions(self):
        """إعداد الانتقالات المسموحة"""
        self.transitions = [
            StateTransition(TradingState.IDLE, TradingState.ANALYZING, "start_analysis"),
            StateTransition(TradingState.ANALYZING, TradingState.SIGNAL_DETECTED, "signal_found"),
            StateTransition(TradingState.ANALYZING, TradingState.IDLE, "no_signal"),
            StateTransition(TradingState.SIGNAL_DETECTED, TradingState.VALIDATING, "validate"),
            StateTransition(TradingState.VALIDATING, TradingState.ENTERING_POSITION, "validation_passed"),
            StateTransition(TradingState.VALIDATING, TradingState.IDLE, "validation_failed"),
            StateTransition(TradingState.ENTERING_POSITION, TradingState.IN_POSITION, "order_filled"),
            StateTransition(TradingState.ENTERING_POSITION, TradingState.ERROR, "order_failed"),
            StateTransition(TradingState.IN_POSITION, TradingState.MANAGING_POSITION, "manage"),
            StateTransition(TradingState.MANAGING_POSITION, TradingState.EXITING_POSITION, "exit_triggered"),
            StateTransition(TradingState.EXITING_POSITION, TradingState.IDLE, "position_closed"),
            StateTransition(TradingState.ERROR, TradingState.IDLE, "reset"),
        ]
    
    def can_transition(self, new_state: TradingState) -> bool:
        """التحقق إذا كان الانتقال مسموحاً"""
        for transition in self.transitions:
            if transition.from_state == self.state and transition.to_state == new_state:
                return True
        return False
    
    def transition(self, new_state: TradingState, reason: str = ""):
        """انتقال إلى حالة جديدة"""
        if not self.can_transition(new_state):
            logger.warning(
                f"Invalid transition: {self.state.name} -> {new_state.name}"
            )
            return False
        
        self.previous_state = self.state
        self.state = new_state
        
        logger.info(
            f"State transition: {self.previous_state.name} -> {new_state.name} "
            f"({reason})"
        )
        
        if self.on_state_change:
            self.on_state_change(self.previous_state, new_state, reason)
        
        return True
    
    def get_state(self) -> TradingState:
        """الحصول على الحالة الحالية"""
        return self.state
    
    def is_in_state(self, state: TradingState) -> bool:
        """التحقق من الحالة"""
        return self.state == state
    
    def reset(self):
        """إعادة تعيين"""
        self.previous_state = None
        self.state = TradingState.IDLE
        logger.info("State machine reset")
