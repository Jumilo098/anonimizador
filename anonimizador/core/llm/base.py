"""Capa OPCIONAL de IA. En V1 esta APAGADA y no hay ninguna implementacion.

Existe solo como punto de extension, con tres condiciones grabadas en piedra:
  1. ANONIMIZADOR debe funcionar completo sin ella;
  2. jamas se envia contenido real fuera del equipo sin una accion explicita
     e inequivoca del usuario;
  3. toda salida del modelo pasa por los mismos validadores deterministas
     (integridad clinica + alucinaciones + adversarial). El modelo nunca
     tiene la ultima palabra.
"""
from __future__ import annotations

from ...config import ALLOW_NETWORK, ENABLE_LLM


class LLMDesactivado(RuntimeError):
    pass


class ProveedorLLM:
    """Interfaz. Cualquier implementacion futura debe respetarla."""

    nombre = "ninguno"
    local = True

    def disponible(self) -> bool:
        return False

    def sugerir_identificadores(self, texto: str) -> list:
        """Solo puede SUGERIR. Nunca reescribe el documento."""
        raise LLMDesactivado(
            "La capa de IA esta desactivada en V1 (ENABLE_LLM=False)."
        )


def obtener_proveedor():
    if not ENABLE_LLM:
        return None
    if not ALLOW_NETWORK:
        # solo se aceptarian proveedores locales
        return None
    return None


def estado() -> dict:
    return {
        "llm_habilitado": ENABLE_LLM,
        "red_permitida": ALLOW_NETWORK,
        "proveedor": None,
        "nota": "V1 es 100% determinista: reglas, parsers y lexicos. Sin IA.",
    }
