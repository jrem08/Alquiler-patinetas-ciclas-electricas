"""
Proyecto: Alquiler de Patinetas y Ciclas Eléctricas
Capa 4: endpoints HTTP (API REST con respuestas 100% JSON).
Las zonas se manejan por NOMBRE; los puntos se buscan por nombre, dirección, zona o coordenadas.
Ejecutar:  python app.py
"""
import os
from flask import Flask, jsonify, request
from dotenv import load_dotenv
import funciones as f

load_dotenv()
app = Flask(__name__)


def respuesta(ok, mensaje, datos=None, codigo=200):
    """Construye una respuesta JSON estándar."""
    return jsonify({"ok": ok, "mensaje": mensaje, "datos": datos}), codigo


def manejar(funcion, mensaje_ok, codigo_ok=200):
    """Ejecuta una función de negocio traduciendo excepciones a respuestas JSON."""
    try:
        return respuesta(True, mensaje_ok, funcion(), codigo_ok)
    except f.ValidacionError as e:
        return respuesta(False, str(e), None, 400)
    except f.NoEncontradoError as e:
        return respuesta(False, str(e), None, 404)
    except (RuntimeError, ConnectionError) as e:
        return respuesta(False, str(e), None, 500)
    except Exception as e:
        return respuesta(False, f"Error inesperado: {e}", None, 500)


# ----------------------------- Zonas -----------------------------
@app.get("/zonas")
def get_zonas():
    filtros = {"nombre": request.args.get("nombre")}
    return manejar(lambda: f.listar_zonas(filtros), "Zonas consultadas correctamente.")


@app.post("/zonas")
def post_zona():
    cuerpo = request.get_json(silent=True)
    return manejar(lambda: f.crear_zona(cuerpo), "Zona creada correctamente.", 201)


# ----------------------------- Puntos ----------------------------
@app.get("/puntos")
def get_puntos():
    filtros = {k: request.args.get(k) for k in ("nombre", "direccion", "zona", "latitud", "longitud")}
    return manejar(lambda: f.listar_puntos(filtros), "Puntos de acopio consultados correctamente.")


@app.get("/puntos/<id_punto>")
def get_punto(id_punto):
    return manejar(lambda: f.obtener_punto(id_punto), "Punto de acopio encontrado.")


@app.post("/puntos")
def post_punto():
    cuerpo = request.get_json(silent=True)
    return manejar(lambda: f.crear_punto(cuerpo), "Punto de acopio creado correctamente.", 201)


@app.put("/puntos/<id_punto>")
def put_punto(id_punto):
    cuerpo = request.get_json(silent=True)
    return manejar(lambda: f.reemplazar_punto(id_punto, cuerpo), "Punto de acopio actualizado (PUT).")


@app.patch("/puntos/<id_punto>")
def patch_punto(id_punto):
    cuerpo = request.get_json(silent=True)
    return manejar(lambda: f.actualizar_parcial_punto(id_punto, cuerpo),
                   "Punto de acopio actualizado parcialmente (PATCH).")


@app.delete("/puntos/<id_punto>")
def delete_punto(id_punto):
    return manejar(lambda: f.eliminar_punto(id_punto), "Punto de acopio eliminado correctamente.")


@app.errorhandler(404)
def no_encontrado(_):
    return respuesta(False, "Ruta no encontrada.", None, 404)


@app.errorhandler(405)
def metodo_no_permitido(_):
    return respuesta(False, "Método HTTP no permitido.", None, 405)


if __name__ == "__main__":
    app.run(host=os.getenv("API_HOST", "127.0.0.1"),
            port=int(os.getenv("API_PORT", "5000")),
            debug=False)