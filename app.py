from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import uuid  # opcional, mas mantive ID incremental para simplicidade

app = Flask(__name__)
CORS(app)  # libera CORS para todos os domínios (ideal para dev)

# ==========================================
# SIMULAÇÃO DE BANCO DE DADOS (MOCK DATA)
# ==========================================
DATABASE = {
    "usuarios": [
        {"id": 1, "nome": "Admin Geral", "tipo": "admin", "usuario": "admin", "senha": "admin123"},
        {"id": 2, "nome": "Dr. Carlos (Dentista)", "tipo": "profissional", "usuario": "carlos", "senha": "123", "jornada": "08:00-17:00"},
        {"id": 3, "nome": "Dra. Ana (Estética)", "tipo": "profissional", "usuario": "ana", "senha": "123", "jornada": "09:00-18:00"},
        {"id": 4, "nome": "João Silva", "tipo": "cliente", "usuario": "joao", "senha": "123", "assinante": True},
        {"id": 5, "nome": "Maria Souza", "tipo": "cliente", "usuario": "maria", "senha": "123", "assinante": False}
    ],
    "servicos": [
        {"id": 1, "nome": "Consulta Geral", "duracao_minutos": 30, "preco": 150.00, "disponivel": True},
        {"id": 2, "nome": "Limpeza Completa", "duracao_minutos": 45, "preco": 200.00, "disponivel": True}
    ],
    "agendamentos": [
        {"id": 1, "cliente_id": 4, "profissional_id": 2, "servico_id": 1, "data_hora": "2026-07-05 09:00", "status": "concluido"},
        {"id": 2, "cliente_id": 5, "profissional_id": 2, "servico_id": 2, "data_hora": "2026-07-05 10:00", "status": "agendado"}
    ]
}

# Contadores para geração de IDs (evita problemas com len() se houver exclusão)
next_id_usuario = max(u["id"] for u in DATABASE["usuarios"]) + 1
next_id_servico = max(s["id"] for s in DATABASE["servicos"]) + 1
next_id_agendamento = max(a["id"] for a in DATABASE["agendamentos"]) + 1

# ==========================================
# HELPERS (FUNÇÕES DE SUPORTE)
# ==========================================

def validar_data_hora(data_hora_str):
    """Valida formato 'YYYY-MM-DD HH:MM' e retorna objeto datetime ou None"""
    try:
        return datetime.strptime(data_hora_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return None

def verificar_existencia(entidade, id):
    """Verifica se um ID existe na lista de entidades"""
    return any(item["id"] == id for item in DATABASE[entidade])

def calcular_metricas_globais():
    agendamentos = DATABASE["agendamentos"]
    servicos = {s["id"]: s for s in DATABASE["servicos"]}
    
    # Soma preços apenas para agendamentos com status 'agendado' ou 'concluido'
    faturamento = 0.0
    for a in agendamentos:
        if a["status"] in ["agendado", "concluido"]:
            servico = servicos.get(a["servico_id"])
            if servico:
                faturamento += servico["preco"]
    
    # Tempo total agendado (apenas agendamentos confirmados)
    tempo_total_agendado = sum(
        servicos[a["servico_id"]]["duracao_minutos"]
        for a in agendamentos
        if a["status"] in ["agendado", "concluido"] and a["servico_id"] in servicos
    )
    
    # Capacidade total = número de profissionais * 8h (480 min)
    profissionais = [u for u in DATABASE["usuarios"] if u["tipo"] == "profissional"]
    capacidade_total = len(profissionais) * 480
    taxa_ocupacao = (tempo_total_agendado / capacidade_total) * 100 if capacidade_total > 0 else 0
    
    return faturamento, min(taxa_ocupacao, 100)

# ==========================================
# AUTENTICAÇÃO SIMULADA (para demonstração)
# ==========================================

def autenticar(usuario, senha):
    """Retorna o usuário se credenciais válidas, senão None"""
    for u in DATABASE["usuarios"]:
        if u["usuario"] == usuario and u.get("senha") == senha:
            return u
    return None

# Decoradores de autorização (simples)
def requer_admin(f):
    def wrapper(*args, **kwargs):
        # Espera-se que o front envie um cabeçalho 'X-User-Id' ou 'Authorization'
        # Aqui simulamos com um parâmetro de query 'user_id' para facilitar testes
        user_id = request.args.get('user_id') or request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({"status": "erro", "mensagem": "Usuário não autenticado"}), 401
        user = next((u for u in DATABASE["usuarios"] if u["id"] == int(user_id)), None)
        if not user or user["tipo"] != "admin":
            return jsonify({"status": "erro", "mensagem": "Acesso negado: necessário admin"}), 403
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def requer_profissional_ou_admin(f):
    def wrapper(*args, **kwargs):
        user_id = request.args.get('user_id') or request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({"status": "erro", "mensagem": "Usuário não autenticado"}), 401
        user = next((u for u in DATABASE["usuarios"] if u["id"] == int(user_id)), None)
        if not user or user["tipo"] not in ["profissional", "admin"]:
            return jsonify({"status": "erro", "mensagem": "Acesso negado: necessário profissional ou admin"}), 403
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ==========================================
# ROTA DE LOGIN (para obter ID do usuário)
# ==========================================

@app.route('/login', methods=['POST'])
def login():
    dados = request.json
    if not dados or "usuario" not in dados or "senha" not in dados:
        return jsonify({"status": "erro", "mensagem": "Campos 'usuario' e 'senha' obrigatórios"}), 400
    
    user = autenticar(dados["usuario"], dados["senha"])
    if not user:
        return jsonify({"status": "erro", "mensagem": "Credenciais inválidas"}), 401
    
    return jsonify({
        "status": "sucesso",
        "usuario": {
            "id": user["id"],
            "nome": user["nome"],
            "tipo": user["tipo"]
        }
    })

# ==========================================
# 1. ÁREA DO ADMINISTRADOR
# ==========================================

@app.route('/admin/dashboard', methods=['GET'])
@requer_admin
def admin_dashboard():
    """Painel geral do administrador"""
    clientes = [u for u in DATABASE["usuarios"] if u["tipo"] == "cliente"]
    assinantes = [c for c in clientes if c.get("assinante", False)]
    faturamento, taxa_ocupacao = calcular_metricas_globais()
    
    return jsonify({
        "status": "sucesso",
        "dados": {
            "total_clientes_cadastrados": len(clientes),
            "total_assinantes": len(assinantes),
            "faturamento_total_R$": faturamento,
            "taxa_de_ocupacao_global_%": round(taxa_ocupacao, 2),
            "profissionais": [u for u in DATABASE["usuarios"] if u["tipo"] == "profissional"]
        }
    })

@app.route('/admin/servicos', methods=['POST'])
@requer_admin
def admin_adicionar_servico():
    """Adiciona ou edita serviços, durações e disponibilidades"""
    dados = request.json
    if not dados:
        return jsonify({"status": "erro", "mensagem": "Dados JSON inválidos"}), 400
    
    # Validação de campos obrigatórios
    campos = ["nome", "duracao_minutos", "preco"]
    for campo in campos:
        if campo not in dados:
            return jsonify({"status": "erro", "mensagem": f"Campo '{campo}' é obrigatório"}), 400
    
    # Validações adicionais
    if not isinstance(dados["duracao_minutos"], int) or dados["duracao_minutos"] <= 0:
        return jsonify({"status": "erro", "mensagem": "duracao_minutos deve ser um inteiro positivo"}), 400
    if not isinstance(dados["preco"], (int, float)) or dados["preco"] < 0:
        return jsonify({"status": "erro", "mensagem": "preco deve ser um número não negativo"}), 400
    
    global next_id_servico
    novo_servico = {
        "id": next_id_servico,
        "nome": dados["nome"],
        "duracao_minutos": dados["duracao_minutos"],
        "preco": float(dados["preco"]),
        "disponivel": dados.get("disponivel", True)
    }
    DATABASE["servicos"].append(novo_servico)
    next_id_servico += 1
    
    return jsonify({
        "status": "sucesso",
        "mensagem": "Serviço criado com sucesso!",
        "servico": novo_servico
    }), 201

@app.route('/admin/profissional/<int:prof_id>/horario', methods=['PUT'])
@requer_admin
def admin_alterar_horario_profissional(prof_id):
    """Regra estrita: Apenas o Admin altera o horário de funcionamento do profissional"""
    dados = request.json
    if not dados or "nova_jornada" not in dados:
        return jsonify({"status": "erro", "mensagem": "Campo 'nova_jornada' obrigatório"}), 400
    
    # Verifica se o profissional existe
    usuario = next((u for u in DATABASE["usuarios"] if u["id"] == prof_id and u["tipo"] == "profissional"), None)
    if not usuario:
        return jsonify({"status": "erro", "mensagem": "Profissional não encontrado"}), 404
    
    # Atualiza a jornada
    usuario["jornada"] = dados["nova_jornada"]
    return jsonify({
        "status": "sucesso",
        "mensagem": f"Jornada de {usuario['nome']} alterada para {dados['nova_jornada']}"
    })

# ==========================================
# 2. ÁREA DO PROFISSIONAL (Visão Limitada)
# ==========================================

@app.route('/profissional/<int:prof_id>/agenda', methods=['GET'])
@requer_profissional_ou_admin
def profissional_agenda(prof_id):
    """Visualização limitada dos agendamentos, produtividade e ocupação do profissional"""
    # Verifica se o usuário é realmente um profissional (ou admin)
    prof = next((u for u in DATABASE["usuarios"] if u["id"] == prof_id and u["tipo"] == "profissional"), None)
    if not prof:
        return jsonify({"status": "erro", "mensagem": "Profissional não encontrado"}), 404
    
    # Filtra os agendamentos deste profissional
    servicos_dict = {s["id"]: s for s in DATABASE["servicos"]}
    clientes_dict = {u["id"]: u["nome"] for u in DATABASE["usuarios"] if u["tipo"] == "cliente"}
    
    meus_agendamentos = []
    tempo_trabalhado = 0
    
    for a in DATABASE["agendamentos"]:
        if a["profissional_id"] == prof_id:
            servico = servicos_dict.get(a["servico_id"])
            if not servico:
                continue  # serviço foi removido? ignorar
            nome_cliente = clientes_dict.get(a["cliente_id"], "Cliente Desconhecido")
            meus_agendamentos.append({
                "data_hora": a["data_hora"],
                "cliente": nome_cliente,
                "servico": servico["nome"],
                "status": a["status"]
            })
            if a["status"] == "concluido":
                tempo_trabalhado += servico["duracao_minutos"]
    
    # Produtividade: minutos atendidos vs jornada atual (assumindo 8h se não definida)
    jornada_str = prof.get("jornada", "08:00-17:00")
    # Para simplificar, considera 8h (480 min) - poderia extrair da string
    jornada_minutos = 480
    taxa_produtividade = (tempo_trabalhado / jornada_minutos) * 100 if jornada_minutos > 0 else 0
    
    return jsonify({
        "status": "sucesso",
        "dados": {
            "profissional": prof["nome"],
            "jornada_de_trabalho": prof.get("jornada", "Não definida"),
            "taxa_produtividade_diaria_%": round(min(taxa_produtividade, 100), 2),
            "seus_agendamentos": meus_agendamentos
        }
    })

# ==========================================
# 3. ÁREA DO CLIENTE (Cadastro e Agendamento)
# ==========================================

@app.route('/cliente/cadastro', methods=['POST'])
def cliente_cadastro():
    """Permite o auto-cadastro do cliente"""
    dados = request.json
    if not dados:
        return jsonify({"status": "erro", "mensagem": "Dados JSON inválidos"}), 400
    
    campos = ["nome", "usuario", "senha"]
    for campo in campos:
        if campo not in dados:
            return jsonify({"status": "erro", "mensagem": f"Campo '{campo}' é obrigatório"}), 400
    
    # Verifica se usuário já existe
    if any(u["usuario"] == dados["usuario"] for u in DATABASE["usuarios"]):
        return jsonify({"status": "erro", "mensagem": "Usuário já cadastrado"}), 409
    
    global next_id_usuario
    novo_cliente = {
        "id": next_id_usuario,
        "nome": dados["nome"],
        "tipo": "cliente",
        "usuario": dados["usuario"],
        "senha": dados["senha"],
        "assinante": dados.get("assinante", False)
    }
    DATABASE["usuarios"].append(novo_cliente)
    next_id_usuario += 1
    
    return jsonify({
        "status": "sucesso",
        "mensagem": "Cadastro realizado com sucesso!",
        "cliente": {"id": novo_cliente["id"], "nome": novo_cliente["nome"], "usuario": novo_cliente["usuario"]}
    }), 201

@app.route('/cliente/agendar', methods=['POST'])
def cliente_agendar():
    """Permite ao cliente escolher o serviço, o profissional e o horário"""
    dados = request.json
    if not dados:
        return jsonify({"status": "erro", "mensagem": "Dados JSON inválidos"}), 400
    
    campos = ["cliente_id", "profissional_id", "servico_id", "data_hora"]
    for campo in campos:
        if campo not in dados:
            return jsonify({"status": "erro", "mensagem": f"Campo '{campo}' é obrigatório"}), 400
    
    # Validar IDs
    if not verificar_existencia("usuarios", dados["cliente_id"]):
        return jsonify({"status": "erro", "mensagem": "Cliente não encontrado"}), 404
    if not verificar_existencia("usuarios", dados["profissional_id"]):
        return jsonify({"status": "erro", "mensagem": "Profissional não encontrado"}), 404
    if not verificar_existencia("servicos", dados["servico_id"]):
        return jsonify({"status": "erro", "mensagem": "Serviço não encontrado"}), 404
    
    # Validar formato da data/hora
    data_hora = validar_data_hora(dados["data_hora"])
    if not data_hora:
        return jsonify({"status": "erro", "mensagem": "Formato de data/hora inválido. Use 'YYYY-MM-DD HH:MM'"}), 400
    
    # Verificar conflito de horário para o mesmo profissional
    for a in DATABASE["agendamentos"]:
        if a["profissional_id"] == dados["profissional_id"] and a["data_hora"] == dados["data_hora"]:
            return jsonify({"status": "erro", "mensagem": "Horário já ocupado para este profissional"}), 409
    
    # Verificar se o serviço está disponível
    servico = next(s for s in DATABASE["servicos"] if s["id"] == dados["servico_id"])
    if not servico["disponivel"]:
        return jsonify({"status": "erro", "mensagem": "Serviço indisponível no momento"}), 400
    
    global next_id_agendamento
    novo_agendamento = {
        "id": next_id_agendamento,
        "cliente_id": dados["cliente_id"],
        "profissional_id": dados["profissional_id"],
        "servico_id": dados["servico_id"],
        "data_hora": dados["data_hora"],
        "status": "agendado"
    }
    DATABASE["agendamentos"].append(novo_agendamento)
    next_id_agendamento += 1
    
    return jsonify({
        "status": "sucesso",
        "mensagem": "Horário agendado com sucesso!",
        "detalhes": novo_agendamento
    }), 201

# ==========================================
# (OPCIONAL) ROTAS PARA LISTAR SERVIÇOS E PROFISSIONAIS (útil para o front)
# ==========================================

@app.route('/servicos', methods=['GET'])
def listar_servicos():
    """Lista todos os serviços disponíveis (público)"""
    return jsonify({
        "status": "sucesso",
        "servicos": [s for s in DATABASE["servicos"] if s["disponivel"]]
    })

@app.route('/profissionais', methods=['GET'])
def listar_profissionais():
    """Lista todos os profissionais (público)"""
    return jsonify({
        "status": "sucesso",
        "profissionais": [{"id": u["id"], "nome": u["nome"], "jornada": u.get("jornada", "N/A")}
                          for u in DATABASE["usuarios"] if u["tipo"] == "profissional"]
    })

# ==========================================
# INICIAR O SERVIDOR
# ==========================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)
