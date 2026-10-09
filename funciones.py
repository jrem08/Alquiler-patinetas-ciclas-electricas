"""
Proyecto: Alquiler de Patinetas y Ciclas Eléctricas
Capa 3: lógica del negocio del PAT-0003 (CRUD Puntos de Acopio con FK a Zonas).

La zona SIEMPRE se indica por su nombre ('nombre_zona'); nunca por id.
Los puntos se buscan por nombre, dirección, zona, latitud o longitud.
"""
import os
import re
from conexion_bd import ejecutar_consulta


class ValidacionError(Exception):
    """Error de validación de datos de entrada (HTTP 400)."""


class NoEncontradoError(Exception):
    """El recurso solicitado no existe (HTTP 404)."""


REGEX_DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")
REGEX_ENTERO = re.compile(r"^\d+$")

# Si la zona no existe, se crea automáticamente (se puede desactivar con
# CREAR_ZONA_AUTOMATICA=false en el archivo .env)
CREAR_ZONA_AUTOMATICA = os.getenv("CREAR_ZONA_AUTOMATICA", "true").strip().lower() != "false"
RADIO_ZONA_POR_DEFECTO_M = 1000

# Campos propios del punto (la zona se indica aparte con 'nombre_zona')
CAMPOS_PUNTO = ["nombre", "direccion", "latitud", "longitud", "capacidad_maxima"]

SELECT_PUNTO = (
    "SELECT p.id_punto, p.nombre, p.direccion, p.latitud, p.longitud, "
    "p.capacidad_maxima, p.fecha_creacion, z.nombre AS nombre_zona "
    "FROM puntos_acopio p JOIN zonas z ON z.id_zona = p.id_zona"
)


# ----------------------------------------------------------------------
# Validación y sanitización
# ----------------------------------------------------------------------
def validar_texto(valor, campo, maximo):
    """Valida que sea texto no vacío, lo limpia y controla la longitud."""
    try:
        if valor is None or not str(valor).strip():
            raise ValidacionError(f"El campo '{campo}' es obligatorio y no puede estar vacío.")
        texto = re.sub(r"\s+", " ", str(valor)).strip()
        if len(texto) > maximo:
            raise ValidacionError(f"El campo '{campo}' no puede superar {maximo} caracteres.")
        if re.search(r"[<>;]", texto):
            raise ValidacionError(f"El campo '{campo}' contiene caracteres no permitidos (< > ;).")
        return texto
    except ValidacionError:
        raise
    except Exception:
        raise ValidacionError(f"Valor inválido en '{campo}'.")


def convertir_float(valor, campo):
    """Convierte a float validando con regex que sea numérico decimal."""
    try:
        if valor is None or isinstance(valor, bool) or not REGEX_DECIMAL.match(str(valor).strip()):
            raise ValidacionError(f"El campo '{campo}' debe ser un número decimal válido.")
        return float(str(valor).strip())
    except ValueError:
        raise ValidacionError(f"El campo '{campo}' debe ser un número decimal válido.")


def convertir_int(valor, campo):
    """Convierte a entero positivo validando con regex."""
    try:
        if valor is None or isinstance(valor, bool) or not REGEX_ENTERO.match(str(valor).strip()):
            raise ValidacionError(f"El campo '{campo}' debe ser un número entero positivo.")
        return int(str(valor).strip())
    except ValueError:
        raise ValidacionError(f"El campo '{campo}' debe ser un número entero positivo.")


def validar_latitud(valor):
    """Latitud decimal entre -90 y 90."""
    lat = convertir_float(valor, "latitud")
    if not -90 <= lat <= 90:
        raise ValidacionError("La latitud debe estar entre -90 y 90.")
    return lat


def validar_longitud(valor):
    """Longitud decimal entre -180 y 180."""
    lon = convertir_float(valor, "longitud")
    if not -180 <= lon <= 180:
        raise ValidacionError("La longitud debe estar entre -180 y 180.")
    return lon


def validar_capacidad(valor):
    """Capacidad máxima de bicicletas: entero mayor que 0."""
    cap = convertir_int(valor, "capacidad_maxima")
    if cap <= 0:
        raise ValidacionError("La capacidad_maxima debe ser mayor que 0.")
    return cap


def validar_campo(campo, valor):
    """Despacha la validación correspondiente a cada campo del punto."""
    validadores = {
        "nombre": lambda v: validar_texto(v, "nombre", 100),
        "direccion": lambda v: validar_texto(v, "direccion", 200),
        "latitud": validar_latitud,
        "longitud": validar_longitud,
        "capacidad_maxima": validar_capacidad,
    }
    return validadores[campo](valor)


def rechazar_id_zona(datos):
    """La zona se identifica por nombre; si llega un id se rechaza con un mensaje claro."""
    if "id_zona" in datos:
        raise ValidacionError("La zona se indica con 'nombre_zona', no con un id.")


# ----------------------------------------------------------------------
# Zonas (siempre por nombre)
# ----------------------------------------------------------------------
def buscar_zona_por_nombre(nombre, latitud=None, longitud=None):
    """
    Busca una zona por su nombre (sin distinguir mayúsculas) y retorna su id INTERNO.
    Si la zona no existe y CREAR_ZONA_AUTOMATICA está activo, la crea usando las
    coordenadas del punto como centro y un radio de cobertura por defecto.
    """
    nombre = validar_texto(nombre, "nombre_zona", 100)
    zona = ejecutar_consulta(
        "SELECT id_zona FROM zonas WHERE LOWER(nombre) = LOWER(%s)", (nombre,), "one")
    if zona:
        return zona["id_zona"]

    if CREAR_ZONA_AUTOMATICA and latitud is not None and longitud is not None:
        return ejecutar_consulta(
            "INSERT INTO zonas (nombre, latitud, longitud, radio_cobertura_m) VALUES (%s, %s, %s, %s)",
            (nombre, latitud, longitud, RADIO_ZONA_POR_DEFECTO_M), "insert")

    filas = ejecutar_consulta("SELECT nombre FROM zonas ORDER BY nombre", tipo="all")
    disponibles = ", ".join(z["nombre"] for z in filas) or "ninguna"
    raise ValidacionError(
        f"No existe una zona llamada '{nombre}'. Zonas disponibles: {disponibles}.")


def listar_zonas(filtros=None):
    """Lista las zonas; filtro opcional por nombre. No expone ids."""
    filtros = filtros or {}
    sql = "SELECT nombre, latitud, longitud, radio_cobertura_m FROM zonas"
    parametros = ()
    if filtros.get("nombre"):
        sql += " WHERE nombre LIKE %s"
        parametros = (f"%{validar_texto(filtros['nombre'], 'nombre', 100)}%",)
    sql += " ORDER BY nombre"
    return _serializar(ejecutar_consulta(sql, parametros, "all"))


def crear_zona(datos):
    """Crea una zona validando nombre, coordenadas y radio de cobertura (POST /zonas)."""
    if not isinstance(datos, dict):
        raise ValidacionError("El cuerpo de la petición debe ser un objeto JSON.")
    faltantes = [c for c in ("nombre", "latitud", "longitud", "radio_cobertura_m") if c not in datos]
    if faltantes:
        raise ValidacionError(f"Faltan campos obligatorios: {', '.join(faltantes)}")

    nombre = validar_texto(datos["nombre"], "nombre", 100)
    latitud = validar_latitud(datos["latitud"])
    longitud = validar_longitud(datos["longitud"])
    radio = convertir_float(datos["radio_cobertura_m"], "radio_cobertura_m")
    if radio <= 0:
        raise ValidacionError("El radio_cobertura_m debe ser mayor que 0.")

    existe = ejecutar_consulta(
        "SELECT 1 AS x FROM zonas WHERE LOWER(nombre) = LOWER(%s)", (nombre,), "one")
    if existe:
        raise ValidacionError(f"Ya existe una zona llamada '{nombre}'.")

    ejecutar_consulta(
        "INSERT INTO zonas (nombre, latitud, longitud, radio_cobertura_m) VALUES (%s, %s, %s, %s)",
        (nombre, latitud, longitud, radio), "insert")
    return listar_zonas({"nombre": nombre})


# ----------------------------------------------------------------------
# Puntos de acopio
# ----------------------------------------------------------------------
def validar_punto_completo(datos):
    """Valida un punto con todos sus campos; la zona va como 'nombre_zona' (POST / PUT)."""
    if not isinstance(datos, dict):
        raise ValidacionError("El cuerpo de la petición debe ser un objeto JSON.")
    rechazar_id_zona(datos)
    faltantes = [c for c in ["nombre_zona"] + CAMPOS_PUNTO if c not in datos]
    if faltantes:
        raise ValidacionError(f"Faltan campos obligatorios: {', '.join(faltantes)}")

    validado = {c: validar_campo(c, datos[c]) for c in CAMPOS_PUNTO}
    validado["id_zona"] = buscar_zona_por_nombre(
        datos["nombre_zona"], validado["latitud"], validado["longitud"])  # id interno
    return validado


def listar_puntos(filtros=None):
    """
    Lista los puntos de acopio. Filtros opcionales (se combinan con AND):
    nombre, direccion, zona (nombre de la zona), latitud, longitud.
    """
    filtros = filtros or {}
    sql = SELECT_PUNTO
    condiciones, parametros = [], []

    if filtros.get("nombre"):
        condiciones.append("p.nombre LIKE %s")
        parametros.append(f"%{validar_texto(filtros['nombre'], 'nombre', 100)}%")
    if filtros.get("direccion"):
        condiciones.append("p.direccion LIKE %s")
        parametros.append(f"%{validar_texto(filtros['direccion'], 'direccion', 200)}%")
    if filtros.get("zona"):
        condiciones.append("z.nombre LIKE %s")
        parametros.append(f"%{validar_texto(filtros['zona'], 'zona', 100)}%")
    if filtros.get("latitud"):
        condiciones.append("ABS(p.latitud - %s) < 0.00001")
        parametros.append(validar_latitud(filtros["latitud"]))
    if filtros.get("longitud"):
        condiciones.append("ABS(p.longitud - %s) < 0.00001")
        parametros.append(validar_longitud(filtros["longitud"]))

    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    sql += " ORDER BY z.nombre, p.nombre"
    return _serializar(ejecutar_consulta(sql, tuple(parametros), "all"))


def obtener_punto(id_punto):
    """Retorna un punto por su id interno o lanza NoEncontradoError."""
    id_punto = convertir_int(id_punto, "id_punto")
    fila = ejecutar_consulta(SELECT_PUNTO + " WHERE p.id_punto = %s", (id_punto,), "one")
    if not fila:
        raise NoEncontradoError("No existe el punto de acopio solicitado.")
    return _serializar([fila])[0]


def crear_punto(datos):
    """Crea un punto de acopio (POST)."""
    d = validar_punto_completo(datos)
    nuevo_id = ejecutar_consulta(
        "INSERT INTO puntos_acopio (id_zona, nombre, direccion, latitud, longitud, capacidad_maxima) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (d["id_zona"], d["nombre"], d["direccion"], d["latitud"], d["longitud"], d["capacidad_maxima"]),
        "insert")
    return obtener_punto(nuevo_id)


def reemplazar_punto(id_punto, datos):
    """Reemplaza todos los campos de un punto (PUT)."""
    obtener_punto(id_punto)  # valida que exista
    d = validar_punto_completo(datos)
    ejecutar_consulta(
        "UPDATE puntos_acopio SET id_zona=%s, nombre=%s, direccion=%s, latitud=%s, "
        "longitud=%s, capacidad_maxima=%s WHERE id_punto=%s",
        (d["id_zona"], d["nombre"], d["direccion"], d["latitud"], d["longitud"],
         d["capacidad_maxima"], int(id_punto)))
    return obtener_punto(id_punto)


def actualizar_parcial_punto(id_punto, datos):
    """Actualiza solo los campos enviados (PATCH). La zona, si se cambia, va por nombre."""
    punto_actual = obtener_punto(id_punto)
    if not isinstance(datos, dict) or not datos:
        raise ValidacionError("Debe enviar al menos un campo para actualizar.")
    rechazar_id_zona(datos)
    permitidos = CAMPOS_PUNTO + ["nombre_zona"]
    invalidos = [c for c in datos if c not in permitidos]
    if invalidos:
        raise ValidacionError(f"Campos no permitidos: {', '.join(invalidos)}")

    campos = {c: validar_campo(c, v) for c, v in datos.items() if c != "nombre_zona"}
    if "nombre_zona" in datos:
        campos["id_zona"] = buscar_zona_por_nombre(
            datos["nombre_zona"],
            campos.get("latitud", punto_actual["latitud"]),
            campos.get("longitud", punto_actual["longitud"]))  # id interno

    asignaciones = ", ".join(f"{c}=%s" for c in campos)
    ejecutar_consulta(
        f"UPDATE puntos_acopio SET {asignaciones} WHERE id_punto=%s",
        tuple(campos.values()) + (int(id_punto),))
    return obtener_punto(id_punto)


def eliminar_punto(id_punto):
    """Elimina un punto de acopio (DELETE) y retorna el punto eliminado."""
    punto = obtener_punto(id_punto)
    ejecutar_consulta("DELETE FROM puntos_acopio WHERE id_punto = %s", (int(id_punto),))
    return punto


def _serializar(filas):
    """Convierte Decimal y datetime a tipos compatibles con JSON."""
    resultado = []
    for fila in filas:
        limpia = {}
        for k, v in fila.items():
            if hasattr(v, "isoformat"):
                limpia[k] = v.isoformat(sep=" ")
            elif v.__class__.__name__ == "Decimal":
                limpia[k] = float(v)
            else:
                limpia[k] = v
        resultado.append(limpia)
    return resultado