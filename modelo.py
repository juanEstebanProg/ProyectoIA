"""
Representación del problema de búsqueda.
Estado = (fila, columna, frozenset_vivas, tick_actual)
"""
from dataclasses import dataclass
from typing import FrozenSet, Tuple

WALL = '#'
FREE = '.'
START = 'S'


@dataclass(frozen=True)
class Victim:
    """Víctima inmutable y hasheable."""
    vid: int
    row: int
    col: int
    survival_ticks: int
    critical: bool = False   # restricción blanda


@dataclass(frozen=True)
class State:
    """
    Estado hasheable del agente.
    - (row, col): posición actual
    - alive: frozenset de IDs de víctimas aún vivas (ni rescatadas ni muertas)
    - tick: ticks transcurridos (== costo g)
    - rescued: frozenset de IDs rescatadas (para reconstruir solución)
    """
    row: int
    col: int
    alive: FrozenSet[int]
    tick: int
    rescued: FrozenSet[int] = frozenset()

    def key(self) -> Tuple:
        """Clave para conjuntos visitados."""
        return (self.row, self.col, self.alive, self.tick)


class RescueMap:
    """Cuadrícula del entorno + índice de víctimas."""

    def __init__(self, grid, victims, start):
        self.grid = grid                    # lista de listas de chars
        self.rows = len(grid)
        self.cols = len(grid[0])
        self.victims = victims              # dict id -> Victim
        self.victims_by_pos = {(v.row, v.col): v for v in victims.values()}
        self.start = start                  # (row, col)

    def is_wall(self, r, c):
        return (r < 0 or r >= self.rows or c < 0 or c >= self.cols
                or self.grid[r][c] == WALL)

    def neighbors(self, r, c):
        """4 direcciones cardinales, filtrando paredes."""
        for dr, dc in ((-1, 0), (1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if not self.is_wall(nr, nc):
                yield nr, nc