"""
Proyecto: Alquiler de Patinetas y Ciclas Eléctricas
Cliente de terminal (VSCode): consume la API 100% por HTTP y muestra JSON.
Ejecutar (con app.py corriendo en otra terminal):  python cliente.py
"""
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")


def llamar_api(metodo, ruta, cuerpo=None, params=None):
    """Hace la petición HTTP e imprime la respuesta JSON en la terminal."""
    try:
        r = requests.request(metodo, f"{API_URL}{ruta}", json=cuerpo, params=params, timeout=10)
        print(f"\n[{metodo} {ruta}] -> HTTP {r.status_code}")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        return r.json()
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
    """Solicita los campos del punto; en modo parcial permite omitirlos con Enter."""
    campos = [("id_zona", "ID de la zona"), ("nombre", "Nombre"), ("direccion", "Dirección"),
              ("latitud", "Latitud"), ("longitud", "Longitud"),
              ("capacidad_maxima", "Capacidad máxima de bicicletas")]
    datos = {}
    for clave, etiqueta in campos:
        valor = input(f"{etiqueta}{' (Enter para omitir)' if parcial else ''}: ").strip()
        if parcial and valor == "":
            continue
        datos[clave] = valor
    return datos


def opcion_crear():
    """Crea puntos de acopio y pregunta si desea agregar otro."""
    llamar_api("GET", "/zonas")
    while True:
        llamar_api("POST", "/puntos", pedir_datos())
        if not pedir_si_no("¿Agregar otro punto de acopio?"):
            break


def menu():
    """Menú principal de terminal."""
    while True:
        print("\n===== ALQUILER DE PATINETAS Y CICLAS ELÉCTRICAS =====\n      Módulo: Puntos de Acopio (PAT-0003)")
        print("1) Listar zonas\n2) Listar puntos\n3) Consultar punto por ID\n4) Crear punto (POST)")
        print("5) Reemplazar punto (PUT)\n6) Modificar parcial (PATCH)\n7) Eliminar punto (DELETE)\n8) Salir")
        op = input("Seleccione una opción: ").strip()

        if op == "1":
            llamar_api("GET", "/zonas")
        elif op == "2":
            zona = input("Filtrar por ID de zona (Enter = todas): ").strip()
            llamar_api("GET", "/puntos", params={"id_zona": zona} if zona else None)
        elif op == "3":
            llamar_api("GET", f"/puntos/{input('ID del punto: ').strip()}")
        elif op == "4":
            opcion_crear()
        elif op == "5":
            id_p = input("ID del punto a reemplazar: ").strip()
            llamar_api("PUT", f"/puntos/{id_p}", pedir_datos())
        elif op == "6":
            id_p = input("ID del punto a modificar: ").strip()
            llamar_api("PATCH", f"/puntos/{id_p}", pedir_datos(parcial=True))
        elif op == "7":
            id_p = input("ID del punto a eliminar: ").strip()
            if pedir_si_no(f"¿Confirma eliminar el punto {id_p}?"):
                llamar_api("DELETE", f"/puntos/{id_p}")
        elif op == "8":
            if pedir_si_no("¿Desea salir del programa?"):
                print("Hasta luego.")
                break
        else:
            print("Opción inválida.")


if __name__ == "__main__":
    menu()