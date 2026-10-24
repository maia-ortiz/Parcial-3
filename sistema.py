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

# Creamos el método para leer todos los .dcm de la carpeta y subcarpetas (los ordena y extrae la información)
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

# Creamos otro método que ordene los cortes por su posición real en el espacio (si no hay posición entonces usa InstanceNumber)
    def __posicion_corte(self, ds):
        try:
            orientacion = np.array(ds.ImageOrientationPatient, dtype=float)
            normal = np.cross(orientacion[:3], orientacion[3:])
            posicion = np.array(ds.ImagePositionPatient, dtype=float)
            return float(np.dot(normal, posicion))
        except AttributeError:
            return float(getattr(ds, "InstanceNumber", 0))

# Otro método que escale cada corte al doble de su tamaño y apile todo en el volumen 3D
    def __escalar_y_reconstruir(self):
        cortes = []
        for corte in self.__matriz_pixeles:
            grande = cv2.resize(corte, (self.__columnas * 2, self.__filas * 2), interpolation=cv2.INTER_LINEAR)
            cortes.append(grande)
        self.__volumen = np.stack(cortes, axis=0)

        # Al duplicar los píxeles, cada píxel mide la mitad (el grosor del corte no cambia)
        alto, largo, ancho = self.__voxel
        self.__voxel_escalado = (alto / 2, largo / 2, ancho)

# Otro método que devuelve el volumen que se debe usar (el corregido si el usuario ya lo rotó, si aún no entonces el original)
    def __volumen_activo(self):
        if self.__volumen_corregido is not None:
            return self.__volumen_corregido
        return self.__volumen

# Otro método que convierte cualquier imagen a uint8 (que va de 0 - 255)
    def __normalizar_uint8(self, imagen):
        return cv2.normalize(imagen, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)

# Otro método que rota todos los cortes del volumen (siempre partiendo del volumen original, no se acumulan giros)
    def corregirAngulo(self, angulo):
        if not isinstance(angulo, (int, float)):
            raise ValueError("Error, el ángulo debe ser un número")

        n, filas, columnas = self.__volumen.shape
        centro = (columnas / 2, filas / 2) # Punto medio de la imagen
        matriz = cv2.getRotationMatrix2D(centro, angulo, 1.0)

        # Lo que quede por fuera al rotar se rellena con el valor mínimo del volumen
        relleno = float(self.__volumen.min())
        rotados = []
        for corte in self.__volumen:
            rotado = cv2.warpAffine(corte, matriz, (columnas, filas), flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_CONSTANT, borderValue=relleno)
            rotados.append(rotado)

        self.__matriz_rotacion = matriz
        self.__volumen_corregido = np.stack(rotados, axis=0)

# Llevamos la imagen al rango 0 - 255 ignorando los valores extremos (1% más bajo y 1% más alto),
# así unos pocos píxeles muy brillantes no opacan el resto de la imagen
    def __normalizar_percentil(self, imagen, bajo=1, alto=99):
        f = imagen.astype(np.float32)
        minimo, maximo = np.percentile(f, [bajo, alto])
        f = (f - minimo) / (maximo - minimo + 1e-6) * 255
        return np.clip(f, 0, 255)

# Hacemos el método para ecualizar el histograma, lo dividimos en 5 pasos
    def __ecualizar(self, imagen, fondo=10, limite=1.5, mezcla=0.9):
        tejido = imagen > fondo
        if not tejido.any():
            return np.round(imagen).astype(np.uint8)

        # 1. Histograma de 256 tonos, usando solo los píxeles de tejido
        hist, bordes = np.histogram(imagen[tejido], bins=256, range=(0, 255))
        hist = hist.astype(np.float64)

        # 2. Recortamos los picos muy altos y el exceso se reparte entre todos los tonos disponibles
        tope = limite * hist.mean()
        exceso = np.maximum(hist - tope, 0).sum()
        hist = np.minimum(hist, tope) + exceso / 256

        # 3. Suma acumulada normalizada (0 a 1) = tabla de conversión de tonos
        acumulada = np.cumsum(hist)
        acumulada = (acumulada - acumulada[0]) / (acumulada[-1] - acumulada[0] + 1e-9)
        centros = (bordes[:-1] + bordes[1:]) / 2

        # 4. Se aplica la tabla con interpolación (así se usan tonos intermedios y no quedan huecos en el histograma)
        ecualizada = np.interp(imagen, centros, acumulada * 255)

        # 5. Mezclamos con la imagen original para que no se vea exagerado y poco estético (el fondo no cambia)
        resultado = mezcla * ecualizada + (1 - mezcla) * imagen
        resultado = np.where(tejido, resultado, imagen)
        return np.clip(np.round(resultado), 0, 255).astype(np.uint8)

# Método para normalizar a uint8 un corte transversal de una copia del volumen y lo ecualizamos
    def ecualizar_corte(self, indice, carpeta_salida="resultados"):
        n = self.__volumen_activo().shape[0]
        if indice < 0 or indice >= n:
            raise ValueError(f"Error, el corte debe estar entre 0 y {n - 1}")

        self.__volumen_copia = self.__volumen_activo().copy()
        corte_fino = self.__normalizar_percentil(self.__volumen_copia[indice])
        corte = np.round(corte_fino).astype(np.uint8) # Corte normalizado a uint8

        ecualizada = self.__ecualizar(corte_fino)
        self.__corte_ecualizado = ecualizada

        fig, ejes = plt.subplots(2, 2, figsize=(11, 9))
        ejes[0, 0].imshow(corte, cmap="gray", vmin=0, vmax=255)
        ejes[0, 0].set_title("Corte normalizado (uint8)")
        ejes[0, 1].imshow(ecualizada, cmap="gray", vmin=0, vmax=255)
        ejes[0, 1].set_title("Corte ecualizado")

        ejes[1, 0].hist(corte.ravel(), bins=256, range=(0, 256), color="gray")
        ejes[1, 0].set_title("Histograma antes de ecualizar")
        ejes[1, 1].hist(ecualizada.ravel(), bins=256, range=(0, 256), color="gray")
        ejes[1, 1].set_title("Histograma después de ecualizar")
        for eje in ejes[1]:
            eje.set_yscale("log") # Escala log para ver las barras pequeñas junto al fondo negro
            eje.set_xlabel("Tono de gris")
            eje.set_ylabel("Frecuencia (log)")

        fig.suptitle(f"Ecualización - {self.__nombre} - corte {indice}")
        fig.tight_layout()

        os.makedirs(carpeta_salida, exist_ok=True)
        ruta_grafico = os.path.join(carpeta_salida, f"{self.__nombre}_ecualizacion_corte{indice}.png")
        ruta_imagen = os.path.join(carpeta_salida, f"{self.__nombre}_ecualizada_corte{indice}.png")
        fig.savefig(ruta_grafico)
        cv2.imwrite(ruta_imagen, ecualizada)
        plt.show()
        plt.close(fig)

        return ruta_grafico, ruta_imagen

# Sacamos un corte en el plano pedido y lo deja con píxeles cuadrados
    def __extraer_plano(self, plano, indice):
        volumen = self.__volumen_activo()
        n, filas, columnas = volumen.shape
        mm_filas, mm_columnas, mm_corte = self.__voxel_escalado

        if plano == "transversal":
            maximo = n
        elif plano == "coronal":
            maximo = filas
        elif plano == "sagital":
            maximo = columnas
        else:
            raise ValueError(f"Error, los planos válidos son: {self.PLANOS}")

        if indice < 0 or indice >= maximo:
            raise ValueError(f"Error, para el plano {plano} el índice debe estar entre 0 y {maximo - 1}")

        if plano == "transversal":
            corte = volumen[indice, :, :]
            mm_alto, mm_ancho = mm_filas, mm_columnas
        elif plano == "coronal":
            corte = volumen[:, indice, :]
            mm_alto, mm_ancho = mm_corte, mm_columnas
        else:
            corte = volumen[:, :, indice]
            mm_alto, mm_ancho = mm_corte, mm_filas

        corte = np.ascontiguousarray(corte)

        # Método por si un lado del píxel mide distinto al otro, se estira el corte para igualarlos
        aspecto = mm_alto / mm_ancho
        if abs(aspecto - 1) > 0.01:
            nuevo_alto = max(1, int(round(corte.shape[0] * aspecto)))
            corte = cv2.resize(corte, (corte.shape[1], nuevo_alto), interpolation=cv2.INTER_LINEAR)
            mm_alto = mm_ancho

        return corte, mm_alto, mm_ancho

# Binariza, abre y mide la zona de interés (huecos oscuros dentro del cuerpo)
    def segmentar_corte(self, plano, indice, umbral, tam_kernel, iteraciones, zona="oscura", carpeta_salida="resultados"):
        if zona not in ("oscura", "clara"):
            raise ValueError("Error, la zona de interés debe ser 'oscura' o 'clara'")
        if tam_kernel < 1 or iteraciones < 1:
            raise ValueError("Error, el kernel y las iteraciones deben ser mayores o iguales a 1")
        if umbral < 0 or umbral > 255:
            raise ValueError("Error, el umbral debe estar entre 0 y 255")

        corte, mm_alto, mm_ancho = self.__extraer_plano(plano, indice)
        corte8 = self.__normalizar_uint8(corte)
        alto_px, ancho_px = corte8.shape

        # Zona oscura (aire, T1): umbral inverso. Zona clara (líquido, T2): umbral normal. Lo que nos interesa va a quedar color blanco
        tipo = cv2.THRESH_BINARY_INV if zona == "oscura" else cv2.THRESH_BINARY
        _, binaria = cv2.threshold(corte8, umbral, 255, tipo)

        # Apertura con kernel e iteraciones elegidas por el usuario
        kernel = np.ones((tam_kernel, tam_kernel), np.uint8)
        abierta = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, kernel, iterations=iteraciones)

        # Descartamos los que tocan el borde 
        total, etiquetas, stats, centroides = cv2.connectedComponentsWithStats(abierta, connectivity=8)
        interes = np.zeros_like(abierta)
        mejor = -1
        for i in range(1, total):
            x, y, w, h, area = stats[i]
            toca_borde = x == 0 or y == 0 or x + w == ancho_px or y + h == alto_px
            if toca_borde:
                continue
            interes[etiquetas == i] = 255
            if mejor == -1 or area > stats[mejor, cv2.CC_STAT_AREA]:
                mejor = i

        if mejor == -1:
            raise ValueError("No se encontraron zonas de interés con esos parámetros, pruebe otro umbral o un kernel más pequeño")

        x, y, w, h, area_px = stats[mejor]
        area_mm2 = float(area_px) * mm_alto * mm_ancho