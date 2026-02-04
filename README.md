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
* **Qualidade:** Pytest (Unit & Integration), Ruff, Pre-commit. TBD Cypress.

### 🧠 Decisões Arquiteturais Chave

#### 1. Tratamento de Concorrência (Race Conditions)
Para evitar o problema clássico de dois usuários tentarem alugar o último livro ao mesmo tempo, implementei o **Pessimistic Locking** (`SELECT ... FOR UPDATE`) direto no banco de dados.
* **Por que fiz isso:** Soluções apenas via código (no Python) poderiam falhar se a API escalasse para múltiplas réplicas. O bloqueio no banco garante a integridade do estoque em qualquer cenário.

#### 2. Estratégia de Cache e Invalidação
Adotei o padrão **Cache-Aside** para a listagem de livros, focando em performance de leitura.
* **A Chave:** Criei uma chave composta (`books:list:{skip}:{limit}:{title}:{author}`) que suporta tanto a paginação quanto os filtros de busca.
* **A Invalidação:** Para manter os dados frescos sem travar o Redis, utilizei o `scan_iter`. Sempre que crio um livro ou o estoque muda (alguém aluga/devolve), limpo as chaves relacionadas de forma eficiente, garantindo que o usuário sempre veja a disponibilidade real.

#### 3. Precisão Financeira (Multas)
Rejeitei o uso de `Float` para os valores monetários devido aos conhecidos problemas de arredondamento (IEEE 754).
* **A Solução:** Adotei `Decimal` no Python e `NUMERIC(10, 2)` no PostgreSQL. Isso garante que o cálculo da multa (R$ 2,00/dia) seja contabilmente exato, sem perder centavos no caminho.

#### 4. Status de Atraso (Overdue): Lazy Evaluation
Precisei decidir como identificar empréstimos atrasados para o requisito **RF11**.
* **O Dilema:** Criar um "Job/Cron" que roda à meia-noite para atualizar o banco ou calcular na hora?
* **Minha Decisão:** Optei por **Lazy Evaluation** (Cálculo em Tempo de Leitura).
* **O Motivo:** Se eu usasse um Job, um livro vencido às 14:00 só apareceria como "Atrasado" no dia seguinte. Calculando na hora da leitura (`status == 'ACTIVE'` E `data_prevista < agora`), o sistema reflete a realidade em tempo real e eu evito a complexidade extra de gerenciar filas ou Lambdas.

---

## 🚦 Status de Implementação & Roadmap

### 1. Funcionalidades Core (MVP)
- [x] **[RN01] Prazo:** 14 dias fixos.
- [x] **[RN02] Multa:** R$ 2,00/dia (Persistido como Decimal).
- [x] **[RN03] Limite:** Max 3 empréstimos ativos por usuário.
- [x] **[RN04] Estoque:** Validação atômica de disponibilidade.
- [x] **[RN05] Bloqueio:** Impede novos empréstimos se houver atrasos.
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
- [ ] **Autenticação Básica:** *Planejado (Próxima Sprint).*

#### Nível Avançado
- [x] **Observabilidade:** Health Check endpoint (`/health`) monitorando DB e Redis.
- [ ] **Frontend:** Aplicação React/Vite *Planejado*.
- [ ] **Notificações:** Email/Webhook para vencimentos *Backlog*.
- [ ] **Renovação:** Sistema de renovação de empréstimos *Backlog*.
- [ ] **Relatórios:** Exportação CSV/PDF *Backlog*.
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

### 📫 Collection do Postman
Para facilitar o consumo da API, uma collection completa está disponível no repositório.

1. Importe o arquivo `postman/collections/LibSys.postman_collection.json` no seu Postman.
2. A collection já possui a variável `base_url` configurada como `http://localhost:8000`.
3. Os endpoints estão organizados por domínio (Books, Users, Loans).