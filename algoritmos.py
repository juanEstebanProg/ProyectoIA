"""
algoritmos.py
=============
Implementacion DESDE CERO (solo biblioteca estandar) de:
    * BFS   -> Busqueda en amplitud            (no informada)
    * UCS   -> Busqueda de costo uniforme      (no informada)
    * IDDFS -> Profundidad iterativa           (no informada)
    * A*    -> Busqueda A* con h admisible     (informada)

Garantias anti-bucle infinito (DOS capas independientes)
--------------------------------------------------------
  1) El espacio de estados es finito: el tick crece 1 por movimiento y pasado
     `tick_maximo` todas las victimas estan muertas (estado meta, no se expande).
     Ademas todos los algoritmos usan conjunto de visitados.
  2) LIMITE DE TIEMPO de 10 s (LIMITE_TIEMPO_SEGUNDOS) para TODOS los algoritmos:
     en cada nodo se consulta el reloj; al vencer, la busqueda se corta y se
     devuelve el mejor resultado encontrado hasta ese momento (con la bandera
     `tiempo_agotado = True`).

Como se elige la "mejor" ruta
-----------------------------
BFS e IDDFS exploran el espacio completo (con visitados) y conservan la mejor
meta vista. UCS y A* usan g(n) = (muertas, criticas_muertas, ticks); la primera
meta que sacan de la cola de prioridad ya es optima.
"""
# heapq: cola de prioridad para UCS y A* (min-heap).
# time: reloj para el limite de 10 s.
# deque: cola FIFO para BFS.
# dataclass/field: para la clase Resultado (sin escribir __init__ a mano).
# typing: solo para anotaciones de tipo
import heapq
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional

from modelo import Estado, ProblemaRescate

# Limite de tiempo aplicado a cada algoritmo (segundos).
LIMITE_TIEMPO_SEGUNDOS = 10.0


# Estructuras de datos auxiliares
class Nodo:
    """Nodo del arbol de busqueda: estado + puntero al padre + accion que lo creo."""
    __slots__ = ("estado", "padre", "accion")

    def __init__(self, estado: Estado, padre: Optional["Nodo"], accion: Optional[str]):
        self.estado = estado
        self.padre = padre #se usa para reconstruir el camino hacia atrás, None solo en la raíz
        self.accion = accion #"N", "S", "E" u "O", es None solo en la raíz


@dataclass
class Resultado:
    """Resumen de una ejecucion de algoritmo (lo consume la interfaz grafica)."""
    algoritmo: str
    camino: List[Estado] = field(default_factory=list)   # estados desde el inicial al final
    acciones: List[str] = field(default_factory=list)    # N/S/E/O de cada paso
    nodos_expandidos: int = 0
    nodos_generados: int = 0
    tiempo: float = 0.0                                  # segundos
    total: int = 0
    rescatadas: int = 0
    fallecidas: int = 0
    ticks: int = 0
    tiempo_agotado: bool = False                         # se alcanzo el limite
    meta_alcanzada: bool = False                         # se encontro un estado meta


# Clase base
#contiene lo que comparten todos los algoritmos: cronometro, contadores, guardar la mejor
#meta o estado parcial y armar el resultado final
class AlgoritmoBusqueda:
    """Plantilla comun: cronometro, contadores, mejor meta y construccion del resultado."""

    nombre = "BASE"

    def __init__(self, problema: ProblemaRescate, limite_tiempo: float = LIMITE_TIEMPO_SEGUNDOS):
        self.problema = problema
        self.limite_tiempo = limite_tiempo
        self._reiniciar()

    def _reiniciar(self) -> None:
        self.expandidos = 0
        self.generados = 0
        self.agotado = False
        self._inicio = 0.0
        self._limite_absoluto = 0.0
        self._mejor_meta: Optional[Nodo] = None      # mejor nodo meta encontrado
        self._mejor_g = None                         # su costo g (para comparar)
        self._mejor_parcial: Optional[Nodo] = None   # mejor nodo NO meta
        self._mejor_clave = None                     # su clave_progreso 

    # control de tiempo
    def _vencido(self) -> bool:
        """True si se agoto el limite de tiempo (y deja constancia en la bandera)."""
        #se consulta en cada iteración de los 4 algoritmos, si el reloj ya pasó el limite absoluto, marca
        # agotado=True y devuelve True. La bandera se queda en True para que _construir_resultado sepa que fue parcial.
        if time.perf_counter() >= self._limite_absoluto:
            self.agotado = True
        return self.agotado

    # registro del mejor resultado
    def _registrar(self, nodo: Nodo, es_meta: bool) -> None:
        """Guarda la mejor meta (menor g) y, como respaldo, el mejor estado parcial."""
        p = self.problema
        # si es meta, comparamos por g. Menos muertas = mejor.
        if es_meta:
            g = p.costo_g(nodo.estado, True)
            if self._mejor_g is None or g < self._mejor_g:
                self._mejor_g, self._mejor_meta = g, nodo
        #si no es meta, comparamos por progreso (más rescatadas, más críticas,
        # menos ticks). Solo se usa si se agota el tiempo sin encontrar meta.
        else:
            clave = p.clave_progreso(nodo.estado)
            if self._mejor_clave is None or clave < self._mejor_clave:
                self._mejor_clave, self._mejor_parcial = clave, nodo

    #punto de entrada
    def resolver(self) -> Resultado:
        """Ejecuta la busqueda con limite de tiempo y devuelve un Resultado."""
        self._reiniciar()
        self._inicio = time.perf_counter()
        self._limite_absoluto = self._inicio + self.limite_tiempo
        raiz = Nodo(self.problema.estado_inicial(), None, None)     # se crea la raíz (sin padre ni acción) y se hace la busqueda
        self._buscar(raiz)
        transcurrido = time.perf_counter() - self._inicio
        return self._construir_resultado(raiz, transcurrido)

    def _buscar(self, raiz: Nodo) -> None:       # implementado por cada algoritmo
        raise NotImplementedError

    def _construir_resultado(self, raiz: Nodo, transcurrido: float) -> Resultado:
        """Reconstruye el camino y calcula las estadisticas finales."""
        # Si hubo meta usamos esa, si no la hubo, el mejor parcial. Si no hubo ninguno de los 2, entonces la raíz
        meta = self._mejor_meta is not None
        final = self._mejor_meta or self._mejor_parcial or raiz
        camino, acciones, nodo = [], [], final
        while nodo is not None:                  # vamos de nodo en nodo hacia atrás, hasta el inicio
            camino.append(nodo.estado)
            if nodo.accion is not None:
                acciones.append(nodo.accion)
            nodo = nodo.padre                    # saltamos al nodo del que salió este
        # invertimos el camino porque como venimos de atrás, quedó al revés
        camino.reverse()                        
        acciones.reverse()
        e = final.estado
        total = self.problema.total
        return Resultado(
            algoritmo=self.nombre, camino=camino, acciones=acciones,
            nodos_expandidos=self.expandidos, nodos_generados=self.generados,
            tiempo=transcurrido, total=total, rescatadas=len(e.rescatadas),
            fallecidas=total - len(e.rescatadas), ticks=e.tick,
            tiempo_agotado=self.agotado, meta_alcanzada=meta)


# BFS - Amplitud
class BusquedaAmplitud(AlgoritmoBusqueda):
    """
    BFS por niveles (nivel = tick). Como el objetivo es MAXIMIZAR rescatadas y no
    "llegar a una meta", no se detiene en la primera meta: recorre todo el
    espacio (finito) y se queda con la mejor meta encontrada.
    """
    nombre = "BFS"

    def _buscar(self, raiz: Nodo) -> None:
        p = self.problema
        cola = deque([raiz])            #cola FIFO
        visitados = {raiz.estado}       #almacena los estados ya visitados, para no repetir
        self.generados = 1 
        while cola:
            if self._vencido():                   # limitador de tiempo, en caso de que se acabe, cortamos
                return
            nodo = cola.popleft()                   # se saca el nodo más antiguo
            self.expandidos += 1
            meta = p.es_meta(nodo.estado)
            self._registrar(nodo, meta)
            #las metas no se expanden, pero no se hace return sino que se sigue explorando
            # a ver si se encuentra una meta con menos muertes
            if meta:                           
                continue
            for accion, hijo in p.sucesores(nodo.estado):
                #solo se añade el hijo si su estado no se habia visitado antes
                if hijo not in visitados:           
                    visitados.add(hijo)
                    self.generados += 1
                    cola.append(Nodo(hijo, nodo, accion))

# UCS - Costo uniforme
class CostoUniforme(AlgoritmoBusqueda):
    """
    UCS: cola de prioridad ordenada por g(n) = (muertas, criticas_muertas, ticks).
    Todos los pasos del costo son >= 0, por lo que la primera meta que sale de la
    cola es optima (maximo de rescatadas).
    """
    nombre = "UCS"

    def _buscar(self, raiz: Nodo) -> None:
        p = self.problema
        contador = 0                              # desempate estable en el heap cuando dos nodos tienen la misma g
        meta0 = p.es_meta(raiz.estado)
        # La frontera es un heap de (g, contador, nodo, es_meta)
        frontera = [(p.costo_g(raiz.estado, meta0), contador, raiz, meta0)]
        vistos = {raiz.estado}
        self.generados = 1
        while frontera:
            if self._vencido():
                return
            # Se saca la entrada con menor g
            _, _, nodo, meta = heapq.heappop(frontera)
            self.expandidos += 1
            self._registrar(nodo, meta)
            if meta:                              # primera meta = optima
                return
            for accion, hijo in p.sucesores(nodo.estado):
                if hijo in vistos:
                    continue
                vistos.add(hijo)
                self.generados += 1
                contador += 1
                meta_h = p.es_meta(hijo)
                #se inserta el hijo con su g; el heap lo ordena solo.
                heapq.heappush(frontera, (p.costo_g(hijo, meta_h), contador,
                                          Nodo(hijo, nodo, accion), meta_h))


# IDDFS - Profundidad iterativa
class ProfundidadIterativa(AlgoritmoBusqueda):
    """
    IDDFS: DFS con limite de profundidad L = 0, 1, 2, ... (profundidad == tick).
    Se implementa de forma iterativa (pila explicita, sin recursion). Dentro de
    cada iteracion se usa un conjunto de visitados (valido porque un mismo
    estado siempre aparece a la misma profundidad al incluir el tick).
    Termina cuando una iteracion completa no corta ninguna rama por el limite,
    lo que ocurre a mas tardar con L = tick_maximo. Los nodos se acumulan entre
    iteraciones (por eso IDDFS suele expandir mas nodos).
    """
    nombre = "IDDFS"

    def _buscar(self, raiz: Nodo) -> None:
        limite = 0
        # Probamos con profundidades 0, 1, 2, ..., hasta agotar el espacio o el tiempo
        while True:
            hubo_corte = self._iteracion(raiz, limite)
            if self.agotado or not hubo_corte:    # tiempo agotado o espacio agotado = paramos
                return
            limite += 1

    def _iteracion(self, raiz: Nodo, limite: int) -> bool:
        """Un DFS limitado. Devuelve True si alguna rama fue cortada por el limite."""
        p = self.problema
        pila = [raiz]                       # LIFO: lo último que entra sale primero    
        visitados = {raiz.estado}
        self.generados += 1
        hubo_corte = False
        while pila:
            if self._vencido():
                return hubo_corte
            nodo = pila.pop()               #saca el último (DFS)
            self.expandidos += 1
            meta = p.es_meta(nodo.estado)
            self._registrar(nodo, meta)
            #las metas no se expanden, pero no se hace return sino que se sigue explorando
            # a ver si se encuentra una meta con menos muertes
            if meta:
                continue 
            #si ya se llegó al limite de profundidad, no se sigue explorando esa rama
            if nodo.estado.tick >= limite:        # profundidad == tick
                hubo_corte = True
                continue
            # reversed(): para que el primer sucesor (N) se explore primero.
            for accion, hijo in reversed(p.sucesores(nodo.estado)):
                if hijo not in visitados:
                    visitados.add(hijo)
                    self.generados += 1
                    pila.append(Nodo(hijo, nodo, accion))
        return hubo_corte


# A*
class AEstrella(AlgoritmoBusqueda):
    """
    A*: f(n) = g(n) + h(n) con h(n) = victimas ya condenadas (Manhattan), que es
    admisible (demostracion en modelo.py). La primera meta extraida es optima.
    Desempate: menor h (mas avanzado) y luego orden de insercion.
    """
    nombre = "A*"

    @staticmethod
    # se suman las tuplas (g + h) componente a componente
    def _sumar(a, b):
        return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

    def _entrada(self, nodo: Nodo, contador: int):
        """Crea la tupla del heap: (f, h, contador, nodo, es_meta)."""
        p = self.problema
        meta = p.es_meta(nodo.estado)
        g = p.costo_g(nodo.estado, meta)
        h = p.heuristica(nodo.estado, meta)
        # El heap ordena por f, luego por h (menor h = más cerca de la meta),
        # y por último por el contador (FIFO entre empates)
        return (self._sumar(g, h), h, contador, nodo, meta)

    def _buscar(self, raiz: Nodo) -> None:
        p = self.problema
        contador = 0
        frontera = [self._entrada(raiz, contador)]
        vistos = {raiz.estado}
        self.generados = 1
        while frontera:
            if self._vencido():
                return
            # se saca la entrada con menor f
            _, _, _, nodo, meta = heapq.heappop(frontera)
            self.expandidos += 1
            self._registrar(nodo, meta)
            if meta:                              # primera meta = optima (aqui si paramos)
                return
            for accion, hijo in p.sucesores(nodo.estado):
                if hijo in vistos:
                    continue
                vistos.add(hijo)
                self.generados += 1
                contador += 1
                # se inserta el hijo con su f, h y contador
                heapq.heappush(frontera, self._entrada(Nodo(hijo, nodo, accion), contador))


# Fabrica
ALGORITMOS = {
    "BFS": BusquedaAmplitud,
    "UCS": CostoUniforme,
    "IDDFS": ProfundidadIterativa,
    "A*": AEstrella,
}


def ejecutar(nombre: str, problema: ProblemaRescate,
             limite_tiempo: float = LIMITE_TIEMPO_SEGUNDOS) -> Resultado:
    """Ejecuta el algoritmo `nombre` (BFS, UCS, IDDFS o A*) con limite de tiempo."""
    # se crea la instancia del algoritmo elegido y se llama a resolver()
    return ALGORITMOS[nombre](problema, limite_tiempo).resolver()
