import asyncio
import base64
from dotenv import load_dotenv

load_dotenv()

from app.services.classifier import classify

def image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

async def main():
    descripcion = "Llovio y se cayo un arbol en mi calle y provoco una inundacion tremenda"
    imagen_b64 = image_to_base64("1.jpg")  # pon aquí tu imagen

    resultado = await classify(descripcion, image_base64=imagen_b64)
    print(f"Categoría: {resultado}")

asyncio.run(main())