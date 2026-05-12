# Memoría de Cálculo – Productividad de Perforación

Aplicación interactiva para calcular la productividad y costos de perforación en minería, desarrollada con **Streamlit**.  
Ideal para ingenieros de minas, estudiantes y profesionales del sector.

## 🚀 Características

- ✅ Selección rápida de 10 tipos de equipos predefinidos (Jackleg, Jumbo, Simba, DTH, etc.)
- ✅ Cálculo de **velocidad de penetración (VP)**, **metros por guardia**, **tiempos de ciclo** y **costos por metro**
- ✅ Soporte para múltiples modelos empíricos (Praillet, Bernaola, Bauer & Calder, Bauer 1971)
- ✅ Generación de reporte detallado en formato texto
- ✅ **Gráficas profesionales**:
  - Nomograma VP vs resistencia a compresión
  - Comparativa de métodos de perforación
  - Análisis de sensibilidad (VP, disponibilidad mecánica, utilización)
  - Análisis de costos (TDC, desglose)
  - Diagrama de tiempos de ciclo
  - Tabla de rendimientos de equipos
- ✅ Exportación de resultados a **CSV** y **JSON**
- ✅ Comparativa de tres escenarios predefinidos

## 📦 Requisitos

- Python 3.8 o superior
- Las dependencias se listan en `requirements.txt`

## 🔧 Instalación y ejecución

1. **Clona o descarga este repositorio**

2. **Crea un entorno virtual (opcional pero recomendado)**  
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/macOS
   venv\Scripts\activate         # Windows