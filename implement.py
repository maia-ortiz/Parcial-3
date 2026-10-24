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