"""
estadisticas.py
================
Construye el texto del panel de estadisticas 
"""

from typing import Dict, Optional
from algoritmos import ALGORITMOS, LIMITE_TIEMPO_SEGUNDOS, Resultado

ANCHO_CAJA = 58     # ancho interior de las cajas de estadisticas

def _fila(texto: str = "") -> str:
    """Linea de una caja: '| texto ... |' con ancho fijo."""
    return "| " + texto.ljust(ANCHO_CAJA - 2)[:ANCHO_CAJA - 2] + " |"


def construir_texto(resultado_sim: Optional[Resultado],
                    simulacion_terminada: bool,
                    comparacion: Dict[str, Resultado]) -> str:
    """Devuelve el texto de 'RESULTADO DE LA SIMULACION' y 'COMPARACION'."""
    borde = "+" + "-" * ANCHO_CAJA + "+"
    fila = _fila
    lineas = [borde, fila("RESULTADO DE LA SIMULACION")]
    res = resultado_sim
    if res is not None and simulacion_terminada:
        lineas += [fila(f"Victimas totales   : {res.total}"),
                   fila(f"Victimas rescatadas: {res.rescatadas}"),
                   fila(f"Victimas fallecidas: {res.fallecidas}"),
                   fila(f"Ticks totales      : {res.ticks}")]
        if res.tiempo_agotado:
            lineas.append(fila(f"AVISO: limite de {LIMITE_TIEMPO_SEGUNDOS:.0f} s alcanzado"))
    else:
        lineas.append(fila("(disponible al finalizar la simulacion)"))
    lineas += [borde, fila("COMPARACION DE ALGORITMOS"),
               fila(f"{'Algoritmo':<9} | {'Nodos':>7} | {'Tiempo':>8} | {'Rescatadas':>10} | {'Fallecidas':>10}")]
    hubo_limite = False
    for nombre in ALGORITMOS:
        r = comparacion.get(nombre)
        if r is None:
            continue
        marca = "*" if r.tiempo_agotado else ""
        hubo_limite = hubo_limite or r.tiempo_agotado
        tiempo = f"{r.tiempo:.2f}s{marca}"
        lineas.append(fila(f"{nombre:<9} | {r.nodos_expandidos:>7} | {tiempo:>8} | "
                           f"{r.rescatadas:>10} | {r.fallecidas:>10}"))
    if not comparacion:
        lineas.append(fila("(aun no hay ejecuciones)"))
    if hubo_limite:
        lineas.append(fila("* = limite de tiempo alcanzado (resultado parcial)"))
    lineas.append(borde)
    return "\n".join(lineas)