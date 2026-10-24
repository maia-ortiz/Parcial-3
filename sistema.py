import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import pydicom

class VolumenDicom:
    def __init__(self, ruta, nombre_archivo):

        self.__ruta = ruta
        self.__nombre = nombre_archivo

        # Información extraída del dataset DICOM
        self.__filas = 0
        self.__columnas = 0
        self.__nombre_paciente = ""
        self.__modalidad = ""
        self.__medidas = (0.0, 0.0, 0.0) # (alto, largo, ancho) en mm
        self.__matriz_pixeles = None # Cortes originales apilados (n, filas, columnas)
        
        # Info para procesos
        self.__medidas_escaladas = (0.0, 0.0, 0.0) # duplicación del tamaño de los cortes
        self.__volumen = None # Reconstrucción 3D 
        self.__volumen_corregido = None 
        self.__matriz_rotacion = None
        self.__volumen_copia = None 
        self.__corte_ecualizado = None

        # Al crear el objeto se cargan los archivos y se hace la reconstrucción
        self.__cargar_dicom()
        self.__escalar_y_reconstruir()

# Getters
    def ver_nombre(self):
        return self.__nombre

    def ver_ruta(self):
        return self.__ruta

    def ver_filas(self):
        return self.__filas

    def ver_columnas(self):
        return self.__columnas

    def ver_nombre_paciente(self):
        return self.__nombre_paciente

    def ver_modalidad(self):
        return self.__modalidad

    def ver_medidas(self):
        return self.__medidas

    def ver_medidas_escalado(self):
        return self.__medidas_escaladas

    def ver_matriz_pixeles(self):
        return self.__matriz_pixeles

    def ver_volumen(self):
        return self.__volumen

    def ver_volumen_corregido(self):
        return self.__volumen_corregido

    def ver_matriz_rotacion(self):
        return self.__matriz_rotacion

    def ver_corte_ecualizado(self):
        return self.__corte_ecualizado

    def ver_num_cortes(self):
        return self.__volumen.shape[0]
