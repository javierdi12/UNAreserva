"""Cliente mínimo para enviar notificaciones mediante MailerLite."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class MailerLiteError(RuntimeError):
    """Error controlado al comunicarse con MailerLite."""


def _request(config, method, path, payload=None, allow_status=(200, 201, 202, 204)):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": f"Bearer {config.MAILERLITE_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if config.MAILERLITE_API_VERSION:
        headers["X-Version"] = config.MAILERLITE_API_VERSION
    request = Request(
        f"{config.MAILERLITE_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=config.MAILERLITE_TIMEOUT) as response:
            body = response.read().decode("utf-8")
            if response.status not in allow_status:
                raise MailerLiteError(f"Respuesta inesperada de MailerLite: {response.status}")
            return json.loads(body) if body else {}
    except HTTPError as error:
        detalle = error.read().decode("utf-8", errors="replace")
        raise MailerLiteError(f"MailerLite respondió {error.code}: {detalle}") from error
    except URLError as error:
        raise MailerLiteError(f"No fue posible conectar con MailerLite: {error.reason}") from error


def enviar_recuperacion(config, correo, nombre, enlace):
    """Actualiza un suscriptor y lo añade al grupo que dispara la automatización.

    La automatización debe existir previamente en MailerLite y usar el campo
    personalizado configurado en MAILERLITE_RESET_FIELD_KEY como enlace.
    """
    if not config.MAILERLITE_API_TOKEN or not config.MAILERLITE_RESET_GROUP_ID:
        raise MailerLiteError("MailerLite no está configurado")

    respuesta = _request(config, "POST", "/subscribers", {
        "email": correo,
        "fields": {
            "name": nombre,
            config.MAILERLITE_RESET_FIELD_KEY: enlace,
        },
        "status": "active",
    })
    subscriber_id = (respuesta.get("data") or {}).get("id")
    if not subscriber_id:
        raise MailerLiteError("MailerLite no devolvió el identificador del suscriptor")

    # Permite que la automatización se dispare nuevamente para otra solicitud.
    try:
        _request(
            config,
            "DELETE",
            f"/subscribers/{subscriber_id}/groups/{config.MAILERLITE_RESET_GROUP_ID}",
        )
    except MailerLiteError as error:
        if "respondió 404" not in str(error):
            raise
    _request(
        config,
        "POST",
        f"/subscribers/{subscriber_id}/groups/{config.MAILERLITE_RESET_GROUP_ID}",
    )

    return True
