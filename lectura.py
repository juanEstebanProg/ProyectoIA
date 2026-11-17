# -*- coding: utf-8 -*-
"""
lectura.py
==========
Lectura y validacion de archivos de entrada (mapa.txt y victimas.txt).

"""

from typing import List

from modelo import ErrorDeArchivo, Mapa, Victima


def cargar_mapa(ruta: str) -> Mapa:
    """Lee mapa.txt (ignora lineas en blanco) y construye el Mapa."""
    try:
        with open(ruta, encoding="utf-8-sig") as archivo:
            lineas = [ln.rstrip() for ln in archivo if ln.strip()]
    except OSError as exc:
        raise ErrorDeArchivo(f"No se pudo abrir el mapa: {exc}") from exc
    return Mapa(lineas)          # Mapa valida: rectangular, caracteres, una sola 'S'


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