"""Lectura de mapa.txt y victimas.txt"""
from modelo import Victim, RescueMap, START


def load_map(path):
    with open(path, 'r', encoding='utf-8') as f:
        grid = [list(line.rstrip('\n')) for line in f if line.strip()]
    start = None
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch == START:
                start = (r, c)
    if start is None:
        raise ValueError("El mapa no tiene celda de inicio 'S'")
    return grid, start


def load_victims(path):
    """
    Formato: id,fila,columna,ticks_supervivencia[,critica]
    """
    victims = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = [p.strip() for p in line.split(',')]
            if parts[0].lower() in ('id', 'idv'):
                continue  # cabecera
            vid = int(parts[0])
            critical = len(parts) > 4 and parts[4].lower() in ('1', 'true', 'si', 'crítica', 'critica')
            victims[vid] = Victim(vid, int(parts[1]), int(parts[2]),
                                  int(parts[3]), critical)
    return victims


def build_problem(map_path, victims_path):
    grid, start = load_map(map_path)
    victims = load_victims(victims_path)
    # Sincronizar etiquetas V1..Vn del mapa con víctimas conocidas
    m = RescueMap(grid, victims, start)
    return m