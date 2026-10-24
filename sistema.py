# Importamos las librerías necesarias
import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import pydicom

# Creamos las clases, primero la clase VolumenDicom 
class VolumenDicom:
    PLANOS = ["transversal", "coronal", "sagital"]
    def __init__(self, nombre, carpeta):
        if not nombre:
            raise ValueError("Error, el volumen debe tener un nombre")
        if not os.path.isdir(carpeta):
            raise ValueError(f'Error, la carpeta {carpeta} no existe')
        
        self.__nombre = nombre
        self.__carpeta = carpeta

        # Información extraída del dataset DICOM
        self.__filas = 0
        self.__columnas = 0
        self.__nombre_paciente = ""
        self.__modalidad = ""
        self.__voxel = (0.0, 0.0, 0.0) # es el alto, largo y ancho en mm
        self.__matriz_pixeles = None # Cortes originales apilados (n, filas, columnas)
        
        # Info para procesos
        self.__voxel_escalado = (0.0, 0.0, 0.0) # duplicación del tamaño de los cortes
        self.__volumen = None # Reconstrucción 3D 
        self.__volumen_corregido = None 
        self.__matriz_rotacion = None
        self.__volumen_copia = None # Es la copia del volumen para ecualizar
        self.__corte_ecualizado = None

        # Al crear el objeto se cargan los archivos y se hace la reconstrucción
        self.__cargar_dicom()
        self.__escalar_y_reconstruir()

# Getters, porque la información del dataset no se modifica desde afuera
    def ver_nombre(self):
        return self.__nombre

    def ver_carpeta(self):
        return self.__carpeta

    def ver_filas(self):
        return self.__filas

    def ver_columnas(self):
        return self.__columnas

    def ver_nombre_paciente(self):
        return self.__nombre_paciente

    def ver_modalidad(self):
        return self.__modalidad

    def ver_voxel(self):
        return self.__voxel

    def ver_voxel_escalado(self):
        return self.__voxel_escalado

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