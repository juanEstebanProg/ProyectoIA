"""
estado.py
=========
Representacion EXPLICITA, inmutable y hasheable de un estado de busqueda.
"""
from typing import FrozenSet, NamedTuple, Tuple

# Costo g(n) y heuristica h(n): (muertas, muertas_criticas, ticks)
Costo = Tuple[int, int, int]


class Estado(NamedTuple):
    """
    Estado de busqueda. Es un NamedTuple -> inmutable y hasheable,
    por lo que sirve directamente en sets y en heapq.

    Campos:
        fila, columna : posicion actual del agente.
        vivas         : indices de victimas que ni murieron ni fueron rescatadas.
        tick          : movimientos realizados hasta ahora.
        rescatadas    : indices de victimas ya rescatadas.
                        (Necesario: dos caminos pueden llegar a la misma
                        posicion+tick+vivas habiendo rescatado conjuntos
                        distintos; sin este campo se mezclarian estados
                        con valor diferente.)
    """
    fila: int
    columna: int
    vivas: FrozenSet[int]
    tick: int
    rescatadas: FrozenSet[int]