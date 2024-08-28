from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler
import uuid
import pypdfium2 as pdfium
from pathlib import Path
from PIL import Image
import img2pdf
import os
ESCALA_POR_DEFECTO = 1
CALIDAD_POR_DEFECTO = 70
MENSAJE_AYUDA = f"""Puedes especificar la escala y calidad en la descripción al enviar un documento, usando el formato escala,calidad (ej. 3,90) sin espacios ni comillas. 
Si no se especifica, se usarán los valores por defecto: escala {ESCALA_POR_DEFECTO} y calidad {CALIDAD_POR_DEFECTO}. 
La calidad puede ser entre 1 (peor) y 95 (mejor)."""
TOKEN_BOT_TELEGRAM = "Token de Telegram"


def extraer_numero_de_cadena_o_devolver_valor_por_defecto(numero_como_cadena: str, numero_por_defecto: int) -> int:
    try:
        numero = int(numero_como_cadena)
        return numero
    except ValueError:
        return numero_por_defecto


def parsear_escala_y_calidad(entrada: str) -> tuple[int, int]:
    valores_separados = entrada.split(",")
    valores_por_defecto = (ESCALA_POR_DEFECTO, CALIDAD_POR_DEFECTO)
    if len(valores_separados) != 2:
        return valores_por_defecto
    escala = extraer_numero_de_cadena_o_devolver_valor_por_defecto(
        valores_separados[0], ESCALA_POR_DEFECTO)
    calidad = extraer_numero_de_cadena_o_devolver_valor_por_defecto(
        valores_separados[1], CALIDAD_POR_DEFECTO)
    return (escala, calidad)


def comprimir_pdf(nombre_pdf, escala: int = 2, calidad: int = 70):
    nombre_pdf_comprimido = uuid.uuid4().hex + ".pdf"
    nombre_pdf_sin_extension = Path(nombre_pdf).stem
    """
    Extraer cada página del PDF como imagen
    """
    pdf = pdfium.PdfDocument(nombre_pdf)
    cantidad_paginas = len(pdf)
    imagenes = []
    for indice_pagina in range(cantidad_paginas):
        numero_pagina = indice_pagina+1
        nombre_imagen = f"{nombre_pdf_sin_extension}_{numero_pagina}.jpg"
        imagenes.append(nombre_imagen)
        pagina = pdf.get_page(indice_pagina)
        imagen_para_pil = pagina.render(scale=escala).to_pil()
        imagen_para_pil.save(nombre_imagen)

    imagenes_comprimidas = []
    """
    Comprimir imágenes.
    Entre menor calidad, menos peso del PDF resultante
    """
    for nombre_imagen in imagenes:
        nombre_imagen_sin_extension = Path(nombre_imagen).stem
        nombre_imagen_salida = nombre_imagen_sin_extension + \
            "_comprimida" + nombre_imagen[nombre_imagen.rfind("."):]
        imagen = Image.open(nombre_imagen)
        """
        El parámetro quality para JPEG se especifica en:
        https://pillow-wiredfool.readthedocs.io/en/latest/handbook/image-file-formats.html#jpeg
        """
        imagen.save(nombre_imagen_salida, optimize=True, quality=calidad)
        imagenes_comprimidas.append(nombre_imagen_salida)

    """
    Escribir imágenes en un nuevo PDF
    """
    with open(nombre_pdf_comprimido, "wb") as documento:
        documento.write(img2pdf.convert(imagenes_comprimidas))

    """
    Eliminar imágenes temporales
    """
    for imagen in imagenes + imagenes_comprimidas:
        os.remove(imagen)
    pdf.close()
    return nombre_pdf_comprimido


async def manejadorDeActualizaciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message == None:
        return
    if update.message.text =="/start":
        await update.message.reply_text(MENSAJE_AYUDA)
    if update.message.document != None:
        if update.message.document.mime_type != "application/pdf":
            return
        escala = ESCALA_POR_DEFECTO
        calidad = CALIDAD_POR_DEFECTO
        if update.message.caption != None:
            escala, calidad = parsear_escala_y_calidad(
                update.message.caption)
        await update.message.reply_text(f"Extrayendo páginas con escala {escala} y reduciendo calidad al {calidad} %.\n"+MENSAJE_AYUDA+"\nComprimiendo PDF...")
        archivo_recibido_desde_telegram = await update.message.effective_attachment.get_file()
        nombre_aleatorio_pdf_recibido = uuid.uuid4().hex
        ubicacion_archivo_recibido = await archivo_recibido_desde_telegram.download_to_drive(nombre_aleatorio_pdf_recibido + ".pdf")
        ubicacion_pdf_comprimido = comprimir_pdf(
            ubicacion_archivo_recibido, escala, calidad)
        await update.message.chat.send_document(ubicacion_pdf_comprimido, "Aquí tienes tu PDF comprimido según los parámetros indicados")
        os.remove(ubicacion_archivo_recibido)
        os.remove(ubicacion_pdf_comprimido)

app = ApplicationBuilder().token(TOKEN_BOT_TELEGRAM).build()
app.add_handler(MessageHandler(None, manejadorDeActualizaciones))
app.run_polling()
