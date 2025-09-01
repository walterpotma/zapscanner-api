import subprocess
import json
from pathlib import Path
from dataclasses import dataclass
import os
import logging
from services import notifier

@dataclass
class ScanResult:
    scan_id: str
    report_json: dict
    report_html: str
    
class ZapScanner:
    def __init__(self, script_path, reports_dir, template_dir, template_file):
        self.script_path = Path(script_path)
        self.reports_dir = Path(reports_dir)
        self.template_dir = Path(template_dir)
        self.template_file = template_file
        self.logger = logging.getLogger('ZapScanner')
        
        if not self.script_path.exists(): 
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _generate_safe_filename(self, url):
        """Gera um nome seguro a partir da URL (centralizado no Python)"""
        import re
        safe_name = re.sub(r'^https?://', '', url)
        safe_name = re.sub(r'[^a-zA-Z0-9-]', '_', safe_name)
        return safe_name[:50]


    def execute(self, target_url, log_callback=None):
        try:
            safe_name = self._generate_safe_filename(target_url)
            json_path = self.reports_dir / f'{safe_name}.json'
            html_path = self.reports_dir / f'{safe_name}.html'
            
            cmd = [
                str(self.script_path),
                str(self.reports_dir),
                str(self.template_dir),
                self.template_file,
                safe_name,
                target_url,
            ]
            
            self.logger.info(f"Starting scan for: {target_url}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            self.logger.info(f"Starting scan for: {target_url}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in process.stdout:
                line = line.strip()
                if log_callback:
                    log_callback(line)
                self.logger.info(line)

            process.wait(timeout=600)

            return ScanResult(
                scan_id=safe_name,
                report_json=str(json_path),
                report_html=str(html_path)
            )
            
        except subprocess.TimeoutExpired:
            process.kill()
            error_msg = "Scan timed out after 10 minutes"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            self.logger.error(f"Scan error: {str(e)}")
            raise