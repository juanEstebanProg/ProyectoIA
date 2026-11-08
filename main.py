"tenemos que explicar todo lo que hacemos de manera super clara para la sustentacion"

"""
GUI con Tkinter: carga de archivos, selección de algoritmo,
botón de inicio, animación tick a tick, panel de estadísticas
y comparación de los 4 algoritmos.
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import time

from parser import build_problem
from algori import bfs, ucs, iddfs, astar
from simulacion import trace_solution
from modelo import Victim

CELL = 48
COLORS = {
    'wall':  '#2c3e50',
    'free':  '#ecf0f1',
    'agent': '#e67e22',
    'alive': '#3498db',
    'resc':  '#27ae60',
    'dead':  '#c0392b',
    'crit':  '#8e44ad',
}


class RescueApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Agente de Rescate — Víctimas en Riesgo")
        self.geometry("1150x720")
        self.map_path = None
        self.victims_path = None
        self.rmap = None
        self.trace = []
        self.stats = []
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        top = tk.Frame(self, pady=6)
        top.pack(fill='x')

        # Panel carga
        f1 = tk.LabelFrame(top, text="1. Carga de archivos", padx=8, pady=6)
        f1.pack(side='left', padx=6, fill='y')
        self.lbl_map = tk.Label(f1, text="mapa.txt: (sin cargar)")
        self.lbl_map.pack(anchor='w')
        tk.Button(f1, text="Examinar mapa", command=self.load_map).pack(anchor='w')
        self.lbl_vic = tk.Label(f1, text="victimas.txt: (sin cargar)")
        self.lbl_vic.pack(anchor='w')
        tk.Button(f1, text="Examinar víctimas", command=self.load_victims).pack(anchor='w')

        # Panel configuración
        f2 = tk.LabelFrame(top, text="2. Configuración", padx=8, pady=6)
        f2.pack(side='left', padx=6, fill='y')
        tk.Label(f2, text="Algoritmo:").pack(anchor='w')
        self.algo_var = tk.StringVar(value="A*")
        ttk.Combobox(f2, textvariable=self.algo_var,
                     values=["BFS", "UCS", "IDDFS", "A*"],
                     state='readonly', width=12).pack(anchor='w')
        tk.Label(f2, text="Velocidad (ms/tick):").pack(anchor='w')
        self.speed_var = tk.IntVar(value=400)
        tk.Scale(f2, from_=50, to=1500, orient='horizontal',
                 variable=self.speed_var, length=140).pack(anchor='w')

        # Panel botones
        f3 = tk.LabelFrame(top, text="3. Ejecución", padx=8, pady=6)
        f3.pack(side='left', padx=6, fill='y')
        tk.Button(f3, text="▶ Iniciar Rescate", bg='#27ae60', fg='white',
                  command=self.start_rescue).pack(fill='x', pady=2)
        tk.Button(f3, text="⚖ Comparar 4 algoritmos", bg='#2980b9',
                  fg='white', command=self.compare_all).pack(fill='x', pady=2)

        # Canvas
        self.canvas = tk.Canvas(self, bg='#bdc3c7', width=700, height=560)
        self.canvas.pack(side='left', padx=8, pady=8, fill='both', expand=True)

        # Panel estadísticas
        self.txt = tk.Text(self, width=42, height=34, font=('Consolas', 9))
        self.txt.pack(side='right', padx=8, pady=8, fill='y')
        self.txt.insert('end', "Esperando carga de archivos...\n")

    # ---------- carga ----------
    def load_map(self):
        p = filedialog.askopenfilename(filetypes=[("Texto", "*.txt")])
        if p:
            self.map_path = p
            self.lbl_map.config(text=f"mapa.txt: {p}  ✔", fg='green')

    def load_victims(self):
        p = filedialog.askopenfilename(filetypes=[("Texto", "*.txt")])
        if p:
            self.victims_path = p
            self.lbl_vic.config(text=f"victimas.txt: {p}  ✔", fg='green')

    # ---------- helpers de dibujo ----------
    def _draw_cell(self, r, c, color, text='', tcol='black'):
        x0, y0 = c * CELL, r * CELL
        self.canvas.create_rectangle(x0, y0, x0 + CELL, y0 + CELL,
                                     fill=color, outline='#7f8c8d')
        if text:
            self.canvas.create_text(x0 + CELL / 2, y0 + CELL / 2,
                                    text=text, fill=tcol,
                                    font=('Consolas', 9, 'bold'))

    def _render_state(self, state):
        self.canvas.delete('all')
        rmap = self.rmap
        for r in range(rmap.rows):
            for c in range(rmap.cols):
                if rmap.grid[r][c] == '#':
                    self._draw_cell(r, c, COLORS['wall'])
                else:
                    self._draw_cell(r, c, COLORS['free'])
        # víctimas
        for vid, v in rmap.victims.items():
            if vid in state.rescued:
                color, txt = COLORS['resc'], f"V{vid}✔"
            elif vid in state.alive:
                rem = v.survival_ticks - state.tick
                color = COLORS['crit'] if v.critical else COLORS['alive']
                txt = f"V{vid}({rem})"
            else:
                color, txt = COLORS['dead'], f"V{vid}✘"
            self._draw_cell(v.row, v.col, color, txt, 'white')
        # agente
        self._draw_cell(state.row, state.col, COLORS['agent'], "A", 'white')

    # ---------- ejecución ----------
    def _run_algorithm(self, name):
        if not self.rmap:
            if not (self.map_path and self.victims_path):
                messagebox.showerror("Error", "Carga mapa.txt y victimas.txt")
                return None
        self.rmap = build_problem(self.map_path, self.victims_path)
        funcs = {'BFS': bfs, 'UCS': ucs, 'IDDFS': iddfs, 'A*': astar}
        return funcs[name](self.rmap)

    def start_rescue(self):
        algo = self.algo_var.get()
        result = self._run_algorithm(algo)
        if result is None:
            return
            
        # Desempaquetar los 4 valores
        final, nodes, elapsed, limit_reached = result
        
        # Si se pasó del límite, avisar
        if limit_reached:
            messagebox.showwarning(
                "Límite alcanzado", 
                f"El algoritmo {algo} excedió su capacidad de búsqueda "
                f"({nodes} nodos / {elapsed:.2f}s).\nSe mostrará la mejor ruta parcial encontrada."
            )

        self.trace = trace_solution(final, self.rmap)
        self.current_algo = algo
        self.current_stats = (nodes, elapsed, final)
        self._write_stats_start(algo, final, nodes, elapsed, limit_reached)
        self._animate(0)

    def _animate(self, i):
        if i >= len(self.trace):
            self._write_stats_final()
            return
        self._render_state(self.trace[i])
        self.after(self.speed_var.get(), lambda: self._animate(i + 1))

    # ---------- estadísticas ----------
    def _write_stats_start(self, algo, final, nodes, elapsed, limit_reached):
        total = len(self.rmap.victims)
        resc = len(final.rescued)
        dead = total - resc
        self.txt.delete('1.0', 'end')
        status = "COMPLETADO" if not limit_reached else "LÍMITE ALCANZADO"
        self.txt.insert('end',
            "+-----------------------------+\n"
            "| RESULTADO DE LA SIMULACIÓN  |\n"
            "+-----------------------------+\n"
            f"| Estado           : {status:<10}|\n"
            f"| Algoritmo        : {algo:<10}|\n"
            f"| Víctimas totales : {total:<10}|\n"
            f"| Rescatadas       : {resc:<10}|\n"
            f"| Fallecidas       : {dead:<10}|\n"
            f"| Ticks totales    : {final.tick:<10}|\n"
            f"| Nodos expandidos : {nodes:<10}|\n"
            f"| Tiempo           : {elapsed:.4f}s   |\n"
            "+-----------------------------+\n")
    def _write_stats_final(self):
        self.txt.insert('end', "\nSimulación finalizada.\n")
        if hasattr(self, 'current_stats'):
            _, _, final = self.current_stats
            self.txt.insert('end',
                "Rescatadas: " + str(sorted(final.rescued)) + "\n"
                "Fallecidas: " + str(sorted(set(self.rmap.victims) - final.rescued)) + "\n")

    # ---------- comparación ----------
    def compare_all(self):
        if not (self.map_path and self.victims_path):
            messagebox.showerror("Error", "Carga ambos archivos primero")
            return
        self.rmap = build_problem(self.map_path, self.victims_path)
        rows = []
        for name, fn in (("BFS", bfs), ("UCS", ucs),
                         ("IDDFS", iddfs), ("A*", astar)):
            final, nodes, elapsed = fn(self.rmap)
            rows.append((name, nodes, elapsed,
                         len(final.rescued),
                         len(self.rmap.victims) - len(final.rescued)))
        self.txt.delete('1.0', 'end')
        header = ("+-------------------------------------------+\n"
                  "| COMPARACIÓN DE ALGORITMOS                 |\n"
                  "+-------------------------------------------+\n"
                  "| Algoritmo | Nodos | Tiempo | Resc | Fall |\n"
                  "+-------------------------------------------+\n")
        body = "".join(
            f"| {a:<9}| {n:<5} | {t:5.2f}s | {r:<4} | {d:<4} |\n"
            for a, n, t, r, d in rows)
        footer = "+-------------------------------------------+\n"
        self.txt.insert('end', header + body + footer)


if __name__ == '__main__':
    RescueApp().mainloop()