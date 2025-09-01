# 📘 Documentação – API ZapScanner

## 🔎 Visão Geral

A ZapScanner API é um serviço baseado em Flask que integra o OWASP ZAP para executar varreduras de segurança em aplicações web.  
Ela roda scans, gera relatórios HTML a partir dos resultados, organiza os relatórios em um índice JSON e disponibiliza endpoints REST para consulta, download e exclusão.

O sistema foi projetado para rodar em containers (Docker/Kubernetes) e suporta execução assíncrona dos scans para não bloquear a API.

---

## 📂 Estrutura do Projeto

```
api/
├── scripts/
│   └── run-zap.sh                # Script Bash que executa o ZAP e gera relatórios JSON
├── services/
│   ├── notifier.py               # Serviço de notificações (Google Chat)
│   ├── render.py                 # Processa JSON do ZAP e gera relatórios HTML
│   └── scanner.py                # Classe para execução do scan via subprocess
├── src/
│   └── app.py                    # API Flask com endpoints de controle e relatórios
├── templates/
│   ├── model-reports-dark.html   # Template HTML dark mode
│   └── model-reports-light.html  # Template HTML light mode
├── deployment-aks.yaml           # Manifesto de deploy no AKS (Kubernetes)
├── Dockerfile                    # Configuração de build da imagem
└── requirements.txt              # Dependências Python
```

---

## ⚙️ Componentes Principais

### 1. `scripts/run-zap.sh`
- Script responsável por chamar o OWASP ZAP com os parâmetros configurados.
- Gera relatórios em formato JSON que depois são processados pelo serviço `render.py`.

### 2. `services/notifier.py`
- Serviço de integração com sistemas de alerta.
- Função: `send_google_chat_alert(webhook_url, message)`
- Envia mensagens para o Google Chat via Webhook.
- Corpo da mensagem enviado em JSON (`{"text": message}`).
- Logs registrados em caso de sucesso ou erro.
- **Uso opcional** para notificação automática após execução de scans.

### 3. `services/render.py`
- Processa relatórios JSON gerados pelo ZAP e transforma em relatórios HTML prontos para visualização.

**Funções internas:**
- `calcular_stats(alertas)`: separa alertas por nível de risco.
- `processar_referencias(reference_text)`: concerta links de referencias gerados pelo zap, pois são gerados como texto não como links.

**Função principal:**
- `render_html_report(json_file_path, html_template_path, output_html_path)`
  - Lê relatório JSON.
  - Calcula estatísticas (High, Medium, Low, Informational).
  - Gera cartões de resumo (stats).
  - Renderiza lista detalhada de alertas com CWE, WASC, soluções, referências e URLs afetadas.
  - Substitui placeholders no template HTML.
  - Salva relatório final em disco, se já existir substitui.
  - Atualiza índice de relatórios (`reports_index.json`).
  - Remove JSON do relatorio gerado pelo zap após sucesso.

**Função auxiliar:**
- `update_reports_index(json_file_path, html_file_path)`
  - Atualiza arquivo `reports_index.json` com metadados dos relatórios.
  - Se já existir relatório da mesma URL, substitui.

**Execução direta:**
- Permite rodar manualmente (`python render.py ...`).

### 4. `services/scanner.py`
- Wrapper em Python para execução do script Bash (`run-zap.sh`) que dispara o scan.

**Classe ZapScanner:**
- Construtor recebe caminho do script.
- `scan(url, output_dir, template_path, template_file)`
  - Cria pasta de relatórios, se necessário.
  - Executa script via `subprocess.Popen`.
  - Stream de logs linha a linha.
  - Retorna logs completos.
  - Lança exceção em caso de falha.

**Isolamento:**  
A lógica de scan fica encapsulada e reutilizável em diferentes contextos (API, CLI, testes).

### 5. `src/app.py`
- Arquivo principal da API Flask.

**Setup:**
- Configura diretórios (`reports_dir`, `template_dir`).
- Usa `active_scans` em memória para acompanhar progresso.
- `scan_lock` garante execução thread-safe.

**Execução assíncrona:**
- `run_scan_async(url)`: roda o ZapScanner em thread separada.
- Logs capturados e armazenados em `active_scans[url]["logs"]`.
- Atualiza status para `completed` ou `failed`.

**Endpoints:**
- `/` (GET): teste de vida da API.
- `/api/scan` (POST): inicia novo scan assíncrono. Retorna status inicial + monitor_url.
- `/api/scan/status/<url>` (GET): consulta progresso/status do scan em andamento.
- `/api/reports` (GET): lista relatórios disponíveis (`reports_index.json`).
- `/api/reports/html/<filename>` (GET): serve relatório HTML renderizado.
- `/api/reports/download/<filename>` (GET): permite baixar relatório.
- `/api/reports/delete/<filename>/<urlexecutado>` (DELETE): remove relatório e atualização correspondente no índice.

**Execução standalone:**
- `python app.py`: sobe servidor em `0.0.0.0:8080`.

---

## 🔐 Fluxo de Funcionamento

1. Cliente chama `POST /api/scan` com a URL alvo.
2. API inicia scan em background (`ZapScanner` + `run-zap.sh`).
3. Logs parciais ficam acessíveis via `GET /api/scan/status/<url>`.
4. Ao finalizar, é gerado um JSON → processado por `render.py` → salvo como HTML.
5. `reports_index.json` é atualizado.
6. Relatórios ficam disponíveis para listagem, visualização, download ou exclusão.
7. (Opcional) Envio de alertas para Google Chat (`notifier.py`).

---

## 🚀 Tecnologias Utilizadas

- **Flask** – API REST.
- **OWASP ZAP** – motor de varredura.
- **Subprocess + Threads** – execução assíncrona.
- **Jinja2-like placeholders** – injeção de dados em templates HTML.
- **Google Chat Webhooks** – integração opcional de alertas.
- **Docker + Kubernetes (AKS)** – empacotamento e orquestração.