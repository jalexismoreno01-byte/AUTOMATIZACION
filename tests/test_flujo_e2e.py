"""
Taller U2 (AA2) - Flujos de punta a punta que cruzan capas.

Cada prueba EMPIEZA en una capa (formulario web o API REST) y TERMINA
verificando en la otra: no basta con que "aparezca un mensaje de exito",
el dato debe quedar guardado, ser consultable, listarse y, tras el borrado,
dejar de existir en ambas capas.

Foco asignado al equipo: 1. Ciclo de vida del registro
    crear (web y API) -> consultar -> listar -> eliminar -> verificar ausencia

Marcas: ui (usa Selenium) + e2e (flujo funcional completo), tal como pide el
documento del taller.  Sin time.sleep(): todas las esperas son explicitas
(WebDriverWait dentro de los Page Objects compartidos).

Cada caso crea sus datos con un correo unico (uuid) y limpia al terminar,
de modo que puede ejecutarse en cualquier orden.
"""
import re
import uuid

import pytest
import requests

from pages.inscripcion_page import PaginaInscripcion
from pages.listado_page import PaginaListado

pytestmark = [pytest.mark.ui, pytest.mark.e2e]


# ---------- utilidades de los flujos ----------


def correo_unico():
    """Correo aleatorio para no colisionar con datos de otras pruebas."""
    return f"e2e-{uuid.uuid4().hex[:8]}@ceto.edu.co"


def buscar_por_correo(api_url, correo):
    """Devuelve el registro de la API con ese correo, o None."""
    estudiantes = requests.get(api_url, timeout=10).json()
    return next((e for e in estudiantes if e["correo"] == correo), None)


def contar_por_correo(api_url, correo):
    """Cuantos registros tienen ese correo (1 = integridad correcta)."""
    estudiantes = requests.get(api_url, timeout=10).json()
    return sum(1 for e in estudiantes if e["correo"] == correo)


def borrar_si_existe(api_url, id_est):
    """Limpieza best-effort al final del flujo."""
    requests.delete(f"{api_url}/{id_est}", timeout=10)


def inscribir_por_web(driver, base_url, nombre, correo, programa, semestre, evidencia=None,
                      paso=None):
    """Rellena el formulario, envia y ESPERA la confirmacion (POST ~0.5 s).

    Esperar el mensaje antes de tocar la API es lo que hace estable el flujo:
    si no, se podria consultar la API mientras el servidor aun no ha guardado.
    """
    pagina = PaginaInscripcion(driver, base_url)
    pagina.llenar_formulario(
        nombre=nombre, correo=correo, programa=programa, semestre=semestre,
    ).inscribir()
    mensaje = pagina.esperar_mensaje_exito()
    if evidencia:
        evidencia(paso or "paso_web")
    return pagina, mensaje


# ---------- E2E-01 y E2E-02: creacion cruzando capas ----------


def test_inscripcion_web_queda_registrada_en_api(driver, base_url, api_url, evidencia):
    """E2E-01: inscribo por el FORMULARIO -> lo encuentro en la API."""
    correo = correo_unico()

    # Accion por la interfaz
    _, mensaje = inscribir_por_web(
        driver, base_url,
        nombre="Sofia Mejia Rojas", correo=correo,
        programa="Ingenieria Industrial", semestre=7,
        evidencia=evidencia, paso="01_formulario_enviado",
    )
    assert "Inscripcion exitosa" in mensaje, "el formulario debe reportar exito"

    # Verificacion por la API: el dato realmente quedo guardado
    registro = buscar_por_correo(api_url, correo)
    assert registro is not None, "La inscripcion web no aparece en la API"
    assert registro["nombre"] == "Sofia Mejia Rojas"
    assert registro["programa"] == "Ingenieria Industrial"
    assert registro["semestre"] == 7, "el semestre debe persistir igual en la API"
    borrar_si_existe(api_url, registro["id"])


def test_creacion_api_aparece_en_el_listado_web(driver, base_url, api_url, evidencia):
    """E2E-02: creo por la API -> aparece en el LISTADO WEB."""
    correo = correo_unico()
    creada = requests.post(
        api_url,
        json={
            "nombre": "Andres Felipe Giraldo",
            "correo": correo,
            "programa": "Tecnologia en Desarrollo de Software",
            "semestre": 4,
        },
        timeout=10,
    )
    assert creada.status_code == 201, "la API debe crear el registro"
    id_est = creada.json()["id"]

    # Verificacion por la interfaz: el listado lo muestra con su codigo
    listado = PaginaListado(driver, base_url).abrir().esperar_fila_con(correo)
    evidencia("02_listado_web_con_registro_de_api")

    assert listado.contiene("Andres Felipe Giraldo"), "el nombre debe verse en la tabla"
    assert listado.contiene("Tecnologia en Desarrollo de Software")
    assert f"EST-{id_est:04d}" in listado.codigos(), \
        "el codigo del listado debe corresponder al id que asigno la API"
    borrar_si_existe(api_url, id_est)


# ---------- E2E-03 y E2E-04: ciclo de vida completo (Foco 1) ----------


def test_ciclo_completo_web_consulta_borrado_y_ausencia(driver, base_url, api_url, evidencia):
    """E2E-03 (caso bandera del Foco 1): web -> consultar por API -> listar ->
    eliminar -> verificar que ya no existe en ninguna capa."""
    correo = correo_unico()

    # 1) Crear por el formulario y capturar el codigo EST-XXXX del exito
    _, mensaje = inscribir_por_web(
        driver, base_url,
        nombre="Camilo Andres Vera", correo=correo,
        programa="Ingenieria de Sistemas", semestre=9,
        evidencia=evidencia, paso="03_exito_web",
    )
    coincide = re.search(r"EST-(\d+)", mensaje)
    assert coincide, f"el mensaje de exito debe traer un codigo EST-XXXX: {mensaje!r}"
    id_est = int(coincide.group(1))

    # 2) Consultar por la API con el id derivado del codigo del formulario
    detalle = requests.get(f"{api_url}/{id_est}", timeout=10)
    assert detalle.status_code == 200, "el codigo del formulario debe existir en la API"
    assert detalle.json()["correo"] == correo
    assert detalle.json()["semestre"] == 9
    assert detalle.json()["nombre"] == "Camilo Andres Vera"

    # 3) Listar en la web: el registro aparece en la tabla
    listado = PaginaListado(driver, base_url).abrir().esperar_fila_con(correo)
    evidencia("04_listado_antes_de_borrar")
    assert f"EST-{id_est:04d}" in listado.codigos()

    # 4) Eliminar por la API
    assert requests.delete(f"{api_url}/{id_est}", timeout=10).status_code == 204

    # 5) Verificar la ausencia en AMBAS capas
    assert requests.get(f"{api_url}/{id_est}", timeout=10).status_code == 404, \
        "tras el borrado la API debe responder 404"
    assert buscar_por_correo(api_url, correo) is None, \
        "el correo ya no debe existir en la API"

    listado_final = PaginaListado(driver, base_url).abrir()
    listado_final.esperar_que_no_haya_fila_con(correo)
    evidencia("05_listado_tras_borrar")
    assert not listado_final.contiene(correo), \
        "el listado web ya no debe mostrar el registro eliminado"


def test_ciclo_completo_api_con_verificacion_en_web(driver, base_url, api_url, evidencia):
    """E2E-04: API -> consultar -> listar en la web -> eliminar -> verificar
    la ausencia en la API y en el listado web."""
    correo = correo_unico()

    # 1) Crear por la API
    creada = requests.post(
        api_url,
        json={
            "nombre": "Elena Restrepo Diaz",
            "correo": correo,
            "programa": "Ingenieria Industrial",
            "semestre": 2,
        },
        timeout=10,
    )
    assert creada.status_code == 201
    id_est = creada.json()["id"]

    # 2) Consultar por id: consistencia creacion/consulta
    detalle = requests.get(f"{api_url}/{id_est}", timeout=10)
    assert detalle.status_code == 200
    assert detalle.json() == creada.json(), "la consulta debe devolver lo mismo que la creacion"

    # 3) Listar en la web
    PaginaListado(driver, base_url).abrir().esperar_fila_con(correo)
    evidencia("06_listado_web_de_api")

    # 4) Eliminar por la API
    assert requests.delete(f"{api_url}/{id_est}", timeout=10).status_code == 204

    # 5) Verificar ausencia en ambas capas
    assert requests.get(f"{api_url}/{id_est}", timeout=10).status_code == 404
    assert buscar_por_correo(api_url, correo) is None

    listado_final = PaginaListado(driver, base_url).abrir()
    listado_final.esperar_que_no_haya_fila_con(correo)
    evidencia("07_listado_web_tras_borrar")
    assert not listado_final.contiene(correo), \
        "el listado web ya no debe mostrar el registro eliminado"


# ---------- E2E-05 y E2E-06: duplicados y reincorporacion del correo ----------


def test_correo_duplicado_web_conserva_un_solo_registro_en_api(driver, base_url, api_url, evidencia):
    """E2E-05: inscribo dos veces el mismo correo por la WEB -> el segundo
    intento muestra el error y la API conserva UN UNICO registro."""
    correo = correo_unico()
    datos = dict(nombre="Roberto Carlos Diaz", correo=correo,
                 programa="Ingenieria Industrial", semestre=8)

    # primera inscripcion: esperar el exito antes de reintentar
    primera = PaginaInscripcion(driver, base_url)
    primera.llenar_formulario(**datos).inscribir()
    assert "Inscripcion exitosa" in primera.esperar_mensaje_exito()

    # segundo intento con el mismo correo (nueva pagina, mismo navegador)
    segunda = PaginaInscripcion(driver, base_url)
    segunda.llenar_formulario(**datos).inscribir()
    error = segunda.esperar_error("correo")
    evidencia("08_error_duplicado_web")

    assert "ya esta registrado" in error, "el segundo intento debe mostrar el error en pantalla"
    assert contar_por_correo(api_url, correo) == 1, \
        "la API debe conservar exactamente UN registro con ese correo"

    registro = buscar_por_correo(api_url, correo)
    borrar_si_existe(api_url, registro["id"])


def test_tras_el_borrado_el_correo_se_puede_inscribir_otra_vez(driver, base_url, api_url, evidencia):
    """E2E-06: web -> borro por la API -> vuelvo a inscribir el MISMO correo
    por la web: debe triunfar porque el ciclo de vida del registro termino."""
    correo = correo_unico()
    datos = dict(nombre="Laura Tatiana Mendez", correo=correo,
                 programa="Ingenieria de Sistemas", semestre=6)

    # primera inscripcion (esperar el exito antes de consultar la API:
    # el POST tarda ~0.5 s y sin esa espera la lectura podria ser prematura)
    primera = PaginaInscripcion(driver, base_url)
    primera.llenar_formulario(**datos).inscribir()
    primera.esperar_mensaje_exito()
    registro = buscar_por_correo(api_url, correo)
    assert registro is not None, "la primera inscripcion debe quedar en la API"

    # borrado: cierra el ciclo de vida
    assert requests.delete(f"{api_url}/{registro['id']}", timeout=10).status_code == 204

    # segunda inscripcion con el mismo correo: ahora es legal
    pagina = PaginaInscripcion(driver, base_url)
    pagina.llenar_formulario(**datos).inscribir()
    exito = pagina.esperar_mensaje_exito()
    evidencia("09_reinscripcion_tras_borrado")
    assert "Inscripcion exitosa" in exito, \
        "tras el borrado el correo debe volver a estar disponible en el formulario"

    assert contar_por_correo(api_url, correo) == 1, \
        "debe existir exactamente un registro con ese correo (el nuevo)"
    borrar_si_existe(api_url, buscar_por_correo(api_url, correo)["id"])
