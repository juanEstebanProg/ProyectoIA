"""
modelo.py
=========
Modelo formal del problema "Agente de Rescate con Victimas en Riesgo".

Contiene:
  * Victima          -> datos inmutables de una victima.
  * Estado           -> representacion EXPLICITA e HASHEABLE de un estado de busqueda.
  * Mapa             -> cuadricula 2D (paredes, celdas libres, inicio) + lectura de archivo.
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
from heuristica import calcular_heuristica

# Distancia "infinita" para celdas inalcanzables.
# Usamos un entero grande en vez de float('inf') para mantener las comparaciones
# simples y rapidas (no mezclamos int con float en la matriz de distancias)
INF = 10 ** 9

# Acciones: (nombre, delta_fila, delta_columna). Orden fijo -> resultados deterministas.
DIRECCIONES = (("N", -1, 0), ("S", 1, 0), ("E", 0, 1), ("O", 0, -1))

# Tipo para el costo g(n) y la heuristica h(n): (muertas, muertas_criticas, ticks).
Costo = Tuple[int, int, int]

# Excepcion para que la interfaz pueda distinguir un error de archivo
# de cualquier otro error inesperado del programa.
class ErrorDeArchivo(Exception):
    """Se lanza cuando mapa.txt o victimas.txt tienen un formato invalido."""


# ----------------------------------------------------------------------------
# Datos basicos
# ----------------------------------------------------------------------------
#El frozen=t hace que la instancia sea inmutable, es decir, una vez que se crea, ya no se
#puede modificar. Debido a que la victima nunca cambia (los estados si cambian pero eso
#se guarda en la clase "Estado")
@dataclass(frozen=True)
class Victima:
    """Datos inmutables de una victima (leidos de victimas.txt)."""
    id: str
    fila: int
    columna: int
    ticks: int              # ticks de supervivencia
    critica: bool = False   # restriccion blanda: prioridad entre victimas

#"NadmedTuple" nos da inmutabilidad, hash automatico y acceso por nombre (e.fila en vez de e[0])
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
    vivas: FrozenSet[int] #frozenset: porque es hasheable e inmutable (es obligatorio para meter el Estado en un set)
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
        #validamos el mapa completo antes de construir, y en caso de haber un error se lanza ErrorDeArchivo
        # y la interfaz lo muestra
        if not filas_texto:
            raise ErrorDeArchivo("El mapa esta vacio.")
        ancho = len(filas_texto[0])
        inicio = None
        for f, linea in enumerate(filas_texto):
            #El mapa debe ser rectangular, todas las filas deben tener el mismo ancho
            if len(linea) != ancho:
                raise ErrorDeArchivo(
                    f"Fila {f} del mapa mide {len(linea)} y se esperaba {ancho} "
                    "(el mapa debe ser rectangular).")
            for c, ch in enumerate(linea):
                #solo se aceptan caracteres conocidos (los que están en "CARACTERES_VALIDOS"), si se pone uno
                #que no esté ahi, genera error
                if ch not in self.CARACTERES_VALIDOS:
                    raise ErrorDeArchivo(
                        f"Caracter invalido '{ch}' en fila {f}, columna {c} del mapa.")
                if ch == "S":
                    #tiene que haber exactamente una S en la posición inicial
                    if inicio is not None:
                        raise ErrorDeArchivo("El mapa tiene mas de una 'S'.")
                    inicio = (f, c)
        if inicio is None:
            raise ErrorDeArchivo("El mapa no tiene posicion inicial 'S'.")
        #se guarda el mapa y sus dimensiones
        self.celdas: List[str] = filas_texto
        self.filas = len(filas_texto)
        self.columnas = ancho
        self.inicio: Tuple[int, int] = inicio


    def en_rango(self, fila: int, columna: int) -> bool:
        #Comprueba que la celda exista dentro del mapa
        return 0 <= fila < self.filas and 0 <= columna < self.columnas

    def es_libre(self, fila: int, columna: int) -> bool:
        """True si la celda existe y no es pared."""
        #Primero verificamos el rango para no acceder fuera de la lista y luego verificamos que no sea pared
        return self.en_rango(fila, columna) and self.celdas[fila][columna] != "#"



# ----------------------------------------------------------------------------
# Problema de busqueda
# ----------------------------------------------------------------------------
class ProblemaRescate:
    """Define el espacio de estados que recorren BFS, UCS, IDDFS y A*."""

    def __init__(self, mapa: Mapa, victimas: List[Victima]):
        self.mapa = mapa
        #Converte la lista de objetos "victimas" en una tupla y la guarda en self.victimas, esto con el fin de volverla inmutable
        self.victimas = tuple(victimas)
        self.total = len(self.victimas)
        self.total_criticas = sum(1 for v in self.victimas if v.critica)
        # Pasado este tick TODAS las victimas estan muertas -> cota de profundidad.
        #Se le suma +1 porque en el tick que es igual a max(ticks) la victima con
        #mayor supervivencia aún sigue viva
        self.tick_maximo = max(v.ticks for v in self.victimas) + 1
        # Distancias reales (con paredes) desde cada victima a cada celda.
        # Solo se usan para la prueba de meta ("alcanzable"), no en A*.
        self._distancias = [self._distancias_desde(v.fila, v.columna) for v in self.victimas]

    # -- utilidades -----------------------------------------------------------
    def _distancias_desde(self, fila: int, columna: int) -> List[List[int]]:
        """BFS sobre la cuadricula: distancia real de (fila, columna) a cada celda."""
        #matriz de distancias inicializada con INF (significa "todavia no visitado")
        #el BFS irá reemplazando a estos valores por la distancia real desde el origen a cada celda.
        #las celdas no alcanzables como paredes se quedarán con INF al final
        dist = [[INF] * self.mapa.columnas for _ in range(self.mapa.filas)]
        if not self.mapa.es_libre(fila, columna):
            return dist                        # victima en una pared: inalcanzable
        dist[fila][columna] = 0
        cola = deque([(fila, columna)])
        #implementación de BFS
        while cola:
            f, c = cola.popleft()           #saca la celda más antigua (FIFO)
            for _, df, dc in DIRECCIONES:   #prueba las 4 direcciones (N, S, E, O)
                nf, nc = f + df, c + dc     #calcula la celda vecina
                #si hay una celda valida y que aún no ha sido visitada
                if self.mapa.es_libre(nf, nc) and dist[nf][nc] == INF:
                    dist[nf][nc] = dist[f][c] + 1   #se le asigna la distancia con distancia del padre + 1
                    cola.append((nf, nc))           #se agrega a la cola la celda vecina para explorarla despues
        return dist     #retorna la matriz de distancias completa

    def _construir(self, fila, columna, candidatas, rescatadas, tick) -> Estado:
        """
        Crea el estado resultante de que el agente este en (fila, columna) en `tick`:
          1) la victima cuya celda se pisa y sigue viva (tick <= ticks) se rescata;
          2) las victimas cuyo tiempo ya se agoto (tick > ticks) mueren;
          3) el resto sigue viva.
        """
        #es la unica función que agrega estados nuevos
        vivas, resc = set(), set(rescatadas)
        for i in candidatas:
            v = self.victimas[i]
            #si el tiempo ya se agotó antes de este tick, la victima murió
            if tick > v.ticks:
                continue                       # murio
            #si el agente está justo en su celda y sigue viva, se rescata
            if v.fila == fila and v.columna == columna:
                resc.add(i)                    # rescatada al pisar su celda
            #en cualquier otro caso, la victima sigue viva
            else:
                vivas.add(i)
        #se crea una nueva instancia de Estado; vivas y resc se convierten a frozenset para que el Estado sea hasheable
        return Estado(fila, columna, frozenset(vivas), tick, frozenset(resc))

    # -- interfaz del problema -----------------------------------------------
    def estado_inicial(self) -> Estado:
        """Agente en S, todas las victimas vivas, tick = 0."""
        f, c = self.mapa.inicio
        # Las victimas situadas sobre una pared nunca podran rescatarse: nacen muertas.
        # Solo pasamos como candidatas a las victimas que estén en celdas libres
        posibles = [i for i, v in enumerate(self.victimas) if self.mapa.es_libre(v.fila, v.columna)]
        return self._construir(f, c, posibles, frozenset(), 0)

    def sucesores(self, e: Estado) -> List[Tuple[str, Estado]]:
        """Movimientos N, S, E, O (1 tick c/u). Sin esperar y sin entrar en paredes."""
        resultado = []
        for nombre, df, dc in DIRECCIONES:
            #calcula la celda vecina sumando el delta de fila y columna
            nf, nc = e.fila + df, e.columna + dc
            #si la celda existe y no es pared, se genera el sucesor
            if self.mapa.es_libre(nf, nc):
                # Pasamos e.vivas como candidatas: solo las vivas pueden morir o
                # ser rescatadas en el siguiente tick. Las rescatadas se arrastran
                # dentro de _construir a partir de e.rescatadas.
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
             # Cuantos ticks le quedan de vida a esta víctima desde el tick actual.
            restantes = self.victimas[i].ticks - e.tick
            # Si la distancia real desde el agente hasta la víctima es menor o igual
            #a los ticks que le quedan, todavía se puede llegar a tiempo
            if self._distancias[i][e.fila][e.columna] <= restantes:
                #No es meta
                return False
        #si ninguna victima es alcanzable a tiempo, es meta
        return True

    def costo_g(self, e: Estado, meta: bool) -> Costo:
        """
        g(n) = (muertas, muertas_criticas, ticks). Es funcion solo del estado.
        En un estado meta las victimas vivas restantes (inalcanzables) cuentan
        como perdidas, asi g(meta) = total - rescatadas, valor exacto del objetivo.
        """
        #perdidas incluye a las que ya murieron y si el estado es_meta, tambien a las vivas porque
        # se supone que son inalcanzables. En un estado no meta a las vivas no se las cuenta como perdidas
        perdidas = [i for i in range(self.total)
                    if i not in e.rescatadas and (meta or i not in e.vivas)]
        #de las perdidas se cuentan cuantas eran criticas (primer criterio de desempate)
        criticas = sum(1 for i in perdidas if self.victimas[i].critica)
        #el tick es el ultimo criterio de desempate, se prefiere la ruta más corta cuando hay empate de muertes
        return (len(perdidas), criticas, e.tick)

    def heuristica(self, e: Estado, meta: bool) -> Costo:
        """
         Delegamos el cálculo de la heurística a su propio módulo (heuristica.py)
        """
        return calcular_heuristica(e, self, meta)

    def clave_progreso(self, e: Estado) -> Tuple[int, int, int]:
        """Orden (menor = mejor) para elegir el mejor estado PARCIAL si se agota el tiempo."""
        # Se cuenta cuantas de las rescatadas son criticas
        criticas = sum(1 for i in e.rescatadas if self.victimas[i].critica)
        # se retorna la tupla con valores negativos para que se cumpla que menor = mejor
        return (-len(e.rescatadas), -criticas, e.tick)
