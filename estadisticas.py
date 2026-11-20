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
    #ljust rellena el texto con espacios para que ocupe exactamente ancho_caja-2 caracteres
    # [:ANCHO_CAJA - 2] recorta si el texto es más largo, para que la caja no se desborde
    return "| " + texto.ljust(ANCHO_CAJA - 2)[:ANCHO_CAJA - 2] + " |"


def construir_texto(resultado_sim: Optional[Resultado],
                    simulacion_terminada: bool,
                    comparacion: Dict[str, Resultado]) -> str:
    """Devuelve el texto de 'RESULTADO DE LA SIMULACION' y 'COMPARACION'."""
    borde = "+" + "-" * ANCHO_CAJA + "+"
    fila = _fila
    lineas = [borde, fila("RESULTADO DE LA SIMULACION")]
    res = resultado_sim
    #solo se muestran cifra si ya terminó, si no, se avisa que aún no ha terminado
    if res is not None and simulacion_terminada:
        lineas += [fila(f"Victimas totales   : {res.total}"),
                   fila(f"Victimas rescatadas: {res.rescatadas}"),
                   fila(f"Victimas fallecidas: {res.fallecidas}"),
                   fila(f"Ticks totales      : {res.ticks}")]
        #se avisa si ya se agotó el tiempo, el resultado es parcial
        if res.tiempo_agotado:
            lineas.append(fila(f"AVISO: limite de {LIMITE_TIEMPO_SEGUNDOS:.0f} s alcanzado"))
    else:
        lineas.append(fila("(disponible al finalizar la simulacion)"))

    #tabla comparativa de los 4 algoritmos
    lineas += [borde, fila("COMPARACION DE ALGORITMOS"),
               fila(f"{'Algoritmo':<9} | {'Nodos':>7} | {'Tiempo':>8} | {'Rescatadas':>10} | {'Fallecidas':>10}")]
    hubo_limite = False
    #se recorre ALGORITMOS para que la tabla siempre muestre los 4 en el mismo orden, así falten resultados
    for nombre in ALGORITMOS:
        r = comparacion.get(nombre)             # se busca el resultado de ese algoritmo
        if r is None:                           #si no se ha ejecutado, se salta
            continue
        marca = "*" if r.tiempo_agotado else ""     # Un "*" marca los resultados que se cortaron por limite de tiempo
        hubo_limite = hubo_limite or r.tiempo_agotado
        tiempo = f"{r.tiempo:.2f}s{marca}"
        lineas.append(fila(f"{nombre:<9} | {r.nodos_expandidos:>7} | {tiempo:>8} | "
                           f"{r.rescatadas:>10} | {r.fallecidas:>10}"))
    if not comparacion:
        lineas.append(fila("(aun no hay ejecuciones)"))
    #si hubo algún limite alcanzado, se muestra el "*"
    if hubo_limite:
        lineas.append(fila("* = limite de tiempo alcanzado (resultado parcial)"))
    lineas.append(borde)
    return "\n".join(lineas)
