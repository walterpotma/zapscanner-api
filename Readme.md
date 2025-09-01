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

### 2. `services/render.py`
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

---

## 🚀 Tecnologias Utilizadas

- **Flask** – API REST.
- **OWASP ZAP** – motor de varredura.
- **Subprocess + Threads** – execução assíncrona.
- **Jinja2-like placeholders** – injeção de dados em templates HTML.
- **Google Chat Webhooks** – integração opcional de alertas.
- **Docker + Kubernetes (AKS)** – empacotamento e orquestração.


# 📘 Documentação – Frontend ZapScanner

O objetivo do **frontend** deste projeto é fornecer uma interface simples, interativa e agradável para executar scans com o OWASP ZAP e visualizar relatórios.  
Ele foi desenvolvido apenas com **HTML, CSS e JavaScript puro**.

---

## 📂 Estrutura do Frontend

```
frontend/
├── css/
│ └── style.css # Estilização do frontend (dark/light mode)
├── html/
│ ├── index.html # Página inicial – executa scans e mostra logs
│ └── dashboard.html # Página de dashboard – lista relatórios e filtros
├── img/ # Imagens e ícones
├── Dockerfile # Build da aplicação frontend
└── deployment-aks.yaml # Deploy no Kubernetes (AKS)

```
## ⚙️ Arquivos Principais

### 1. `index.html`
Página inicial usada para executar um novo scan e acompanhar logs em tempo real.

**Endpoints utilizados:**
- `POST /api/scan` → inicia um novo scan para a URL informada.
- `GET /api/scan/status/<url>` → consulta o progresso e logs do scan em andamento.

**Principais funções e classes:**

- **themeToggle**  
  - Alterna entre **modo claro e escuro**.  
  - Salva a preferência no `localStorage`.

- **SmartTerminal (classe)**  
  - Gera um "terminal interativo" que exibe logs linha a linha.  
  - Faz *auto-scroll* quando o usuário está no final da saída.  
  - Se o usuário rolar manualmente, o auto-scroll é pausado.

- **scanBtn (listener assíncrono no botão "Iniciar Scan")**  
  - Valida a URL digitada.  
  - Faz `POST /api/scan`.  
  - Recebe o `monitor_url` da API.  
  - Chama `startPolling()` para verificar status e exibir logs em tempo real.  
  - Atualiza a UI com estado de execução (spinner, status "Executando...").

- **startPolling(monitor_url)**  
  - Faz requisições periódicas ao endpoint de status.  
  - Atualiza os logs no terminal em tempo real.  
  - Quando o scan termina, exibe o resultado (`completed` ou `failed`) e adiciona link para o dashboard.

- **resetUI(statusMessage)**  
  - Restaura a interface para o estado inicial (botão reativado, status atualizado).

- **clearOutput (listener no botão "Limpar")**  
  - Chama `smartTerminal.clear()` para limpar logs.  
  - Restaura mensagem inicial no terminal.  
  - Reseta a UI para "Pronto para executar".

---

### 2. `dashboard.html`
Página de **dashboard** que lista relatórios já gerados e permite filtrar, visualizar, baixar ou excluir.

**Endpoints utilizados:**
- `GET /api/reports` → lista relatórios disponíveis (dados de `reports_index.json`).
- `GET /api/reports/download/<filename>` → baixa relatório HTML.  
- `DELETE /api/reports/delete/<filename>/<url>` → exclui relatório e remove do índice.

**Principais funções:**

- **themeToggle**  
  - Mesmo comportamento da página inicial: alterna dark/light mode e salva no `localStorage`.

- **formatDate(dateString)**  
  - Converte datas do backend em formato legível (`dd/MMM/yyyy HH:mm`).

- **timeAgo(dateString)**  
  - Calcula há quanto tempo o relatório foi gerado (ex: "5 minutes ago").

- **loadReports()**  
  - Monta dinamicamente os cards de relatórios no DOM.  
  - Cada card exibe:
    - Nome do domínio.  
    - Data do scan.  
    - Contadores por nível de risco.  
    - Botões de ações (ver, baixar, excluir).

- **viewReport(htmlFilename)**  
  - Abre relatório em nova aba para visualização.

- **downloadReport(htmlFilename)**  
  - Faz download do relatório HTML via API.

- **updateStats()**  
  - Atualiza os totais de riscos (High, Medium, Low, Informational).  
  - Mostra data/hora do último relatório.  
  - Atualiza os cards de estatísticas no topo do dashboard.

- **deleteReport(url, caminho_html)**  
  - Exibe confirmação antes de excluir.  
  - Chama `DELETE /api/reports/delete/...`.  
  - Atualiza a lista de relatórios.  
  - ⚠️ *Observação:* a função contém um trecho redundante de event listener extra para `#btn-delete`, que pode ser simplificado no futuro.

- **showStatus(message)**  
  - Mostra mensagem de status (alerta).  
  - Recarrega a página após exclusão.

- **searchInput (event listener)**  
  - Permite buscar relatórios por **nome, domínio ou descrição**.  
  - Filtra dinamicamente os cards exibidos.

- **filterButtons (event listener)**  
  - Permite filtrar relatórios por nível de risco (`All`, `High`, `Medium`, `Low`).  
  - Exibe somente os cards que contêm o nível selecionado.

- **updateTimestamp()**  
  - Mostra no rodapé a hora da última atualização do dashboard.

---

## 🔎 Fluxo do Frontend

1. Usuário acessa `index.html`.  
   - Digita a URL.  
   - Inicia scan via botão.  
   - Acompanha logs em tempo real no terminal.  
   - Ao finalizar, recebe link para o dashboard.

2. Usuário acessa `dashboard.html`.  
   - Vê lista de relatórios já processados.  
   - Filtra por risco ou pesquisa por domínio.  
   - Pode visualizar, baixar ou excluir relatórios.

---

## 🚀 Tecnologias Utilizadas no Frontend

- **HTML5 / CSS3 / JavaScript** – Estrutura, estilo e interatividade.  
- **LocalStorage** – Persistência do tema (dark/light).  
- **Fetch API** – Comunicação com a API Flask.  
- **DOM Manipulation** – Inserção dinâmica de logs e relatórios.
