from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)

# ==========================================
# SIMULAÇÃO DE BANCO DE DADOS (MOCK DATA)
# ==========================================
DATABASE = {
    "usuarios": [
        {"id": 1, "nome": "Admin Geral", "tipo": "admin", "usuario": "admin"},
        {"id": 2, "nome": "Dr. Carlos (Dentista)", "tipo": "profissional", "usuario": "carlos", "jornada": "08:00-17:00"},
        {"id": 3, "nome": "Dra. Ana (Estética)", "tipo": "profissional", "usuario": "ana", "jornada": "09:00-18:00"},
        {"id": 4, "nome": "João Silva", "tipo": "cliente", "usuario": "joao", "assinante": True},
        {"id": 5, "nome": "Maria Souza", "tipo": "cliente", "usuario": "maria", "assinante": False}
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

# ==========================================
# HELPERS (FUNÇÕES DE SUPORTE)
# ==========================================
def calcular_metricas_globais():
    agendamentos = DATABASE["agendamentos"]
    servicos = {s["id"]: s for s in DATABASE["servicos"]}
    
    faturamento = sum(servicos[a["servico_id"]]["preco"] for a in agendamentos if a["status"] in ["agendado", "concluido"])
    
    # Taxa de Ocupação Simplificada: (Horas Agendadas / Horas Disponíveis Estimadas)
    tempo_total_agendado = sum(servicos[a["servico_id"]]["duracao_minutos"] for a in agendamentos)
    tempo_limite_sistema = 2 * 8 * 60 # 2 profissionais trabalhando 8 horas
    taxa_ocupacao = (tempo_total_agendado / tempo_limite_sistema) * 100
    
    return faturamento, min(taxa_ocupacao, 100)

# ==========================================
# 1. ÁREA DO ADMINISTRADOR
# ==========================================

@app.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    """Painel geral do administrador"""
    clientes = [u for u in DATABASE["usuarios"] if u["tipo"] == "cliente"]
    assinantes = [c for c in clientes if c["assinante"]]
    faturamento, taxa_ocupacao = calcular_metricas_globais()
    
    return jsonify({
        "total_clientes_cadastrados": len(clientes),
        "total_assinantes": len(assinantes),
        "faturamento_total_R$": faturamento,
        "taxa_de_ocupacao_global_%": round(taxa_ocupacao, 2),
        "profissionais": [u for u in DATABASE["usuarios"] if u["tipo"] == "profissional"]
    })

@app.route('/admin/servicos', methods=['POST'])
def admin_adicionar_servico():
    """Adiciona ou edita serviços, durações e disponibilidades"""
    dados = request.json
    novo_servico = {
        "id": len(DATABASE["servicos"]) + 1,
        "nome": dados["nome"],
        "duracao_minutos": dados["duracao_minutos"],
        "preco": dados["preco"],
        "disponivel": dados.get("disponivel", True)
    }
    DATABASE["servicos"].append(novo_servico)
    return jsonify({"mensagem": "Serviço gerenciado com sucesso!", "servico": novo_servico}), 210

@app.route('/admin/profissional/<int:prof_id>/horario', methods=['PUT'])
def admin_alterar_horario_profissional(prof_id):
    """Regra estrita: Apenas o Admin altera o horário de funcionamento do profissional"""
    dados = request.json
    for usuario in DATABASE["usuarios"]:
        if usuario["id"] == prof_id and usuario["tipo"] == "profissional":
            usuario["jornada"] = dados["nova_jornada"]
            return jsonify({"mensagem": f"Jornada de {usuario['nome']} alterada para {dados['nova_jornada']}"})
    return jsonify({"erro": "Profissional não encontrado"}), 404


# ==========================================
# 2. ÁREA DO PROFISSIONAL (Visão Limitada)
# ==========================================

@app.route('/profissional/<int:prof_id>/agenda', methods=['GET'])
def profissional_agenda(prof_id):
    """Visualização limitada dos agendamentos, produtividade e ocupação do profissional"""
    # Verifica se o usuário é realmente um profissional
    prof = next((u for u in DATABASE["usuarios"] if u["id"] == prof_id and u["tipo"] == "profissional"), None)
    if not prof:
        return jsonify({"erro": "Acesso negado ou profissional não encontrado"}), 403
        
    # Filtra os agendamentos deste profissional específico
    meus_agendamentos = []
    tempo_trabalhado = 0
    servicos_dict = {s["id"]: s for s in DATABASE["servicos"]}
    clientes_dict = {u["id"]: u["nome"] for u in DATABASE["usuarios"] if u["tipo"] == "cliente"}
    
    for a in DATABASE["agendamentos"]:
        if a["profissional_id"] == prof_id:
            nome_cliente = clientes_dict.get(a["cliente_id"], "Cliente Desconhecido")
            nome_servico = servicos_dict[a["servico_id"]]["nome"]
            duracao = servicos_dict[a["servico_id"]]["duracao_minutos"]
            
            meus_agendamentos.append({
                "data_hora": a["data_hora"],
                "cliente": nome_cliente,
                "servico": nome_servico,
                "status": a["status"]
            })
            if a["status"] == "concluido":
                tempo_trabalhado += duracao

    # Cálculo de Produtividade (Exemplo: minutos atendidos vs jornada de 8h (480 min))
    taxa_produtividade = (tempo_trabalhado / 480) * 100
    
    return jsonify({
        "profissional": prof["nome"],
        "jornada_de_trabalho": prof["jornada"],
        "taxa_produtividade_diaria_%": round(min(taxa_produtividade, 100), 2),
        "seus_agendamentos": meus_agendamentos
    })


# ==========================================
# 3. ÁREA DO CLIENTE (Cadastro e Agendamento)
# ==========================================

@app.route('/cliente/cadastro', methods=['POST'])
def cliente_cadastro():
    """Permite o auto-cadastro do cliente"""
    dados = request.json
    novo_cliente = {
        "id": len(DATABASE["usuarios"]) + 1,
        "nome": dados["nome"],
        "tipo": "cliente",
        "usuario": dados["usuario"],
        "assinante": dados.get("assinante", False)
    }
    DATABASE["usuarios"].append(novo_cliente)
    return jsonify({"mensagem": "Cadastro realizado com sucesso!", "cliente": novo_cliente}), 201

@app.route('/cliente/agendar', methods=['POST'])
def cliente_agendar():
    """Permite ao cliente escolher o serviço, o profissional e o horário"""
    dados = request.json
    
    # Simula a criação do agendamento na agenda
    novo_agendamento = {
        "id": len(DATABASE["agendamentos"]) + 1,
        "cliente_id": dados["cliente_id"],
        "profissional_id": dados["profissional_id"],
        "servico_id": dados["servico_id"],
        "data_hora": dados["data_hora"], # Ex: "2026-07-06 14:00"
        "status": "agendado"
    }
    DATABASE["agendamentos"].append(novo_agendamento)
    return jsonify({"mensagem": "Horário agendado com sucesso!", "detalhes": novo_agendamento}), 201


if __name__ == '__main__':
    # Roda o servidor local de testes
    app.run(debug=True, port=5000)