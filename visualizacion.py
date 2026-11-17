"""
visualizacion.py
================
Módulo exclusivo para dibujar el mapa y el estado en el Canvas de Tkinter.
"""

# Colores de la visualizacion
COLOR_PARED = "#37474f"
COLOR_LIBRE = "#ffffff"
COLOR_RASTRO = "#d6e9fb"      # celdas ya recorridas por el agente
COLOR_AGENTE = "#1565c0"
COLOR_VIVA = "#ffc107"
COLOR_RESCATADA = "#43a047"
COLOR_MUERTA = "#e53935"
 

class MapaCanvas:
    def __init__(self, canvas):
        self.canvas = canvas

    def dibujar(self, mapa, victimas, estado, es_final, rastro):
        """Dibuja la cuadricula completa para el estado actual."""
        c = self.canvas
        c.delete("all")
        
        if mapa is None:
            c.create_text(c.winfo_width() // 2, c.winfo_height() // 2,
                          text="Cargue mapa.txt para ver el entorno", fill="gray")
            return

        ancho, alto = max(c.winfo_width(), 50), max(c.winfo_height(), 50)
        lado = max(12, min(64, (ancho - 10) // mapa.columnas, (alto - 10) // mapa.filas))
        x0 = (ancho - lado * mapa.columnas) // 2
        y0 = (alto - lado * mapa.filas) // 2

        # Celdas del mapa
        for f in range(mapa.filas):
            for col in range(mapa.columnas):
                if not mapa.es_libre(f, col):
                    color = COLOR_PARED
                elif (f, col) in rastro:
                    color = COLOR_RASTRO
                else:
                    color = COLOR_LIBRE
                x, y = x0 + col * lado, y0 + f * lado
                c.create_rectangle(x, y, x + lado, y + lado, fill=color, outline="#b0bec5")
                
        # Marca de inicio
        fi, ci = mapa.inicio
        c.create_text(x0 + ci * lado + lado * 0.15, y0 + fi * lado + lado * 0.2, text="S",
                      fill="#607d8b", font=("Segoe UI", max(7, lado // 5), "bold"))

        if estado is None:
            return
            
        fuente = ("Segoe UI", max(7, lado // 4), "bold")

        # Victimas
        for i, v in enumerate(victimas or []):
            if not mapa.en_rango(v.fila, v.columna):
                continue
            x, y = x0 + v.columna * lado, y0 + v.fila * lado
            marca = "*" if v.critica else ""
            
            if i in estado.rescatadas:
                color, texto = COLOR_RESCATADA, f"{v.id}{marca}"
            elif i in estado.vivas and not es_final:
                color, texto = COLOR_VIVA, f"{v.id}{marca}\n{v.ticks - estado.tick}"
            else:
                color, texto = COLOR_MUERTA, f"{v.id}{marca}"
                
            c.create_rectangle(x + 2, y + 2, x + lado - 2, y + lado - 2, fill=color, outline="")
            c.create_text(x + lado / 2, y + lado / 2, text=texto, font=fuente,
                          fill="white" if color != COLOR_VIVA else "black")

        # Agente: circulo azul (aro si esta sobre una victima para no taparla)
        x, y = x0 + estado.columna * lado, y0 + estado.fila * lado
        pad = lado * 0.18
        sobre_victima = any(v.fila == estado.fila and v.columna == estado.columna for v in (victimas or []))
        
        if sobre_victima:
            c.create_oval(x + pad / 2, y + pad / 2, x + lado - pad / 2, y + lado - pad / 2,
                          outline=COLOR_AGENTE, width=3)
        else:
            c.create_oval(x + pad, y + pad, x + lado - pad, y + lado - pad, fill=COLOR_AGENTE, outline="")
            c.create_text(x + lado / 2, y + lado / 2, text="A", fill="white", font=fuente)