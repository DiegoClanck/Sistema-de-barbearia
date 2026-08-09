# Sistema de Barbearia

API para gestão de barbearias com clientes, profissionais, serviços, jornadas e agendamentos.

## Recursos atuais

- Autenticação JWT com senhas armazenadas por hash.
- Perfis de administrador, profissional e cliente.
- Cadastro e edição de serviços.
- Cadastro de barbeiros e configuração da jornada semanal.
- Agendamentos persistidos em SQLite.
- Validação de horário futuro, jornada e sobreposição de atendimentos.
- Agenda restrita ao dono, ao profissional responsável ou ao administrador.
- Fluxo de confirmação, conclusão e cancelamento.
- Dashboard administrativo com atendimentos e faturamento realizado.

## Como executar

Requer Python 3.10 ou superior.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

A API estará disponível em `http://localhost:5000`. O banco é criado automaticamente em `instance/barbearia.db`.

Em produção, defina uma chave segura:

```powershell
$env:JWT_SECRET_KEY = "uma-chave-longa-e-secreta"
python app.py
```

## Usuários de demonstração

| Perfil | Usuário | Senha |
| --- | --- | --- |
| Administrador | `admin` | `admin123` |
| Profissional | `carlos` | `123456` |
| Cliente | `joao` | `123456` |

Troque essas credenciais antes de publicar o sistema.

## Rotas principais

| Método | Rota | Acesso |
| --- | --- | --- |
| POST | `/api/auth/login` | Público |
| POST | `/api/clientes` | Público |
| GET | `/api/servicos` | Público |
| POST/PATCH | `/api/servicos` | Admin |
| GET | `/api/profissionais` | Público |
| POST | `/api/profissionais` | Admin |
| PUT | `/api/profissionais/:id/jornada` | Admin |
| POST | `/api/agendamentos` | Cliente/Admin |
| GET | `/api/agendamentos` | Autenticado |
| PATCH | `/api/agendamentos/:id/status` | Autenticado |
| GET | `/api/admin/dashboard` | Admin |

Nas rotas protegidas envie `Authorization: Bearer SEU_TOKEN`.

Exemplo de agendamento:

```json
{
  "profissional_id": 2,
  "servico_id": 1,
  "data_hora": "2026-08-10 14:00"
}
```

## Testes

```powershell
pytest -q
```
