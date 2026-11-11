"""
Page Object del formulario de inscripcion (/inscripcion).

Centraliza localizadores y acciones: si la plantilla cambia, solo se
actualiza este archivo y las pruebas siguen intactas.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


class PaginaInscripcion:
    """Interfaz automatizable de la pagina /inscripcion."""

    RUTA = "/inscripcion"

    # ---- localizadores (un unico lugar para todo el HTML) ----
    CAMPO_NOMBRE = (By.ID, "nombre")
    CAMPO_CORREO = (By.ID, "correo")
    CAMPO_PROGRAMA = (By.ID, "programa")
    CAMPO_SEMESTRE = (By.ID, "semestre")
    BOTON_INSCRIBIR = (By.ID, "btn-inscribir")
    MENSAJE_EXITO = (By.ID, "mensaje-exito")
    ENLACE_LISTADO = (By.ID, "ver-listado")

    def __init__(self, driver, base_url, espera=8):
        self.driver = driver
        self.espera = WebDriverWait(driver, espera)
        self.driver.get(f"{base_url}{self.RUTA}")
        self.espera.until(EC.presence_of_element_located(self.CAMPO_NOMBRE))

    # ---------------- acciones ----------------
    def escribir(self, campo, valor):
        """Escribe en un campo por su clave logica (nombre, correo, semestre)."""
        elemento = self.espera.until(EC.presence_of_element_located(campo))
        elemento.clear()
        elemento.send_keys(valor)
        return self

    def llenar_formulario(self, nombre, correo, programa, semestre):
        """Completa los cuatro campos del formulario.

        `programa` vacio deja la opcion por defecto "-- Seleccione --"
        (el caso de prueba "sin_programa" del CSV).
        """
        self.escribir(self.CAMPO_NOMBRE, nombre)
        self.escribir(self.CAMPO_CORREO, correo)
        selector = Select(self.driver.find_element(*self.CAMPO_PROGRAMA))
        if programa:
            selector.select_by_visible_text(programa)
        else:
            selector.select_by_value("")
        self.escribir(self.CAMPO_SEMESTRE, str(semestre))
        return self

    def inscribir(self):
        """Pulsa el boton de envio (el servidor tarda ~0.5 s en responder)."""
        self.driver.find_element(*self.BOTON_INSCRIBIR).click()
        return self

    def enviar_vacio(self):
        """Pulsa Inscribir sin tocar nada (dispara todas las validaciones)."""
        return self.inscribir()

    def ir_al_listado(self):
        """Navega a /estudiantes mediante el enlace de la pagina."""
        self.espera.until(EC.element_to_be_clickable(self.ENLACE_LISTADO)).click()
        self.espera.until(EC.presence_of_element_located((By.ID, "tabla-estudiantes")))
        return self

    # ---------------- lecturas / esperas ----------------
    def esperar_mensaje_exito(self, tiempo=8):
        """Espera la confirmacion y devuelve su texto."""
        mensaje = self.espera.until(EC.presence_of_element_located(self.MENSAJE_EXITO))
        return mensaje.text.strip()

    def esperar_error(self, campo, tiempo=8):
        """Espera la div de error de un campo y devuelve su texto."""
        error = (By.ID, f"error-{campo}")
        elemento = WebDriverWait(self.driver, tiempo).until(EC.presence_of_element_located(error))
        return elemento.text.strip()

    def texto_error(self, campo):
        """Devuelve el texto del error si existe, o None."""
        elementos = self.driver.find_elements(By.ID, f"error-{campo}")
        return elementos[0].text.strip() if elementos else None

    def errores_visibles(self):
        """Lista de campos con error en pantalla."""
        return [e.get_attribute("id").replace("error-", "")
                for e in self.driver.find_elements(By.CSS_SELECTOR, ".error")]

    def esperar_errores(self, tiempo=8):
        """Espera a que el servidor responda con los errores y los lista.

        Necesario porque el POST tarda ~0.5 s (latencia simulada): sin esta
        espera se leeria la pagina anterior.
        """
        WebDriverWait(self.driver, tiempo).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".error"))
        )
        return self.errores_visibles()

    def valores_actuales(self):
        """Estado actual de los campos (para evidenciar preservacion de datos)."""
        return {
            "nombre": self.driver.find_element(*self.CAMPO_NOMBRE).get_attribute("value"),
            "correo": self.driver.find_element(*self.CAMPO_CORREO).get_attribute("value"),
            "semestre": self.driver.find_element(*self.CAMPO_SEMESTRE).get_attribute("value"),
        }

    def filas_del_listado(self):
        """Filas de la tabla de /estudiantes (requiere haber navegado a ella)."""
        return self.driver.find_elements(By.CSS_SELECTOR, "#tabla-estudiantes .fila-estudiante")
