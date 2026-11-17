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
    if meta:
        return (0, 0, 0)
    
    condenadas = 0
    criticas = 0

    for i in estado.vivas:
        v = problema.victimas[i]
        distancia = abs(estado.fila - v.fila) + abs(estado.columna - v.columna)
        ticks_restantes = v.ticks - estado.tick

        if distancia > ticks_restantes:
            condenadas += 1
            if v.critica:
                criticas += 1
    return (condenadas, criticas, 0)