 # -*- coding: utf-8 -*-

"""
heuristica.py
=============
Contiene la función de estimación (heurística) utilizada por A*.
Se ha separado del modelo para facilitar su estudio y sustentación.
"""

def calcular_heuristica(estado, problema, meta):
    """
    h(n) admisible (ver demostracion en el docstring del modulo): cuenta las
    victimas vivas condenadas por distancia Manhattan > ticks restantes.
    """
    # si el estado ya es meta, entonces no queda nada por rescatar
    # h = 0
    if meta:
        return (0, 0, 0)
    #contadores
    condenadas = 0
    criticas = 0

    #se revisan solo las víctimas que siguen vivas en este estado
    for i in estado.vivas:
        v = problema.victimas[i]
        # Distancia Manhattan: movimientos minimos si no hubiera paredes
        distancia = abs(estado.fila - v.fila) + abs(estado.columna - v.columna)
        ticks_restantes = v.ticks - estado.tick     # ticks que le quedan de vida a la víctima desde el tick actual

        #si ni yendo en linea recta se llega a tiempo, la victima ya está condenada
        if distancia > ticks_restantes:
            condenadas += 1
            if v.critica:
                criticas += 1

    # h = (condenadas, críticas condenadas, 0)
    #se pone 0 en el tercer componente porque en esta heuristica no se estiman ticks adicionales
    #ya que si se pone algún valor positivo diferente de 0, podria sobreestimar el costo real y dejar de ser admisible.
    return (condenadas, criticas, 0)