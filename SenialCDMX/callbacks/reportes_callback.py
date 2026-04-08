from dash import callback, Output, Input, State
from db.queries import crear_reporte


# 🔥 GUARDAR REPORTE EN NEON
@callback(
    Output("store-ai-result", "data"),
    Input("store-paso-actual", "data"),
    State("descripcion-texto", "value"),
    State("lat-input", "value"),
    State("lon-input", "value"),
    State("store-usuario", "data"),
    prevent_initial_call=True
)
def guardar_reporte_en_db(paso, descripcion, lat, lon, user):

    # Solo guardar cuando llega al paso final
    if paso != 4:
        return None

    if not user:
        print("No hay usuario logueado")
        return None

    try:
        data = {
            "usuario_id": user["id"],  # 🔥 REAL
            "descripcion": descripcion,
            "categoria": "infraestructura",  # luego lo puedes hacer dinámico
            "lat": float(lat),
            "lng": float(lon),
            "direccion": "CDMX",
            "fuente": "texto",
            "tiene_imagen": False
        }

        result = crear_reporte(data)

        print("Reporte guardado:", result)

        return {
            "id": result[0],
            "codigo": result[1]
        }

    except Exception as e:
        print("ERROR AL GUARDAR:", e)
        return None