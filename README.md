# 📚 LibSys | Sistema de Gerenciamento de Biblioteca Digital

## 📖 Visão Geral

O **LibSys** é uma solução completa para gestão de bibliotecas digitais, composta por uma API RESTful e um front-end. O sistema gerencia o ciclo de vida completo de livros, autores, usuários e empréstimos, aplicando regras de negócio financeiras (multas) e de estoque.

Este projeto foi desenvolvido como case técnico, focando em **Arquitetura de Software**, **Clean Code**, **DDD** e **Escalabilidade**.

---

## 🏗️ Arquitetura e Decisões Técnicas Preliminares

A arquitetura segue os princípios de **Clean Architecture** (Arquitetura Limpa), visando desacoplamento e testabilidade.

### 🛠 Tech Stack
* **Backend:** Python 3.12 + **FastAPI** (Async).
* **Banco de Dados:** PostgreSQL (Driver `asyncpg`).
* **ORM:** SQLAlchemy 2.0 + Alembic (Migrations).
* **Cache:** Redis (Cluster-ready).
* **Frontend TBD:** **React** (Vite + TypeScript) com **TailwindCSS**.
* **Observabilidade:** Structlog (JSON Logs) + Health Checks.
* **Infraestrutura:** Docker.
* **Qualidade:** Pytest (Unit & Integration), Ruff. TBD Cypress.

---

## 🚦 Status de Implementação & Roadmap

### 1. Funcionalidades Core (MVP)
- [x] **Prazo:** 14 dias fixos.
- [x] **Multa:** R$ 2,00/dia (Persistido como Decimal).
- [x] **Limite:** Max 3 empréstimos ativos por usuário.
- [x] **Estoque:** Validação atômica de disponibilidade.
- [x] **Bloqueio:** Impede novos empréstimos se houver atrasos.
- [x] **CRUDs:** Gestão completa de Usuários, Livros e Empréstimos.

### 2. Diferenciais Implementados (Extra Features)

#### Nível Básico
- [x] **Paginação:** Implementada globalmente (`skip`/`limit`).
- [x] **Swagger/OpenAPI:** Documentação automática ativa.
- [x] **Validação Robusta:** Pydantic V2 em modo estrito.
- [x] **Logging Estruturado:** JSON Logs com rastreamento de latência e Request ID.

#### Nível Intermediário
- [x] **Cache (Redis):** Implementado na listagem de livros com invalidação inteligente.
- [x] **Rate Limiting:** Proteção contra abuso implementada (5 req/min em empréstimos).
- [x] **Testes Automatizados:** Suíte de testes unitários e de integração (Pytest + Docker).
- [X] **Autenticação Básica:** Implementado

#### Nível Avançado
- [x] **Observabilidade:** Health Check endpoint (`/health`) monitorando DB e Redis.
- [ ] **Frontend:** Aplicação React/Vite *Planejado*.
- [ ] **Notificações:** Email/Webhook para vencimentos *Backlog*.
- [ ] **Renovação:** Sistema de renovação de empréstimos *Backlog*.
- [ ] **Relatórios:** Exportação CSV/PDF *Backlog*.

#### Plus

- [ ] **Painel administrador**: Reset de senhas, criação, gestão de acessos, livros, prazos e multas.
- [ ] **Reservas:** Fila de espera para livros sem estoque *Backlog*.

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos
* Docker e Docker Compose instalados.

### Passos
1. **Subir a infraestrutura:**
   ```bash
   docker compose up --build

2. **Validar subida da infra:**
   ```bash
   http://127.0.0.1:8000/

3. **Consultar health do container:**
   ```bash
   http://127.0.0.1:8000/health

4. **Consultar documentação:**
   ```bash
   http://127.0.0.1:8000/docs
   ```

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


### 📫 Collection do Postman
Para facilitar o consumo da API, uma collection completa está disponível no repositório.

1. Importe o arquivo `postman/collections/LibSys.postman_collection.json` no seu Postman.
2. A collection já possui a variável `base_url` configurada como `http://localhost:8000`.
3. Os endpoints estão organizados por domínio (Books, Users, Loans).