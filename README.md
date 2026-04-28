# 📚 BiblioWeb

BiblioWeb é uma aplicação web desenvolvida em **Python**, utilizando **Flask** e **Jinja**, voltada para a gestão de bibliotecas.  
O sistema oferece funcionalidades de catálogo, gestão de usuários, relatórios e controle de empréstimos, com suporte a integração via **Brasil API**.

---

## 🚀 Funcionalidades Principais

### Catálogo de Acervo
- Cadastro manual de livros ou via integração com **Brasil API**.
- Edição dos dados do acervo após importação.
- Geração de etiquetas com código de barras.

### Gestão de Usuários
- Perfis: **Administrador**, **Bibliotecário** e **Usuário**.
- Controle de permissões e matrículas.

### Portal de Relatórios
- **Acervo Completo**: lista detalhada de livros (autor, ISBN, cópias).
- **Base de Usuários**: relatório de leitores e administradores cadastrados.
- **Movimentação (Empréstimos)**: histórico completo de empréstimos, devoluções, status e multas.

### Empréstimos & Devoluções
- Configurações do sistema:
  - 📚 Máximo de livros por usuário: **2**
  - 📅 Duração do empréstimo: **7 dias**
  - 🔄 Máximo de renovações: **2**
  - 💰 Multa por dia de atraso: **R$ 0,00**
- Devolução rápida via leitura de código de barras.

### Métricas
- 📖 Acervo: **3**
- 👥 Leitores: **1**
- 📤 Em Aberto: **2**
- ⚠️ Atrasados: **0**

---

## 🛠️ Tecnologias Utilizadas
- **Python 3**
- **Flask**
- **Jinja2**
- **Brasil API**
- **Docker** (deploy via **EasyPanel**)

---

## 📦 Instalação e Execução

1. Clone este repositório:
   ```bash
   git clone https://github.com/seuusuario/biblioweb.git
   cd biblioweb
