# Projeto IoT Dashboard - Versão Final Refatorada (v3)

Este projeto é uma aplicação Flask que fornece um dashboard para monitorar e controlar dispositivos IoT via MQTT. Esta versão foi extensivamente refatorada para usar `user.py` para autenticação, exibir dados em tempo real, gerenciar tópicos MQTT dinamicamente, e registrar e exibir um histórico de comandos enviados aos atuadores.

## Funcionalidades Principais

- **Autenticação de Usuário via `user.py`:** Utiliza as credenciais e lógica de `user.py` para login de administradores e usuários normais.
- **Dashboard em Tempo Real:** Exibe dados de sensores (temperatura, umidade) e status de atuadores (ventilador, mangueira de água) atualizados via MQTT e AJAX polling.
- **Controle de Atuadores:** Permite que administradores liguem/desliguem atuadores através da interface.
- **Gerenciamento Dinâmico de Dispositivos:**
    - Administradores podem registrar novos sensores e atuadores com seus respectivos tópicos MQTT.
    - Visualizar e gerenciar os dispositivos registrados.
    - Deletar dispositivos (não padrão) do sistema.
- **Histórico de Comandos:** Registra todos os comandos enviados aos atuadores (timestamp, usuário, atuador, comando, tópico, payload) e os exibe no dashboard.
- **Simulador Wokwi:** Inclui código MicroPython (`wokwi.py`) para simular um ESP32 publicando dados de sensores e recebendo comandos para atuadores, facilitando testes sem hardware físico.

## Estrutura do Projeto

```
projetoIOT-main/
├── app.py                      # Aplicação principal Flask, lógica MQTT, endpoints API, gerenciamento de dispositivos
├── user.py                     # Blueprint para autenticação e gerenciamento de usuários
├── wokwi.py                    # Código MicroPython para simulador ESP32 Wokwi
├── static/
│   ├── css/base.css
│   ├── img/logo.png
│   └── js/nav.js
├── templates/
│   ├── baseAdmin.html
│   ├── baseUser.html
│   ├── components/
│   │   └── dashboard_cards.html  # Cards do dashboard principal com JS para tempo real e histórico
│   ├── dashboard.html            # Página de dashboard detalhado com todos os dispositivos e histórico completo
│   ├── errors/                   # Templates para páginas de erro (401, 403, 404, 500)
│   ├── home.html                 # Página inicial/principal do dashboard
│   ├── login.html
│   ├── manage_actuator.html
│   ├── manage_sensor.html
│   ├── manage_user.html
│   ├── register_actuator.html
│   ├── register_sensor.html
│   └── register_user.html
├── docs/
│   └── todo.md                 # Checklist de desenvolvimento e correções (para referência interna)
├── .gitignore
├── README.md                   # Este arquivo
└── ... (outros arquivos de configuração ou cache)
```

## Pré-requisitos

- Python 3.x
- pip (gerenciador de pacotes Python)

## Configuração e Execução

1.  **Extraia os arquivos do projeto.**

2.  **Navegue até o diretório raiz do projeto (`projetoIOT-main`).**

3.  **Crie um ambiente virtual (recomendado):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```

4.  **Instale as dependências:**
    ```bash
    pip install Flask paho-mqtt
    ```

5.  **Execute o simulador Wokwi (opcional, mas recomendado para ver dados):**
    - Abra o arquivo `wokwi.py`.
    - Copie o conteúdo e cole em um projeto ESP32 MicroPython no Wokwi (https://wokwi.com/).
    - Certifique-se que o Wokwi ESP32 está conectado à internet.
    - Inicie a simulação no Wokwi. Ele começará a publicar dados para `broker.emqx.io` nos tópicos padrão e ouvirá comandos.

6.  **Execute a aplicação Flask:**
    ```bash
    python app.py
    ```
    A aplicação estará rodando em `http://0.0.0.0:5000` (ou `http://localhost:5000`).

7.  **Acesse o dashboard no seu navegador:**
    Abra `http://localhost:5000` (será redirecionado para `/user/login`).

    - **Credenciais de Login (Definidas em `user.py`):**
        - Administradores Padrão: `admin1` / `1234`, `admin2` / `1234`, `admin3` / `1234`
        - Usuários Padrão: `user1` / `1234`, `user2` / `1234`
        - Novos usuários podem ser registrados pela interface de gerenciamento de usuários (acessível por administradores).

## Principais Alterações Realizadas (Versão 3)

- **Autenticação via `user.py`:** A lógica de autenticação e gerenciamento de usuários foi movida para `user.py` e integrada em `app.py` usando um Blueprint. As credenciais agora são lidas de `users_dict` e `admins_dict` em `user.py`.
- **Histórico de Comandos:**
    - Todos os comandos enviados para atuadores são registrados (timestamp, usuário, nome do atuador, comando, tópico, payload).
    - O histórico de comandos recentes é exibido no dashboard principal (`home.html`).
    - Um histórico mais completo é visível na página de dashboard detalhado (`dashboard.html`).
- **Unificação e Refatoração:**
    - Lógica MQTT centralizada e robustecida em `app.py`.
    - Gerenciamento de sensores e atuadores (registro, listagem, exclusão) implementado com Blueprints dedicados (`sensor_main`, `actuator_main`).
    - Inscrição e cancelamento de inscrição MQTT dinâmicos ao adicionar/remover dispositivos.
- **Exibição de Dados em Tempo Real:**
    - `home.html` (via `components/dashboard_cards.html`) e `dashboard.html` usam JavaScript (AJAX polling) para buscar e exibir dados atualizados de sensores, status de atuadores e histórico de comandos a cada 3-5 segundos.
- **Templates Atualizados:**
    - `login.html` corrigido para usar `url_for` e nomes de campos corretos.
    - `dashboard_cards.html` e `dashboard.html` atualizados para exibir todos os dados dinâmicos, incluindo o histórico de comandos.
    - Melhorias gerais na interface e navegação.

## Como Usar

1.  **Login:** Use as credenciais definidas em `user.py` (ex: `admin1`/`1234` para admin).
2.  **Dashboard Principal (`/home`):**
    - Veja dados em tempo real dos sensores padrão (Temperatura, Umidade).
    - Veja status em tempo real dos atuadores padrão (Ventilador, Mangueira).
    - Se admin, controle os atuadores padrão.
    - Veja um resumo do histórico de comandos recentes.
    - Acesse o gerenciamento de usuários (se admin).
3.  **Dashboard Detalhado (`/dashboard`):**
    - Veja dados de *todos* os sensores registrados.
    - Veja status de *todos* os atuadores registrados e controle-os (se admin).
    - Veja o histórico de comandos completo.
4.  **Gerenciamento de Dispositivos (Admin):**
    - Navegue para "Gerenciar Sensores" ou "Gerenciar Atuadores" no menu.
    - Registre novos dispositivos, fornecendo nome, tópico MQTT (e tipo/tópico de status).
    - Delete dispositivos não padrão.
5.  **Gerenciamento de Usuários (Admin):**
    - Navegue para "Gerenciar Usuários".
    - Registre novos usuários (definindo se são admin ou não).
    - Delete usuários existentes.

## Broker MQTT

O projeto está configurado para usar o broker público `broker.emqx.io` na porta `1883`.
Se você desejar usar um broker MQTT diferente, altere as variáveis `MQTT_BROKER_HOST` e `MQTT_BROKER_PORT` no arquivo `app.py` e também no `wokwi.py` (ou no seu código de dispositivo físico).

