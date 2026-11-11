# Taller U2 - Proyecto base para el estudiante

Sistema bajo prueba: mini aplicacion "Inscripciones CETO" (Flask)
- API REST:   GET/POST /api/estudiantes  ·  GET/DELETE /api/estudiantes/<id>
- Formulario: /inscripcion  ·  Listado: /estudiantes

> **Trabajo grupal AA2 (este repositorio).** Foco asignado: **1. Ciclo de vida
> del registro** (crear web/API → consultar → listar → eliminar → verificar
> ausencia). La suite completa son **37 pruebas**: 20 de API, 11 de interfaz y
> **6 flujos E2E** que cruzan capas. Guia completa en `GUIA_AA2.md` /
> `GUIA_AA2.html`.

## 0. Comandos del AA2 (resumen)

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt

python -m pytest -v                                   # suite completa (37)
python -m pytest -m api -v                            # solo API
python -m pytest -m ui -v                             # interfaz + flujos
python -m pytest -m e2e -v                            # solo flujos punta a punta
python -m pytest -v --html=reportes/reporte.html --self-contained-html
python tools/md_a_html.py GUIA_AA2.md GUIA_AA2.html   # documento HTML
```

Estructura (reparto de responsabilidades del equipo):

```
tests/conftest.py                    ← fixtures compartidas (no se modifica sin avisar)
tests/test_api_estudiantes.py        ← responsable de API (20 pruebas)
tests/test_formulario_inscripcion.py ← responsable de interfaz (11 pruebas)
tests/test_flujo_e2e.py              ← entre todos (6 flujos E2E)
pages/inscripcion_page.py            ← Page Object del formulario (interfaz)
pages/listado_page.py                ← Page Object del listado (interfaz)
data/casos_formulario.csv            ← datos de prueba parametrizados
.github/workflows/pruebas.yml        ← pipeline de CI
```


## 1. Instalar
```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/Mac: source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 2. Conocer la aplicacion (exploracion manual)
```bash
python -m app.servidor
```
Abra http://127.0.0.1:5000/inscripcion y http://127.0.0.1:5000/api/estudiantes

## 3. Escribir sus pruebas
- `tests/conftest.py` YA TRAE las fixtures: `base_url`, `api_url`, `driver`, `evidencia`.
  Las pruebas levantan su propio servidor: no necesita tener abierto el paso 2.
- Sus scripts van en `tests/` (nombres `test_*.py`) y sus Page Objects en `pages/`.

## 4. Ejecutar
```bash
python -m pytest -v
python -m pytest -v --html=reportes/reporte.html --self-contained-html
```

## Contrato de la API (lo que debe verificar)
| Operacion | Exito | Errores |
|---|---|---|
| POST /api/estudiantes (JSON: nombre, correo, programa, semestre) | 201 + estudiante con id | 400 cuerpo no JSON · 422 datos invalidos · 409 correo repetido |
| GET /api/estudiantes[?programa=...] | 200 + lista | - |
| GET /api/estudiantes/<id> | 200 + estudiante | 404 |
| DELETE /api/estudiantes/<id> | 204 | 404 |

Reglas: nombre minimo 3 caracteres · correo valido y unico · programa en
{Ingenieria de Sistemas, Tecnologia en Desarrollo de Software, Ingenieria Industrial} · semestre 1 a 10.
