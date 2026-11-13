"""Envío de correos transaccionales mediante la API de Resend."""
import json
from html import escape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ResendError(RuntimeError):
    """Error controlado al comunicarse con Resend."""


def enviar_recuperacion(config, correo, nombre, enlace):
    """Envía directamente el enlace de recuperación al usuario."""
    if not config.RESEND_API_KEY or not config.RESEND_FROM_EMAIL:
        raise ResendError("Resend no está configurado")
    html = (
        f"<p>Hola {escape(nombre)},</p>"
        "<p>Recibimos una solicitud para restablecer tu contraseña de UNAreserva.</p>"
        f'<p><a href="{escape(enlace, quote=True)}">Restablecer contraseña</a></p>'
        "<p>Si no solicitaste este cambio, puedes ignorar este correo.</p>"
    )
    payload = {"from": config.RESEND_FROM_EMAIL, "to": [correo],
               "subject": "Recuperación de contraseña - UNAreserva", "html": html}
    request = Request(
        "https://api.resend.com/emails", data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {config.RESEND_API_KEY}",
                 "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=config.RESEND_TIMEOUT) as response:
            if not 200 <= response.status < 300:
                raise ResendError(f"Respuesta inesperada de Resend: {response.status}")
    except HTTPError as error:
        raise ResendError(f"Resend respondió con el código {error.code}") from error
    except (URLError, TimeoutError) as error:
        raise ResendError("No fue posible conectar con Resend") from error
    return True
