"""
Proyecto: Alquiler de Patinetas y Ciclas Eléctricas
Capa 3: lógica del negocio del PAT-0003 (CRUD Puntos de Acopio con FK a Zonas).
Contiene validaciones, sanitización y las operaciones sobre la base de datos.
"""
import re
from conexion_bd import ejecutar_consulta


class ValidacionError(Exception):
    """Error de validación de datos de entrada (HTTP 400)."""


class NoEncontradoError(Exception):
    """El recurso solicitado no existe (HTTP 404)."""


REGEX_DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")
REGEX_ENTERO = re.compile(r"^\d+$")

CAMPOS_EDITABLES = ["id_zona", "nombre", "direccion", "latitud", "longitud", "capacidad_maxima"]


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


def validar_zona_existente(valor):
    """Valida que id_zona sea entero y que exista en la tabla zonas (FK)."""
    id_zona = convertir_int(valor, "id_zona")
    zona = ejecutar_consulta("SELECT id_zona FROM zonas WHERE id_zona = %s", (id_zona,), "one")
    if not zona:
        raise ValidacionError(f"La zona con id {id_zona} no existe. Debe asignar una zona existente.")
    return id_zona


def validar_campo(campo, valor):
    """Despacha la validación correspondiente a cada campo."""
    validadores = {
        "id_zona": validar_zona_existente,
        "nombre": lambda v: validar_texto(v, "nombre", 100),
        "direccion": lambda v: validar_texto(v, "direccion", 200),
        "latitud": validar_latitud,
        "longitud": validar_longitud,
        "capacidad_maxima": validar_capacidad,
    }
    return validadores[campo](valor)


def validar_punto_completo(datos):
    """Valida un punto de acopio con todos sus campos (POST / PUT)."""
    if not isinstance(datos, dict):
        raise ValidacionError("El cuerpo de la petición debe ser un objeto JSON.")
    faltantes = [c for c in CAMPOS_EDITABLES if c not in datos]
    if faltantes:
        raise ValidacionError(f"Faltan campos obligatorios: {', '.join(faltantes)}")
    return {campo: validar_campo(campo, datos[campo]) for campo in CAMPOS_EDITABLES}


# ----------------------------------------------------------------------
# Operaciones CRUD
# ----------------------------------------------------------------------
def listar_zonas():
    """Retorna todas las zonas disponibles."""
    return ejecutar_consulta("SELECT * FROM zonas ORDER BY id_zona", tipo="all")


def listar_puntos(id_zona=None):
    """Lista los puntos de acopio, opcionalmente filtrados por zona."""
    sql = ("SELECT p.*, z.nombre AS nombre_zona FROM puntos_acopio p "
           "JOIN zonas z ON z.id_zona = p.id_zona")
    parametros = ()
    if id_zona is not None:
        sql += " WHERE p.id_zona = %s"
        parametros = (convertir_int(id_zona, "id_zona"),)
    sql += " ORDER BY p.id_punto"
    return _serializar(ejecutar_consulta(sql, parametros, "all"))


def obtener_punto(id_punto):
    """Retorna un punto por su id o lanza NoEncontradoError."""
    id_punto = convertir_int(id_punto, "id_punto")
    fila = ejecutar_consulta(
        "SELECT p.*, z.nombre AS nombre_zona FROM puntos_acopio p "
        "JOIN zonas z ON z.id_zona = p.id_zona WHERE p.id_punto = %s",
        (id_punto,), "one")
    if not fila:
        raise NoEncontradoError(f"No existe el punto de acopio con id {id_punto}.")
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
    """Actualiza solo los campos enviados (PATCH)."""
    obtener_punto(id_punto)
    if not isinstance(datos, dict) or not datos:
        raise ValidacionError("Debe enviar al menos un campo para actualizar.")
    invalidos = [c for c in datos if c not in CAMPOS_EDITABLES]
    if invalidos:
        raise ValidacionError(f"Campos no permitidos: {', '.join(invalidos)}")

    campos = {c: validar_campo(c, v) for c, v in datos.items()}
    asignaciones = ", ".join(f"{c}=%s" for c in campos)
    ejecutar_consulta(
        f"UPDATE puntos_acopio SET {asignaciones} WHERE id_punto=%s",
        tuple(campos.values()) + (int(id_punto),))
    return obtener_punto(id_punto)


def eliminar_punto(id_punto):
    """Elimina un punto de acopio (DELETE)."""
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