#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
MEMORIA DE CÁLCULO - PRODUCTIVIDAD DE PERFORACIÓN
Universidad Nacional del Altiplano Puno - Facultad de Ingeniería de Minas
Autor: Capacoila Quispe Luisinho | Docente: Apaza Chino Julian | Año: 2026
APLICACIÓN COMPLETA CON STREAMLIT (versión para GitHub + Streamlit Cloud)
================================================================================
"""

import math
import json
import csv
import io
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# =================================================================================
# 1. LIBRERÍA DE FÓRMULAS (completa, sin cambios)
# =================================================================================

def velocidad_penetracion_basica(recorrido_tricono_m: float, horas_efectivas: float) -> float:
    if horas_efectivas <= 0:
        raise ValueError("Las horas efectivas deben ser mayores a cero")
    return recorrido_tricono_m / horas_efectivas

def velocidad_media_perforacion(vp: float) -> float:
    if vp <= 0:
        raise ValueError("La velocidad de penetración debe ser mayor a cero")
    return 2 * (vp ** 0.65)

def vp_bauer_calder_1967(empuje_libras_por_pulgada: float, 
                         resistencia_compresion_psi: float, 
                         factor_k: float = 1.5) -> float:
    if resistencia_compresion_psi <= 0 or empuje_libras_por_pulgada <= 0:
        raise ValueError("Los valores de empuje y resistencia deben ser positivos")
    ratio = (empuje_libras_por_pulgada / resistencia_compresion_psi) / 12
    if ratio <= 0:
        raise ValueError("El ratio E/RC debe ser positivo")
    log_vp_6 = factor_k * math.log10(ratio)
    vp_pies_hora = 6 * (10 ** log_vp_6)
    return vp_pies_hora * 0.3048

def vp_bauer_1971(resistencia_compresion_miles_psi: float,
                  empuje_unitario_miles_libras_por_pulgada: float,
                  velocidad_rotacion_rpm: float) -> float:
    if resistencia_compresion_miles_psi <= 0:
        raise ValueError("La resistencia a compresión debe ser positiva")
    vp_pies_hora = (61 - 28 * math.log10(resistencia_compresion_miles_psi)) * \
                   empuje_unitario_miles_libras_por_pulgada * \
                   (velocidad_rotacion_rpm / 300)
    return vp_pies_hora * 0.3048

def vp_praillet_1978(empuje_kg: float, 
                     velocidad_rotacion_rpm: float,
                     resistencia_compresion_mpa: float,
                     diametro_broca_mm: float) -> float:
    if resistencia_compresion_mpa <= 0 or diametro_broca_mm <= 0:
        raise ValueError("RC y diámetro deben ser positivos")
    return (empuje_kg * velocidad_rotacion_rpm) / (1000 * resistencia_compresion_mpa * diametro_broca_mm)

def vp_bernaola_1985(longitud_filo_mm: float,
                     numero_golpes_minuto: float,
                     carrera_piston_mm: float,
                     tipo_broca: str = "botones") -> float:
    vp_base = (longitud_filo_mm * numero_golpes_minuto * carrera_piston_mm) / 1000
    factores_correccion = {"botones": 1.15, "bisel": 0.85, "cross": 1.0, "x": 1.0}
    factor = factores_correccion.get(tipo_broca.lower(), 1.0)
    return vp_base * factor

def calcular_longitud_filo(diametro_broca_mm: float, tipo_broca: str = "pastillas") -> float:
    if tipo_broca.lower() == "pastillas":
        return 1.7 * diametro_broca_mm - 0.7
    return diametro_broca_mm

def velocidad_media_numero_varillas(vp_primera_varilla: float, 
                                    numero_varillas: int,
                                    tiempo_cambio_varilla_min: float = 1.5) -> float:
    if numero_varillas <= 0:
        raise ValueError("El número de varillas debe ser mayor a cero")
    longitud_por_varilla = 3.66
    longitud_total = longitud_por_varilla * numero_varillas
    tiempo_perforacion = longitud_total / vp_primera_varilla
    numero_cambios = numero_varillas - 1
    tiempo_cambios = (numero_cambios * tiempo_cambio_varilla_min) / 60.0
    tiempo_total = tiempo_perforacion + tiempo_cambios
    if tiempo_total <= 0:
        return vp_primera_varilla
    return longitud_total / tiempo_total

def velocidad_media_tiempos_muertos(longitud_perforada_m: float,
                                    tiempo_perforacion_pura_h: float,
                                    tiempo_maniobras_h: float) -> float:
    tiempo_total = tiempo_perforacion_pura_h + tiempo_maniobras_h
    if tiempo_total <= 0:
        raise ValueError("El tiempo total debe ser mayor a cero")
    return longitud_perforada_m / tiempo_total

def velocidad_efectiva(vp_teorica: float, factor_utilizacion: float, disponibilidad_mecanica: float) -> float:
    if not (0 <= factor_utilizacion <= 1) or not (0 <= disponibilidad_mecanica <= 1):
        raise ValueError("U y DM deben estar entre 0 y 1")
    return vp_teorica * factor_utilizacion * disponibilidad_mecanica

def tiempo_efectivo_perforacion(tiempo_guardia_h: float,
                                factor_utilizacion: float,
                                disponibilidad_mecanica: float) -> float:
    if not (0 <= factor_utilizacion <= 1) or not (0 <= disponibilidad_mecanica <= 1):
        raise ValueError("U y DM deben estar entre 0 y 1")
    return tiempo_guardia_h * factor_utilizacion * disponibilidad_mecanica

def metros_por_guardia(velocidad_efectiva_m_h: float, tiempo_efectivo_h: float) -> float:
    return velocidad_efectiva_m_h * tiempo_efectivo_h

def metros_por_guardia_completo(vm_media: float, tiempo_guardia_h: float,
                                disponibilidad_mecanica: float, factor_utilizacion: float) -> float:
    return vm_media * tiempo_guardia_h * disponibilidad_mecanica * factor_utilizacion

def costo_horario_total(costo_equipo_usd_h: float, costo_mano_obra_usd_h: float,
                        costo_consumibles_usd_h: float, costo_mantenimiento_usd_h: float) -> float:
    return costo_equipo_usd_h + costo_mano_obra_usd_h + costo_consumibles_usd_h + costo_mantenimiento_usd_h

def costo_por_metro(costo_horario_usd_h: float, velocidad_efectiva_m_h: float) -> float:
    if velocidad_efectiva_m_h <= 0:
        raise ValueError("La velocidad efectiva debe ser mayor a cero")
    return costo_horario_usd_h / velocidad_efectiva_m_h

def costo_consumibles_por_metro(precio_broca_usd: float, vida_util_broca_m: float,
                                precio_barra_usd: float = 0, vida_util_barra_m: float = 1) -> float:
    costo_broca = precio_broca_usd / vida_util_broca_m if vida_util_broca_m > 0 else 0
    costo_barra = precio_barra_usd / vida_util_barra_m if vida_util_barra_m > 0 else 0
    return costo_broca + costo_barra

def costo_total_por_metro(costo_broca_usd: float, metros_perforados_broca: float,
                          costo_horario_usd_h: float, velocidad_penetracion_m_h: float) -> float:
    if metros_perforados_broca <= 0 or velocidad_penetracion_m_h <= 0:
        raise ValueError("M y V deben ser mayores a cero")
    return (costo_broca_usd / metros_perforados_broca) + (costo_horario_usd_h / velocidad_penetracion_m_h)

def tdc_total_drilling_cost(precio_broca_usd: float, metros_perforados_broca: float,
                            costo_horario_perforadora_usd_h: float, velocidad_penetracion_m_h: float) -> float:
    if metros_perforados_broca <= 0 or velocidad_penetracion_m_h <= 0:
        raise ValueError("M y ROP deben ser mayores a cero")
    return (precio_broca_usd / metros_perforados_broca) + (costo_horario_perforadora_usd_h / velocidad_penetracion_m_h)

def costo_amortizacion(precio_adquisicion_usd: float, valor_residual_usd: float, horas_vida_util: float) -> float:
    if horas_vida_util <= 0:
        raise ValueError("Las horas de vida útil deben ser mayores a cero")
    return (precio_adquisicion_usd - valor_residual_usd) / horas_vida_util

def costo_intereses_seguros(precio_adquisicion_usd: float, num_anios_vida: int,
                            porcentaje_intereses_seguros_impuestos: float, horas_trabajo_anio: float) -> float:
    if num_anios_vida <= 0 or horas_trabajo_anio <= 0:
        raise ValueError("N y horas de trabajo deben ser mayores a cero")
    factor = (num_anios_vida + 1) / (2 * num_anios_vida)
    return (factor * precio_adquisicion_usd * (porcentaje_intereses_seguros_impuestos / 100)) / horas_trabajo_anio

def costo_mantenimiento_reparaciones(precio_equipo_usd: float, factor_reparacion_porcentaje: float) -> float:
    return (precio_equipo_usd / 1000) * (factor_reparacion_porcentaje / 100)

def coeficiente_resistencia_protodyakonov(ucs_mpa: float) -> float:
    return ucs_mpa / 10

def clasificar_roca_cerchar(cai: float) -> str:
    if cai < 0.3:
        return "Roca suave (CAI < 0.3)"
    elif cai < 1.0:
        return "Roca media (CAI 0.3 - 1.0)"
    elif cai < 2.0:
        return "Roca abrasiva (CAI 1.0 - 2.0)"
    elif cai < 4.0:
        return "Roca muy abrasiva (CAI 2.0 - 4.0)"
    else:
        return "Roca extremadamente abrasiva (CAI > 4.0)"

def eficiencia_perforacion(avance_real_m: float, longitud_perforada_m: float) -> float:
    if longitud_perforada_m <= 0:
        raise ValueError("La longitud perforada debe ser mayor a cero")
    return avance_real_m / longitud_perforada_m

def tiempo_perforacion_pura(longitud_taladro_m: float, velocidad_penetracion_m_h: float) -> float:
    if velocidad_penetracion_m_h <= 0:
        raise ValueError("La velocidad de penetración debe ser mayor a cero")
    return longitud_taladro_m / velocidad_penetracion_m_h

def convertir_pies_a_metros(pies: float) -> float:
    return pies * 0.3048
def convertir_metros_a_pies(metros: float) -> float:
    return metros / 0.3048
def convertir_psi_a_mpa(psi: float) -> float:
    return psi * 0.00689476
def convertir_mpa_a_psi(mpa: float) -> float:
    return mpa / 0.00689476
def convertir_libras_a_kg(libras: float) -> float:
    return libras * 0.453592
def convertir_kg_a_libras(kg: float) -> float:
    return kg / 0.453592

# =================================================================================
# 2. CLASES DE DATOS Y CALCULADORA
# =================================================================================

class DatosEquipo:
    def __init__(self, tipo, num_brazos=1, potencia_martillo_kw=0.0, presion_operacion_bar=0.0,
                 disponibilidad_mecanica=0.90, factor_utilizacion=0.80):
        self.tipo = tipo
        self.num_brazos = num_brazos
        self.potencia_martillo_kw = potencia_martillo_kw
        self.presion_operacion_bar = presion_operacion_bar
        self.disponibilidad_mecanica = disponibilidad_mecanica
        self.factor_utilizacion = factor_utilizacion

class DatosRoca:
    def __init__(self, ucs_mpa, cai=0.5, rqd=80.0):
        self.ucs_mpa = ucs_mpa
        self.cai = cai
        self.rqd = rqd
    @property
    def coeficiente_protodyakonov(self):
        return coeficiente_resistencia_protodyakonov(self.ucs_mpa)
    @property
    def clasificacion(self):
        return clasificar_roca_cerchar(self.cai)

class DatosTaladros:
    def __init__(self, diametro_broca_mm, longitud_taladro_m, num_taladros_por_disparo=1, eficiencia_perforacion=0.95):
        self.diametro_broca_mm = diametro_broca_mm
        self.longitud_taladro_m = longitud_taladro_m
        self.num_taladros_por_disparo = num_taladros_por_disparo
        self.eficiencia_perforacion = eficiencia_perforacion

class DatosTiempos:
    def __init__(self, tiempo_perforacion_neta_min, tiempo_posicionamiento_min=5.0,
                 tiempo_extension_aceros_min=0.0, tiempo_mantenimiento_preventivo_h=0.5, duracion_guardia_h=8.0):
        self.tiempo_perforacion_neta_min = tiempo_perforacion_neta_min
        self.tiempo_posicionamiento_min = tiempo_posicionamiento_min
        self.tiempo_extension_aceros_min = tiempo_extension_aceros_min
        self.tiempo_mantenimiento_preventivo_h = tiempo_mantenimiento_preventivo_h
        self.duracion_guardia_h = duracion_guardia_h

class DatosCostos:
    def __init__(self, costo_equipo_usd_h, costo_mano_obra_usd_h, costo_consumibles_usd_h=0.0,
                 costo_mantenimiento_usd_h=0.0, precio_broca_usd=230.0, vida_util_broca_m=250.0,
                 precio_barra_usd=800.0, vida_util_barra_m=1000.0):
        self.costo_equipo_usd_h = costo_equipo_usd_h
        self.costo_mano_obra_usd_h = costo_mano_obra_usd_h
        self.costo_consumibles_usd_h = costo_consumibles_usd_h
        self.costo_mantenimiento_usd_h = costo_mantenimiento_usd_h
        self.precio_broca_usd = precio_broca_usd
        self.vida_util_broca_m = vida_util_broca_m
        self.precio_barra_usd = precio_barra_usd
        self.vida_util_barra_m = vida_util_barra_m

class CalculadoraPerforacion:
    def __init__(self, equipo, roca, taladros, tiempos, costos):
        self.equipo = equipo
        self.roca = roca
        self.taladros = taladros
        self.tiempos = tiempos
        self.costos = costos
        self.resultados = {}

    def calcular_velocidad_penetracion_teorica(self, metodo="campo", vp_campo=45.0,
                                               empuje_kg=5000.0, rpm=100.0):
        if metodo == "campo":
            return vp_campo
        elif metodo == "praillet":
            return vp_praillet_1978(empuje_kg, rpm, self.roca.ucs_mpa, self.taladros.diametro_broca_mm)
        elif metodo == "bernaola":
            longitud_filo = calcular_longitud_filo(self.taladros.diametro_broca_mm)
            return vp_bernaola_1985(longitud_filo, 3000, 50, "botones")
        elif metodo == "bauer_calder":
            ucs_psi = convertir_mpa_a_psi(self.roca.ucs_mpa)
            empuje_libras_pulgada = convertir_kg_a_libras(empuje_kg) / (self.taladros.diametro_broca_mm / 25.4)
            return vp_bauer_calder_1967(empuje_libras_pulgada, ucs_psi)
        elif metodo == "bauer_1971":
            ucs_miles_psi = convertir_mpa_a_psi(self.roca.ucs_mpa) / 1000
            empuje_unitario = convertir_kg_a_libras(empuje_kg) / (self.taladros.diametro_broca_mm / 25.4) / 1000
            return vp_bauer_1971(ucs_miles_psi, empuje_unitario, rpm)
        else:
            raise ValueError(f"Método '{metodo}' no reconocido")

    def calcular_productividad_completa(self, vp_teorica):
        ve = velocidad_efectiva(vp_teorica, self.equipo.factor_utilizacion, self.equipo.disponibilidad_mecanica)
        te = tiempo_efectivo_perforacion(self.tiempos.duracion_guardia_h, self.equipo.factor_utilizacion, self.equipo.disponibilidad_mecanica)
        vm = velocidad_media_perforacion(vp_teorica)
        mg = metros_por_guardia(ve, te)
        tp = tiempo_perforacion_pura(self.taladros.longitud_taladro_m, vp_teorica)
        tiempo_maniobras_h = (self.tiempos.tiempo_posicionamiento_min + self.tiempos.tiempo_extension_aceros_min) / 60
        vm_real = velocidad_media_tiempos_muertos(self.taladros.longitud_taladro_m, tp, tiempo_maniobras_h)
        self.resultados = {
            "velocidad_penetracion_teorica": vp_teorica,
            "velocidad_efectiva": ve,
            "tiempo_efectivo_h": te,
            "velocidad_media": vm,
            "metros_por_guardia": mg,
            "tiempo_perforacion_pura_h": tp,
            "tiempo_maniobras_h": tiempo_maniobras_h,
            "velocidad_media_real": vm_real,
            "eficiencia_perforacion": self.taladros.eficiencia_perforacion,
            "num_taladros_guardia": int(mg / self.taladros.longitud_taladro_m) if self.taladros.longitud_taladro_m > 0 else 0
        }
        return self.resultados

    def calcular_costos_completos(self):
        if not self.resultados:
            raise ValueError("Primero debe calcular la productividad con calcular_productividad_completa()")
        ve = self.resultados["velocidad_efectiva"]
        vp_teorica = self.resultados["velocidad_penetracion_teorica"]
        ch = costo_horario_total(self.costos.costo_equipo_usd_h, self.costos.costo_mano_obra_usd_h,
                                 self.costos.costo_consumibles_usd_h, self.costos.costo_mantenimiento_usd_h)
        cm = costo_por_metro(ch, ve)
        c_cons_m = costo_consumibles_por_metro(self.costos.precio_broca_usd, self.costos.vida_util_broca_m,
                                               self.costos.precio_barra_usd, self.costos.vida_util_barra_m)
        c_total = costo_total_por_metro(self.costos.precio_broca_usd, self.costos.vida_util_broca_m, ch, vp_teorica)
        tdc = tdc_total_drilling_cost(self.costos.precio_broca_usd, self.costos.vida_util_broca_m, ch, vp_teorica)
        costo_directo = cm + c_cons_m
        costos_resultados = {
            "costo_horario_total_usd_h": ch,
            "costo_por_metro_operativo_usd_m": cm,
            "costo_consumibles_usd_m": c_cons_m,
            "costo_total_por_metro_usd_m": c_total,
            "tdc_usd_m": tdc,
            "costo_directo_total_usd_m": costo_directo
        }
        self.resultados.update(costos_resultados)
        return costos_resultados

    def generar_reporte(self):
        if not self.resultados:
            return "Error: No se han calculado resultados aún."
        r = self.resultados
        return f"""
{'='*70}
    MEMORIA DE CÁLCULO - PRODUCTIVIDAD DE PERFORACIÓN
    Universidad Nacional del Altiplano Puno
    Facultad de Ingeniería de Minas - 2026
{'='*70}

DATOS DE ENTRADA:
-----------------
EQUIPO:
  - Tipo: {self.equipo.tipo}
  - Número de brazos: {self.equipo.num_brazos}
  - Potencia del martillo: {self.equipo.potencia_martillo_kw} kW
  - Presión de operación: {self.equipo.presion_operacion_bar} bar
  - Disponibilidad mecánica: {self.equipo.disponibilidad_mecanica:.0%}
  - Factor de utilización: {self.equipo.factor_utilizacion:.0%}

ROCA:
  - UCS: {self.roca.ucs_mpa} MPa
  - Coef. Protodyakonov (f): {self.roca.coeficiente_protodyakonov:.2f}
  - CAI: {self.roca.cai}
  - Clasificación: {self.roca.clasificacion}
  - RQD: {self.roca.rqd}%

TALADROS:
  - Diámetro de broca: {self.taladros.diametro_broca_mm} mm
  - Longitud de taladro: {self.taladros.longitud_taladro_m} m
  - Número de taladros/disparo: {self.taladros.num_taladros_por_disparo}
  - Eficiencia de perforación: {self.taladros.eficiencia_perforacion:.0%}

TIEMPOS:
  - Duración de guardia: {self.tiempos.duracion_guardia_h} h
  - Tiempo perforación neta: {self.tiempos.tiempo_perforacion_neta_min} min
  - Tiempo posicionamiento: {self.tiempos.tiempo_posicionamiento_min} min
  - Tiempo extensión aceros: {self.tiempos.tiempo_extension_aceros_min} min

COSTOS:
  - Costo equipo: ${self.costos.costo_equipo_usd_h:.2f}/h
  - Costo mano de obra: ${self.costos.costo_mano_obra_usd_h:.2f}/h
  - Costo consumibles: ${self.costos.costo_consumibles_usd_h:.2f}/h
  - Costo mantenimiento: ${self.costos.costo_mantenimiento_usd_h:.2f}/h
  - Precio broca: ${self.costos.precio_broca_usd:.2f}
  - Vida útil broca: {self.costos.vida_util_broca_m} m
  - Precio barra: ${self.costos.precio_barra_usd:.2f}
  - Vida útil barra: {self.costos.vida_util_barra_m} m

{'='*70}
RESULTADOS DE PRODUCTIVIDAD:
{'='*70}
  Velocidad de Penetración (VP):     {r.get('velocidad_penetracion_teorica', 0):.2f} m/h
  Velocidad Efectiva (Ve):           {r.get('velocidad_efectiva', 0):.2f} m/h
  Velocidad Media (VM):              {r.get('velocidad_media', 0):.2f} m/h
  Velocidad Media Real:              {r.get('velocidad_media_real', 0):.2f} m/h
  Tiempo Efectivo de Perforación:    {r.get('tiempo_efectivo_h', 0):.2f} h
  Tiempo Perforación Pura:           {r.get('tiempo_perforacion_pura_h', 0):.2f} h
  Tiempo Maniobras:                  {r.get('tiempo_maniobras_h', 0):.2f} h
  Metros por Guardia:                {r.get('metros_por_guardia', 0):.2f} m/guardia
  Taladros por Guardia:              {r.get('num_taladros_guardia', 0)} taladros

{'='*70}
RESULTADOS DE COSTOS:
{'='*70}
  Costo Horario Total:               ${r.get('costo_horario_total_usd_h', 0):.2f}/h
  Costo por Metro (Operativo):       ${r.get('costo_por_metro_operativo_usd_m', 0):.2f}/m
  Costo Consumibles:                 ${r.get('costo_consumibles_usd_m', 0):.2f}/m
  Costo Total por Metro:             ${r.get('costo_total_por_metro_usd_m', 0):.2f}/m
  TDC (Total Drilling Cost):         ${r.get('tdc_usd_m', 0):.2f}/m
  Costo Directo Total:               ${r.get('costo_directo_total_usd_m', 0):.2f}/m

{'='*70}
"""

# =================================================================================
# 3. FUNCIONES PARA GRÁFICAS (matplotlib)
# =================================================================================

def nomograma_vp_resistencia_compresion():
    fig, ax = plt.subplots(figsize=(10, 8))
    ucs_mpa = np.linspace(20, 300, 100)
    ucs_psi = ucs_mpa * 145.038
    empujes = [1000, 2000, 3000, 5000, 8000, 12000]
    colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    for empuje, color in zip(empujes, colores):
        vp_pies_hora = []
        for ucs in ucs_psi:
            try:
                vp = vp_bauer_calder_1967(empuje, ucs, factor_k=1.5)
                vp_pies = vp / 0.3048
                vp_pies_hora.append(vp_pies)
            except:
                vp_pies_hora.append(np.nan)
        ax.plot(ucs_mpa, vp_pies_hora, color=color, linewidth=2.5, label=f'E = {empuje} lb/in')
    ax.set_xlabel('Resistencia a Compresión (UCS) [MPa]', fontsize=12, fontweight='bold')
    ax.set_ylabel('Velocidad de Penetración (VP) [pies/h]', fontsize=12, fontweight='bold')
    ax.set_title('NOMOGRAMA: Estimación de VP a partir de la Resistencia a Compresión', fontsize=14, fontweight='bold')
    ax.legend(title='Empuje Unitario', loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.axvspan(20, 50, alpha=0.1, color='green')
    ax.axvspan(50, 150, alpha=0.1, color='yellow')
    ax.axvspan(150, 250, alpha=0.1, color='orange')
    ax.axvspan(250, 300, alpha=0.1, color='red')
    ax.text(35, 75, 'BLANDA', ha='center', color='green', fontweight='bold')
    ax.text(100, 75, 'MEDIA', ha='center', color='goldenrod', fontweight='bold')
    ax.text(200, 75, 'DURA', ha='center', color='darkorange', fontweight='bold')
    ax.text(275, 75, 'MUY DURA', ha='center', color='darkred', fontweight='bold')
    plt.tight_layout()
    return fig

def grafica_comparativa_metodos_perforacion():
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    ucs_mpa = 150
    diametro_broca = 45
    empuje_kg = 8000
    rpm = 150
    ax1 = axes[0,0]
    ucs_range = np.linspace(30, 250, 50)
    vp_praillet = [vp_praillet_1978(empuje_kg, rpm, ucs, diametro_broca) for ucs in ucs_range]
    longitud_filo = calcular_longitud_filo(diametro_broca)
    vp_bernaola = [vp_bernaola_1985(longitud_filo, 2500, 60, "botones") for _ in ucs_range]
    ax1.plot(ucs_range, vp_praillet, 'b-', label='Praillet (1978)')
    ax1.plot(ucs_range, vp_bernaola, 'r-', label='Bernaola (1985)')
    ax1.set_xlabel('UCS [MPa]'); ax1.set_ylabel('VP [m/h]'); ax1.set_title('Comparación de Modelos'); ax1.legend(); ax1.grid(True)
    ax2 = axes[0,1]
    diametros = np.arange(25, 200, 5)
    vp_vs_diametro = [vp_praillet_1978(empuje_kg, rpm, ucs_mpa, d) for d in diametros]
    ax2.plot(diametros, vp_vs_diametro, 'g-', marker='D')
    ax2.set_xlabel('Diámetro de Broca [mm]'); ax2.set_ylabel('VP [m/h]'); ax2.set_title('VP vs Diámetro'); ax2.grid(True)
    ax3 = axes[1,0]
    rpm_range = np.linspace(50, 400, 50)
    vp_vs_rpm = [vp_praillet_1978(empuje_kg, r, ucs_mpa, diametro_broca) for r in rpm_range]
    ax3.plot(rpm_range, vp_vs_rpm, 'purple', marker='^')
    ax3.set_xlabel('RPM'); ax3.set_ylabel('VP [m/h]'); ax3.set_title('VP vs RPM'); ax3.grid(True)
    ax4 = axes[1,1]
    empujes = np.linspace(1000, 20000, 50)
    vp_vs_empuje = [vp_praillet_1978(e, rpm, ucs_mpa, diametro_broca) for e in empujes]
    ax4.plot(empujes, vp_vs_empuje, 'darkorange', marker='v')
    ax4.set_xlabel('Empuje [kg]'); ax4.set_ylabel('VP [m/h]'); ax4.set_title('VP vs Empuje'); ax4.grid(True)
    plt.suptitle('ANÁLISIS COMPARATIVO DE MÉTODOS DE PERFORACIÓN', fontsize=16, fontweight='bold')
    plt.tight_layout()
    return fig

def grafica_sensibilidad_productividad():
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    vp_base, dm_base, u_base, tg = 45, 0.90, 0.80, 8
    ax1 = axes[0,0]
    vp_range = np.linspace(10, 80, 50)
    metros_vp = [metros_por_guardia_completo(velocidad_media_perforacion(vp), tg, dm_base, u_base) for vp in vp_range]
    ax1.plot(vp_range, metros_vp, 'b-')
    ax1.axvline(x=45, color='red', linestyle='--', label='VP base')
    ax1.set_xlabel('VP [m/h]'); ax1.set_ylabel('Metros/Guardia [m]'); ax1.set_title('Sensibilidad a VP'); ax1.legend(); ax1.grid(True)
    ax2 = axes[0,1]
    dm_range = np.linspace(0.5, 0.98, 50)
    metros_dm = [metros_por_guardia_completo(velocidad_media_perforacion(vp_base), tg, dm, u_base) for dm in dm_range]
    ax2.plot(dm_range, metros_dm, 'g-')
    ax2.axvline(x=0.90, color='red', linestyle='--', label='DM base')
    ax2.set_xlabel('Disponibilidad Mecánica'); ax2.set_ylabel('Metros/Guardia [m]'); ax2.set_title('Sensibilidad a DM'); ax2.legend(); ax2.grid(True)
    ax3 = axes[1,0]
    u_range = np.linspace(0.4, 0.95, 50)
    metros_u = [metros_por_guardia_completo(velocidad_media_perforacion(vp_base), tg, dm_base, u) for u in u_range]
    ax3.plot(u_range, metros_u, 'r-')
    ax3.axvline(x=0.80, color='blue', linestyle='--', label='U base')
    ax3.set_xlabel('Factor de Utilización'); ax3.set_ylabel('Metros/Guardia [m]'); ax3.set_title('Sensibilidad a Utilización'); ax3.legend(); ax3.grid(True)
    ax4 = axes[1,1]
    vp_grid = np.linspace(20, 70, 30)
    dm_grid = np.linspace(0.6, 0.98, 30)
    VP, DM = np.meshgrid(vp_grid, dm_grid)
    MG = np.zeros_like(VP)
    for i in range(VP.shape[0]):
        for j in range(VP.shape[1]):
            MG[i,j] = metros_por_guardia_completo(velocidad_media_perforacion(VP[i,j]), tg, DM[i,j], u_base)
    contour = ax4.contourf(VP, DM, MG, levels=20, cmap='viridis')
    plt.colorbar(contour, ax=ax4, label='Metros/Guardia [m]')
    ax4.set_xlabel('VP [m/h]'); ax4.set_ylabel('DM'); ax4.set_title('Mapa de Calor VP vs DM')
    plt.suptitle('ANÁLISIS DE SENSIBILIDAD', fontsize=16, fontweight='bold')
    plt.tight_layout()
    return fig

def grafica_analisis_costos():
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    ch = 105.82
    pb, vu_b, pbarr, vu_barr = 230, 250, 800, 1000
    ax1 = axes[0,0]
    vp_range = np.linspace(10, 80, 50)
    costos_vp = [costo_total_por_metro(pb, vu_b, ch, vp) for vp in vp_range]
    ax1.plot(vp_range, costos_vp, 'b-')
    ax1.axvline(x=45, color='red', linestyle='--', label='VP=45 m/h')
    ax1.set_xlabel('VP [m/h]'); ax1.set_ylabel('Costo Total [USD/m]'); ax1.set_title('Costo Total vs VP'); ax1.legend(); ax1.grid(True)
    ax2 = axes[0,1]
    vp_ej = 45
    c_broca = pb / vu_b
    c_barra = pbarr / vu_barr
    c_operativo = ch / vp_ej
    componentes = [c_broca, c_barra, c_operativo]
    etiquetas = [f'Broca\n${c_broca:.2f}/m', f'Barra\n${c_barra:.2f}/m', f'Operativo\n${c_operativo:.2f}/m']
    ax2.pie(componentes, labels=etiquetas, autopct='%1.1f%%', startangle=90)
    ax2.set_title('Desglose de Costos (VP=45 m/h)')
    ax3 = axes[1,0]
    vu_range = np.linspace(50, 500, 50)
    tdc_values = [tdc_total_drilling_cost(pb, vu, ch, vp_ej) for vu in vu_range]
    ax3.plot(vu_range, tdc_values, 'purple')
    ax3.axvline(x=250, color='red', linestyle='--', label='VU base')
    ax3.set_xlabel('Vida Útil Broca [m]'); ax3.set_ylabel('TDC [USD/m]'); ax3.set_title('TDC vs VU Broca'); ax3.legend(); ax3.grid(True)
    ax4 = axes[1,1]
    equipos = ['Jackleg', 'Jumbo', 'Simba', 'DTH']
    costos_eq = [45, 105.82, 150, 200]
    vps_eq = [15, 45, 35, 25]
    costos_m = [c/v for c,v in zip(costos_eq, vps_eq)]
    bars = ax4.bar(equipos, costos_m, color=['#e74c3c','#3498db','#2ecc71','#f39c12'])
    ax4.set_ylabel('Costo Operativo [USD/m]'); ax4.set_title('Costo por Metro según Equipo')
    for bar, costo in zip(bars, costos_m):
        ax4.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f'${costo:.2f}', ha='center', va='bottom')
    plt.suptitle('ANÁLISIS DE COSTOS', fontsize=16, fontweight='bold')
    plt.tight_layout()
    return fig

def grafica_tiempos_ciclo():
    fig, ax = plt.subplots(figsize=(12, 8))
    actividades = [
        ('Posicionamiento', 0, 5, '#3498db'),
        ('Perforación Pura', 5, 15, '#2ecc71'),
        ('Extensión de Aceros', 20, 3, '#f39c12'),
        ('Perforación Pura (2da)', 23, 12, '#2ecc71'),
        ('Soplado', 35, 2, '#e74c3c'),
        ('Retiro de Varillaje', 37, 4, '#9b59b6'),
        ('Mantenimiento', 41, 2, '#95a5a6')
    ]
    y_pos = np.arange(len(actividades))
    for i, (act, inicio, duracion, color) in enumerate(actividades):
        ax.barh(i, duracion, left=inicio, height=0.6, color=color, edgecolor='black')
        ax.text(inicio+duracion/2, i, f'{duracion} min', ha='center', va='center', color='white', fontweight='bold')
    ax.set_yticks(y_pos); ax.set_yticklabels([a[0] for a in actividades])
    ax.set_xlabel('Tiempo [minutos]'); ax.set_title('DIAGRAMA DE TIEMPOS DE CICLO')
    ax.axvline(x=43, color='red', linestyle='--', label='Total ciclo: 43 min')
    ax.legend(); ax.grid(True, axis='x')
    plt.tight_layout()
    return fig

def grafica_rendimientos_equipos():
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.axis('off')
    datos = [
        ['TIPO DE PERFORADORA', 'DIÁMETRO (mm)', 'APLICACIÓN', 'VP TÍPICA (m/h)', 'MP/GUARDIA (m)'],
        ['Jackleg (neumático)', '32-45', 'Desarrollo', '8-15', '40-80'],
        ['Stoper (neumático)', '32-45', 'Preparación', '10-18', '50-100'],
        ['Jumbo 1 brazo', '38-51', 'Desarrollo', '20-35', '100-180'],
        ['Jumbo 2 brazos', '38-51', 'Desarrollo', '25-40', '150-250'],
        ['Simba (producción)', '51-65', 'Producción', '15-30', '120-200'],
        ['DTH (cielo abierto)', '100-200', 'Perforación primaria', '10-25', '80-150'],
        ['DTH (subterráneo)', '75-165', 'Perforación larga', '12-28', '100-180'],
        ['Top hammer (percusión)', '64-102', 'Banqueo', '18-35', '140-250'],
        ['Rotativa (tricono)', '127-311', 'Cielo abierto', '5-20', '40-120'],
        ['Perforadora manual', '28-38', 'Trabajos menores', '3-8', '15-40']
    ]
    tabla = ax.table(cellText=datos[1:], colLabels=datos[0], cellLoc='center', loc='center', colColours=['#2c3e50']*5)
    tabla.auto_set_font_size(False); tabla.set_fontsize(10); tabla.scale(1.2, 2.5)
    for i in range(5):
        tabla[(0,i)].set_text_props(color='white', fontweight='bold')
        tabla[(0,i)].set_facecolor('#2c3e50')
    colores_filas = ['#ecf0f1', '#bdc3c7']
    for i in range(1, len(datos)):
        for j in range(5):
            tabla[(i,j)].set_facecolor(colores_filas[i%2])
            if j==0: tabla[(i,j)].set_text_props(fontweight='bold')
    ax.set_title('RENDIMIENTOS DE EQUIPOS DE PERFORACIÓN', fontsize=14, fontweight='bold', pad=30)
    plt.tight_layout()
    return fig

# =================================================================================
# 4. APLICACIÓN PRINCIPAL CON STREAMLIT
# =================================================================================

def main():
    st.set_page_config(page_title="Productividad de Perforación", layout="wide")
    st.title("📊 MEMORIA DE CÁLCULO - PRODUCTIVIDAD DE PERFORACIÓN")
    st.markdown("**Universidad Nacional del Altiplano Puno - Facultad de Ingeniería de Minas**")
    st.markdown("---")

    # Inicializar estado de sesión
    if 'calculadora' not in st.session_state:
        st.session_state.calculadora = None
    if 'resultados' not in st.session_state:
        st.session_state.resultados = None

    # ---------- SIDEBAR: DATOS DE ENTRADA ----------
    with st.sidebar:
        st.header("⚙️ Parámetros de entrada")
        
        # Selección rápida de equipo
        equipos_predef = {
            "Jackleg (neumático)": {"vp":12, "dm":0.85, "u":0.70, "costo_eq":15, "costo_mo":20, "diam":38, "potencia":5, "presion":7},
            "Stoper (neumático)": {"vp":15, "dm":0.85, "u":0.72, "costo_eq":18, "costo_mo":20, "diam":38, "potencia":5, "presion":7},
            "Jumbo 1 brazo (hidráulico)": {"vp":30, "dm":0.90, "u":0.80, "costo_eq":50, "costo_mo":35, "diam":45, "potencia":18, "presion":200},
            "Jumbo 2 brazos (hidráulico)": {"vp":40, "dm":0.92, "u":0.82, "costo_eq":70, "costo_mo":45, "diam":45, "potencia":22, "presion":200},
            "Simba (producción)": {"vp":25, "dm":0.88, "u":0.78, "costo_eq":80, "costo_mo":40, "diam":51, "potencia":15, "presion":150},
            "DTH (subterráneo)": {"vp":20, "dm":0.85, "u":0.75, "costo_eq":90, "costo_mo":40, "diam":89, "potencia":20, "presion":250},
            "DTH (cielo abierto)": {"vp":18, "dm":0.82, "u":0.72, "costo_eq":120, "costo_mo":45, "diam":127, "potencia":25, "presion":300},
            "Top hammer (percusión)": {"vp":28, "dm":0.88, "u":0.78, "costo_eq":65, "costo_mo":38, "diam":76, "potencia":18, "presion":180},
            "Rotativa (tricono)": {"vp":15, "dm":0.80, "u":0.70, "costo_eq":100, "costo_mo":35, "diam":152, "potencia":30, "presion":0},
            "Perforadora manual": {"vp":6, "dm":0.75, "u":0.60, "costo_eq":5, "costo_mo":15, "diam":32, "potencia":2, "presion":5}
        }
        equipo_seleccionado = st.selectbox("🔧 Selección rápida de equipo", list(equipos_predef.keys()))
        if st.button("Cargar valores de este equipo"):
            vals = equipos_predef[equipo_seleccionado]
            st.session_update = True
            # Se actualizarán los valores por defecto, pero como Streamlit no tiene 'default' dinámico, se usan session_state
            st.session_state['vp_campo'] = vals["vp"]
            st.session_state['dm'] = vals["dm"]
            st.session_state['u'] = vals["u"]
            st.session_state['costo_eq'] = vals["costo_eq"]
            st.session_state['costo_mo'] = vals["costo_mo"]
            st.session_state['diam'] = vals["diam"]
            st.session_state['potencia'] = vals["potencia"]
            st.session_state['presion'] = vals["presion"]
            st.rerun()
        
        # Inicializar valores por defecto en session_state si no existen
        defaults = {
            'vp_campo': 45.0, 'dm': 0.90, 'u': 0.80, 'costo_eq': 50.63, 'costo_mo': 37.56,
            'diam': 45, 'potencia': 18, 'presion': 200, 'num_brazos': 2, 'ucs': 120.0, 'cai': 2.5,
            'rqd': 75.0, 'long_taladro': 3.5, 'num_taladros': 45, 'eficiencia': 0.95,
            'tp_neta': 4.67, 'tp_pos': 3.0, 'tp_ext': 2.0, 'tp_mant': 0.5, 'guardia': 8.0,
            'costo_cons': 8.5, 'costo_mant': 9.13, 'precio_broca': 230.0, 'vu_broca': 250.0,
            'precio_barra': 800.0, 'vu_barra': 1000.0, 'empuje_kg': 5000, 'rpm': 150
        }
        for key, val in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val
        
        # Datos del equipo
        with st.expander("🚜 Datos del Equipo", expanded=True):
            tipo_equipo = st.text_input("Tipo de equipo", value="Jumbo electrohidráulico")
            num_brazos = st.number_input("N° de brazos", min_value=1, max_value=4, value=st.session_state.num_brazos)
            potencia = st.number_input("Potencia martillo (kW)", value=st.session_state.potencia)
            presion = st.number_input("Presión operación (bar)", value=st.session_state.presion)
            dm = st.slider("Disponibilidad Mecánica", 0.5, 1.0, st.session_state.dm, 0.01)
            u = st.slider("Factor de Utilización", 0.4, 0.98, st.session_state.u, 0.01)
        
        # Propiedades de la roca
        with st.expander("⛰️ Propiedades de la Roca"):
            ucs = st.number_input("UCS (MPa)", min_value=10.0, max_value=500.0, value=st.session_state.ucs)
            cai = st.number_input("CAI", min_value=0.0, max_value=10.0, value=st.session_state.cai)
            rqd = st.slider("RQD (%)", 0, 100, int(st.session_state.rqd))
        
        # Parámetros de perforación
        with st.expander("🔩 Taladros y Perforación"):
            diam = st.number_input("Diámetro broca (mm)", min_value=25, max_value=300, value=st.session_state.diam)
            long_taladro = st.number_input("Longitud taladro (m)", min_value=0.5, max_value=50.0, value=st.session_state.long_taladro)
            num_taladros_disparo = st.number_input("N° taladros/disparo", min_value=1, max_value=200, value=st.session_state.num_taladros)
            eficiencia_perf = st.slider("Eficiencia perforación", 0.7, 1.0, st.session_state.eficiencia)
        
        # Tiempos
        with st.expander("⏱️ Tiempos"):
            tp_neta = st.number_input("Perforación neta (min/taladro)", value=st.session_state.tp_neta)
            tp_pos = st.number_input("Posicionamiento (min)", value=st.session_state.tp_pos)
            tp_ext = st.number_input("Extensión aceros (min)", value=st.session_state.tp_ext)
            tp_mant = st.number_input("Mantenimiento (h/guardia)", value=st.session_state.tp_mant)
            guardia = st.number_input("Duración guardia (h)", value=st.session_state.guardia)
        
        # Costos
        with st.expander("💰 Costos"):
            costo_eq = st.number_input("Costo equipo (USD/h)", value=st.session_state.costo_eq)
            costo_mo = st.number_input("Costo mano de obra (USD/h)", value=st.session_state.costo_mo)
            costo_cons = st.number_input("Consumibles (USD/h)", value=st.session_state.costo_cons)
            costo_mant = st.number_input("Mantenimiento (USD/h)", value=st.session_state.costo_mant)
            precio_broca = st.number_input("Precio broca (USD)", value=st.session_state.precio_broca)
            vu_broca = st.number_input("Vida útil broca (m)", value=st.session_state.vu_broca)
            precio_barra = st.number_input("Precio barra (USD)", value=st.session_state.precio_barra)
            vu_barra = st.number_input("Vida útil barra (m)", value=st.session_state.vu_barra)
        
        # Datos para modelos empíricos (opcional)
        with st.expander("🔬 Modelos empíricos (avanzado)"):
            empuje_kg = st.number_input("Empuje (kg)", value=st.session_state.empuje_kg)
            rpm = st.number_input("RPM", value=st.session_state.rpm)
            metodo_vp = st.selectbox("Método para VP teórica", ["campo", "praillet", "bernaola", "bauer_calder", "bauer_1971"])
        
        # Botón principal de cálculo
        calcular = st.button("🚀 Calcular Productividad y Costos", type="primary")
    
    # Crear objetos de datos con los valores actuales (se toman de session_state y widgets)
    # Nota: los widgets ya tienen sus valores, pero algunos pueden venir de session_state actualizada
    equipo = DatosEquipo(tipo_equipo, num_brazos, potencia, presion, dm, u)
    roca = DatosRoca(ucs, cai, rqd)
    taladros = DatosTaladros(diam, long_taladro, num_taladros_disparo, eficiencia_perf)
    tiempos = DatosTiempos(tp_neta, tp_pos, tp_ext, tp_mant, guardia)
    costos = DatosCostos(costo_eq, costo_mo, costo_cons, costo_mant, precio_broca, vu_broca, precio_barra, vu_barra)
    
    if calcular:
        try:
            calc = CalculadoraPerforacion(equipo, roca, taladros, tiempos, costos)
            vp_teorica = calc.calcular_velocidad_penetracion_teorica(metodo=metodo_vp, vp_campo=st.session_state.vp_campo,
                                                                     empuje_kg=empuje_kg, rpm=rpm)
            calc.calcular_productividad_completa(vp_teorica)
            calc.calcular_costos_completos()
            st.session_state.calculadora = calc
            st.session_state.resultados = calc.resultados
            st.success("✅ Cálculo completado correctamente.")
        except Exception as e:
            st.error(f"Error en el cálculo: {str(e)}")
            st.session_state.calculadora = None
            st.session_state.resultados = None
    
    # Mostrar resultados en pestañas
    if st.session_state.resultados:
        tab1, tab2, tab3, tab4 = st.tabs(["📄 Reporte", "📈 Gráficas", "⚖️ Comparativa", "💾 Exportar"])
        
        with tab1:
            st.markdown(st.session_state.calculadora.generar_reporte())
        
        with tab2:
            st.subheader("Gráficas disponibles")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Nomograma VP vs Resistencia"):
                    st.pyplot(nomograma_vp_resistencia_compresion())
                if st.button("Comparativa de métodos"):
                    st.pyplot(grafica_comparativa_metodos_perforacion())
                if st.button("Análisis de sensibilidad"):
                    st.pyplot(grafica_sensibilidad_productividad())
            with col2:
                if st.button("Análisis de costos"):
                    st.pyplot(grafica_analisis_costos())
                if st.button("Tiempos de ciclo"):
                    st.pyplot(grafica_tiempos_ciclo())
                if st.button("Rendimientos de equipos"):
                    st.pyplot(grafica_rendimientos_equipos())
        
        with tab3:
            st.subheader("Comparativa de 3 escenarios predefinidos")
            if st.button("Ejecutar comparativa"):
                # Escenario 1: Jumbo hidráulico
                eq1 = DatosEquipo("Jumbo Hidráulico", 2, 22, 200, 0.92, 0.85)
                roca1 = DatosRoca(120, 1.5, 85)
                tal1 = DatosTaladros(45, 4.0, 50, 0.95)
                tiem1 = DatosTiempos(4, 2, 0, 0.3, 8)
                cost1 = DatosCostos(55, 40, 10, 8, 250, 300, 900, 1200)
                calc1 = CalculadoraPerforacion(eq1, roca1, tal1, tiem1, cost1)
                calc1.calcular_productividad_completa(50)
                calc1.calcular_costos_completos()
                
                # Escenario 2: Jackleg
                eq2 = DatosEquipo("Jackleg", 1, 5, 7, 0.85, 0.70)
                roca2 = DatosRoca(80, 1.0, 70)
                tal2 = DatosTaladros(38, 1.8, 30, 0.90)
                tiem2 = DatosTiempos(8, 5, 0, 0.5, 8)
                cost2 = DatosCostos(15, 20, 3, 2, 80, 150, 300, 600)
                calc2 = CalculadoraPerforacion(eq2, roca2, tal2, tiem2, cost2)
                calc2.calcular_productividad_completa(12)
                calc2.calcular_costos_completos()
                
                # Escenario 3: Simba
                eq3 = DatosEquipo("Simba", 1, 15, 150, 0.88, 0.78)
                roca3 = DatosRoca(180, 3.0, 75)
                tal3 = DatosTaladros(51, 20.0, 20, 0.92)
                tiem3 = DatosTiempos(45, 10, 5, 1.0, 10)
                cost3 = DatosCostos(80, 45, 12, 10, 350, 200, 1000, 800)
                calc3 = CalculadoraPerforacion(eq3, roca3, tal3, tiem3, cost3)
                calc3.calcular_productividad_completa(25)
                calc3.calcular_costos_completos()
                
                comparativa = f"""
                | Escenario | m/guardia | USD/m (directo) | VP efectiva (m/h) |
                |----------|-----------|----------------|-------------------|
                | Jumbo Hidráulico | {calc1.resultados['metros_por_guardia']:.2f} | {calc1.resultados['costo_directo_total_usd_m']:.2f} | {calc1.resultados['velocidad_efectiva']:.2f} |
                | Jackleg | {calc2.resultados['metros_por_guardia']:.2f} | {calc2.resultados['costo_directo_total_usd_m']:.2f} | {calc2.resultados['velocidad_efectiva']:.2f} |
                | Simba | {calc3.resultados['metros_por_guardia']:.2f} | {calc3.resultados['costo_directo_total_usd_m']:.2f} | {calc3.resultados['velocidad_efectiva']:.2f} |
                """
                st.markdown(comparativa)
        
        with tab4:
            st.subheader("Exportar resultados")
            # CSV
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["Parámetro", "Valor"])
            for k, v in st.session_state.resultados.items():
                writer.writerow([k, v])
            st.download_button("📥 Descargar CSV", csv_buffer.getvalue(), "resultados.csv", "text/csv")
            
            # JSON
            json_buffer = io.StringIO()
            json.dump(st.session_state.resultados, json_buffer, indent=4)
            st.download_button("📥 Descargar JSON", json_buffer.getvalue(), "resultados.json", "application/json")
    else:
        st.info("Ingrese los parámetros en la barra lateral y presione 'Calcular'.")
    
    # Pie de página
    st.markdown("---")
    st.caption("© 2026 - Facultad de Ingeniería de Minas - Universidad Nacional del Altiplano Puno")

if __name__ == "__main__":
    main()