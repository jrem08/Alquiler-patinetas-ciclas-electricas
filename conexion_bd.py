"""
Proyecto: Alquiler de Patinetas y Ciclas Eléctricas
Capa 2: conexión a la base de datos.
Lee las credenciales desde el archivo .env (Capa 1) y entrega conexiones MySQL.
"""
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()


def obtener_conexion():
    """
    Crea y retorna una conexión a MySQL usando las variables de entorno.

    Returns:
        mysql.connector.connection.MySQLConnection: conexión activa.

    Raises:
        ConnectionError: si no es posible conectar con la base de datos.
    """
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
    except (Error, ValueError) as e:
        raise ConnectionError(f"No se pudo conectar a la base de datos: {e}")


def ejecutar_consulta(sql, parametros=None, tipo="none"):
    """
    Ejecuta una sentencia SQL parametrizada (evita inyección SQL).

    Args:
        sql (str): sentencia SQL con marcadores %s.
        parametros (tuple): valores para los marcadores.
        tipo (str): 'all' -> lista de filas, 'one' -> una fila,
                    'insert' -> id insertado, 'none' -> filas afectadas.

    Returns:
        list | dict | int | None: según el parámetro tipo.
    """
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(sql, parametros or ())

        if tipo == "all":
            return cursor.fetchall()
        if tipo == "one":
            return cursor.fetchone()

        conexion.commit()
        if tipo == "insert":
            return cursor.lastrowid
        return cursor.rowcount
    except Error as e:
        if conexion:
            conexion.rollback()
        raise RuntimeError(f"Error de base de datos: {e}")
    finally:
        if cursor:
            cursor.close()
        if conexion and conexion.is_connected():
            conexion.close()