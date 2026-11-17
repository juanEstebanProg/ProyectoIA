"""
interfaz.py
===========
Interfaz grafica de escritorio (SOLO Tkinter, biblioteca estandar).

Paneles:
  1. Carga de archivos  -> botones "Examinar", ruta e indicador de lectura.
  2. Configuracion      -> algoritmo (BFS/UCS/IDDFS/A*), velocidad y comparacion.
  3. Boton "Iniciar Rescate".
  4. Mapa animado       -> agente, victimas vivas (con ticks restantes), rescatadas
                           (verde) y muertas (rojo), actualizado tick a tick.
  5. Estadisticas       -> resultado de la simulacion + comparacion de algoritmos.

Los algoritmos corren en un hilo secundario (threading) para que la ventana no se
congele; el hilo comunica sus resultados mediante una cola (queue) que la
interfaz consulta periodicamente con `after`. Cada algoritmo tiene un limite de
10 s (ver algoritmos.LIMITE_TIEMPO_SEGUNDOS).
"""

import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Dict, List, Optional
from visualizacion import (MapaCanvas, COLOR_AGENTE, COLOR_VIVA, 
                           COLOR_RESCATADA, COLOR_MUERTA, COLOR_PARED) 

from algoritmos import ALGORITMOS, LIMITE_TIEMPO_SEGUNDOS, Resultado, ejecutar
from modelo import ErrorDeArchivo, Estado, Mapa, ProblemaRescate, Victima
from lectura import cargar_mapa, cargar_victimas, validar_victimas
from estadisticas import construir_texto

# Colores de la visualizacion

COLOR_OK = "#2e7d32"
COLOR_ERROR = "#c62828"
COLOR_AVISO = "#ef6c00"

ANCHO_CAJA = 58               # ancho interior de las cajas de estadisticas


# ----------------------------------------------------------------------------
# Widget reutilizable: selector de archivo
# ----------------------------------------------------------------------------
class SelectorArchivo(ttk.Frame):
    """Fila 'etiqueta + ruta + boton Examinar + indicador de lectura'."""

    def __init__(self, padre, titulo: str, comando_al_elegir):
        super().__init__(padre)
        self._comando = comando_al_elegir
        self._titulo = titulo
        self.ruta = tk.StringVar(value="(ningun archivo seleccionado)")
        ttk.Label(self, text=titulo, width=14).grid(row=0, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.ruta, state="readonly", width=60).grid(
            row=0, column=1, padx=4, sticky="ew")
        self.boton = ttk.Button(self, text="Examinar...", command=self._examinar)
        self.boton.grid(row=0, column=2, padx=4)
        self.indicador = tk.Label(self, text="Sin leer", fg="gray", width=34, anchor="w")
        self.indicador.grid(row=0, column=3, sticky="w")
        self.columnconfigure(1, weight=1)

    def _examinar(self) -> None:
        ruta = filedialog.askopenfilename(
            title=f"Seleccionar {self._titulo}",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")])
        if ruta:
            self.ruta.set(ruta)
            self._comando(ruta)

    def marcar(self, texto: str, color: str) -> None:
        """Actualiza el indicador de lectura (verde = correcto, rojo = error)."""
        self.indicador.config(text=texto, fg=color)

    def habilitar(self, activo: bool) -> None:
        self.boton.config(state="normal" if activo else "disabled")


# ----------------------------------------------------------------------------
# Aplicacion principal
# ----------------------------------------------------------------------------
class Aplicacion(tk.Tk):
    """Ventana principal del simulador de rescate."""

    def __init__(self):
        super().__init__()
        self.title("Agente de Rescate con Victimas en Riesgo")
        self.geometry("1000x860")
        self.minsize(900, 760)

        # --- datos del dominio ---
        self.mapa: Optional[Mapa] = None
        self.victimas_leidas: Optional[List[Victima]] = None
        self.problema: Optional[ProblemaRescate] = None
        self.comparacion: Dict[str, Resultado] = {}     # algoritmo -> ultimo resultado

        # --- estado de la simulacion / hilos ---
        self._cola: "queue.Queue" = queue.Queue()
        self._hilo: Optional[threading.Thread] = None
        self._after_anim: Optional[str] = None
        self._resultado_sim: Optional[Resultado] = None
        self._frame = 0
        self._estado_actual: Optional[Estado] = None
        self._es_final = False
        self._simulacion_terminada = False
        self._algoritmo_simulado = ""
        self._rastro: set = set()

        self._crear_widgets()
        self._lienzo = MapaCanvas(self.canvas) 
        self._refrescar_estadisticas()

    # ======================================================================
    # Construccion de la interfaz
    # ======================================================================
    def _crear_widgets(self) -> None:
        # 1) Panel de carga de archivos
        panel_archivos = ttk.LabelFrame(self, text=" 1. Carga de archivos ")
        panel_archivos.pack(fill="x", padx=10, pady=(10, 4))
        self.sel_mapa = SelectorArchivo(panel_archivos, "mapa.txt", self._al_elegir_mapa)
        self.sel_mapa.pack(fill="x", padx=6, pady=3)
        self.sel_victimas = SelectorArchivo(panel_archivos, "victimas.txt", self._al_elegir_victimas)
        self.sel_victimas.pack(fill="x", padx=6, pady=3)

        # 2) Panel de configuracion
        panel_conf = ttk.LabelFrame(self, text=" 2. Configuracion ")
        panel_conf.pack(fill="x", padx=10, pady=4)
        ttk.Label(panel_conf, text="Algoritmo:").grid(row=0, column=0, padx=6, pady=6)
        self.var_algoritmo = tk.StringVar(value="A*")
        ttk.Combobox(panel_conf, textvariable=self.var_algoritmo, state="readonly", width=8,
                     values=list(ALGORITMOS.keys())).grid(row=0, column=1, padx=6)
        ttk.Label(panel_conf, text="Velocidad (ms por tick):").grid(row=0, column=2, padx=(18, 4))
        self.var_velocidad = tk.IntVar(value=600)
        ttk.Scale(panel_conf, from_=50, to=1500, variable=self.var_velocidad,
                  orient="horizontal", length=180,
                  command=lambda _v: self.var_velocidad.set(int(float(_v)))).grid(row=0, column=3)
        ttk.Label(panel_conf, textvariable=self.var_velocidad, width=5).grid(row=0, column=4)
        self.var_comparar = tk.BooleanVar(value=True)
        ttk.Checkbutton(panel_conf, text="Ejecutar tambien los demas algoritmos (tabla comparativa)",
                        variable=self.var_comparar).grid(row=0, column=5, padx=14)

        # 3) Boton Iniciar Rescate
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=10, pady=4)
        self.boton_iniciar = ttk.Button(barra, text="Iniciar Rescate", command=self._iniciar,
                                        state="disabled")
        self.boton_iniciar.pack(side="left")
        self.var_estado = tk.StringVar(value="Cargue mapa.txt y victimas.txt para comenzar.")
        ttk.Label(barra, textvariable=self.var_estado).pack(side="left", padx=12)

        # 4) Visualizacion del mapa
        panel_mapa = ttk.LabelFrame(self, text=" 3. Simulacion ")
        panel_mapa.pack(fill="both", expand=True, padx=10, pady=4)
        self.canvas = tk.Canvas(panel_mapa, bg="#eceff1", highlightthickness=0, height=360)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=(6, 2))
        self.canvas.bind("<Configure>", lambda _e: self._redibujar())
        self.var_tick = tk.StringVar(value="Tick: -")
        ttk.Label(panel_mapa, textvariable=self.var_tick, font=("Segoe UI", 10, "bold")).pack()
        leyenda = ttk.Frame(panel_mapa)
        leyenda.pack(pady=(0, 4))
        for texto, color in (("Agente", COLOR_AGENTE), ("Viva (ticks restantes)", COLOR_VIVA),
                             ("Rescatada", COLOR_RESCATADA), ("Muerta", COLOR_MUERTA),
                             ("Pared", COLOR_PARED)):
            tk.Label(leyenda, width=2, bg=color).pack(side="left", padx=(10, 2))
            ttk.Label(leyenda, text=texto).pack(side="left")
        ttk.Label(leyenda, text="   (* = victima critica)").pack(side="left")

        # 5) Panel de estadisticas
        panel_est = ttk.LabelFrame(self, text=" 4. Estadisticas ")
        panel_est.pack(fill="x", padx=10, pady=(4, 10))
        self.texto_est = tk.Text(panel_est, height=18, width=64, font=("Courier New", 10),
                                 state="disabled", bg="#fafafa")
        self.texto_est.pack(padx=6, pady=6)

    # ======================================================================
    # Carga de archivos
    # ======================================================================
    def _al_elegir_mapa(self, ruta: str) -> None:
        try:
            self.mapa = cargar_mapa(ruta)
            self.sel_mapa.marcar(f"OK: lectura correcta ({self.mapa.filas}x{self.mapa.columnas})",
                                 COLOR_OK)
        except ErrorDeArchivo as exc:
            self.mapa = None
            self.sel_mapa.marcar(f"ERROR: {exc}", COLOR_ERROR)
        self._revalidar()

    def _al_elegir_victimas(self, ruta: str) -> None:
        try:
            self.victimas_leidas = cargar_victimas(ruta)
            self.sel_victimas.marcar(f"OK: {len(self.victimas_leidas)} victimas leidas", COLOR_OK)
        except ErrorDeArchivo as exc:
            self.victimas_leidas = None
            self.sel_victimas.marcar(f"ERROR: {exc}", COLOR_ERROR)
        self._revalidar()

    def _revalidar(self) -> None:
        """Cuando hay mapa y victimas leidos, los valida entre si y arma el problema."""
        self._cancelar_animacion()
        self.problema = None
        self.comparacion.clear()
        self._resultado_sim = None
        self._estado_actual = None
        self._es_final = False
        self._simulacion_terminada = False
        self.var_tick.set("Tick: -")
        if self.mapa is not None and self.victimas_leidas is not None:
            try:
                avisos = validar_victimas(self.mapa, self.victimas_leidas)
                self.problema = ProblemaRescate(self.mapa, self.victimas_leidas)
                self._estado_actual = self.problema.estado_inicial()
                if avisos:
                    self.sel_victimas.marcar(f"AVISO: {avisos[0]}", COLOR_AVISO)
                    self.var_estado.set("  |  ".join(avisos))
                else:
                    self.var_estado.set("Archivos listos. Pulse 'Iniciar Rescate'.")
            except ErrorDeArchivo as exc:
                self.sel_victimas.marcar(f"ERROR: {exc}", COLOR_ERROR)
                self.var_estado.set("Corrija el archivo de victimas.")
        self.boton_iniciar.config(state="normal" if self.problema else "disabled")
        self._redibujar()
        self._refrescar_estadisticas()

    # ======================================================================
    # Ejecucion de algoritmos (hilo secundario) y simulacion
    # ======================================================================
    def _iniciar(self) -> None:
        """Lanza el algoritmo elegido (y opcionalmente los demas) en un hilo."""
        if self.problema is None or (self._hilo and self._hilo.is_alive()):
            return
        elegido = self.var_algoritmo.get()
        nombres = [elegido]
        if self.var_comparar.get():
            nombres += [n for n in ALGORITMOS if n != elegido]
        self._algoritmo_simulado = elegido
        self._cancelar_animacion()
        self._simulacion_terminada = False
        self._es_final = False
        self._resultado_sim = None
        self._rastro = set()
        self._cola = queue.Queue()
        self._bloquear(True)
        self.var_estado.set(f"Ejecutando {elegido} (limite {LIMITE_TIEMPO_SEGUNDOS:.0f} s)...")
        self._hilo = threading.Thread(target=self._trabajo, args=(self.problema, nombres, self._cola),
                                      daemon=True)
        self._hilo.start()
        self.after(80, self._sondear_cola)

    @staticmethod
    def _trabajo(problema: ProblemaRescate, nombres: List[str], cola: "queue.Queue") -> None:
        """Cuerpo del hilo: corre cada algoritmo y deposita el resultado en la cola."""
        try:
            for nombre in nombres:
                cola.put(("ejecutando", nombre))
                cola.put(("resultado", ejecutar(nombre, problema, LIMITE_TIEMPO_SEGUNDOS)))
        except Exception as exc:                       # nunca dejar el hilo sin avisar
            cola.put(("error", str(exc)))
        finally:
            cola.put(("fin", None))

    def _sondear_cola(self) -> None:
        """Procesa los mensajes del hilo (se ejecuta en el hilo de la interfaz)."""
        terminado = False
        try:
            while True:
                tipo, dato = self._cola.get_nowait()
                if tipo == "ejecutando":
                    self.var_estado.set(f"Ejecutando {dato} (limite {LIMITE_TIEMPO_SEGUNDOS:.0f} s)...")
                elif tipo == "resultado":
                    self.comparacion[dato.algoritmo] = dato
                    if dato.algoritmo == self._algoritmo_simulado:
                        self._iniciar_animacion(dato)
                    self._refrescar_estadisticas()
                elif tipo == "error":
                    self.var_estado.set(f"Error en la ejecucion: {dato}")
                elif tipo == "fin":
                    terminado = True
        except queue.Empty:
            pass
        if terminado:
            self._bloquear(False)
        else:
            self.after(80, self._sondear_cola)

    def _bloquear(self, ocupado: bool) -> None:
        """Evita cambiar archivos o relanzar mientras el hilo trabaja."""
        self.boton_iniciar.config(state="disabled" if ocupado else "normal")
        self.sel_mapa.habilitar(not ocupado)
        self.sel_victimas.habilitar(not ocupado)

    # -- animacion ------------------------------------------------------------
    def _iniciar_animacion(self, res: Resultado) -> None:
        self._cancelar_animacion()
        self._resultado_sim = res
        self._frame = 0
        self._rastro = set()
        self._paso()

    def _cancelar_animacion(self) -> None:
        if self._after_anim is not None:
            self.after_cancel(self._after_anim)
            self._after_anim = None

    def _paso(self) -> None:
        """Dibuja un tick de la simulacion y programa el siguiente."""
        res = self._resultado_sim
        if res is None:
            return
        estado = res.camino[self._frame]
        ultimo = self._frame == len(res.camino) - 1
        self._estado_actual = estado
        self._es_final = ultimo
        self._rastro.add((estado.fila, estado.columna))
        self._redibujar()
        self.var_tick.set(f"Tick: {estado.tick}   |   Rescatadas: {len(estado.rescatadas)} / {res.total}"
                          f"   |   Algoritmo: {res.algoritmo}")
        if ultimo:
            self._simulacion_terminada = True
            aviso = "  (limite de tiempo alcanzado: resultado parcial)" if res.tiempo_agotado else ""
            self.var_estado.set(f"Simulacion terminada: no quedan victimas alcanzables.{aviso}")
            self._refrescar_estadisticas()
            self._after_anim = None
            return
        self._frame += 1
        self._after_anim = self.after(max(20, int(self.var_velocidad.get())), self._paso)

    # ======================================================================
    # Dibujo del mapa
    # ======================================================================
    def _redibujar(self) -> None:
        """ delega el dibujo al modulo visualizacion.py"""

        self._lienzo.dibujar(self.mapa, self.victimas_leidas, self._estado_actual, self._es_final, self._rastro)

    # ======================================================================
    # Panel de estadisticas
    # ======================================================================


    def _refrescar_estadisticas(self) -> None:
        """Reconstruye el texto de 'RESULTADO DE LA SIMULACION' y 'COMPARACION'."""
        texto = construir_texto(self._resultado_sim,
                                self._simulacion_terminada,
                                self.comparacion) 

        self.texto_est.config(state="normal")
        self.texto_est.delete("1.0", "end")
        self.texto_est.insert("1.0", texto)
        self.texto_est.config(state="disabled")
