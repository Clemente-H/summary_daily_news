"""
Categorizador de noticias por keywords. Sin dependencias internas.
"""
import re

_CATEGORIAS: list[tuple[str, list[str]]] = [
    ("Política", [
        "boric", "kast", "gobierno", "ministro", "ministra", "senado", "senador",
        "diputado", "diputada", "congreso", "cámara", "constitución", "constitucional",
        "udi", "partido", "oposición", "oficialismo", "reforma", "proyecto de ley",
        "sala cuna", "gabinete", "moneda", "concertación", "chile vamos", "frente amplio",
        "subsecretario", "intendente", "alcalde", "alcaldesa", "municipio",
    ]),
    ("Economía", [
        "dólar", "peso", "imacec", "inflación", "ipc", "banco central", "tasa",
        "cobre", "litio", "petróleo", "bencina", "combustible", "mercado", "bolsa",
        "pib", "empresa", "inversión", "exportación", "importación", "aranceles",
        "latam", "copec", "cmpc", "falabella", "codelco", "enap", "soquimich",
        "recesión", "desempleo", "empleo", "pensión", "afp", "isapre",
    ]),
    ("Mundo", [
        "trump", "estados unidos", "eeuu", "israel", "irán", "guerra", "kuwait",
        "rusia", "ucrania", "china", "gaza", "palestina", "medio oriente", "dubai",
        "arabia", "otan", "onu", "biden", "zelensky", "putin", "milei", "argentina",
        "brasil", "venezuela", "colombia", "perú", "bolivia", "migrante", "migración",
    ]),
    ("Deportes", [
        "colo colo", "universidad de chile", "la u ", "fútbol", "jarry", "tenis",
        "gol", "monumental", "superclásico", "copa", "mundial", "selección",
        "barrios", "maratón", "ciclismo", "básquetbol", "volleyball", "atletismo",
        "indian wells", "roland garros", "wimbledon", "us open",
    ]),
    ("Tecnología", [
        r"\bia\b", "inteligencia artificial", "anthropic", "openai", "google",
        "microsoft", "apple", "samsung", "startup", "ciberseguridad", "hack",
        "bitcoin", "criptomoneda", "blockchain", "robot", "automatización",
    ]),
    ("Ciencia", [
        "virus", "bacteria", "vacuna", "pandemia", "covid", "cáncer", "salud",
        "hospital", "médico", "investigación", "estudio", "nasa", "planeta",
        "terremoto", "tsunami", "volcán", "clima", "cambio climático",
    ]),
]

ORDEN = ["Política", "Economía", "Mundo", "Deportes", "Ciencia", "Tecnología", "General"]


def categorizar(title: str) -> str:
    t = title.lower()
    for cat, keywords in _CATEGORIAS:
        for kw in keywords:
            pattern = kw if kw.startswith(r"\b") else rf"\b{re.escape(kw)}\b"
            if re.search(pattern, t):
                return cat
    return "General"
