"""State machine for managing hexapod operational modes."""

import asyncio
from enum import Enum, auto
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from loguru import logger


class OperationalMode(Enum):
    """Operational modes for the hexapod."""
    AUTONOMOUS = auto()
    SEMI_AUTONOMOUS = auto()
    REMOTE_CONTROL = auto()
    EMERGENCY_STOP = auto()
    INITIALIZATION = auto()
    SHUTDOWN = auto()
    MAINTENANCE = auto()


@dataclass
class StateTransition:
    """Represents a state transition with metadata."""
    from_state: OperationalMode
    to_state: OperationalMode
    timestamp: datetime
    reason: str
    triggered_by: str  # 'operator', 'system', 'emergency'


class StateMachine:
    """
    Finite State Machine for managing hexapod operational modes.

    Handles state transitions, validates allowed transitions, and
    triggers appropriate callbacks when states change.
    """

    # Define allowed state transitions
    ALLOWED_TRANSITIONS: Dict[OperationalMode, list[OperationalMode]] = {
        OperationalMode.INITIALIZATION: [
            OperationalMode.AUTONOMOUS,
            OperationalMode.SEMI_AUTONOMOUS,
            OperationalMode.REMOTE_CONTROL,
            OperationalMode.SHUTDOWN,
        ],
        OperationalMode.AUTONOMOUS: [
            OperationalMode.SEMI_AUTONOMOUS,
            OperationalMode.REMOTE_CONTROL,
            OperationalMode.EMERGENCY_STOP,
            OperationalMode.MAINTENANCE,
            OperationalMode.SHUTDOWN,
        ],
        OperationalMode.SEMI_AUTONOMOUS: [
            OperationalMode.AUTONOMOUS,
            OperationalMode.REMOTE_CONTROL,
            OperationalMode.EMERGENCY_STOP,
            OperationalMode.MAINTENANCE,
            OperationalMode.SHUTDOWN,
        ],
        OperationalMode.REMOTE_CONTROL: [
            OperationalMode.AUTONOMOUS,
            OperationalMode.SEMI_AUTONOMOUS,
            OperationalMode.EMERGENCY_STOP,
            OperationalMode.MAINTENANCE,
            OperationalMode.SHUTDOWN,
        ],
        OperationalMode.EMERGENCY_STOP: [
            OperationalMode.REMOTE_CONTROL,  # Must go through remote control first
            OperationalMode.SHUTDOWN,
        ],
        OperationalMode.MAINTENANCE: [
            OperationalMode.AUTONOMOUS,
            OperationalMode.SEMI_AUTONOMOUS,
            OperationalMode.REMOTE_CONTROL,
            OperationalMode.SHUTDOWN,
        ],
        OperationalMode.SHUTDOWN: [],  # Terminal state
    }

    def __init__(self, initial_mode: OperationalMode = OperationalMode.INITIALIZATION):
        """
        Initialize state machine.

        Args:
            initial_mode: Starting operational mode
        """
        self._current_mode = initial_mode
        self._previous_mode: Optional[OperationalMode] = None
        self._transition_history: list[StateTransition] = []
        self._callbacks: Dict[OperationalMode, list[Callable]] = {}
        self._lock = asyncio.Lock()

        logger.info(f"StateMachine initialized in {initial_mode.name} mode")

    @property
    def current_mode(self) -> OperationalMode:
        """Get current operational mode."""
        return self._current_mode

    @property
    def previous_mode(self) -> Optional[OperationalMode]:
        """Get previous operational mode."""
        return self._previous_mode

    @property
    def mode_name(self) -> str:
        """Get current mode name as string."""
        return self._current_mode.name

    def is_mode(self, mode: OperationalMode) -> bool:
        """
        Check if currently in specified mode.

        Args:
            mode: Mode to check

        Returns:
            True if in specified mode
        """
        return self._current_mode == mode

    def can_transition_to(self, target_mode: OperationalMode) -> bool:
        """
        Check if transition to target mode is allowed.

        Args:
            target_mode: Desired mode

        Returns:
            True if transition is allowed
        """
        allowed = self.ALLOWED_TRANSITIONS.get(self._current_mode, [])
        return target_mode in allowed

    async def transition_to(
        self,
        target_mode: OperationalMode,
        reason: str = "",
        triggered_by: str = "system"
    ) -> bool:
        """
        Transition to a new operational mode.

        Args:
            target_mode: Desired operational mode
            reason: Reason for transition
            triggered_by: Who triggered the transition ('operator', 'system', 'emergency')

        Returns:
            True if transition successful, False otherwise
        """
        async with self._lock:
            # Check if transition is allowed
            if not self.can_transition_to(target_mode):
                logger.warning(
                    f"Transition from {self._current_mode.name} to {target_mode.name} "
                    f"is not allowed"
                )
                return False

            # Same state transition is a no-op
            if self._current_mode == target_mode:
                logger.debug(f"Already in {target_mode.name} mode, ignoring transition")
                return True

            # Record transition
            transition = StateTransition(
                from_state=self._current_mode,
                to_state=target_mode,
                timestamp=datetime.now(),
                reason=reason,
                triggered_by=triggered_by
            )

            logger.info(
                f"State transition: {self._current_mode.name} → {target_mode.name} "
                f"(reason: {reason}, triggered by: {triggered_by})"
            )

            # Update state
            self._previous_mode = self._current_mode
            self._current_mode = target_mode
            self._transition_history.append(transition)

            # Trigger callbacks for new state
            await self._trigger_callbacks(target_mode)

            return True

    async def emergency_stop(self, reason: str = "Emergency stop triggered"):
        """
        Emergency stop - immediately transition to EMERGENCY_STOP mode.

        This bypasses normal transition rules for safety.

        Args:
            reason: Reason for emergency stop
        """
        async with self._lock:
            logger.critical(f"EMERGENCY STOP: {reason}")

            transition = StateTransition(
                from_state=self._current_mode,
                to_state=OperationalMode.EMERGENCY_STOP,
                timestamp=datetime.now(),
                reason=reason,
                triggered_by="emergency"
            )

            self._previous_mode = self._current_mode
            self._current_mode = OperationalMode.EMERGENCY_STOP
            self._transition_history.append(transition)

            # Trigger emergency stop callbacks
            await self._trigger_callbacks(OperationalMode.EMERGENCY_STOP)

    def register_callback(self, mode: OperationalMode, callback: Callable):
        """
        Register a callback to be called when entering a specific mode.

        Args:
            mode: Operational mode
            callback: Async callable to execute on mode entry
        """
        if mode not in self._callbacks:
            self._callbacks[mode] = []

        self._callbacks[mode].append(callback)
        logger.debug(f"Registered callback for {mode.name} mode")

    async def _trigger_callbacks(self, mode: OperationalMode):
        """
        Trigger all callbacks for a specific mode.

        Args:
            mode: Operational mode that was entered
        """
        callbacks = self._callbacks.get(mode, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(mode)
                else:
                    callback(mode)
            except Exception as e:
                logger.error(f"Error executing callback for {mode.name}: {e}")

    def get_transition_history(self, limit: Optional[int] = None) -> list[StateTransition]:
        """
        Get transition history.

        Args:
            limit: Maximum number of transitions to return (most recent first)

        Returns:
            List of state transitions
        """
        history = list(reversed(self._transition_history))
        if limit:
            return history[:limit]
        return history

    def get_mode_duration(self) -> float:
        """
        Get duration in current mode (seconds).

        Returns:
            Seconds in current mode
        """
        if not self._transition_history:
            return 0.0

        last_transition = self._transition_history[-1]
        duration = (datetime.now() - last_transition.timestamp).total_seconds()
        return duration

    def is_operational(self) -> bool:
        """
        Check if system is in an operational mode (not initializing, shutdown, or emergency).

        Returns:
            True if in operational mode
        """
        operational_modes = [
            OperationalMode.AUTONOMOUS,
            OperationalMode.SEMI_AUTONOMOUS,
            OperationalMode.REMOTE_CONTROL,
            OperationalMode.MAINTENANCE,
        ]
        return self._current_mode in operational_modes

    def requires_operator_approval(self) -> bool:
        """
        Check if current mode requires operator approval for decisions.

        Returns:
            True if operator approval required
        """
        return self._current_mode == OperationalMode.SEMI_AUTONOMOUS

    def is_autonomous(self) -> bool:
        """
        Check if in fully autonomous mode.

        Returns:
            True if in autonomous mode
        """
        return self._current_mode == OperationalMode.AUTONOMOUS

    def is_remote_controlled(self) -> bool:
        """
        Check if in remote control mode.

        Returns:
            True if in remote control mode
        """
        return self._current_mode == OperationalMode.REMOTE_CONTROL

    def is_emergency_stopped(self) -> bool:
        """
        Check if in emergency stop mode.

        Returns:
            True if emergency stopped
        """
        return self._current_mode == OperationalMode.EMERGENCY_STOP

    def get_state_info(self) -> Dict[str, Any]:
        """
        Get comprehensive state information.

        Returns:
            Dictionary with current state information
        """
        return {
            'current_mode': self._current_mode.name,
            'previous_mode': self._previous_mode.name if self._previous_mode else None,
            'mode_duration': self.get_mode_duration(),
            'is_operational': self.is_operational(),
            'requires_operator_approval': self.requires_operator_approval(),
            'transition_count': len(self._transition_history),
            'last_transition': {
                'to_state': self._transition_history[-1].to_state.name,
                'timestamp': self._transition_history[-1].timestamp.isoformat(),
                'reason': self._transition_history[-1].reason,
                'triggered_by': self._transition_history[-1].triggered_by,
            } if self._transition_history else None
        }

    def __str__(self) -> str:
        """String representation of state machine."""
        return f"StateMachine(mode={self._current_mode.name}, operational={self.is_operational()})"

    def __repr__(self) -> str:
        """Developer representation of state machine."""
        return (
            f"StateMachine(current={self._current_mode.name}, "
            f"previous={self._previous_mode.name if self._previous_mode else 'None'}, "
            f"transitions={len(self._transition_history)})"
        )
