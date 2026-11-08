"""
Implementación desde cero de BFS, UCS, IDDFS y A*.
El objetivo NO es llegar a un nodo meta fijo, sino maximizar rescates
hasta que NINGUNA víctima viva sea alcanzable a tiempo.
"""
import heapq
import time
from collections import deque
from modelo import State
from heuristica import h_doomed
MAX_NODES = 50000   # Límite máximo de nodos a explorar
MAX_TIME = 30.0      # Límite de tiempo en segundos por algoritmo

# ---------- utilidades comunes ----------
def _successors(state, rmap):
    """
    Expande movimientos. Retorna lista (next_state, rescued_count_delta).
    Reglas duras:
      - no atravesar paredes
      - al pisar una víctima viva con tick_actual <= supervivencia -> rescate
      - si tick_actual > supervivencia -> la víctima muere (sale de alive)
    Nota: el tick del nuevo estado = state.tick + 1.
    """
    nt = state.tick + 1
    succ = []
    for nr, nc in rmap.neighbors(state.row, state.col):
        alive = set(state.alive)
        rescued = set(state.rescued)
        # 1) actualizar muertes por paso del tiempo (víctimas que expiran
        #    sin que el agente las pise)
        for vid in list(alive):
            v = rmap.victims[vid]
            if nt > v.survival_ticks and (nr, nc) != (v.row, v.col):
                # muere sola si ya expiró y el agente no la pisa justo ahora
                # (si la pisa ahora, también muere, ver abajo)
                pass
        # 2) intentar rescate en la celda destino
        v_at = rmap.victims_by_pos.get((nr, nc))
        if v_at and v_at.vid in alive:
            if nt <= v_at.survival_ticks:
                alive.discard(v_at.vid)
                rescued.add(v_at.vid)
            else:
                alive.discard(v_at.vid)   # llega tarde -> muere
        # 3) víctimas que expiran este tick (no pisadas)
        for vid in list(alive):
            v = rmap.victims[vid]
            if nt > v.survival_ticks:
                alive.discard(vid)        # murió por tiempo
        succ.append(State(nr, nc, frozenset(alive), nt, frozenset(rescued)))
    return succ


def _terminal(state):
    """Estado objetivo: no quedan víctimas vivas."""
    return len(state.alive) == 0


def _score(state):
    return len(state.rescued)


# ---------- BFS ----------
def bfs(rmap, max_nodes=MAX_NODES, max_time=MAX_TIME):
    start = State(rmap.start[0], rmap.start[1], frozenset(rmap.victims.keys()), 0, frozenset())
    t0 = time.time()
    frontier = deque([start])
    visited = {start.key()}
    nodes = 0
    best = start
    limit_reached = False

    while frontier:
        # CONDICIONES DE PARADA
        if nodes >= max_nodes or (time.time() - t0) > max_time:
            limit_reached = True
            break

        s = frontier.popleft()
        nodes += 1
        if _score(s) > _score(best):
            best = s
        if _terminal(s):
            break
            
        for ns in _successors(s, rmap):
            if ns.key() not in visited:
                visited.add(ns.key())
                frontier.append(ns)
                
    return best, nodes, time.time() - t0, limit_reached


# ---------- UCS (costo uniforme = menos ticks primero) ----------
def ucs(rmap, max_nodes=MAX_NODES, max_time=MAX_TIME):
    start = State(rmap.start[0], rmap.start[1], frozenset(rmap.victims.keys()), 0, frozenset())
    t0 = time.time()
    pq = [(0, 0, start)]     
    counter = 0
    visited = {}
    nodes = 0
    best = start
    limit_reached = False

    while pq:
        # CONDICIONES DE PARADA
        if nodes >= max_nodes or (time.time() - t0) > max_time:
            limit_reached = True
            break

        g, _, s = heapq.heappop(pq)
        if s.key() in visited and visited[s.key()] <= g:
            continue
        visited[s.key()] = g
        nodes += 1
        if _score(s) > _score(best):
            best = s
        if _terminal(s):
            break
        for ns in _successors(s, rmap):
            counter += 1
            heapq.heappush(pq, (ns.tick, counter, ns))
            
    return best, nodes, time.time() - t0, limit_reached


# ---------- IDDFS ----------
def _dls(state, rmap, limit, visited, counter_box):
    """Búsqueda en profundidad con límite; devuelve mejor estado encontrado."""
    counter_box[0] += 1
    if _terminal(state) or state.tick >= limit:
        return state
    best = state
    for ns in _successors(state, rmap):
        if ns.key() in visited:
            continue
        visited.add(ns.key())
        cand = _dls(ns, rmap, limit, visited, counter_box)
        if _score(cand) > _score(best):
            best = cand
        visited.discard(ns.key())
    return best


def iddfs(rmap, max_depth=40):
    start = State(rmap.start[0], rmap.start[1],
                  frozenset(rmap.victims.keys()), 0, frozenset())
    t0 = time.time()
    nodes = 0
    best = start
    for depth in range(0, max_depth + 1):
        box = [0]
        cand = _dls(start, rmap, depth, {start.key()}, box)
        nodes += box[0]
        if _score(cand) > _score(best):
            best = cand
        if _terminal(best):
            break
    return best, nodes, time.time() - t0


# ---------- A* ----------
"""
    f = g + h  (minimización) pero nuestro objetivo es MAXIMIZAR rescates.
    Reformulamos: f(n) = tick(n) + h_doomed(n) - k*rescued(n)
    Usamos heapq con f como costo; el criterio de parada acepta
    el mejor estado cuando se agota la frontera o se alcanza terminal.
"""
def astar(rmap, max_nodes=MAX_NODES, max_time=MAX_TIME):
    start = State(rmap.start[0], rmap.start[1], frozenset(rmap.victims.keys()), 0, frozenset())
    t0 = time.time()
    counter = 0
    h0 = h_doomed(start, rmap) - 3 * _score(start)
    pq = [(start.tick + h0, counter, start)]
    best_g = {}
    nodes = 0
    best = start
    limit_reached = False

    while pq:
        # CONDICIONES DE PARADA
        if nodes >= max_nodes or (time.time() - t0) > max_time:
            limit_reached = True
            break

        _, _, s = heapq.heappop(pq)
        if s.key() in best_g:
            continue
        best_g[s.key()] = s.tick
        nodes += 1
        if _score(s) > _score(best):
            best = s
        if _terminal(s):
            break
        for ns in _successors(s, rmap):
            if ns.key() in best_g:
                continue
            counter += 1
            f = ns.tick + h_doomed(ns, rmap) - 3 * _score(ns)
            heapq.heappush(pq, (f, counter, ns))
            
    return best, nodes, time.time() - t0, limit_reached