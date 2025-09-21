🤖 InstaPY Automator

Este projeto é um bot automatizador para Instagram desenvolvido em Python + Selenium, com foco em curtidas (like) e comentários (comment) de maneira segura e configurável.

🚀 Funcionalidades

Login automático com persistência de sessão (/sessions).

Aplicação de geolocalização simulada (padrão: São Gonçalo - RJ).

Alternância entre ações de like e comentário de forma randômica.

Busca de posts por tags/palavras-chave configuradas.

Digitação humanizada para login e comentários.

Comentários carregados a partir do arquivo comentarios.txt.

Logs detalhados em tempo real com marcação visual dos elementos clicados.

📂 Estrutura do Projeto

insta_py/
│── main.py
│── .env
│── comentarios.txt
│── sessions/ # Armazena a sessão persistente do Chrome
│── utils/
│ ├── action.py # Like & comentários
│ ├── auth.py # Login e persistência de sessão
│ ├── collector.py # Coleta de links por tags
│ ├── config.py # Configurações globais
│ ├── driver.py # Setup do Selenium/Chrome
│ ├── logger.py # Sistema de logging
│ └── orchestrator.py # Orquestra o fluxo do bot

⚙️ Configuração

Clone este repositório e entre no diretório:

git clone https://github.com/victorbraga8/insta_py.git

cd insta_py

Crie e ative um ambiente virtual:

python -m venv venv
source venv/bin/activate # Linux/Mac
venv\Scripts\activate # Windows

Instale as dependências:

pip install -r requirements.txt

Configure o arquivo .env (exemplo abaixo):

IG_PROFILE=seu_usuario
IG_PASS=sua_senha
HEADLESS=false
WINDOW_WIDTH=1366
WINDOW_HEIGHT=900
LANG=pt-BR
GEO_LAT=-22.8268
GEO_LON=-43.0634
GEO_ACC=120

Crie o arquivo comentarios.txt na raiz e adicione uma lista de comentários (um por linha).

▶️ Execução

Rodar o bot:

python main.py

Durante a execução você verá logs detalhados informando:

Qual post foi acessado

Se foi feito like

Se foi feito comentário

Tempo de espera entre ações

Marcações visuais em vermelho mostrando onde o clique ocorreu

🛠️ Customização

Tags monitoradas: configure em config.py no campo tags.

Distribuição de ações (like x comment): ajustável em config.py.

Sessões persistentes: ficam salvas na pasta /sessions.