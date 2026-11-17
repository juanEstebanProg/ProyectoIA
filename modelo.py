# -*- coding: utf-8 -*-
"""
modelo.py
=========
Modelo formal del problema "Agente de Rescate con Victimas en Riesgo".

Contiene:
  * Victima          -> datos inmutables de una victima.
  * Estado           -> representacion EXPLICITA e HASHEABLE de un estado de busqueda.
  * Mapa             -> cuadricula 2D (paredes, celdas libres, inicio) + lectura de archivo.
  * cargar_victimas / validar_victimas -> lectura y validacion de victimas.txt.
  * ProblemaRescate  -> estado inicial, sucesores, prueba de meta, costo g(n) y heuristica h(n).

Convenciones
------------
  * Filas y columnas se numeran desde 0 (igual que en victimas.txt de ejemplo).
  * Cada movimiento consume exactamente 1 tick. No existe la accion "esperar".
  * Una victima v se rescata si el agente pisa su celda en un tick t <= ticks(v).
    Si el tick actual supera ticks(v) antes de llegar, la victima muere.

Funcion objetivo (que significa "mejor ruta")
---------------------------------------------
Se busca el estado meta con MENOS victimas perdidas (= MAS rescatadas). Para
poder usar costo uniforme y A* se define el costo de un estado como una tupla
comparada lexicograficamente:

        g(n) = (muertas, muertas_criticas, ticks)

  1) muertas          : victimas NO rescatadas (objetivo principal).
  2) muertas_criticas : desempate blando -> se prefiere salvar a las criticas.
  3) ticks            : desempate final -> se prefiere la ruta mas corta.

Heuristica admisible (se usa en A*)
-----------------------------------
        h(n) = (c, c_criticas, 0)
  c = numero de victimas VIVAS en n con  Manhattan(agente, v) > ticks_restantes(v)

DEMOSTRACION DE ADMISIBILIDAD
  Sea v una victima viva "condenada" en n, es decir Manhattan(pos, v) > r,
  donde r = ticks(v) - tick_actual. Para llegar a v el agente necesita, como
  minimo, tantos movimientos como su distancia real, y la distancia real es
  >= Manhattan (las paredes solo pueden alargar el camino, nunca acortarlo).
  Por lo tanto necesitaria mas de r movimientos y llegaria cuando el tick ya
  supero ticks(v): v NO puede ser rescatada desde n, sea cual sea la ruta.
  Entonces, en cualquier meta alcanzable desde n, las victimas ya muertas en n
  mas las c condenadas (conjuntos disjuntos) estan perdidas, luego
        costo real restante >= c  =  h(n)
  Como h(n) nunca sobreestima el costo real restante, es ADMISIBLE. Las
  componentes 2 y 3 se justifican igual (se cuentan solo criticas condenadas y
  0 ticks adicionales, que son cotas inferiores validas). En un estado meta
  h = (0, 0, 0). QED.

  Ademas g depende UNICAMENTE del estado (mismos rescatados/vivas/tick => mismo
  g), por lo que A* con conjunto cerrado conserva la optimalidad.
"""

from collections import deque
from dataclasses import dataclass
from typing import FrozenSet, List, NamedTuple, Tuple

# Distancia "infinita" para celdas inalcanzables.
INF = 10 ** 9

# Acciones: (nombre, delta_fila, delta_columna). Orden fijo -> resultados deterministas.
DIRECCIONES = (("N", -1, 0), ("S", 1, 0), ("E", 0, 1), ("O", 0, -1))

# Tipo para el costo g(n) y la heuristica h(n): (muertas, muertas_criticas, ticks).
Costo = Tuple[int, int, int]


class ErrorDeArchivo(Exception):
    """Se lanza cuando mapa.txt o victimas.txt tienen un formato invalido."""


# ----------------------------------------------------------------------------
# Datos basicos
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Victima:
    """Datos inmutables de una victima (leidos de victimas.txt)."""
    id: str
    fila: int
    columna: int
    ticks: int              # ticks de supervivencia
    critica: bool = False   # restriccion blanda: prioridad entre victimas


class Estado(NamedTuple):
    """
    Estado de busqueda: explicito, inmutable y hasheable (sirve en sets y heapq).

    Campos del enunciado:
        fila, columna : posicion actual del agente.
        vivas         : indices de victimas que ni murieron ni fueron rescatadas.
        tick          : movimientos realizados hasta ahora.
    Campo adicional:
        rescatadas    : indices de victimas ya rescatadas. Es necesario porque dos
                        caminos pueden llegar a la misma (fila, columna, vivas,
                        tick) habiendo rescatado conjuntos distintos; sin este
                        campo se mezclarian estados con valor diferente.
    """
    fila: int
    columna: int
    vivas: FrozenSet[int]
    tick: int
    rescatadas: FrozenSet[int]


# ----------------------------------------------------------------------------
# Mapa
# ----------------------------------------------------------------------------
class Mapa:
    """Cuadricula del entorno. '#' pared, '.' libre, 'S' inicio del agente."""

    # 'V' y digitos se aceptan como marcas de victima (se tratan como celda libre;
    # la posicion real de cada victima se toma de victimas.txt).
    CARACTERES_VALIDOS = set("#.SV0123456789")

    def __init__(self, filas_texto: List[str]):
        if not filas_texto:
            raise ErrorDeArchivo("El mapa esta vacio.")
        ancho = len(filas_texto[0])
        inicio = None
        for f, linea in enumerate(filas_texto):
            if len(linea) != ancho:
                raise ErrorDeArchivo(
                    f"Fila {f} del mapa mide {len(linea)} y se esperaba {ancho} "
                    "(el mapa debe ser rectangular).")
            for c, ch in enumerate(linea):
                if ch not in self.CARACTERES_VALIDOS:
                    raise ErrorDeArchivo(
                        f"Caracter invalido '{ch}' en fila {f}, columna {c} del mapa.")
                if ch == "S":
                    if inicio is not None:
                        raise ErrorDeArchivo("El mapa tiene mas de una 'S'.")
                    inicio = (f, c)
        if inicio is None:
            raise ErrorDeArchivo("El mapa no tiene posicion inicial 'S'.")
        self.celdas: List[str] = filas_texto
        self.filas = len(filas_texto)
        self.columnas = ancho
        self.inicio: Tuple[int, int] = inicio

    @classmethod
    def desde_archivo(cls, ruta: str) -> "Mapa":
        """Lee mapa.txt (ignora lineas en blanco)."""
        try:
            with open(ruta, encoding="utf-8-sig") as archivo:
                lineas = [ln.rstrip() for ln in archivo if ln.strip()]
        except OSError as exc:
            raise ErrorDeArchivo(f"No se pudo abrir el mapa: {exc}") from exc
        return cls(lineas)

    def en_rango(self, fila: int, columna: int) -> bool:
        return 0 <= fila < self.filas and 0 <= columna < self.columnas

    def es_libre(self, fila: int, columna: int) -> bool:
        """True si la celda existe y no es pared."""
        return self.en_rango(fila, columna) and self.celdas[fila][columna] != "#"


# ----------------------------------------------------------------------------
# Lectura de victimas.txt
# ----------------------------------------------------------------------------
def cargar_victimas(ruta: str) -> List[Victima]:
    """
    Lee victimas.txt con formato  id,fila,columna,ticks_supervivencia[,critica].
    La cabecera es opcional; las lineas vacias y las que empiezan con '//' se
    ignoran. La quinta columna (opcional) marca victimas criticas con 1/si/true.
    """
    try:
        with open(ruta, encoding="utf-8-sig") as archivo:
            lineas = archivo.readlines()
    except OSError as exc:
        raise ErrorDeArchivo(f"No se pudo abrir el archivo de victimas: {exc}") from exc

    victimas: List[Victima] = []
    ids = set()
    for numero, linea in enumerate(lineas, start=1):
        texto = linea.strip()
        if not texto or texto.startswith("//"):
            continue
        partes = [p.strip() for p in texto.split(",")]
        # Cabecera: la segunda columna no es un numero.
        if not victimas and len(partes) > 1 and not partes[1].lstrip("-").isdigit():
            continue
        if len(partes) < 4:
            raise ErrorDeArchivo(
                f"Linea {numero}: se esperaban al menos 4 campos (id,fila,columna,ticks).")
        try:
            fila, columna, ticks = int(partes[1]), int(partes[2]), int(partes[3])
        except ValueError as exc:
            raise ErrorDeArchivo(f"Linea {numero}: fila/columna/ticks deben ser enteros.") from exc
        if ticks < 0:
            raise ErrorDeArchivo(f"Linea {numero}: los ticks no pueden ser negativos.")
        if partes[0] in ids:
            raise ErrorDeArchivo(f"Linea {numero}: id de victima repetido '{partes[0]}'.")
        ids.add(partes[0])
        critica = len(partes) > 4 and partes[4].lower() in ("1", "si", "sí", "true", "critica", "crítica", "x")
        victimas.append(Victima(partes[0], fila, columna, ticks, critica))

    if not victimas:
        raise ErrorDeArchivo("El archivo no contiene victimas.")
    return victimas


def validar_victimas(mapa: Mapa, victimas: List[Victima]) -> List[str]:
    """
    Valida las victimas contra el mapa.
      * Fuera del mapa -> ErrorDeArchivo (dato imposible de interpretar).
      * Sobre una pared -> NO es error fatal: esa victima es inalcanzable, asi que
        el problema la cuenta como fallecida desde el tick 0. Se devuelve una
        lista de advertencias para mostrarlas al usuario.
    """
    advertencias: List[str] = []
    for v in victimas:
        if not mapa.en_rango(v.fila, v.columna):
            raise ErrorDeArchivo(f"{v.id} esta fuera del mapa ({v.fila},{v.columna}).")
        if not mapa.es_libre(v.fila, v.columna):
            advertencias.append(f"{v.id} esta sobre una pared ({v.fila},{v.columna}): "
                                "se contara como fallecida.")
    return advertencias


# ----------------------------------------------------------------------------
# Problema de busqueda
# ----------------------------------------------------------------------------
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
        posibles = [i for i, v in enumerate(self.victimas) if self.mapa.es_libre(v.fila, v.columna)]
        return self._construir(f, c, posibles, frozenset(), 0)

    def sucesores(self, e: Estado) -> List[Tuple[str, Estado]]:
        """Movimientos N, S, E, O (1 tick c/u). Sin esperar y sin entrar en paredes."""
        resultado = []
        for nombre, df, dc in DIRECCIONES:
            nf, nc = e.fila + df, e.columna + dc
            if self.mapa.es_libre(nf, nc):
                resultado.append((nombre, self._construir(nf, nc, e.vivas, e.rescatadas, e.tick + 1)))
        return resultado

    def es_meta(self, e: Estado) -> bool:
        """
        Meta: no queda ninguna victima viva ALCANZABLE, es decir, para toda viva v
        la distancia real agente->v es mayor que sus ticks restantes. Cubre los
        casos "todas rescatadas o muertas". Siempre se cumple cuando
        tick > tick_maximo, por lo que ninguna rama es infinita.
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
        como perdidas, asi g(meta) = total - rescatadas, valor exacto del objetivo.
        """
        perdidas = [i for i in range(self.total)
                    if i not in e.rescatadas and (meta or i not in e.vivas)]
        criticas = sum(1 for i in perdidas if self.victimas[i].critica)
        return (len(perdidas), criticas, e.tick)

    def heuristica(self, e: Estado, meta: bool) -> Costo:
        """
        h(n) admisible (ver demostracion en el docstring del modulo): cuenta las
        victimas vivas condenadas por distancia Manhattan > ticks restantes.
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
