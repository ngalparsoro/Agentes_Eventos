"""Autoriza Gmail en Composio."""

from composio import SESSION_PRESET_DIRECT_TOOLS

from src.gmail import crear_cliente_composio
from src.parametros import COMPOSIO_USER_ID


TOOLKIT = "gmail"


def autorizar_google():
    """Autoriza la conexión de Gmail."""

    composio = crear_cliente_composio()

    sesion = composio.create(
        user_id=COMPOSIO_USER_ID,
        toolkits=[TOOLKIT],
        session_preset=SESSION_PRESET_DIRECT_TOOLS,
    )

    cuentas = composio.connected_accounts.list(
        user_ids=[COMPOSIO_USER_ID],
        toolkit_slugs=[TOOLKIT],
        statuses=["ACTIVE"],
    )

    if cuentas.items:
        print("gmail ya está conectado.")
        return

    solicitud = sesion.authorize(TOOLKIT)

    print("\nAutoriza Gmail en este enlace:")
    print(solicitud.redirect_url)

    solicitud.wait_for_connection(timeout=300)
    print("gmail conectado correctamente.")


if __name__ == "__main__":
    autorizar_google()
