import sistema as sd

# Creamos una función para pedir un número entero (devuelve None si el usuario escribe algo inválido)
def pedir_entero(mensaje):
    try:
        return int(input(mensaje))
    except ValueError:
        print("Valor inválido. Por favor, intente de nuevo.")
        return None

# Otra función para pedir un número decimal (devuelve None si el usuario escribe algo inválido)
def pedir_decimal(mensaje):
    try:
        return float(input(mensaje))
    except ValueError:
        print("Valor inválido. Por favor, intente de nuevo.")
        return None

# Otra función para mostrar los nombres de los volúmenes cargados y preguntar al usuario cuál usar
def elegir_volumen(gestor):
    volumenes = gestor.consultar_volumenes()
    if len(volumenes) == 0:
        print("No hay volúmenes cargados. Cargue una carpeta primero (opción 1).")
        return None

    print("Volúmenes cargados: " + ", ".join(v.ver_nombre() for v in volumenes))
    nombre = input("Ingrese el nombre del volumen: ")
    volumen = gestor.buscar_volumen(nombre)
    if volumen is None:
        print(f"No se encontró un volumen con el nombre {nombre}.")
    return volumen

# Creamos el menú principal y sub-menús para la gestión de los volúmenes DICOM
def main():
    gestor = sd.GestorDicom() # Objeto que almacena los volúmenes cargados

    while True:
        op = pedir_entero("""
Bienvenido al sistema de análisis de imágenes DICOM, ingrese la opción deseada:
            1. Cargar datos.
            2. Ver volúmenes cargados.
            3. Corregir ángulo (rotar volumen).
            4. Ecualizar un corte.
            5. Segmentar un corte.
            6. Salir.
            Coloque aquí su opción --> """)

        if op is None:
            continue

        if op == 1:
            menu2 = pedir_entero("""Ingrese la opción deseada:
            1. Cargar una carpeta DICOM.
            2. Cargar las carpetas de clase (PPMI, Sarcoma y T2).
            0. Volver al menú principal.
            Coloque aquí su opción --> """)

            if menu2 == 0 or menu2 is None:
                continue

            elif menu2 == 1:
                nombre = input("Ingrese un nombre para el volumen (ej: T2): ")
                carpeta = input("Ingrese la ruta de la carpeta DICOM: ")
                try:
                    volumen = gestor.cargar_carpeta(nombre, carpeta)
                    print("\nVolumen cargado y reconstruido exitosamente.")
                    print(volumen)
                except ValueError as e:
                    print(e)

            elif menu2 == 2:
                ruta = input("Ingrese la ruta de la carpeta 'datos' (Enter para usar ./datos): ")
                if ruta == "":
                    ruta = "datos"
                print("Cargando, esto puede tardar unos segundos...")
                cargados, errores = gestor.cargar_carpetas_clase(ruta)
                if len(cargados) > 0:
                    print("\nVolúmenes cargados: " + ", ".join(cargados))
                for e in errores:
                    print(e)
            else:
                print("Opción inválida. Por favor, intente de nuevo.")

        elif op == 2:
            volumenes = gestor.consultar_volumenes()
            if len(volumenes) == 0:
                print("No hay volúmenes cargados.")
            else:
                print(sd.generar_reporte(gestor))

        elif op == 3:
            volumen = elegir_volumen(gestor)
            if volumen is None:
                continue

            angulo = pedir_decimal("Ingrese el ángulo de inclinación en grados (positivo = antihorario): ")
            if angulo is None:
                continue

            try:
                volumen.corregirAngulo(angulo)
                print(f"\nVolumen {volumen.ver_nombre()} rotado {angulo} grados. Los procesos siguientes usarán el volumen corregido.")
                print("Matriz de rotación:")
                print(volumen.ver_matriz_rotacion())
            except ValueError as e:
                print(e)

        elif op == 4:
            volumen = elegir_volumen(gestor)
            if volumen is None:
                continue

            indice = pedir_entero(f"Ingrese el número del corte (0 a {volumen.ver_num_cortes() - 1}): ")
            if indice is None:
                continue

            try:
                ruta_grafico, ruta_imagen = volumen.ecualizar_corte(indice)
                print(f"\nGráfico guardado en: {ruta_grafico}")
                print(f"Imagen ecualizada guardada en: {ruta_imagen}")
            except ValueError as e:
                print(e)

        elif op == 5:
            volumen = elegir_volumen(gestor)
            if volumen is None:
                continue

            menu2 = pedir_entero("""Ingrese el plano del corte:
                        1. Transversal.
                        2. Coronal.
                        3. Sagital.
                        0. Volver al menú principal.
                        Coloque aquí su opción: """)

                        if menu2 == 0 or menu2 is None:
                                continue
                        elif menu2 not in (1, 2, 3):
                            print("Opción inválida. Por favor, intente de nuevo.")
                            continue

                        plano = sd.VolumenDicom.PLANOS[menu2 - 1]
                        indice = pedir_entero(f"Ingrese el número del corte {plano}: ")
                        if indice is None:
                            continue

                        menu3 = pedir_entero("""Ingrese el tipo de zona de interés:
                        1. Zona oscura (aire, huecos en imágenes T1 o TC).
                        2. Zona clara (líquido, ventrículos en imágenes T2).
                        0. Volver al menú principal.
                        Coloque aquí su opción: """)
