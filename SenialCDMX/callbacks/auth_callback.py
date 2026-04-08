from dash import callback, Output, Input, State
from db.queries import crear_usuario

@callback(
    Output("store-usuario", "data", allow_duplicate=True),
    Output("store-rol", "data", allow_duplicate=True),
    Output("login-error", "children", allow_duplicate=True),
    Input("btn-register", "n_clicks"),
    State("reg-nombre", "value"),
    State("reg-telefono", "value"),
    State("reg-direccion", "value"),
    State("reg-email", "value"),
    State("reg-pass", "value"),
    prevent_initial_call=True
)
def registrar_usuario(n, nombre, telefono, direccion, email, password):

    if not n:
        return None, None, ""

    if not nombre or not email or not password:
        return None, None, "Faltan campos obligatorios"

    try:
        data = {
            "nombre": nombre,
            "correo": email,
            "password": password,
        }

        result = crear_usuario(data)

        print("Usuario creado:", result)

        # 🔥 LOGIN AUTOMÁTICO
        return (
            {
                "id": result[0],
                "nombre": nombre,
                "email": email
            },
            "ciudadano",
            ""
        )

    except Exception as e:
        print("ERROR REGISTRO:", e)
        return None, None, "Error al registrar usuario"