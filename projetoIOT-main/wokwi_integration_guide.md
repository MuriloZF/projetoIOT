## Guia de Integração Wokwi com seu Projeto Flask via MQTT

Este guia descreve como conectar seus dispositivos simulados no Wokwi ao seu backend Flask utilizando um broker MQTT (como o EMQX, que você mencionou para o dashboard). Isso permitirá que seus sensores simulados no Wokwi enviem dados para sua aplicação e que sua aplicação envie comandos para atuadores simulados no Wokwi.

### Visão Geral da Arquitetura

1.  **Wokwi (Dispositivo Simulado, ex: ESP32):**
    *   Conecta-se à sua rede Wi-Fi (simulada no Wokwi).
    *   Conecta-se a um broker MQTT.
    *   Publica dados de sensores (ex: temperatura, umidade) em tópicos MQTT específicos.
    *   Subscreve-se a tópicos MQTT para receber comandos para atuadores (ex: ligar/desligar mangueira).

2.  **Broker MQTT (ex: EMQX Cloud, ou um local):**
    *   Recebe mensagens dos dispositivos Wokwi.
    *   Encaminha mensagens para os subscritores (sua aplicação Flask e, potencialmente, o dashboard EMQX).

3.  **Aplicação Flask (Seu Backend):**
    *   Conecta-se ao mesmo broker MQTT.
    *   Subscreve-se aos tópicos de dados dos sensores para receber atualizações do Wokwi.
    *   Publica comandos para os atuadores em tópicos MQTT específicos quando uma ação é disparada pela interface web.
    *   Armazena o histórico de dados dos sensores e comandos dos atuadores.

### 1. Configurando o Wokwi e o Código do Microcontrolador (Exemplo para ESP32 com Arduino)

Você precisará adicionar uma biblioteca MQTT ao seu projeto no Wokwi (ex: PubSubClient).

**Exemplo de código `main.ino` para um ESP32 no Wokwi:**

```cpp
#include <WiFi.h>
#include <PubSubClient.h>

// Configurações de Wi-Fi
const char* ssid = "Wokwi-GUEST"; // Ou a rede que você configurar no Wokwi
const char* password = ""; // Senha da rede Wi-Fi (vazio para Wokwi-GUEST)

// Configurações do Broker MQTT
const char* mqtt_server = "endereço_do_seu_broker_mqtt"; // Ex: broker.emqx.io ou IP local
const int mqtt_port = 1883;
const char* mqtt_user = "seu_usuario_mqtt"; // Se houver autenticação
const char* mqtt_password = "sua_senha_mqtt"; // Se houver autenticação
const char* client_id = "esp32-wokwi-client";

// Tópicos MQTT (ajuste conforme sua necessidade)
const char* temp_topic_pub = "iot/sensor/temperatura";
const char* umidade_topic_pub = "iot/sensor/umidade";
const char* mangueira_topic_sub = "iot/actuator/mangueira/command";
const char* ventilador_topic_sub = "iot/actuator/ventilador/command";

WiFiClient espClient;
PubSubClient client(espClient);

long lastMsg = 0;
float temperature = 0.0;
float humidity = 0.0;

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi conectado");
  Serial.println("Endereço IP: ");
  Serial.println(WiFi.localIP());
}

// Função chamada quando uma mensagem chega para um tópico que o ESP32 subscreveu
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Mensagem recebida no tópico: ");
  Serial.println(topic);
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.print("Mensagem: ");
  Serial.println(message);

  if (String(topic) == mangueira_topic_sub) {
    if (message == "Ligar") {
      Serial.println("Ligando a Mangueira de Água");
      // Adicione aqui o código para ligar o atuador da mangueira
    } else if (message == "Desligar") {
      Serial.println("Desligando a Mangueira de Água");
      // Adicione aqui o código para desligar o atuador da mangueira
    }
  } else if (String(topic) == ventilador_topic_sub) {
    if (message == "Ligar") {
      Serial.println("Ligando o Ventilador");
      // Adicione aqui o código para ligar o atuador do ventilador
    } else if (message == "Desligar") {
      Serial.println("Desligando o Ventilador");
      // Adicione aqui o código para desligar o atuador do ventilador
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Tentando conexão MQTT...");
    if (client.connect(client_id, mqtt_user, mqtt_password)) { // Use autenticação se configurada
    //if (client.connect(client_id)) { // Sem autenticação
      Serial.println("conectado");
      // Subscreve aos tópicos dos atuadores
      client.subscribe(mangueira_topic_sub);
      client.subscribe(ventilador_topic_sub);
      Serial.println("Subscrito aos tópicos dos atuadores.");
    } else {
      Serial.print("falhou, rc=");
      Serial.print(client.state());
      Serial.println(" tentando novamente em 5 segundos");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  // Aqui você pode inicializar seus sensores e atuadores físicos/simulados
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop(); // Mantém a conexão MQTT e processa mensagens recebidas

  long now = millis();
  if (now - lastMsg > 5000) { // Publica a cada 5 segundos
    lastMsg = now;

    // Simula leitura de sensores
    temperature = random(20, 30) + (random(0, 100) / 100.0); // Exemplo: 20.00 - 30.99
    humidity = random(40, 60) + (random(0, 100) / 100.0);    // Exemplo: 40.00 - 60.99

    char tempString[8];
    dtostrf(temperature, 1, 2, tempString);
    Serial.print("Publicando temperatura: ");
    Serial.println(tempString);
    client.publish(temp_topic_pub, tempString);

    char humString[8];
    dtostrf(humidity, 1, 2, humString);
    Serial.print("Publicando umidade: ");
    Serial.println(humString);
    client.publish(umidade_topic_pub, humString);
  }
}

```

**No Wokwi (`diagram.json`):**

Certifique-se de que seu `diagram.json` no Wokwi inclua a conexão Wi-Fi. Se você estiver usando um ESP32 Dev Kit, ele já terá Wi-Fi. Você pode precisar adicionar:

```json
// Dentro do seu diagram.json
{ 
  "version": 1,
  "author": "Wokwi Course",
  "editor": "wokwi",
  "parts": [
    // ... seus outros componentes ...
    { "type": "wokwi-esp32-devkit-v1", "id": "esp", "top": 0, "left": 0, "attrs": {} }
    // Para conectar à internet no Wokwi, não é necessário um componente Wi-Fi explícito no diagrama
    // A conexão é configurada no sketch (.ino) e o Wokwi simula o acesso à rede.
  ],
  "connections": [
    // ... suas conexões ...
  ]
  // Adicione a seguinte configuração para habilitar a internet no Wokwi:
  // "wokwi": {
  //   "internet": true
  // }
  // Nota: A forma de habilitar internet pode variar. Consulte a documentação do Wokwi.
  // Geralmente, para ESP32, a conexão à "Wokwi-GUEST" é automática se o código tentar.
}
```
Para que o ESP32 no Wokwi acesse a internet (e seu broker MQTT), você geralmente não precisa de uma configuração especial no `diagram.json` além de usar `WiFi.begin("Wokwi-GUEST", "");`. O Wokwi simula essa conexão automaticamente.

### 2. Configurando o Broker MQTT

*   **EMQX Cloud:** Você pode criar uma instância gratuita no [EMQX Cloud](https://www.emqx.com/en/cloud). Anote o endereço do broker, porta, usuário e senha.
*   **Broker Local:** Você pode instalar o EMQX ou Mosquitto em sua máquina local ou em um servidor. Se for local, o `mqtt_server` no código do ESP32 será o IP da sua máquina na rede local.

### Próximos Passos (No seu Projeto Flask)

1.  **Instalar a biblioteca Paho-MQTT:**
    ```bash
    pip install paho-mqtt
    ```
2.  **Modificar `app.py` (ou um novo arquivo `mqtt_client.py`)** para incluir um cliente MQTT que:
    *   Conecte-se ao broker.
    *   Subscreva-se aos tópicos `iot/sensor/temperatura` e `iot/sensor/umidade`.
    *   Ao receber uma mensagem, atualize os valores dos sensores (que atualmente estão em dicionários globais em `sensor.py`) e salve no histórico.
3.  **Modificar `actuator.py`:**
    *   Quando uma rota de gerenciamento de atuador for chamada (ex: para ligar/desligar), publique uma mensagem no tópico MQTT correspondente (`iot/actuator/mangueira/command` ou `iot/actuator/ventilador/command`) com o comando ("Ligar" ou "Desligar").

Este guia fornece a base para a comunicação entre Wokwi e sua aplicação. As próximas etapas envolverão a codificação da lógica MQTT no seu backend Flask.

