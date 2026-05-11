# ArteHub

ArteHub é uma aplicação web desenvolvida para gerenciar uma biblioteca digital de matrizes de bordado e encomendas. Construída com Flask e MongoDB, ela oferece uma interface limpa e interativa para enviar, categorizar e navegar por arquivos `.pes` e gerenciar encomendas. A aplicação extrai automaticamente metadados importantes e gera pré-visualizações das matrizes, tornando-se uma ferramenta eficiente para entusiastas e profissionais do bordado.

---

# ✨ Principais Funcionalidades

- **Upload de arquivos PES:** envie novas matrizes `.pes` através de um formulário simples.
- **Extração automática de metadados:** leitura automática de propriedades como quantidade de pontos, dimensões e paleta de cores original usando a biblioteca `pyembroidery`.
- **Geração de preview PNG:** cria automaticamente uma imagem `.png` para cada matriz enviada.
- **Biblioteca dinâmica:** visualize todas as matrizes em uma interface pesquisável e filtrável.
- **Categorias e pesquisa:** organize sua biblioteca com categorias e temas personalizados. Pesquise em tempo real por nome, categoria ou tema.
- **Painel de detalhes interativo:** selecione uma matriz para visualizar informações técnicas completas e uma lista de cores editável.
- **Edição de cores em tempo real:** altere as cores da paleta e visualize a atualização imediatamente. Também é possível salvar o novo conjunto de cores, regenerando o preview PNG.
- **Gerenciamento de matrizes:** exclua matrizes indesejadas, removendo também os arquivos associados do servidor.
- **Interface moderna:** visual limpo com suporte a tema escuro.

---

# 🛠️ Tecnologias Utilizadas

- **Backend:** Python, Flask
- **Banco de Dados:** MongoDB
- **Processamento de Arquivos:** `pyembroidery`
- **Frontend:** JavaScript Vanilla, HTML5, CSS3
- **Dependências:** `pymongo`, `Flask`, `python-dotenv`
- **Gerenciamento de Pacotes:** `pipenv`

---

# 🚀 Começando

Siga os passos abaixo para executar o projeto localmente.

## Pré-requisitos

- Python 3.11
- `pipenv` instalado:

```bash
pip install pipenv
```

- Acesso a uma instância MongoDB (por exemplo, MongoDB Atlas)

---

# 📦 Instalação

## 1. Clone o repositório

```bash
git clone https://github.com/isbllvt/arteHub.git
cd arteHub
```

---

## 2. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto e adicione suas credenciais do MongoDB:

```env
MONGO_URI="sua_string_de_conexao"
MONGO_DB="nome_do_banco"
MONGO_COLLECTION="nome_da_colecao"
```

---

## 3. Instale as dependências

Use o `pipenv` para criar o ambiente virtual e instalar os pacotes necessários:

```bash
pipenv install
```

---

## 4. Execute a aplicação

Inicie o servidor Flask:

```bash
pipenv run python app.py
```

A aplicação estará disponível em:

```text
http://127.0.0.1:5000
```

---

# Como Usar

- Acesse `http://127.0.0.1:5000/nova` para enviar uma nova matriz.
- Preencha o formulário com:
  - nome da matriz
  - categoria
  - tema
  - arquivo `.pes`
- Após o envio, você será redirecionado para a biblioteca principal (`/`).
- Utilize a barra de pesquisa e os filtros laterais para navegar pelas matrizes.
- Clique em qualquer card para visualizar seus detalhes no painel lateral.
- No painel de detalhes, você pode:
  - alterar cores
  - visualizar novas combinações
  - salvar alterações
  - excluir a matriz

---

# 📌 Melhorias Futuras

- Sistema de autenticação
- Favoritos
- Histórico de pedidos
- Dashboard administrativo

---
