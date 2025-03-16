import asyncio
import json
import datetime
import os
from dotenv import load_dotenv
from telegram.ext import MessageHandler, filters

# Carregar variáveis do .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Criando os botões
def criar_botoes(tarefas):
    keyboard = []
    for tarefa in tarefas:
        keyboard.append([InlineKeyboardButton(f"Concluir {tarefa}", callback_data=f"concluir_tarefa_{tarefa}")])
    return InlineKeyboardMarkup(keyboard)


# Nome do arquivo para armazenar pontos
PONTOS_FILE = 'pontos.json'

# Tradução dos dias da semana
dias_da_semana = {
    'monday': 'segunda-feira',
    'tuesday': 'terça-feira',
    'wednesday': 'quarta-feira',
    'thursday': 'quinta-feira',
    'friday': 'sexta-feira',
    'saturday': 'sábado',
    'sunday': 'domingo'
}

# Lista de tarefas diárias
tarefas_diarias = {
    'monday': ['Varrer a casa', 'Varrer a Garagem', 'Lavar a louça', 'Arrumar as Camas'],
    'tuesday': ['Lavar o banheiro', 'Tirar o pó da estante', 'Tirar os lixos', 'Arrumar as Camas'],
    'wednesday': ['Arrumar as Camas', 'Lavar a louça', 'Varrer a casa'],
    'thursday': ['Varrer a casa', 'Varrer a Garagem', 'Lavar a louça', 'Tirar os lixos', 'Arrumar as Camas'],
    'friday': ['Lavar o banheiro', 'Arrumar as Camas', 'Lavar a louça'],
    'saturday': ['Arrumar as Camas', 'Lavar a louça', 'Varrer a casa'],
    'sunday': ['Varrer a Garagem', 'Lavar a louça', 'Arrumar as Camas', 'Tirar os lixos']
}

CONCLUIDAS_FILE = 'concluidas.json'

def carregar_concluidas():
    if not os.path.exists(CONCLUIDAS_FILE):
        return {}
    try:
        with open(CONCLUIDAS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def salvar_concluidas(concluidas):
    with open(CONCLUIDAS_FILE, 'w') as f:
        json.dump(concluidas, f, indent=4)


# Carregar pontos do arquivo JSON
def carregar_pontos():
    if not os.path.exists(PONTOS_FILE):
        return {}
    try:
        with open(PONTOS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

# Salvar pontos no arquivo JSON
def salvar_pontos(pontos):
    with open(PONTOS_FILE, 'w') as f:
        json.dump(pontos, f, indent=4)

# Adicionar pontos ao usuário
def adicionar_pontos(usuario_id, pontos_adicionais):
    pontos = carregar_pontos()
    usuario_id = str(usuario_id)
    pontos[usuario_id] = pontos.get(usuario_id, 0) + pontos_adicionais
    salvar_pontos(pontos)

# Função para lidar com mensagens não reconhecidas
async def mensagem_invalida(update: Update,context: ContextTypes.DEFAULT_TYPE) -> None:
    usuario_id = update.message.chat_id
    await update.message.reply_text("⚠️ uai cebesta digite /start para iniciar.")
    imagem_path = 'imagens/risos.png'  # Caminho da imagem que você quer enviar
    with open(imagem_path, 'rb') as imagem:
        await context.bot.send_photo(chat_id=usuario_id, photo=imagem)

# Criar menu principal
async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("📋 Ver Tarefas do Dia", callback_data='ver_tarefas')],
        [InlineKeyboardButton("✅ Marcar Tarefa Concluída", callback_data='selecionar_tarefa')],
        [InlineKeyboardButton("✅✅ Concluir Todas as Tarefas     ", callback_data='concluir_todas')],
        [InlineKeyboardButton("🏆 Ver Meus Pontos", callback_data='ver_ranking')],
        [InlineKeyboardButton("💰 Trocar Pontos", callback_data='trocar_pontos')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("Escolha uma opção:", reply_markup=reply_markup)

    elif update.callback_query:
        await update.callback_query.message.edit_text("Escolha uma opção:", reply_markup=reply_markup)

# Exibir tarefas do dia
async def ver_tarefas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    dia_atual = datetime.datetime.now().strftime('%A').lower()
    dia_em_portugues = dias_da_semana.get(dia_atual, 'Não há tarefas definidas para hoje.')
    tarefas = tarefas_diarias.get(dia_atual, [])

    if not tarefas:
        mensagem = "🚫 Não há tarefas definidas para hoje."
    else:
        mensagem = f"📋 *Tarefas para {dia_em_portugues.capitalize()}*:\n" + "\n".join([f"• {tarefa}" for tarefa in tarefas])

    await query.message.edit_text(mensagem, parse_mode="Markdown")


# Exibir lista de tarefas para selecionar e concluir
async def selecionar_tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    dia_atual = datetime.datetime.now().strftime('%A').lower()
    tarefas = tarefas_diarias.get(dia_atual, [])

    if not tarefas:
        await query.edit_message_text("🚫 Não há tarefas para concluir hoje.")

        return

    # Carregar tarefas concluídas
    usuario_id = str(query.from_user.id)
    concluidas = carregar_concluidas()
    dia_atual_str = datetime.datetime.now().strftime('%Y-%m-%d')

    if usuario_id in concluidas and dia_atual_str in concluidas[usuario_id]:
        tarefas_concluidas = concluidas[usuario_id][dia_atual_str]
    else:
        tarefas_concluidas = []

    # Filtrar tarefas que ainda não foram concluídas
    tarefas_pendentes = [tarefa for tarefa in tarefas if tarefa not in tarefas_concluidas]

    if not tarefas_pendentes:
        await query.edit_message_text("✅ Todas as tarefas do dia já foram concluídas.")

        return

    # Criando botões para cada tarefa pendente
    keyboard = [[InlineKeyboardButton(tarefa, callback_data=f"concluir_{tarefa}")] for tarefa in tarefas_pendentes]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text("✅ Selecione a tarefa que deseja marcar como concluída:", reply_markup=reply_markup)

# Função para concluir tarefas individualmente
async def concluir_tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    usuario_id = str(query.from_user.id)

    # Print para depuração
    print(f"callback_data: {query.data}")

    # Caso especial: concluir todas as tarefas
    if query.data == "concluir_todas":
        await concluir_todas_as_tarefas(usuario_id, query,context)

        return

    # Tenta extrair a tarefa do callback_data
    try:
        tarefa = query.data.split("_", 1)[1]  # Extrai o nome da tarefa
    except IndexError:
        await query.edit_message_text("⚠️ O formato da tarefa está incorreto.")

        return

    print(f"Tarefa a ser concluída: {tarefa}")

    dia_atual = datetime.datetime.now().strftime('%Y-%m-%d')
    tarefas = tarefas_diarias.get(datetime.datetime.now().strftime('%A').lower(), [])

    if tarefa not in tarefas:
        await query.edit_message_text(f"⚠️ A tarefa '{tarefa}' não é válida para hoje.")

        return

    # Carregar tarefas concluídas
    concluidas = carregar_concluidas()

    if usuario_id not in concluidas:
        concluidas[usuario_id] = {}

    if dia_atual not in concluidas[usuario_id]:
        concluidas[usuario_id][dia_atual] = []

    if tarefa in concluidas[usuario_id][dia_atual]:
        await query.edit_message_text(f"⚠️ A tarefa '{tarefa}' já foi concluída hoje.")

        return

    # Marcar tarefa como concluída
    concluidas[usuario_id][dia_atual].append(tarefa)
    salvar_concluidas(concluidas)

    # Adicionar pontos ao usuário
    adicionar_pontos(usuario_id, 2)

    await query.edit_message_text(f"✅ Tarefa '{tarefa}' concluída! Você ganhou 2 XP!")


    print(f"Tarefas concluídas para {usuario_id} no dia {dia_atual}: {concluidas[usuario_id][dia_atual]}")


async def concluir_todas_as_tarefas(usuario_id: str, query, context) -> None:
    dia_atual = datetime.datetime.now().strftime('%Y-%m-%d')
    tarefas = tarefas_diarias.get(datetime.datetime.now().strftime('%A').lower(), [])

    concluidas = carregar_concluidas()

    if usuario_id not in concluidas:
        concluidas[usuario_id] = {}

    if dia_atual not in concluidas[usuario_id]:
        concluidas[usuario_id][dia_atual] = []

    # Verifica quais tarefas ainda não foram concluídas
    novas_tarefas = [tarefa for tarefa in tarefas if tarefa not in concluidas[usuario_id][dia_atual]]

    if not novas_tarefas:
        await query.edit_message_text("⚠️ Você já concluiu todas as tarefas de hoje!")

        return

    # Adiciona todas as tarefas não concluídas
    concluidas[usuario_id][dia_atual].extend(novas_tarefas)
    salvar_concluidas(concluidas)

    # Adicionar pontos ao usuário (2 pontos por tarefa)
    total_pontos = len(novas_tarefas) * 2
    adicionar_pontos(usuario_id, total_pontos)

    await query.edit_message_text(f"✅ Todas as tarefas foram concluídas! Você ganhou {total_pontos} XP!")

    print(f"Tarefas concluídas para {usuario_id} no dia {dia_atual}: {concluidas[usuario_id][dia_atual]}")

    # Enviar a imagem após a conclusão das tarefas
    imagem_path = 'imagens/gato.jpg'  # Caminho da imagem que você quer enviar
    with open(imagem_path, 'rb') as imagem:
        await context.bot.send_photo(chat_id=usuario_id, photo=imagem)

# Função para concluir todas as tarefas pendentes de uma vez
async def concluir_todas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    usuario_id = str(query.from_user.id)
    dia_atual = datetime.datetime.now().strftime('%Y-%m-%d')
    tarefas = tarefas_diarias.get(datetime.datetime.now().strftime('%A').lower(), [])
    if not tarefas:
        await query.edit_message_text("⚠️ Não há tarefas para concluir hoje.")
        return

    concluidas = carregar_concluidas()

    # Criar estrutura para o usuário e o dia, se não existirem
    if usuario_id not in concluidas:
        concluidas[usuario_id] = {}

    if dia_atual not in concluidas[usuario_id]:
        concluidas[usuario_id][dia_atual] = []

    # Filtrar tarefas que ainda não foram concluídas
    tarefas_pendentes = [tarefa for tarefa in tarefas if tarefa not in concluidas[usuario_id][dia_atual]]

    if not tarefas_pendentes:
        await query.edit_message_text("✅ Todas as tarefas do dia já foram concluídas.")

        return

    # Marcar todas as tarefas como concluídas e salvar
    concluidas[usuario_id][dia_atual].extend(tarefas_pendentes)
    salvar_concluidas(concluidas)

    # Calcular os pontos ganhos
    total_pontos = len(tarefas_pendentes) * 2
    adicionar_pontos(usuario_id, total_pontos)

    # Mostrar mensagem de confirmação
    await query.edit_message_text(f"✅ Todas as {len(tarefas_pendentes)} tarefas pendentes foram concluídas! Você ganhou {total_pontos} XP!")

async def enviar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Concluir todas as tarefas", callback_data="concluir_todas")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Você tem tarefas pendentes. Quer concluir todas?",
        reply_markup=reply_markup
    )

#ver ranking


async def ver_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pontos = carregar_pontos()
    if not pontos:
        await update.callback_query.answer("Ainda não há usuários com pontos registrados.", show_alert=True)
        return

    ranking = sorted(pontos.items(), key=lambda x: x[1], reverse=True)  # Ordena por pontos
    mensagem = "🏆 **Pontos Acumulados** 🏆\n\n"

    for idx, (usuario_id, pontos_usuario) in enumerate(ranking[:10], 1):  # Exibir top 10
        # Buscar o nome de usuário
        usuario = await context.bot.get_chat(usuario_id)  # Obter informações do usuário
        nome_usuario = usuario.username if usuario.username else usuario.first_name

        mensagem += f"{idx}. {nome_usuario}: {pontos_usuario} XP\n"  # Exibe nome ao invés de ID

    # Envia a mensagem de ranking
    await update.callback_query.message.edit_text(mensagem)

# Função para verificar se é o dia 10
def pode_trocar_pontos():
    hoje = datetime.datetime.now()
    return hoje.day == 10

async def trocar_pontos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    usuario_id = str(query.from_user.id)
    pontos = carregar_pontos()  # Função que carrega os pontos do usuário (no seu banco de dados ou arquivo)

    # Verificar se o dia atual é 10
    if not pode_trocar_pontos():
        await query.edit_message_text("⚠️ A troca de pontos só pode ser feita no dia 10 de cada mês.")
        return

    # Verificar se o usuário tem pontos suficientes
    if usuario_id not in pontos or pontos[usuario_id] == 0:
        await query.edit_message_text("❌ Você não tem pontos suficientes para trocar por dinheiro.")
        return

    valor_dinheiro = pontos[usuario_id] * 0.17  # Cada ponto vale R$ 0,17
    pontos[usuario_id] = 0  # Zera os pontos após a conversão
    salvar_pontos(pontos)  # Salva a atualização no arquivo JSON

    mensagem = f"💰 Você trocou seus pontos por **R$ {valor_dinheiro:.2f}**!\nSeus pontos foram resetados."
    await query.edit_message_text(mensagem)


# Configuração e inicialização do bot
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", menu_principal))
    application.add_handler(CallbackQueryHandler(ver_tarefas, pattern="^ver_tarefas$"))
    application.add_handler(CallbackQueryHandler(selecionar_tarefa, pattern="^selecionar_tarefa$"))
    application.add_handler(CallbackQueryHandler(concluir_tarefa, pattern=r"^concluir_.*$"))
    application.add_handler(CallbackQueryHandler(concluir_todas, pattern="^concluir_todas$"))
    application.add_handler(CallbackQueryHandler(ver_ranking, pattern="^ver_ranking$"))
    application.add_handler(CallbackQueryHandler(trocar_pontos, pattern="^trocar_pontos$"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensagem_invalida))

    application.run_polling()

if __name__ == '__main__':
    main()
