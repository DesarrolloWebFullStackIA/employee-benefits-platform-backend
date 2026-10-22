import os
from typing import List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.ollama_service import responder

router = APIRouter(prefix="/chat", tags=["Chat IA"])


class ChatMessage(BaseModel):
    role: str
    text: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


@router.post("/", status_code=status.HTTP_200_OK, summary="Hablar con el asistente virtual (Ollama)")
def chat_with_ai(request: ChatRequest):
    try:
        history_dicts = [{"role": h.role, "text": h.text} for h in request.history]
        resultado = responder(request.message, history_dicts)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el chat de IA: {str(e)}")


@router.get("/pdf/{nombre_archivo}", summary="Descargar PDF generado por la IA")
def descargar_pdf(nombre_archivo: str):
  
    ruta_pdf = os.path.join("pdfs", nombre_archivo)

    if not os.path.exists(ruta_pdf):
        raise HTTPException(status_code=404, detail="El archivo PDF no existe o ha caducado.")

    return FileResponse(
        path=ruta_pdf,
        filename=nombre_archivo,
        media_type="application/pdf"
    )