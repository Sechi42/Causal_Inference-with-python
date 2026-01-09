import time
import random
import os
import math
import pandas as pd
from plotnine import *
import numpy as np

# --- CONFIGURACIÓN GLOBAL ---
META = 150
DELAY_TURNO = 0.2
PHI_INERCIA = 0.3 

# Probabilidades de eventos
PROB_JALAR_RIVAL = 0.05       
PROB_STUN_2_TURNOS = 0.00025   
PROB_RETROCESO_CUANTICO = 0.0001 

class Color:
    RED = '\033[91m'; BLUE = '\033[94m'; GREEN = '\033[92m'; 
    ORANGE = '\033[93m'; PURPLE = '\033[95m'; CYAN = '\033[96m'; 
    RESET = '\033[0m'; BOLD = '\033[1m'; WHITE = '\033[97m'

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def mapa_logistico(x, r=3.95):
    """Genera caos determinista."""
    return r * x * (1 - x)

def paso_levy(beta=1.5):
    """Genera un paso usando distribución Lévy."""
    beta = max(1.1, min(beta, 1.95))
    sigma_u = (math.gamma(1 + beta) * math.sin(math.pi * beta / 2) /
               (math.gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))) ** (1 / beta)
    u = random.gauss(0, sigma_u)
    v = random.gauss(0, 1)
    paso = u / abs(v) ** (1 / beta)
    return max(1, min(int(abs(paso)), 25))

# --- NUEVO: Función para dibujar el Dashboard arriba ---
def dibujar_telemetria(buses, pos, estado, ranking_ids):
    print(f"{Color.WHITE}{'='*28} TELEMETRÍA EN VIVO {'='*28}{Color.RESET}")
    print(f"{'RNK':<4} | {'BUS':<12} | {'DIST':<8} | {'β (VOLAT)':<10} | {'MOMENTUM':<8} | {'ESTADO'}")
    print(f"{'-'*75}")

    for rank_idx, bus_id in enumerate(ranking_ids):
        # Buscar el objeto bus correspondiente al ID
        bus_obj = next(b for b in buses if b['id'] == bus_id)
        
        # Datos
        distancia = pos[bus_id]
        beta_val = estado['beta_actual'][bus_id] # Guardaremos esto en el estado
        inercia = estado['ultimo_salto'][bus_id]
        
        # Estado (Stun, Retroceso, Normal)
        status = "🟢 OK"
        if estado['skip_turns'][bus_id] > 0:
            status = f"{Color.RED}❄️ STUN{Color.RESET}"
        elif estado['retroceso'][bus_id]:
            status = f"{Color.ORANGE}🔥 OVER{Color.RESET}"
        elif bus_id in estado['afectados_cuanticos']: # Hack para visualizar el evento
            status = f"{Color.PURPLE}🌀 QUANT{Color.RESET}"

        # Formato de línea
        color_bus = bus_obj['color']
        print(f"{rank_idx+1:<4} | {color_bus}{bus_obj['nombre']:<12}{Color.RESET} | {distancia:<4}/{META} | {beta_val:.2f}       | {inercia:<8} | {status}")
    print(f"{'-'*75}\n")

def dibujar_bus(nombre, pos, meta, color_ansi):
    """Dibuja SOLO el bus, sin estadísticas laterales."""
    pos_visual = min(pos, meta)
    pad = " " * int(pos_visual)
    
    # Cálculo de espacio para la meta
    espacio_restante = max(0, meta - int(pos_visual) - 20)
    resto = " " * espacio_restante
    
    print(f"{color_ansi}{pad}   __________________  {resto}|{Color.RESET}")
    print(f"{color_ansi}{pad}  |__|__|__|__|__|__|  {resto}|{Color.RESET}")
    print(f"{color_ansi}{pad}  |{nombre:^18}|) {resto}|{Color.RESET}")
    print(f"{color_ansi}{pad}  |~~~@~~~~~~@~~~~~~|) {resto}|{Color.RESET}")

def correr_carrera(config_carrera, buses, numero_carrera):
    pos = {b['id']: int(config_carrera[b['id']]['inicio']) for b in buses}

    estado = {
        'saltos_grandes': {b['id']: 0 for b in buses},
        'ultimo_salto': {b['id']: 1 for b in buses},
        'retroceso': {b['id']: False for b in buses},
        'movimientos': {b['id']: [] for b in buses},
        'usos_poder': {b['id']: 0 for b in buses},
        'skip_turns': {b['id']: 0 for b in buses},
        'semilla_caos': {b['id']: random.random() for b in buses},
        'beta_actual': {b['id']: 1.5 for b in buses}, # Para mostrar en dashboard
        'afectados_cuanticos': [] # Para visualización temporal
    }
    
    registro_saltos = []
    stun_usado = False
    
    while max(pos.values()) < META:
        limpiar_pantalla()
        print(f"{Color.BOLD}GRAND PRIX - CARRERA {numero_carrera}{Color.RESET}")
        
        # Calcular Ranking actual
        ranking = sorted(pos.items(), key=lambda item: item[1], reverse=True)
        ranking_ids = [r[0] for r in ranking] # Lista ordenada de IDs
        
        # --- CÁLCULO DE BETA DINÁMICO (Antes de dibujar) ---
        for bus_id in [b['id'] for b in buses]:
            rank_actual = ranking_ids.index(bus_id)
            total_buses = len(buses)
            
            # Caos
            estado['semilla_caos'][bus_id] = mapa_logistico(estado['semilla_caos'][bus_id])
            perturbacion = estado['semilla_caos'][bus_id] * 0.2
            
            # Factor posición (Si vas último, Beta baja -> más locura)
            factor_pos = 1 - (rank_actual / max(1, total_buses - 1))
            beta_dinamico = 1.1 + (factor_pos * 0.7) + (perturbacion * 0.1)
            estado['beta_actual'][bus_id] = beta_dinamico

        # --- DIBUJAR DASHBOARD SUPERIOR ---
        dibujar_telemetria(buses, pos, estado, ranking_ids)

        mensajes_evento = []

        # --- EVENTO CUÁNTICO ---
        estado['afectados_cuanticos'] = [] # Reset visual
        if random.random() < PROB_RETROCESO_CUANTICO:
            k = max(1, len(buses) // 2)
            estado['afectados_cuanticos'] = random.sample([b['id'] for b in buses], k)
            mensajes_evento.append(f"{Color.PURPLE}🌀 ¡ANOMALÍA CUÁNTICA! Inversión temporal detectada.{Color.RESET}")

        # --- DIBUJAR PISTA Y MOVER ---
        for idx, b in enumerate(buses):
            bus_id = b['id']
            dibujar_bus(b['nombre'], pos[bus_id], META, b['color'])
            if idx != len(buses) - 1: print() # Separador

            # Lógica de movimiento
            if estado['skip_turns'][bus_id] > 0:
                estado['skip_turns'][bus_id] -= 1
                registro_saltos.append({'carrera': numero_carrera, 'bus': bus_id, 'salto': 0})
                continue

            # Salto
            beta = estado['beta_actual'][bus_id]
            salto_levy = paso_levy(beta=beta)
            
            # Inercia
            salto_inercia = (PHI_INERCIA * estado['ultimo_salto'][bus_id]) + ((1 - PHI_INERCIA) * salto_levy)
            salto_final = int(salto_inercia)

            # Aplicar Movimiento
            if bus_id in estado['afectados_cuanticos']:
                pos[bus_id] = max(0, pos[bus_id] - salto_final)
                estado['ultimo_salto'][bus_id] = -salto_final
            else:
                # Recalentamiento
                if salto_final > 20 and estado['saltos_grandes'][bus_id] >= 3:
                     retroceso = int(salto_final * 0.5)
                     pos[bus_id] = max(0, pos[bus_id] - retroceso)
                     estado['retroceso'][bus_id] = True
                     estado['saltos_grandes'][bus_id] = 0
                     mensajes_evento.append(f"🔥 {b['nombre']} se sobrecalienta.")
                else:
                    pos[bus_id] += salto_final
                    estado['retroceso'][bus_id] = False # Reset flag visual
                    estado['ultimo_salto'][bus_id] = salto_final
                    if salto_final > 20: estado['saltos_grandes'][bus_id] += 1

            registro_saltos.append({'carrera': numero_carrera, 'bus': bus_id, 'salto': salto_final})
            estado['movimientos'][bus_id].append(salto_final)

            # Eventos (Jalar/Stun/Poder)
            if random.random() < PROB_JALAR_RIVAL:
                rivales = [oid for oid in pos if oid != bus_id and pos[oid] > pos[bus_id]]
                if rivales:
                    target = random.choice(rivales)
                    pos[target] = pos[bus_id]
                    mensajes_evento.append(f"🧲 {b['nombre']} usó imán contra {target.upper()}!")

            if not stun_usado and random.random() < PROB_STUN_2_TURNOS:
                ops = [oid for oid in pos if oid != bus_id]
                if ops:
                    target = random.choice(ops)
                    estado['skip_turns'][target] += 2
                    stun_usado = True
                    mensajes_evento.append(f"💫 {b['nombre']} aturdió a {target.upper()}!")

            # Poder especial
            lim = config_carrera[bus_id]['limite_poder']
            hist = estado['movimientos'][bus_id]
            if len(hist) >= 5 and all(x < 5 for x in hist[-5:]) and estado['usos_poder'][bus_id] < lim:
                 ops = [oid for oid in pos if oid != bus_id]
                 if ops:
                     target = random.choice(ops)
                     dmg = sum(hist[-5:])
                     pos[target] = max(0, pos[target] - dmg)
                     estado['usos_poder'][bus_id] += 1
                     mensajes_evento.append(f"⚡ {b['nombre']} descargó energía sobre {target.upper()}!")

        if mensajes_evento:
            print(f"\n{Color.CYAN}--- LISTA DE EVENTOS ---{Color.RESET}")
            print("\n".join(mensajes_evento))
            time.sleep(1.5)

        time.sleep(DELAY_TURNO)

    ganador = max(pos, key=pos.get)
    ultimos_saltos = {bid: (estado['movimientos'][bid][-1] if estado['movimientos'][bid] else 0) for bid in pos}
    return ganador, registro_saltos, ultimos_saltos, pos

def main():
    try:
        num_carreras = int(input("¿Cuántas carreras quieres simular? "))
        num_buses = int(input("¿Cuántos buses (2-5)? "))
    except ValueError:
        return

    buses_disponibles = [
        {'id': 'coca', 'nombre': 'COCA COLA', 'color': Color.RED},
        {'id': 'pepsi', 'nombre': 'PEPSI', 'color': Color.BLUE},
        {'id': 'fanta', 'nombre': 'FANTA', 'color': Color.ORANGE},
        {'id': 'sprite', 'nombre': 'SPRITE', 'color': Color.GREEN},
        {'id': 'sevenup', 'nombre': '7UP', 'color': Color.CYAN},
    ]
    buses = buses_disponibles[:max(2, min(num_buses, 5))]

    historial_ganadores = []
    todos_los_saltos = []
    puntuacion_global = {b['id']: 0 for b in buses}
    historial_ultimos_saltos = {b['id']: [] for b in buses}
    racha_derrotas = {b['id']: 0 for b in buses}
    ultima_pos_inicio = {b['id']: 0 for b in buses}

    for i in range(num_carreras):
        idx = i + 1
        config = {b['id']: {'inicio': 0, 'beta': 1.5, 'limite_poder': 2} for b in buses}
        
        # Intervenciones (Catch-up / Handicap)
        mensajes_intervencion = []
        limite_meta = int(META * 0.75)
        
        if len(historial_ganadores) >= 2 and historial_ganadores[-1] == historial_ganadores[-2]:
             g = historial_ganadores[-1]
             config[g]['limite_poder'] = 1
             config[g]['inicio'] = -15
             mensajes_intervencion.append(f"⚖️ Handicap aplicado a {g.upper()}.")

        for bid in buses:
            bus_id = bid['id']
            if racha_derrotas[bus_id] >= 2:
                base = 10
                if len(historial_ultimos_saltos[bus_id]) >= 1:
                     base = abs(historial_ultimos_saltos[bus_id][-1]) * 2
                inicio_calc = min(base * random.randint(1, 5), limite_meta)
                config[bus_id]['inicio'] = int(inicio_calc)
                mensajes_intervencion.append(f"🚀 Catch-up activado para {bid['nombre']}.")

        if mensajes_intervencion:
            print("\n" + "\n".join(mensajes_intervencion))
            input("Presiona Enter para iniciar...")

        ganador, saltos_carrera, ultimos, posiciones_finales = correr_carrera(config, buses, idx)
        
        historial_ganadores.append(ganador)
        todos_los_saltos.extend(saltos_carrera)
        
        print(f"\n🏆 GANADOR CARRERA {idx}: {ganador.upper()} (+50 Pts)")
        puntuacion_global[ganador] += 50
        for bid, metros in posiciones_finales.items():
            pts_distancia = int(metros * 0.5)
            puntuacion_global[bid] += pts_distancia
            print(f"   - {bid.upper()}: +{pts_distancia} pts por distancia.")

        for bid, u_salto in ultimos.items():
            historial_ultimos_saltos[bid].append(u_salto)
            ultima_pos_inicio[bid] = int(config[bid]['inicio'])
            if bid == ganador:
                racha_derrotas[bid] = 0
            else:
                racha_derrotas[bid] += 1
        
        time.sleep(2)

    limpiar_pantalla()
    print(f"{Color.BOLD}{'='*20} RESULTADOS DEL CAMPEONATO {'='*20}{Color.RESET}")
    podio = sorted(puntuacion_global.items(), key=lambda x: x[1], reverse=True)
    
    for pos, (bid, ptos) in enumerate(podio):
        emoji = "🥇" if pos == 0 else "🥈" if pos == 1 else "🥉" if pos == 2 else "  "
        nombre = next(b['nombre'] for b in buses if b['id'] == bid)
        print(f"{emoji} {pos+1}. {nombre:<10} | Puntos Totales: {ptos}")

    print("\nGenerando gráficos...")
    df = pd.DataFrame(todos_los_saltos)
    grafico = (
        ggplot(df, aes(x='salto', fill='bus'))
        + geom_density(alpha=0.5)
        + facet_wrap('~carrera')
        + theme_dark()
        + labs(title="Distribución de Saltos por Carrera", x="Metros saltados", y="Densidad")
    )
    print(grafico)
    grafico.save("analisis_final.png", width=12, height=8, verbose=False)
    print("\n💾 Gráfico guardado.")

if __name__ == "__main__":
    main()