"""Reconstruye la traza de la simulación para la animación."""
from modelo import State


def trace_solution(final_state, rmap):
    """
    Dado un estado final, reconstruye la lista de estados visitados.
    Como no guardamos predecesores explícitos en los 4 algoritmos
    (por simplicidad), recorremos desde el inicio aplicando la misma
    transición hasta llegar al estado final por BFS de reconstrucción.
    """
    from collections import deque
    start = State(rmap.start[0], rmap.start[1],
                  frozenset(rmap.victims.keys()), 0, frozenset())
    if final_state.key() == start.key():
        return [start]
    prev = {start.key(): None}
    states = {start.key(): start}
    q = deque([start])
    from algori import _successors
    while q:
        s = q.popleft()
        for ns in _successors(s, rmap):
            if ns.key() not in prev:
                prev[ns.key()] = s.key()
                states[ns.key()] = ns
                if ns.key() == final_state.key():
                    # reconstruir
                    path = [final_state]
                    k = final_state.key()
                    while prev[k] is not None:
                        k = prev[k]
                        path.append(states[k])
                    return list(reversed(path))
                q.append(ns)
    return [start]