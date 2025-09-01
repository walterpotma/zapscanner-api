import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pathlib import Path
import os
import json
import threading
from services.scanner import ZapScanner
from services.render import render_html_report

script_path = "/app/scripts/run-zap.sh"
reports_dir = os.getenv("REPORTS_DIR", "/app/reports")
template_dir = os.getenv("TEMPLATE_DIR", "/app/templates")
template_file = "model-reports-dark.html"
index_filename = "reports_index.json"

active_scans = {}
scan_lock = threading.Lock()

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": [
        "http://localhost:5500", 
        "http://localhost:3000", 
        "https://zapscanner.bne.com.br",
    ]}})
    
    def run_scan_async(url):
        try:
            print(f"Iniciando scan para {url}")
            def log_callback(line):
                with scan_lock:
                    logs = active_scans[url].setdefault("logs", [])
                    logs.append(line)
            scanner = ZapScanner(
                script_path,
                reports_dir,
                template_dir,
                template_file,
            )
            result = scanner.execute(url, log_callback=log_callback)
            print(f"Scan finalizado para {url}")

            report_data = {
                **result.__dict__,
                "date": datetime.datetime.now().isoformat(),
                "url": url,
                "status": "completed"
            }
            with scan_lock:
                active_scans[url].update(report_data)
            print(f"Status atualizado para completed: {url}")

        except Exception as e:
            print(f"Erro no scan: {e}")
            with scan_lock:
                active_scans[url] = {
                    "status": "failed",
                    "error": str(e),
                    "date": datetime.datetime.now().isoformat()
                }

    @app.route('/')
    def home():
        return "API OWASP ZAP Scanner - Async Mode"

    @app.route('/api/scan', methods=['POST'])
    def start_scan():
        """Endpoint para iniciar um novo scan de forma assíncrona"""
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"error": "URL parameter is required"}), 400
            
        url = data['url']
        
        with scan_lock:
            if url in active_scans:
                status = active_scans[url].get('status')
                if status in ['started', 'running']:
                    return jsonify({
                        "status": "already_running",
                        "message": "Scan already in progress for this URL"
                    }), 409
        
        thread = threading.Thread(
            target=run_scan_async,
            args=(url,),
            daemon=True
        )
        thread.start()
        
        with scan_lock:
            active_scans[url] = {
                "status": "started",
                "date": datetime.datetime.now().isoformat(),
                "url": url
            }
        
        return jsonify({
            "status": "started",
            "message": "Scan initiated in background",
            "url": url,
            "monitor_url": f"/api/scan/status/{url}"
        })

    @app.route('/api/scan/status/<path:url>')
    def scan_status(url):
        """Endpoint para verificar status do scan"""
        with scan_lock:
            scan_data = active_scans.get(url, {})
        
        if not scan_data:
            return jsonify({"error": "No scan found for this URL"}), 404
            
        return jsonify(scan_data)

    @app.route('/api/reports', methods=['GET'])
    def list_reports():
        """Lista todos os relatórios disponíveis a partir do arquivo JSON local"""
        try:
            index_filepath = os.path.join(reports_dir, index_filename)
            if not os.path.exists(index_filepath):
                print("Arquivo de índice não encontrado.")
                return jsonify([])

            with open(index_filepath, "r", encoding="utf-8") as f:
                reports_index = json.load(f)
            return jsonify(reports_index)
        except Exception as e:
            print(f"Erro ao listar relatórios: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/reports/html/<path:filename>', methods=['GET'])
    def get_report_html(filename):
        """Serve um relatório HTML diretamente da pasta reports"""
        try:
            reports_path = Path(reports_dir)
            return send_from_directory(
                reports_path,
                filename,
                mimetype="text/html"
            )
        except FileNotFoundError:
            return jsonify({"error": "Report not found"}), 404

    @app.route('/api/reports/delete/<path:filename>/<path:urlexecutado>', methods=['DELETE'])
    def delete_report(filename, urlexecutado):
        """Endpoint para deletar um relatório específico"""
        try:
            json_path = Path(reports_dir) / index_filename
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    reports = json.load(f)
            else:
                reports = []

            report = next((r for r in reports if r.get("caminho_html") == filename), None)

            if not report:
                report = next((r for r in reports if r.get("url_executado") == urlexecutado), None)

            if not report:
                return jsonify({"error": "Report not found"}), 404
            
            reports = [r for r in reports if r != report]
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(reports, f, ensure_ascii=False, indent=4)
                
            report_path = Path(reports_dir) / report.get("caminho_html", "")
            if report_path.exists():
                report_path.unlink()

            return jsonify({"status": "success", "message": "Report deleted successfully"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
    @app.route('/api/reports/download/<path:filename>', methods=['GET'])
    def download_report(filename):
        """Endpoint para baixar um relatório específico"""
        try:
            reports_path = Path(reports_dir)
            return send_from_directory(
                reports_path,
                filename,
                as_attachment=True,
                mimetype="text/html"
            )
        except FileNotFoundError:
            return jsonify({"error": "Report not found"}), 404

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)