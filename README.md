# 📚 LibSys | Sistema de Gerenciamento de Biblioteca Digital

## 📖 Visão Geral

O **LibSys** é uma solução completa para gestão de bibliotecas digitais, composta por uma API RESTful (FastAPI) e um front-end (React). O sistema gerencia o ciclo de vida completo de livros, usuários e empréstimos, aplicando regras de negócio financeiras (multas) e de estoque.

Este projeto foi desenvolvido como case técnico, focando em **Arquitetura de Software**, **Clean Code**, **DDD** e **Escalabilidade**.

---

## 🏗️ Arquitetura e Tech Stack

A arquitetura segue os princípios de **Clean Architecture**, visando desacoplamento e testabilidade.

### 🛠 Tech Stack
* **Backend:** Python 3.12 + **FastAPI** (Async).
* **Banco de Dados:** PostgreSQL 16 (Driver `asyncpg`).
* **ORM:** SQLAlchemy 2.0 + Alembic (Migrations).
* **Cache:** Redis 7 (Cache-Aside Pattern).
* **Autenticação:** JWT (PyJWT) + Argon2 (hashing de senhas).
* **Frontend:** **React 19** (Vite + TypeScript) com **TailwindCSS 4**.
* **Observabilidade:** Structlog (JSON Logs) + Health Checks.
* **Infraestrutura:** Docker + Docker Compose (5 containers).
* **Qualidade:** Pytest (Unit & Integration), Ruff.

---

## 🚦 Status de Implementação & Roadmap

### 1. Funcionalidades Core (MVP)
- [x] **Prazo:** 14 dias fixos (configurável via env).
- [x] **Multa:** R$ 2,00/dia (Decimal/NUMERIC — precisão financeira).
- [x] **Limite:** Max 3 empréstimos ativos por usuário.
- [x] **Estoque:** Validação atômica de disponibilidade (Pessimistic Locking).
- [x] **Bloqueio:** Impede novos empréstimos se houver atrasos.
- [x] **CRUDs:** Gestão completa de Usuários, Livros e Empréstimos.

### 2. Diferenciais Implementados (Extra Features)

#### Nível Básico
- [x] **Paginação:** Implementada globalmente (`skip`/`limit`).
- [x] **Swagger/OpenAPI:** Documentação automática ativa.
- [x] **Validação Robusta:** Pydantic V2 em modo estrito.
- [x] **Logging Estruturado:** JSON Logs com rastreamento de latência e Request ID.

#### Nível Intermediário
- [x] **Cache (Redis):** Cache-Aside na listagem de livros com invalidação via `scan_iter`.
- [x] **Rate Limiting:** Proteção contra abuso (configurável via env).
- [x] **Testes Automatizados:** Suíte de testes unitários e de integração (Pytest + Docker).
- [x] **Autenticação JWT:** Login, roles (admin/librarian/user), reset de senha obrigatório.

#### Nível Avançado
- [x] **Observabilidade:** Health Check endpoint (`/health`) monitorando DB e Redis.
- [x] **Frontend:** Aplicação React 19 com dashboard, dark mode e i18n (pt-BR/en-US).
- [x] **Notificações:** Email/Webhook para vencimentos (simulado via logs, persistido em BD).
- [x] **Renovação:** Sistema de renovação de empréstimos.
- [x] **Relatórios:** Exportação CSV (streaming) e PDF.

#### Plus
- [x] **Painel Administrativo:** Dashboard com métricas, gestão de usuários, reset de senhas, ativação/inativação de contas.
- [x] **Controle de Acesso (RBAC):** Roles com permissões diferenciadas por endpoint.
- [x] **Audit Log:** Registro de todas as ações críticas (criação, devolução, alterações).
- [ ] **Reservas:** Fila de espera para livros sem estoque *Backlog*.
- [ ] **Validações:** Validar formato ISBN com Regex *Backlog*.
- [ ] **Maior detalhe dos livros:** Quantidade de páginas, gênero e etc *Backlog*.
- [ ] **Gestão de variáveis:** Administrador gerenciar multa, prazos, juros etc.
- [ ] **Limite de renovação:** Limitar renovações por livro, por usuário.
- [ ] **Checkout de pagamento:** Simular um checkout de pagamento que o usuário "pagaria" o que fosse devido.



---

## 🚀 Como Rodar o Projeto

### Pré-requisitos
* Docker e Docker Compose instalados.

### Passos

1. **Ambiente**: Configurar .env baseado no .env.sample

2. **Subir a infraestrutura:**
   ```bash
   docker compose up --build
   ```

3. **Acessar os serviços:**
   * **API:** http://127.0.0.1:8000/
   * **Frontend:** http://127.0.0.1:3000/
   * **Docs (Swagger):** http://127.0.0.1:8000/docs
   * **Health Check:** http://127.0.0.1:8000/health

### 🧪 Executando os Testes
O projeto possui testes automatizados (unitários e de integração) rodando via Pytest. Para executá-los dentro do container:

```bash
# Rodar todos os testes
docker compose exec backend pytest

# Rodar com logs de saída (-s) e verboso (-v)
docker compose exec backend pytest -v -s
```

### 🌱 Criação de Tabelas e Seed de Dados
Para criar as tabelas (migrations Alembic) dentro do container:

```bash
docker compose exec backend alembic upgrade head
```

Para popular o banco com alguns dados iniciais:

```bash
docker compose exec backend python -m app.seed
```

ou com maior massa de dados:

```bash
docker compose exec backend python -m app.seed --reset --with-loans
```

### 📫 Collection do Postman
Para facilitar o consumo da API, uma collection completa está disponível no repositório.

1. Importe o arquivo `postman/collections/LibSys.postman_collection.json` no seu Postman.
2. A collection já possui a variável `base_url` configurada como `http://localhost:8000`.
3. Os endpoints estão organizados por domínio (Books, Users, Loans).


### 🔔 Notificações de Vencimento (Simulado)
O envio de notificações é simulado por logs e persistido na tabela `notifications`.

#### Disparo manual via API
```bash
curl -X POST http://localhost:8000/notifications/dispatch \
   -H "Authorization: Bearer <TOKEN>" \
   -H "Content-Type: application/json" \
   -d '{"channels":["email","webhook"],"limit":100}'
```
Obs: request acima existe no Postman.

#### Scheduler local (dev)
O worker roda em um container separado e executa o dispatch periodicamente:
```bash
docker compose up --build notifications_worker
```

#### Produção (sugestão)
Em produção, o ideal seria usar um job serverless (ex.: Lambda + EventBridge) que
execute o dispatch em intervalos fixos para uma fila, mantendo a API desacoplada.

