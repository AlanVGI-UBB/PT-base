import unicodedata

from normalizacion import normalizar_texto


def test_normalizacion_minusculas_y_puntuacion_espanol():
    entrada = "¿Qué es un Árbol Binario? ¡Es clave en INF-221, profe!"
    assert normalizar_texto(entrada) == "qué es un árbol binario es clave en inf 221 profe"


def test_normalizacion_unicode_nfc():
    descompuesto = "a\u0301rbol y recursio\u0301n con bu\u0301squeda"
    resultado = normalizar_texto(descompuesto)
    assert resultado == "árbol y recursión con búsqueda"
    assert unicodedata.is_normalized("NFC", resultado)


def test_normalizacion_preserva_numeros_como_se_transcriben():
    entrada = "Tiene complejidad O(1), usa 2 punteros y cinco nodos."
    assert normalizar_texto(entrada) == "tiene complejidad o 1 usa 2 punteros y cinco nodos"


def test_normalizacion_colapsa_espacios_y_es_idempotente():
    entrada = "  «Hola»,\n\tmundo — prueba...  "
    norm = normalizar_texto(entrada)
    assert norm == "hola mundo prueba"
    assert normalizar_texto(norm) == norm
    assert normalizar_texto("   \n\t ") == ""
    assert normalizar_texto("") == ""
