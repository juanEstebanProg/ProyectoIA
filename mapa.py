"""
mapa.py
=======
Cuadricula 2D del entorno: paredes, celdas libres y posicion inicial.
"""
from typing import List, Tuple

from victima import ErrorDeArchivo


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