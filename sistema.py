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

# Lee todos los .dcm de la carpeta (y subcarpetas), los ordena y extrae la información
    def __cargar_dicom(self):
        archivos = []
        for raiz, _, nombres in os.walk(self.__carpeta):
            for n in sorted(nombres):
                if n.lower().endswith(".dcm"):
                    archivos.append(os.path.join(raiz, n))

        if len(archivos) == 0:
            raise ValueError(f"Error, no se encontraron archivos .dcm en {self.__carpeta}")

        datasets = [pydicom.dcmread(a) for a in archivos]

        filas = int(datasets[0].Rows)
        columnas = int(datasets[0].Columns)
        datasets = [d for d in datasets if int(d.Rows) == filas and int(d.Columns) == columnas]
        datasets.sort(key=self.__posicion_corte)

        ds = datasets[0]
        self.__filas = filas
        self.__columnas = columnas
        self.__nombre_paciente = str(ds.PatientName)
        self.__modalidad = str(ds.Modality)

        espaciado = getattr(ds, "PixelSpacing", [1.0, 1.0])
        grosor = float(getattr(ds, "SliceThickness", 1.0))
        self.__voxel = (float(espaciado[0]), float(espaciado[1]), grosor)

        self.__matriz_pixeles = np.stack([d.pixel_array for d in datasets], axis=0)

# Ordena los cortes por su posición real en el espacio (si no hay posición usa InstanceNumber)
    def __posicion_corte(self, ds):
        try:
            orientacion = np.array(ds.ImageOrientationPatient, dtype=float)
            normal = np.cross(orientacion[:3], orientacion[3:])
            posicion = np.array(ds.ImagePositionPatient, dtype=float)
            return float(np.dot(normal, posicion))
        except AttributeError:
            return float(getattr(ds, "InstanceNumber", 0))

# Se escala cada corte al doble de su tamaño y apila todo en el volumen 3D
    def __escalar_y_reconstruir(self):
        cortes = []
        for corte in self.__matriz_pixeles:
            grande = cv2.resize(corte, (self.__columnas * 2, self.__filas * 2), interpolation=cv2.INTER_LINEAR)
            cortes.append(grande)
        self.__volumen = np.stack(cortes, axis=0)

        # Al duplicar los píxeles, cada píxel mide la mitad (el grosor del corte no cambia)
        alto, largo, ancho = self.__voxel
        self.__voxel_escalado = (alto / 2, largo / 2, ancho)

# Devuelve el volumen que se debe usar (el corregido si ya se rotó, si no el original)
    def __volumen_activo(self):
        if self.__volumen_corregido is not None:
            return self.__volumen_corregido
        return self.__volumen

# Convierte cualquier imagen a uint8 (0 - 255)
    def __normalizar_uint8(self, imagen):
        return cv2.normalize(imagen, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)