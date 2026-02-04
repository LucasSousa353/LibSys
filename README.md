# 📚 LibSys | Sistema de Gerenciamento de Biblioteca Digital

## 📖 Visão Geral Preliminar

O **LibSys** é uma solução completa para gestão de bibliotecas digitais, composta por uma API RESTful um Front-end. O sistema gerencia o ciclo de vida completo de livros, autores, usuários e empréstimos, aplicando regras de negócio financeiras (multas) e de estoque.

Este projeto foi desenvolvido como case técnico, focando em **Arquitetura de Software**, **Clean Code**, **DDD** e **Escalabilidade**.

---

## 🏗️ Arquitetura e Decisões Técnicas Preliminares

A arquitetura segue os princípios de **Clean Architecture** (Arquitetura Limpa), visando desacoplamento e testabilidade.

### Stack Tecnológica
* **Backend:** Python 3.12 + **FastAPI**.
* **Banco de Dados:** PostgreSQL
* **ORM:** SQLAlchemy + Alembic
* **Cache & Mensageria:** Redis
* **Frontend:** **React** (Vite + TypeScript) com **TailwindCSS**.
* **Infraestrutura:** Docker Compose
* **Qualidade:** **Pytest** (Testes), **Ruff** (Linter), **Pre-commit** e TBD **Cypress**.

---

## 🎯 Requisitos Preliminares do Sistema

### 1. Regras de Negócio (RN)
* **[RN01] Prazo de Empréstimo:** O prazo padrão para devolução é de **14 dias** corridos.
* **[RN02] Cálculo de Multa:** Deve ser cobrada uma multa de **R$ 2,00** por dia de atraso na devolução.
* **[RN03] Limite de Empréstimos:** Um usuário não pode ter mais de **3 empréstimos ativos** simultaneamente.
* **[RN04] Controle de Estoque:** Um livro só pode ser emprestado se `quantity_available > 0`.
* **[RN05] Bloqueio:** Usuários com multas pendentes ou livros atrasados não podem realizar novos empréstimos.

### 2. Requisitos Funcionais (RF)

#### Módulo A: Gestão de Usuários
* **[RF01]** Listar todos os usuários (com paginação).
* **[RF02]** Cadastrar novo usuário.
* **[RF03]** Buscar usuário por ID.
* **[RF04]** Listar histórico de empréstimos de um usuário específico.

#### Módulo B: Catálogo de Livros
* **[RF05]** Listar livros do acervo (com filtros por título/autor).
* **[RF06]** Cadastrar novo livro (vinculado a autor e quantidade inicial).
* **[RF07]** Consultar disponibilidade de um livro (Estoque).

#### Módulo C: Sistema de Empréstimos
* **[RF08]** Realizar empréstimo (Check-out).
* **[RF09]** Realizar devolução (Check-in) com cálculo automático de multa.
* **[RF10]** Listar empréstimos ativos.
* **[RF11]** Listar empréstimos atrasados (Overdue).

#### Módulo D: Avançados & Extras
* **[RF12]** Reservar livro (Fila de espera).
* **[RF13]** Renovar empréstimo (se não houver reservas).
* **[RF14]** Exportar relatório de empréstimos (CSV/PDF).
* **[RF15]** Notificar usuário sobre vencimento (Simulação de E-mail).

### 3. Requisitos Não-Funcionais (RNF)
* **[RNF01] Paginação:** Todas as listas devem ser paginadas.
* **[RNF02] Documentação:** Swagger/OpenAPI habilitado automaticamente.
* **[RNF03] Validação:** Uso rigoroso de Pydantic para integridade de dados.
* **[RNF04] Logs:** Logging estruturado para rastreabilidade de operações.
* **[RNF05] Cache:** Cache com Redis para endpoint de listagem de livros.
* **[RNF06] Rate Limiting:** Proteção contra abuso da API.
* **[RNF07] Testes:** Cobertura de testes unitários e de integração.
* **[RNF08] Autenticação:** Middleware básico ou JWT.
* **[RNF09] Observabilidade:** Endpoint de métricas e Health Check.

---

## 🚀 Instalação e Execução

*(Esta seção será preenchida ao final do projeto com os comandos reais)*
