"""
===========
ProblemaRescate: define el espacio de estados que recorren BFS, UCS, IDDFS y A*.
Contiene: estado inicial, sucesores, prueba de meta, costo g(n) y heuristica h(n).
"""
from collections import deque
from typing import List, Tuple

from estado import Costo, Estado
from mapa import Mapa
from victima import Victima

# Distancia "infinita" para celdas inalcanzables.
INF = 10 ** 9

# Acciones: (nombre, delta_fila, delta_columna). Orden fijo -> resultados deterministas.
DIRECCIONES = (("N", -1, 0), ("S", 1, 0), ("E", 0, 1), ("O", 0, -1))


class ProblemaRescate:
    """Define el espacio de estados que recorren BFS, UCS, IDDFS y A*."""

    def __init__(self, mapa: Mapa, victimas: List[Victima]):
        self.mapa = mapa
        self.victimas = tuple(victimas)
        self.total = len(self.victimas)
        self.total_criticas = sum(1 for v in self.victimas if v.critica)
        # Pasado este tick TODAS las victimas estan muertas -> cota de profundidad.
        self.tick_maximo = max(v.ticks for v in self.victimas) + 1
        # Distancias reales (con paredes) desde cada victima a cada celda.
        # Solo se usan para la prueba de meta ("alcanzable"), no en A*.
        self._distancias = [self._distancias_desde(v.fila, v.columna) for v in self.victimas]

    # -- utilidades -----------------------------------------------------------
    def _distancias_desde(self, fila: int, columna: int) -> List[List[int]]:
        """BFS sobre la cuadricula: distancia real de (fila, columna) a cada celda."""
        dist = [[INF] * self.mapa.columnas for _ in range(self.mapa.filas)]
        if not self.mapa.es_libre(fila, columna):
            return dist                        # victima en una pared: inalcanzable
        dist[fila][columna] = 0
        cola = deque([(fila, columna)])
        while cola:
            f, c = cola.popleft()
            for _, df, dc in DIRECCIONES:
                nf, nc = f + df, c + dc
                if self.mapa.es_libre(nf, nc) and dist[nf][nc] == INF:
                    dist[nf][nc] = dist[f][c] + 1
                    cola.append((nf, nc))
        return dist

    def _construir(self, fila, columna, candidatas, rescatadas, tick) -> Estado:
        """
        Crea el estado resultante de que el agente este en (fila, columna) en `tick`:
          1) la victima cuya celda se pisa y sigue viva (tick <= ticks) se rescata;
          2) las victimas cuyo tiempo ya se agoto (tick > ticks) mueren;
          3) el resto sigue viva.
        """
        vivas, resc = set(), set(rescatadas)
        for i in candidatas:
            v = self.victimas[i]
            if tick > v.ticks:
                continue                       # murio
            if v.fila == fila and v.columna == columna:
                resc.add(i)                    # rescatada al pisar su celda
            else:
                vivas.add(i)
        return Estado(fila, columna, frozenset(vivas), tick, frozenset(resc))

    # -- interfaz del problema -----------------------------------------------
    def estado_inicial(self) -> Estado:
        """Agente en S, todas las victimas vivas, tick = 0."""
        f, c = self.mapa.inicio
        # Las victimas situadas sobre una pared nunca podran rescatarse: nacen muertas.
        posibles = [i for i, v in enumerate(self.victimas)
                    if self.mapa.es_libre(v.fila, v.columna)]
        return self._construir(f, c, posibles, frozenset(), 0)

    def sucesores(self, e: Estado) -> List[Tuple[str, Estado]]:
        """Movimientos N, S, E, O (1 tick c/u). Sin esperar y sin entrar en paredes."""
        resultado = []
        for nombre, df, dc in DIRECCIONES:
            nf, nc = e.fila + df, e.columna + dc
            if self.mapa.es_libre(nf, nc):
                resultado.append((nombre, self._construir(nf, nc, e.vivas,
                                                         e.rescatadas, e.tick + 1)))
        return resultado

    def es_meta(self, e: Estado) -> bool:
        """
        Meta: no queda ninguna victima viva ALCANZABLE, es decir, para toda viva v
        la distancia real agente->v es mayor que sus ticks restantes.
        Siempre se cumple cuando tick > tick_maximo -> ninguna rama es infinita.
        """
        for i in e.vivas:
            restantes = self.victimas[i].ticks - e.tick
            if self._distancias[i][e.fila][e.columna] <= restantes:
                return False
        return True

    def costo_g(self, e: Estado, meta: bool) -> Costo:
        """
        g(n) = (muertas, muertas_criticas, ticks). Es funcion solo del estado.
        En un estado meta las victimas vivas restantes (inalcanzables) cuentan
        como perdidas, asi g(meta) = total - rescatadas.
        """
        perdidas = [i for i in range(self.total)
                    if i not in e.rescatadas and (meta or i not in e.vivas)]
        criticas = sum(1 for i in perdidas if self.victimas[i].critica)
        return (len(perdidas), criticas, e.tick)

    def heuristica(self, e: Estado, meta: bool) -> Costo:
        """
        h(n) admisible: cuenta victimas vivas condenadas
        (Manhattan > ticks restantes). Ver demostracion en el informe.
        """
        if meta:
            return (0, 0, 0)
        condenadas = criticas = 0
        for i in e.vivas:
            v = self.victimas[i]
            if abs(e.fila - v.fila) + abs(e.columna - v.columna) > v.ticks - e.tick:
                condenadas += 1
                criticas += 1 if v.critica else 0
        return (condenadas, criticas, 0)

    def clave_progreso(self, e: Estado) -> Tuple[int, int, int]:
        """Orden (menor = mejor) para elegir el mejor estado PARCIAL si se agota el tiempo."""
        criticas = sum(1 for i in e.rescatadas if self.victimas[i].critica)
        return (-len(e.rescatadas), -criticas, e.tick)