"""
Page Object del listado de estudiantes (/estudiantes).

Regla del taller: UN SOLO Page Object por pagina, compartido por todo el
equipo.  Las pruebas de interfaz y los flujos punta a punta reutilizan esta
clase en lugar de localizar elementos a mano; si el HTML cambia, se corrige
solo aqui y las pruebas siguen intactas.

Solo informa (metodos de lectura/espera): los asserts viven en las pruebas.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class PaginaListado:
    """Interfaz automatizable de la pagina /estudiantes."""

    RUTA = "/estudiantes"

    # ---- localizadores (unico lugar para el HTML de esta pagina) ----
    TABLA = (By.ID, "tabla-estudiantes")
    FILAS = (By.CSS_SELECTOR, "#tabla-estudiantes .fila-estudiante")
    CONTADOR = (By.ID, "total")
    ENLACE_NUEVA = (By.PARTIAL_LINK_TEXT, "Nueva")

    def __init__(self, driver, base_url, espera=8):
        self.driver = driver
        self.base_url = base_url
        self.espera = WebDriverWait(driver, espera)

    # ---------------- acciones / navegacion ----------------
    def abrir(self):
        """Abre /estudiantes y espera a que la tabla este presente."""
        self.driver.get(f"{self.base_url}{self.RUTA}")
        self.espera.until(EC.presence_of_element_located(self.TABLA))
        return self

    def ir_a_inscripcion(self):
        """Vuelve al formulario mediante el enlace 'Nueva inscripcion'."""
        self.espera.until(EC.element_to_be_clickable(self.ENLACE_NUEVA)).click()
        self.espera.until(EC.presence_of_element_located((By.ID, "nombre")))
        return self

    # ---------------- lecturas ----------------
    def filas(self):
        """Filas visibles de la tabla (puede devolver [] si no hay datos)."""
        return self.driver.find_elements(*self.FILAS)

    def textos_de_filas(self):
        """Texto completo de cada fila (nombre + correo + programa + ...)."""
        return [f.text for f in self.filas()]

    def contiene(self, texto):
        """True si alguna fila de la tabla menciona el texto (correo, nombre...)."""
        return any(texto in fila for fila in self.textos_de_filas())

    def codigos(self):
        """Primer columna de cada fila: los codigos EST-XXXX visibles."""
        codigos = []
        for fila in self.filas():
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if celdas:
                codigos.append(celdas[0].text.strip())
        return codigos

    def total_declarado(self):
        """Numero que muestra el contador #total ('Total: N')."""
        texto = self.driver.find_element(*self.CONTADOR).text.strip()
        return int(texto.rsplit(":", 1)[-1].strip())

    # ---------------- esperas explicitas (nunca time.sleep) ----------------
    def esperar_fila_con(self, texto, tiempo=8):
        """Espera a que aparezca una fila que mencione el texto."""
        WebDriverWait(self.driver, tiempo).until(
            lambda d: any(texto in f.text for f in d.find_elements(*self.FILAS))
        )
        return self

    def esperar_que_no_haya_fila_con(self, texto, tiempo=8):
        """Espera a que desaparezca toda fila que mencione el texto.

        Clave para verificar el borrado: el GET de /estudiantes es inmediato,
        pero el navegador recarga la pagina, asi que hay que esperar el
        refresco en lugar de leer la tabla al azar.
        """
        WebDriverWait(self.driver, tiempo).until(
            lambda d: not any(texto in f.text for f in d.find_elements(*self.FILAS))
        )
        return self
