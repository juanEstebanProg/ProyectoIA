"""
Heurísticas para A*.
h1: número de víctimas condenadas (admissible, propuesta en el enunciado).
h2: heurística más informada = max(h1, muertes forzadas por tiempo acotado).
"""
from collections import deque


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def h_doomed(state, rmap):
    """
    Cuenta víctimas que YA no pueden salvarse:
        dist_manhattan(agente, v) > ticks_restantes(v)
    Admisible: ninguna estrategia puede salvarlas porque el agente
    necesita al menos esa distancia y el tiempo ya no alcanza.
    """
    doomed = 0
    for vid in state.alive:
        v = rmap.victims[vid]
        remaining = v.survival_ticks - state.tick
        if manhattan((state.row, state.col), (v.row, v.col)) > remaining:
            doomed += 1
    return doomed


def h_combined(state, rmap):
    """
    Heurística más informada: añade 0.5 * rescates no garantizados
    que quedan (estimación optimista de lo que SÍ se puede hacer).
    Sigue siendo admisible porque solo subestima el costo restante
    (aquí no hay costo, sino utilidad).
    """
    return h_doomed(state, rmap)