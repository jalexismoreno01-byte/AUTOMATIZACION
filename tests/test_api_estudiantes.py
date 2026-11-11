"""
Taller U2 - Pruebas de la API REST  /api/estudiantes   (requests + pytest)

Contrato verificado (README del proyecto):
  POST   /api/estudiantes        -> 201 + id | 400 no JSON | 422 invalidos | 409 correo repetido
  GET    /api/estudiantes        -> 200 + lista  (?programa=... filtra)
  GET    /api/estudiantes/<id>   -> 200 + estudiante | 404
  DELETE /api/estudiantes/<id>   -> 204 | 404

Reglas: nombre >= 3 caracteres · correo valido y unico · programa en la lista
permitida · semestre entre 1 y 10.

Cada prueba crea sus propios datos con un correo unico y los elimina al
final, de modo que puede ejecutarse en cualquier orden sin afectarse.
"""
import uuid

import pytest
import requests

pytestmark = pytest.mark.api

# ---------- utilidades de prueba ----------


def correo_unico():
    """Correo aleatorio para no colisionar con datos de otras pruebas."""
    return f"estudiante-{uuid.uuid4().hex[:10]}@correo.com"


def datos_validos(**cambios):
    """Payload valido por defecto; permite sobreescribir campos."""
    datos = {
        "nombre": "Maria Fernanda Lopez",
        "correo": correo_unico(),
        "programa": "Ingenieria de Sistemas",
        "semestre": 5,
    }
    datos.update(cambios)
    return datos


def crear(api_url, **cambios):
    """POST y devuelve la respuesta (sin asumir su resultado)."""
    return requests.post(api_url, json=datos_validos(**cambios), timeout=10)


def borrar_si_existe(api_url, id_est):
    """Limpieza best-effort para no dejar datos residuales."""
    requests.delete(f"{api_url}/{id_est}", timeout=10)


# ---------- POST: creación ----------


def test_post_crea_estudiante_con_id(api_url):
    """201 Created: devuelve el estudiante completo con id asignado."""
    respuesta = crear(api_url, nombre="Carlos Andres Ruiz")
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["id"] >= 1, "el id debe ser un entero positivo"
    assert cuerpo["nombre"] == "Carlos Andres Ruiz"
    assert "@" in cuerpo["correo"], "el correo debe devolverse completo"
    assert cuerpo["programa"] == "Ingenieria de Sistemas"
    assert cuerpo["semestre"] == 5
    borrar_si_existe(api_url, cuerpo["id"])


def test_post_con_semestre_en_texto_lo_convierte_a_numero(api_url):
    """Acepta semestre como string numerico ('7' -> 7)."""
    respuesta = crear(api_url, semestre="7")
    assert respuesta.status_code == 201
    assert respuesta.json()["semestre"] == 7
    borrar_si_existe(api_url, respuesta.json()["id"])


def test_post_exitoso_persiste_en_el_listado(api_url):
    """Lo que se crea por API aparece en GET /api/estudiantes."""
    datos = datos_validos(nombre="Pedro Pascal Gomez")
    creada = requests.post(api_url, json=datos, timeout=10)
    assert creada.status_code == 201

    lista = requests.get(api_url, timeout=10).json()
    assert any(e["correo"] == datos["correo"] for e in lista)
    borrar_si_existe(api_url, creada.json()["id"])


# ---------- POST: errores ----------


def test_post_cuerpo_no_json_da_400(api_url):
    """400 Bad Request cuando el cuerpo no es JSON (contrato del README)."""
    respuesta = requests.post(api_url, data="esto no es json", timeout=10)
    assert respuesta.status_code == 400
    assert "JSON" in respuesta.json()["error"]


@pytest.mark.parametrize(
    "campo, valor, mensaje_esperado",
    [
        ("nombre", "Ab", "minimo 3 caracteres"),          # nombre demasiado corto
        ("correo", "correo-malo", "Correo invalido"),      # formato invalido
        ("programa", "Cocina", "Programa no valido"),      # programa fuera de la lista
        ("semestre", 0, "entre 1 y 10"),                   # semestre por debajo
        ("semestre", 11, "entre 1 y 10"),                  # semestre por encima
        ("semestre", "abc", "entre 1 y 10"),               # semestre no numerico
    ],
)
def test_post_datos_invalidos_da_422(api_url, campo, valor, mensaje_esperado):
    """422 Unprocessable Entity + mensaje del campo que fallo."""
    respuesta = crear(api_url, **{campo: valor})
    assert respuesta.status_code == 422
    errores = respuesta.json()["errores"]
    assert campo in errores, f"debe venir el error del campo {campo}"
    assert mensaje_esperado.lower() in errores[campo].lower()


def test_post_con_varios_errores_da_422(api_url):
    """Si fallan varios campos, la respuesta los lista todos."""
    respuesta = crear(api_url, nombre="X", correo="malo", programa="Nada", semestre=99)
    assert respuesta.status_code == 422
    errores = respuesta.json()["errores"]
    assert set(errores) == {"nombre", "correo", "programa", "semestre"}


def test_post_correo_repetido_da_409(api_url):
    """409 Conflict: el correo ya esta registrado (unico error permitido)."""
    original = crear(api_url, nombre="Laura Tatiana Mendez")
    assert original.status_code == 201
    id_est = original.json()["id"]

    repetido = requests.post(
        api_url,
        json=datos_validos(nombre="Otra Persona Distinta", correo=original.json()["correo"]),
        timeout=10,
    )
    assert repetido.status_code == 409
    assert repetido.json()["errores"]["correo"] == "El correo ya esta registrado"
    borrar_si_existe(api_url, id_est)


# ---------- GET ----------


def test_get_listado_devuelve_200_y_lista(api_url):
    """200 OK con una lista (aunque este vacia)."""
    respuesta = requests.get(api_url, timeout=10)
    assert respuesta.status_code == 200
    assert isinstance(respuesta.json(), list)


def test_get_filtra_por_programa(api_url):
    """?programa=... solo devuelve estudiantes de ese programa."""
    uno = crear(api_url, nombre="Ana Sofia Torres", programa="Ingenieria Industrial")
    dos = crear(api_url, nombre="Luis Enrique Vera", programa="Tecnologia en Desarrollo de Software")
    assert uno.status_code == 201 and dos.status_code == 201

    filtrada = requests.get(api_url, params={"programa": "Ingenieria Industrial"}, timeout=10)
    assert filtrada.status_code == 200
    lista = filtrada.json()
    assert all(e["programa"] == "Ingenieria Industrial" for e in lista)
    assert any(e["id"] == uno.json()["id"] for e in lista)
    assert not any(e["id"] == dos.json()["id"] for e in lista)

    borrar_si_existe(api_url, uno.json()["id"])
    borrar_si_existe(api_url, dos.json()["id"])


def test_get_por_id_devuelve_200(api_url):
    """200 OK con el estudiante recien creado."""
    creada = crear(api_url, nombre="Diego Armando Marin")
    id_est = creada.json()["id"]

    respuesta = requests.get(f"{api_url}/{id_est}", timeout=10)
    assert respuesta.status_code == 200
    assert respuesta.json()["correo"] == creada.json()["correo"]
    borrar_si_existe(api_url, id_est)


def test_get_por_id_inexistente_da_404(api_url):
    """404 Not Found para un id que no existe."""
    respuesta = requests.get(f"{api_url}/999999", timeout=10)
    assert respuesta.status_code == 404
    assert "no encontrado" in respuesta.json()["error"].lower()


# ---------- DELETE ----------


def test_delete_devuelve_204_y_luego_404(api_url):
    """204 al borrar; 404 al volver a pedirlo (borrado doble)."""
    creada = crear(api_url, nombre="Sofia Elena Ramirez")
    id_est = creada.json()["id"]

    borrado = requests.delete(f"{api_url}/{id_est}", timeout=10)
    assert borrado.status_code == 204
    assert borrado.text == "", "204 no debe llevar cuerpo"

    assert requests.get(f"{api_url}/{id_est}", timeout=10).status_code == 404
    assert requests.delete(f"{api_url}/{id_est}", timeout=10).status_code == 404


def test_delete_inexistente_da_404(api_url):
    """404 al intentar borrar un id inexistente."""
    respuesta = requests.delete(f"{api_url}/888888", timeout=10)
    assert respuesta.status_code == 404


# ---------- Foco 1: ciclo de vida completo del registro ----------


def test_ciclo_completo_crear_consultar_listar_eliminar(api_url):
    """Foco 1: crear -> consultar -> listar -> eliminar -> verificar ausencia.

    Un solo caso recorre el ciclo de vida completo en la capa API y comprueba
    que cada paso deja el sistema en el estado esperado.
    """
    creada = crear(api_url, nombre="Ciclo De Vida Prueba")
    assert creada.status_code == 201
    id_est = creada.json()["id"]

    # consultar por id: la consulta debe devolver exactamente lo que se creo
    detalle = requests.get(f"{api_url}/{id_est}", timeout=10)
    assert detalle.status_code == 200
    assert detalle.json() == creada.json(), "la consulta debe ser consistente con la creacion"

    # listar: el registro nuevo debe estar en la coleccion
    assert any(e["id"] == id_est for e in requests.get(api_url, timeout=10).json()), \
        "el estudiante debe aparecer en el listado"

    # eliminar
    assert requests.delete(f"{api_url}/{id_est}", timeout=10).status_code == 204

    # verificar que ya no existe (por id ni en el listado)
    assert requests.get(f"{api_url}/{id_est}", timeout=10).status_code == 404
    assert not any(e["id"] == id_est for e in requests.get(api_url, timeout=10).json()), \
        "tras el borrado ya no debe aparecer en el listado"


def test_borrar_libera_el_correo_para_volver_a_inscribir(api_url):
    """Foco 1: tras eliminar el registro, el correo vuelve a estar disponible."""
    datos = datos_validos(nombre="Correo Liberado Patricia")
    creada = requests.post(api_url, json=datos, timeout=10)
    assert creada.status_code == 201

    assert requests.delete(f"{api_url}/{creada.json()['id']}", timeout=10).status_code == 204

    vuelta = requests.post(api_url, json=datos, timeout=10)
    assert vuelta.status_code == 201, "tras el borrado el correo no debe seguir bloqueado"
    borrar_si_existe(api_url, vuelta.json()["id"])
