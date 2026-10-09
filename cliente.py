"""
Proyecto: Alquiler de Patinetas y Ciclas Eléctricas
Cliente de terminal (VSCode): consume la API 100% por HTTP y muestra JSON.
El usuario nunca escribe IDs: zonas y puntos se buscan por nombre, dirección, latitud o longitud.
Ejecutar (con app.py corriendo en otra terminal):  python cliente.py
"""
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")


def llamar_api(metodo, ruta, cuerpo=None, params=None, mostrar=True):
    """Hace la petición HTTP; imprime la respuesta JSON si mostrar=True y la retorna."""
    try:
        r = requests.request(metodo, f"{API_URL}{ruta}", json=cuerpo, params=params, timeout=10)
        resp = r.json()
        if mostrar:
            print(f"\n[{metodo} {ruta}] -> HTTP {r.status_code}")
            print(json.dumps(resp, indent=2, ensure_ascii=False))
        return resp
    except requests.exceptions.ConnectionError:
        print("\n{\"ok\": false, \"mensaje\": \"No se pudo conectar con la API. ¿Está corriendo app.py?\"}")
    except requests.exceptions.Timeout:
        print("\n{\"ok\": false, \"mensaje\": \"La API tardó demasiado en responder.\"}")
    except ValueError:
        print("\n{\"ok\": false, \"mensaje\": \"La API no devolvió JSON válido.\"}")
    return None


def pedir_si_no(pregunta):
    """Pregunta S/N y repite hasta recibir una respuesta válida."""
    while True:
        r = input(f"{pregunta} (S/N): ").strip().upper()
        if r in ("S", "N"):
            return r == "S"
        print("Respuesta inválida. Escriba S o N.")


def pedir_datos(parcial=False):
    """Solicita los campos del punto; la zona se indica por NOMBRE. En modo parcial Enter omite."""
    campos = [("nombre_zona", "Nombre de la zona"), ("nombre", "Nombre del punto"),
              ("direccion", "Dirección"), ("latitud", "Latitud"), ("longitud", "Longitud"),
              ("capacidad_maxima", "Capacidad máxima de bicicletas")]
    datos = {}
    for clave, etiqueta in campos:
        valor = input(f"{etiqueta}{' (Enter para omitir)' if parcial else ''}: ").strip()
        if parcial and valor == "":
            continue
        datos[clave] = valor
    return datos


def pedir_filtros():
    """Pide criterios de búsqueda opcionales (Enter omite cada uno)."""
    criterios = [("nombre", "Nombre del punto"), ("direccion", "Dirección"),
                 ("zona", "Nombre de la zona"), ("latitud", "Latitud"), ("longitud", "Longitud")]
    filtros = {}
    for clave, etiqueta in criterios:
        valor = input(f"{etiqueta} (Enter para omitir): ").strip()
        if valor:
            filtros[clave] = valor
    return filtros


def buscar_punto():
    """
    Busca un punto por nombre, dirección, zona, latitud o longitud (sin pedir ID).
    Si hay varias coincidencias, muestra una lista numerada para elegir.
    Retorna el punto elegido (dict) o None.
    """
    print("\nBuscar punto de acopio (escriba al menos un criterio):")
    filtros = pedir_filtros()
    if not filtros:
        print("Debe escribir al menos un criterio de búsqueda.")
        return None

    resp = llamar_api("GET", "/puntos", params=filtros, mostrar=False)
    if resp is None:
        return None
    if not resp.get("ok"):
        print(json.dumps(resp, indent=2, ensure_ascii=False))
        return None

    puntos = resp["datos"]
    if not puntos:
        print("No se encontraron puntos con esos criterios.")
        return None
    if len(puntos) == 1:
        p = puntos[0]
        print(f"Punto encontrado: {p['nombre']} - {p['direccion']} (zona {p['nombre_zona']})")
        return p

    print(f"\nSe encontraron {len(puntos)} puntos:")
    for i, p in enumerate(puntos, start=1):
        print(f"  {i}) {p['nombre']} - {p['direccion']} (zona {p['nombre_zona']})")
    while True:
        eleccion = input("Elija el número de la lista (0 para cancelar): ").strip()
        if eleccion.isdigit() and 0 <= int(eleccion) <= len(puntos):
            return puntos[int(eleccion) - 1] if int(eleccion) > 0 else None
        print("Número inválido.")


def mostrar_zonas():
    """Muestra las zonas disponibles para que el usuario escriba el nombre de una."""
    resp = llamar_api("GET", "/zonas", mostrar=False)
    if resp and resp.get("ok"):
        nombres = ", ".join(z["nombre"] for z in resp["datos"])
        print(f"\nZonas existentes: {nombres}")
        print("(Si escribe una zona nueva, se creará automáticamente.)")


def opcion_crear():
    """Crea puntos de acopio indicando la zona por nombre y pregunta si desea agregar otro."""
    while True:
        mostrar_zonas()
        llamar_api("POST", "/puntos", pedir_datos())
        if not pedir_si_no("¿Agregar otro punto de acopio?"):
            break


def menu():
    """Menú principal de terminal."""
    while True:
        print("\n===== ALQUILER DE PATINETAS Y CICLAS ELÉCTRICAS =====")
        print("      Módulo: Puntos de Acopio (PAT-0003)")
        print("1) Listar zonas\n2) Listar / buscar puntos\n3) Consultar punto\n4) Crear punto (POST)")
        print("5) Reemplazar punto (PUT)\n6) Modificar parcial (PATCH)\n7) Eliminar punto (DELETE)\n8) Salir")
        op = input("Seleccione una opción: ").strip()

        if op == "1":
            nombre = input("Nombre de la zona (Enter para ver todas): ").strip()
            llamar_api("GET", "/zonas", params={"nombre": nombre} if nombre else None)
        elif op == "2":
            print("\nFiltros opcionales (Enter en todos para ver todos los puntos):")
            llamar_api("GET", "/puntos", params=pedir_filtros())
        elif op == "3":
            punto = buscar_punto()
            if punto:
                llamar_api("GET", f"/puntos/{punto['id_punto']}")
        elif op == "4":
            opcion_crear()
        elif op == "5":
            punto = buscar_punto()
            if punto:
                mostrar_zonas()
                print("Escriba los NUEVOS datos completos:")
                llamar_api("PUT", f"/puntos/{punto['id_punto']}", pedir_datos())
        elif op == "6":
            punto = buscar_punto()
            if punto:
                mostrar_zonas()
                print("Escriba solo los datos que desea cambiar:")
                llamar_api("PATCH", f"/puntos/{punto['id_punto']}", pedir_datos(parcial=True))
        elif op == "7":
            punto = buscar_punto()
            if punto and pedir_si_no(f"¿Confirma eliminar '{punto['nombre']}' ({punto['direccion']})?"):
                llamar_api("DELETE", f"/puntos/{punto['id_punto']}")
        elif op == "8":
            if pedir_si_no("¿Desea salir del programa?"):
                print("Hasta luego.")
                break
        else:
            print("Opción inválida.")


if __name__ == "__main__":
    menu()