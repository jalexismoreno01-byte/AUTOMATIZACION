"""
Taller U2 - Pruebas del formulario web /inscripcion  (Selenium + Page Object)

Flujo: el navegador abre la pagina, se rellena el formulario con el Page
Object (pages/inscripcion_page.py) y se verifica lo que el usuario ve:
mensaje de exito, errores de validacion y persistencia en el listado.

El servidor tarda ~0.5 s al enviar (latencia simulada), por eso todas las
esperas usan WebDriverWait con explicito en lugar de time.sleep().
Cada prueba guarda capturas en evidencias/ con el fixture `evidencia`.
"""
import csv
import re
import uuid
from pathlib import Path

import pytest

from pages.inscripcion_page import PaginaInscripcion
from pages.listado_page import PaginaListado

pytestmark = pytest.mark.ui

# Casos de error definidos en datos (no en el codigo): agregar un caso es
# agregar una fila al CSV. Se abre con utf-8 para no romper las tildes.
DATOS = Path(__file__).resolve().parent.parent / "data" / "casos_formulario.csv"


def cargar_casos_invalidos():
    """Lee data/casos_formulario.csv y lo convierte en parametros de pytest."""
    with open(DATOS, encoding="utf-8", newline="") as archivo:
        return [pytest.param(fila, id=fila["caso"]) for fila in csv.DictReader(archivo)]

# ---------- casos de exito ----------


def test_inscripcion_exitosa_muestra_codigo(driver, base_url, evidencia):
    """Formulario valido -> mensaje #mensaje-exito con codigo EST-XXXX."""
    pagina = PaginaInscripcion(driver, base_url)
    correo = f"ui-{uuid.uuid4().hex[:8]}@correo.com"

    pagina.llenar_formulario(
        nombre="Jhon Alexis Moreno",
        correo=correo,
        programa="Ingenieria de Sistemas",
        semestre=3,
    )
    evidencia("01_formulario_lleno")

    pagina.inscribir()
    mensaje = pagina.esperar_mensaje_exito()
    evidencia("02_mensaje_exito")

    assert "Inscripcion exitosa" in mensaje
    assert re.search(r"EST-\d{4}", mensaje), "debe mostrar un codigo EST-0000"


def test_listado_refleja_la_inscripcion(driver, base_url, evidencia):
    """Flujo completo: inscribir y comprobar que aparece en /estudiantes."""
    pagina = PaginaInscripcion(driver, base_url)
    correo = f"flujo-{uuid.uuid4().hex[:8]}@correo.com"

    pagina.llenar_formulario(
        nombre="Valentina Rojas Cruz",
        correo=correo,
        programa="Tecnologia en Desarrollo de Software",
        semestre=6,
    ).inscribir()
    pagina.esperar_mensaje_exito()
    evidencia("03_exito_antes_de_navegar")

    pagina.ir_al_listado()
    evidencia("04_listado_estudiantes")

    filas = pagina.filas_del_listado()
    assert len(filas) >= 1, "la tabla debe tener al menos una fila"
    assert any(correo in f.text for f in filas), "el correo inscrito debe aparecer en la tabla"
    assert any("Valentina Rojas Cruz" in f.text for f in filas)


# ---------- casos de error (validacion del servidor) ----------


def test_envio_vacio_muestra_los_cuatro_errores(driver, base_url, evidencia):
    """Enviar sin nada -> errores en nombre, correo, programa y semestre."""
    pagina = PaginaInscripcion(driver, base_url)
    pagina.enviar_vacio()

    errores = pagina.esperar_errores()   # espera explicita: el POST tarda ~0.5 s
    evidencia("05_errores_campos_vacios")

    assert set(errores) == {"nombre", "correo", "programa", "semestre"}
    assert "minimo 3 caracteres" in pagina.esperar_error("nombre")
    assert "Correo invalido" in pagina.texto_error("correo")
    assert "Programa no valido" in pagina.texto_error("programa")
    assert "entre 1 y 10" in pagina.texto_error("semestre")


@pytest.mark.parametrize("caso", cargar_casos_invalidos())
def test_formulario_muestra_error_por_campo(driver, base_url, evidencia, caso):
    """Un solo campo invalido -> el error aparece SOLO debajo de ese campo.

    Los datos salen de data/casos_formulario.csv (parametrizacion externa).
    """
    pagina = PaginaInscripcion(driver, base_url)
    pagina.llenar_formulario(
        nombre=caso["nombre"],
        correo=caso["correo"],
        programa=caso["programa"],
        semestre=caso["semestre"],
    ).inscribir()

    mensaje = pagina.esperar_error(caso["campo_error"])   # espera explicita (~0.5 s)
    evidencia(f"error_{caso['caso']}")

    assert mensaje == caso["mensaje_esperado"]
    assert pagina.errores_visibles() == [caso["campo_error"]], \
        "solo debe marcarse el campo que falto"


def test_semestre_fuera_de_rango_se_preservan_los_datos(driver, base_url, evidencia):
    """Semestre 99 -> error; ademas el servidor conserva lo que escribio el usuario."""
    pagina = PaginaInscripcion(driver, base_url)
    pagina.llenar_formulario(
        nombre="Camila Andres Herrera",
        correo=f"rango-{uuid.uuid4().hex[:8]}@correo.com",
        programa="Ingenieria de Sistemas",
        semestre=99,
    ).inscribir()

    assert "entre 1 y 10" in pagina.esperar_error("semestre")
    evidencia("07_error_semestre_99")

    actuales = pagina.valores_actuales()
    assert actuales["nombre"] == "Camila Andres Herrera", "el nombre debe seguir en el campo"
    assert actuales["semestre"] == "99", "el semestre debe seguir en el campo"


def test_correo_duplicado_se_marca_en_el_formulario(driver, base_url, evidencia):
    """Inscribir dos veces el mismo correo -> 'El correo ya esta registrado'."""
    correo = f"doble-{uuid.uuid4().hex[:8]}@correo.com"

    primera = PaginaInscripcion(driver, base_url)
    primera.llenar_formulario(
        nombre="Roberto Carlos Diaz",
        correo=correo,
        programa="Ingenieria Industrial",
        semestre=8,
    ).inscribir()
    primera.esperar_mensaje_exito()

    # segunda inscripcion con el mismo correo (nueva pagina, mismo navegador)
    segunda = PaginaInscripcion(driver, base_url)
    segunda.llenar_formulario(
        nombre="Roberto Carlos Diaz",
        correo=correo,
        programa="Ingenieria Industrial",
        semestre=8,
    ).inscribir()

    assert "ya esta registrado" in segunda.esperar_error("correo")
    evidencia("08_error_correo_duplicado")


# ---------- listado web (pagina /estudiantes, Page Object compartido) ----------


def test_listado_muestra_filas_y_contador_consistentes(driver, base_url, evidencia):
    """Pagina /estudiantes: filas visibles y contador #total coincidentes.

    Prueba de interfaz pura (solo navegador): valida la estructura del
    listado sin tocar la API. Reutiliza pages/listado_page.py, el Page
    Object compartido por todo el equipo.
    """
    pagina = PaginaListado(driver, base_url).abrir()
    evidencia("09_listado_pagina_completa")

    filas = pagina.filas()
    assert len(filas) >= 1, "el listado debe mostrar al menos un estudiante"
    assert pagina.total_declarado() == len(filas), \
        "el contador #total debe coincidir con el numero de filas de la tabla"
    assert all(re.match(r"EST-\d{4}$", codigo) for codigo in pagina.codigos()), \
        "cada fila debe mostrar su codigo EST-XXXX en la primera columna"
