"""Locomotion control modules for hexapod."""

from .ik_solver_wrapper import IKSolver, Position3D, JointAngles, LegDimensions
from .servo_controller import ServoController  # Legacy PCA9685
from .maestro_controller import MaestroController  # Pololu Maestro
from .gait_controller import GaitController

__all__ = [
    'IKSolver',
    'Position3D',
    'JointAngles',
    'LegDimensions',
    'ServoController',
    'MaestroController',
    'GaitController',
]
