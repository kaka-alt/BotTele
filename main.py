import logging
import os
import threading
from dotenv import load_dotenv

from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)
import handlers
from handlers import *

from fastapi import FastAPI
import uvicorn

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def cancelar(update, context):
    await update.message.reply_text("Operação cancelada pelo usuário.")
    context.user_data.clear()
    return ConversationHandler.END

async def start(update, context):
    await update.message.reply_text("Olá! Use /iniciar para começar o registro de uma ocorrência.")

def iniciar_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)

def iniciar_bot():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("Error: BOT_TOKEN not found in environment variables or .env file")
        return

    application = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('iniciar', handlers.iniciar_colaborador)],
        states={
            # ... seus estados ...
            "COLABORADOR": [CallbackQueryHandler(handlers.colaborador_button, pattern="^colaborador_")],
            "COLABORADOR_MANUAL": [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.colaborador_manual)],
            "ORGAO_PUBLICO_KEYWORD": [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.buscar_orgao)],
            "ORGAO_PUBLICO_PAGINACAO": [CallbackQueryHandler(handlers.orgao_paginacao, pattern="^orgao_")],
            "ORGAO_PUBLICO_MANUAL": [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.orgao_manual)],
            "FIGURA_PUBLICA": [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.figura_publica_input)],
            "CARGO": [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.cargo)],
            "ASSUNTO_PALAVRA_CHAVE": [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.buscar_assunto)],
            "ASSUNTO_PAGINACAO": [CallbackQueryHandler(handlers.assunto_paginacao, pattern="^assunto_")],
            "ASSUNTO_MANUAL": [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.assunto_manual)],
            "MUNICIPIO": [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.municipio)],
            "DATA": [
                CallbackQueryHandler(handlers.data, pattern="^data_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.data),
            ],
            "DATA_MANUAL": [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.data)],
            "FOTO": [MessageHandler(filters.PHOTO, handlers.foto)],
            "DEMANDA_ESCOLHA": [CallbackQueryHandler(handlers.demanda, pattern="^(add_demanda|pular_demanda|fim_demandas)$")],
            "DEMANDA_DIGITAR": [MessageHandler(filters.TEXT & ~filters.COMMAND, demanda_digitar)],
            "OV": [MessageHandler(filters.TEXT & ~filters.COMMAND, ov)],
            "PRO": [MessageHandler(filters.TEXT & ~filters.COMMAND, pro)],
            "OBSERVACAO_ESCOLHA": [CallbackQueryHandler(observacao_escolha, pattern="^(add_obs|skip_obs)$")],
            "OBSERVACAO_DIGITAR": [MessageHandler(filters.TEXT & ~filters.COMMAND, observacao_digitar)],
            "CONFIRMACAO_FINAL": [CallbackQueryHandler(handlers.confirmacao, pattern="^(confirmar_salvar|cancelar_resumo)$")],
        },
        fallbacks=[CommandHandler('cancelar', cancelar)],
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)

    application.run_polling()

app = FastAPI()

@app.get("/export")
def exportar():
    os.system("python export_to_excel.py")
    return {"status": "Exportação iniciada"}

if __name__ == "__main__":
    # FastAPI rodando em thread daemon (background)
    threading.Thread(target=iniciar_fastapi, daemon=True).start()

    # Bot rodando no main thread (obrigatório para PTB lidar com sinais)
    iniciar_bot()
