# =====================================================================
#  TP07 - Inteligencia Artificial
#  Agente que interpreta comandos en lenguaje natural
#
#  ESTE ES EL ARCHIVO DONDE ESCRIBIS TU PROGRAMA.
#
#  Antes de ejecutarlo:
#    1. Abri INICIAR_SIMULADOR (elegi G1 o Go2)
#    2. Espera a que aparezca la ventana con el robot
#    3. Recien ahi ejecuta este archivo
#
#  Nombre y apellido:  .....................................
#  Comision:           .....................................
# =====================================================================

import re
import unicodedata
from robot import Robot
from evaluar import evaluar
from ejecutor import DICCIONARIO_SENAS, Ejecutor


class ClasificadorIntencion:
    """Decide QUE quiere el usuario, incluyendo la interpretacion de senas."""

    TIPOS = ("MOVER", "GIRAR", "DETENERSE", "SALUDO", "SENAS",
             "CONSULTAR_ESTADO", "DESCONOCIDO")

    def __init__(self):
        self.modelo = None

    def clasificar(self, texto):
        texto_l = texto.lower().strip()

        # Patron para detectar peticiones de lenguaje de senas
        if re.search(r"\b(seña|señas|lenguaje de señas|traduc\w*|interpreta|dec\w*|gesto)\b", texto_l):
            return "SENAS"
        if re.fullmatch(r"(gracias|chau)", texto_l):
            return "SENAS"
        texto_sin_acentos = "".join(
            caracter for caracter in unicodedata.normalize("NFD", texto_l)
            if unicodedata.category(caracter) != "Mn"
        )
        if texto_sin_acentos in DICCIONARIO_SENAS and texto_sin_acentos != "hola":
            return "SENAS"
        palabras_senas = re.findall(
            r"\b(hola|gracias|chau|por|favor|ayuda|amigo|buenos|dias|"
            r"si|no|perdon|robot|manana|noche|agua|comer|casa|escuela|"
            r"familia|venir|donde|nombre)\b",
            texto_l,
        )
        if len(palabras_senas) >= 2:
            return "SENAS"
        if re.search(r"\b(avanza|movete|adelante|camina|retrocede)\b", texto_l):
            return "MOVER"
        if re.search(r"\b(gira|rota|vuelta|dobla)\b", texto_l):
            return "GIRAR"
        if re.search(r"\b(detente|para|frena|quieto|stop)\b", texto_l):
            return "DETENERSE"
        if re.fullmatch(r"hola", texto_l) or re.search(
            r"\b(saluda|hace un saludo)\b", texto_l):
            return "SALUDO"
        if re.search(r"\b(bateria|estado|como estas)\b", texto_l):
            return "CONSULTAR_ESTADO"

        return "DESCONOCIDO"


# =====================================================================
#  ETAPA 2 - EXTRACTOR DE PARAMETROS
# =====================================================================
class ExtractorParametros:
    """Extrae parametros numericos y de texto del comando."""

    def extraer(self, texto, tipo):
        p = {}
        texto_l = texto.lower()

        if tipo == "SENAS":
            # Extrae la frase encerrada entre comillas o remueve palabras de activacion
            match_comillas = re.search(r'["\']([^"\']+)["\']', texto)
            if match_comillas:
                p["texto_senas"] = match_comillas.group(1)
            else:
                limpio = re.sub(
                    r"\b(hacé|hace|haz|en|lenguaje|de|señas|seña|traducí|traducime|"
                    r"traduce|traducir|interpreta|decí|diga|esta|este|oración|"
                    r"oracion|frase|a|al|la|el|una|un)\b",
                    "",
                    texto_l,
                )
                p["texto_senas"] = limpio.strip()

        elif tipo == "MOVER":
            match_dist = re.search(r"(\d+(?:\.\d+)?)\0*m(?:etros)?", texto_l)
            if match_dist:
                p["distancia_m"] = float(match_dist.group(1))
            if "atras" in texto_l or "retrocede" in texto_l:
                p["direccion"] = "atras"

        elif tipo == "GIRAR":
            match_ang = re.search(r"(\d+(?:\.\d+)?)\0*grad(?:os)?", texto_l)
            if match_ang:
                p["angulo_deg"] = float(match_ang.group(1))
            if "derecha" in texto_l:
                p["direccion"] = "derecha"

        return p


# =====================================================================
#  ETAPA 3 - VALIDADOR DE SEGURIDAD
# =====================================================================
class ValidadorSeguridad:
    PALABRAS_PELIGROSAS = ("salta", "salto", "corre", "corré", "sprint",
                           "empuja", "empujá", "golpea", "rompe", "tira",
                           "cae", "fuerza")

    def __init__(self, perfil):
        self.perfil = perfil

    def validar(self, texto, tipo, parametros):
        texto_l = texto.lower()
        for peligro in self.PALABRAS_PELIGROSAS:
            if peligro in texto_l:
                return False, f"Comando bloqueado por contener palabra peligrosa: '{peligro}'"

        if tipo == "MOVER":
            if parametros.get("distancia_m", 0) > 10.0:
                return False, "Distancia excesiva para el entorno."
        elif tipo == "GIRAR":
            if parametros.get("angulo_deg", 0) > 360:
                return False, "Angulo de giro fuera de limite seguro."

        return True, ""


# =====================================================================
#  EL AGENTE - Pipeline completo
# =====================================================================
class AgenteRobot:
    def __init__(self, robot=None):
        self.robot = robot
        self.clasificador = ClasificadorIntencion()
        self.extractor = ExtractorParametros()
        self.validador = ValidadorSeguridad(
            robot.perfil if robot else _perfil_por_defecto())
        self.ejecutor = Ejecutor(robot) if robot else None

    def procesar(self, texto):
        tipo = self.clasificador.clasificar(texto)
        parametros = self.extractor.extraer(texto, tipo)
        es_seguro, motivo = self.validador.validar(texto, tipo, parametros)

        if not es_seguro:
            return {
                "tipo": tipo,
                "parametros": parametros,
                "ejecutar": False,
                "bloqueado": True,
                "confianza": 1.0,
                "texto_original": texto,
                "mensaje": motivo,
            }

        if tipo == "DESCONOCIDO":
            return {
                "tipo": "DESCONOCIDO",
                "parametros": {},
                "ejecutar": False,
                "bloqueado": False,
                "confianza": 0.0,
                "texto_original": texto,
                "mensaje": "No reconozco la intencion del comando.",
            }

        mensaje_ej = ""
        if self.ejecutor:
            mensaje_ej = self.ejecutor.ejecutar(tipo, parametros)

        return {
            "tipo": tipo,
            "parametros": parametros,
            "ejecutar": True,
            "bloqueado": False,
            "confianza": 0.9,
            "texto_original": texto,
            "mensaje": mensaje_ej,
        }

def _perfil_por_defecto():
    import sys
    from pathlib import Path
    entorno = Path(__file__).resolve().parent.parent / "entorno"
    if str(entorno) not in sys.path:
        sys.path.insert(0, str(entorno))
    from sim.safety import perfil
    return perfil("tp07")


# =====================================================================
#  PROGRAMA PRINCIPAL - no hace falta que lo toques
# =====================================================================
def main():
    import sys

    # Modo sin robot: solo evalua los 25 casos. Sirve para trabajar el
    # clasificador sin tener el simulador abierto.
    sin_robot = "--sin-robot" in sys.argv

    robot_cliente = None
    if not sin_robot:
        robot_cliente = Robot()
        robot_cliente.conectar()

    try:
        agente = AgenteRobot(robot_cliente)
        evaluar(agente)

        if robot_cliente is not None:
            print("\n  Escribi ordenes para el robot. Enter vacio para salir.")
            while True:
                try:
                    texto = input("\n  > ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not texto:
                    break
                r = agente.procesar(texto)
                print(f"    {r['tipo']}  {r.get('mensaje', '')}")
    finally:
        if robot_cliente is not None:
            robot_cliente.detenerse()
            robot_cliente.desconectar()


if __name__ == "__main__":
    main()
