import json
import os
import sys
from datetime import datetime
import os
from pathlib import Path
import re


def calcular_stats(alertas):
    stats = {"high": 0, "medium": 0, "low": 0, "info": 0, "total": len(alertas)}
    for alerta in alertas:
        risk = str(alerta.get("riskcode", "0"))
        if risk == "3":
            stats["high"] += 1
        elif risk == "2":
            stats["medium"] += 1
        elif risk == "1":
            stats["low"] += 1
        else: 
            stats["info"] += 1
    return stats

def processar_referencias(reference_text):
    """
    Processa texto de referência contendo múltiplos URLs e converte em links HTML
    Exemplo: 
    Input: "<p>https://example1.com</p><p>https://example2.com</p>"
    Output: '<a href="https://example1.com" target="_blank">https://example1.com</a><br><a href="https://example2.com" target="_blank">https://example2.com</a>'
    """
    if not reference_text:
        return ""
    
    url_pattern = r'https?://[^\s<>"]+'
    
    urls = re.findall(url_pattern, reference_text)
    
    if not urls:
        return reference_text

    links_html = []
    for url in urls:
        clean_url = url.rstrip('</p>').rstrip('>').rstrip('"').rstrip("'")
        links_html.append(f'<a href="{clean_url}" target="_blank" rel="noopener noreferrer">{clean_url}</a>')
    
    return '<br>'.join(links_html)

def render_html_report(json_file_path, html_template_path, output_html_path):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            zap_report_data = json.load(f)

        with open(html_template_path, 'r', encoding='utf-8') as f:
            html_template_content = f.read()

        site_data = zap_report_data.get("site", [{}])[0]
        alertas = site_data.get("alerts", [])
        
        stats = calcular_stats(alertas)
        
        scan_date_from_report = zap_report_data.get('@generated')
        if scan_date_from_report:
            try:
                dt_obj = datetime.strptime(scan_date_from_report, '%a, %d %b %Y %H:%M:%S %z')
                scan_date_formatted = dt_obj.strftime('%d/%m/%Y %H:%M:%S')
            except ValueError:
                scan_date_formatted = scan_date_from_report
        else:
            scan_date_formatted = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        summary_cards_html = f"""
            <div class="stat-card">
                <h3>Total de Alertas</h3>
                <p>{stats['total']}</p>
            </div>
            <div class="stat-card">
                <h3>Alto Risco</h3>
                <p class="high">{stats['high']}</p>
            </div>
            <div class="stat-card">
                <h3>Médio Risco</h3>
                <p class="medium">{stats['medium']}</p>
            </div>
            <div class="stat-card">
                <h3>Baixo Risco</h3>
                <p class="low">{stats['low']}</p>
            </div>
            <div class="stat-card">
                <h3>Informativo</h3>
                <p class="info">{stats['info']}</p>
            </div>
        """

        alerts_list_html = ''
        if not alertas:
            alerts_list_html = """
                <div class="empty-state" id="empty-message-no-alerts">
                    <img src="https://cdn-icons-png.flaticon.com/512/4076/4076478.png" alt="Nenhum alerta">
                    <h3>Nenhuma vulnerabilidade encontrada</h3>
                    <p>O scan não identificou problemas de segurança.</p>
                </div>
            """
        else:
            risk_map_html = {
                '3': {'class': 'high', 'label': 'Alto', 'filter': 'high'},
                '2': {'class': 'medium', 'label': 'Médio', 'filter': 'medium'},
                '1': {'class': 'low', 'label': 'Baixo', 'filter': 'low'},
                '0': {'class': 'info', 'label': 'Informativo', 'filter': 'info'},
                'High': {'class': 'high', 'label': 'Alto', 'filter': 'high'},
                'Medium': {'class': 'medium', 'label': 'Médio', 'filter': 'medium'},
                'Low': {'class': 'low', 'label': 'Baixo', 'filter': 'low'},
                'Informational': {'class': 'info', 'label': 'Informativo', 'filter': 'info'}
            }
            for alerta in alertas:
                risk_level_key = str(alerta.get('riskcode', '0'))
                risk_info = risk_map_html.get(risk_level_key)
                if not risk_info:
                    risk_info = risk_map_html.get(alerta.get('riskdesc', '').split(' ')[0], {'class': 'info', 'label': 'Desconhecido', 'filter': 'info'})

                instances_html = ''
                for instance in alerta.get('instances', []):
                    uri = instance.get('uri', '#')
                    method = instance.get('method', 'GET')
                    instances_html += f"""
                        <li><strong>URI:</strong> <a href="{uri}" target="_blank">{uri}</a> ({method})</li>
                    """
                if not instances_html:
                    instances_html = '<li>Nenhuma URL específica encontrada</li>'

                alert_name = alerta.get('name', 'Alerta sem nome')
                alert_desc = alerta.get('desc', 'Sem descrição disponível.')
                alert_solution = alerta.get('solution', 'Sem solução recomendada disponível.')
                alert_reference = alerta.get('reference')
                alert_cweid = alerta.get('cweid', 'N/A')
                alert_wascid = alerta.get('wascid', 'N/A')

                ref_html = f"""
                    <div class="alert-section">
                        <h4>Referência</h4>
                        <p><p>{processar_referencias(alert_reference)}</p></p>
                    </div>
                """ if alert_reference else ''

                alerts_list_html += f"""
                    <div class="alert alert-{risk_info['class']}" data-riskcode="{risk_info['filter']}">
                        <div class="alert-header">
                            <h3 class="alert-title">{alert_name}</h3>
                            <span class="alert-risk risk-{risk_info['class']}">{risk_info['label']}</span>
                        </div>
                        <div class="alert-body">
                            <div class="alert-section">
                                <h4>Descrição</h4>
                                <p>{alert_desc}</p>
                            </div>
                            <div class="alert-extra" style="display:none">
                                <div class="alert-section">
                                    <h4>Solução</h4>
                                    <p>{alert_solution}</p>
                                </div>
                                <div class="alert-section">
                                    <h4>CWE ID:</h4>
                                    <p>{alert_cweid}</p>
                                </div>
                                <div class="alert-section">
                                    <h4>WASC ID:</h4>
                                    <p>{alert_wascid}</p>
                                </div>
                                <div class="alert-section">
                                    <h4>URLs Afetadas ({len(alerta.get('instances', []))})</h4>
                                    <ul class="url-list">
                                        {instances_html}
                                    </ul>
                                </div>
                                {ref_html}
                            </div>
                            <button class="ver-mais-btn">Ver mais ▼</button>
                        </div>
                    </div>
                """
        
        html_template_content = html_template_content.replace(
            "<!-- ZAP_SCAN_DATE_PLACEHOLDER -->", scan_date_formatted
        )

        html_template_content = html_template_content.replace(
            "<!-- ZAP_STATS_PLACEHOLDER -->", summary_cards_html
        )

        html_template_content = html_template_content.replace(
            "<!-- ZAP_ALERTS_LIST_PLACEHOLDER -->", alerts_list_html
        )

        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html_template_content)

        print(f"Relatório HTML final gerado em: {output_html_path}")
        
        try:
            if update_reports_index(json_file_path, output_html_path):
                print("📋 Índice de relatórios atualizado")

                json_file_reports = Path(json_file_path)

                if json_file_reports.exists():
                    json_file_reports.unlink()
                    print(f"🗑️ Arquivo JSON temporário removido: {json_file_reports}")
                else:
                    print(f"⚠️ Arquivo JSON temporário não encontrado para remoção: {json_file_reports}")
            else:
                print("⚠️ Falha ao atualizar índice de relatórios")
        except Exception as e:
            print(f"⚠️ Erro ao atualizar índice: {e}")
        
        return True

    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado. Verifique os caminhos: JSON '{json_file_path}', HTML Template '{html_template_path}'")
        return False
    except json.JSONDecodeError:
        print(f"Erro: O arquivo JSON '{json_file_path}' não é um JSON válido.")
        return False
    except Exception as e:
        print(f"Um erro inesperado ocorreu: {e}")
        return False


def update_reports_index(json_file_path, html_file_path):
    try:
        reports_dir = os.getenv("REPORTS_DIR", os.path.dirname(html_file_path))
        os.makedirs(reports_dir, exist_ok=True)

        index_filename = os.path.join(reports_dir, "reports_index.json")
        
        if os.path.exists(index_filename):
            with open(index_filename, 'r', encoding='utf-8') as f:
                reports_index = json.load(f)
        else:
            reports_index = []

        with open(json_file_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)

        site_data = report_data.get("site", [{}])[0]
        url_executado = site_data.get("@name", "URL não identificada")

        alertas = site_data.get("alerts", [])
        quantidade_riscos = {
            "alto": sum(1 for a in alertas if str(a.get("riskcode", "0")) == "3"),
            "medio": sum(1 for a in alertas if str(a.get("riskcode", "0")) == "2"),
            "baixo": sum(1 for a in alertas if str(a.get("riskcode", "0")) == "1"),
            "informativo": sum(1 for a in alertas if str(a.get("riskcode", "0")) not in ["1", "2", "3"]),
            "total": len(alertas)
        }

        data_execucao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        caminho_html = os.path.basename(html_file_path)

        report_record = {
            "url_executado": url_executado,
            "data_execucao": data_execucao,
            "quantidade_riscos": quantidade_riscos,
            "resumo": "",
            "caminho_html": caminho_html
        }

        for i, existing_record in enumerate(reports_index):
            if existing_record.get("url_executado") == url_executado:
                reports_index[i] = report_record
                break
        else:
            reports_index.append(report_record)

        with open(index_filename, 'w', encoding='utf-8') as f:
            json.dump(reports_index, f, indent=2, ensure_ascii=False)

        print(f"📋 Índice de relatórios atualizado localmente: {index_filename}")
        
        return True

    except Exception as e:
        print(f"Erro ao atualizar índice local: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python render.py <caminho_json> <caminho_template_html> <caminho_saida_html>")
        sys.exit(1)

    json_path = sys.argv[1]
    template_path = sys.argv[2]
    output_path = sys.argv[3]
    
    if not render_html_report(json_path, template_path, output_path):
        sys.exit(1)