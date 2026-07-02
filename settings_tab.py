"""
Settings tab - Phase 1.

Lets the user pick an AI provider and edit API keys / endpoints.
Edits are saved to config/settings.yaml on Save.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.paths import SETTINGS_FILE, load_yaml, save_yaml


PROVIDERS = [
    ("manual", "Manual (no AI - review & edit text by hand)"),
    ("openai", "OpenAI direct (api.openai.com)"),
    ("azure_openai", "Azure OpenAI Service"),
    ("anthropic", "Anthropic Claude"),
    ("ollama", "Ollama (local)"),
    ("local_server", "Local OpenAI-compatible server (LM Studio / llama.cpp / vLLM / GLM-4.6)"),
]


class SettingsTab(QWidget):
    def __init__(self, status_cb=None):
        super().__init__()
        self.status_cb = status_cb or (lambda msg: None)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        v = QVBoxLayout(self)

        # AI provider group
        ai_group = QGroupBox("AI Provider")
        ai_form = QFormLayout(ai_group)

        self.in_provider = QComboBox()
        for code, label in PROVIDERS:
            self.in_provider.addItem(label, code)
        ai_form.addRow("Provider:", self.in_provider)

        # OpenAI direct
        self.in_openai_key = QLineEdit()
        self.in_openai_key.setEchoMode(QLineEdit.Password)
        self.in_openai_key.setPlaceholderText("sk-...")
        self.in_openai_model = QLineEdit("gpt-4o-mini")
        ai_form.addRow("OpenAI API Key:", self.in_openai_key)
        ai_form.addRow("OpenAI Model:", self.in_openai_model)

        # Azure OpenAI
        self.in_azure_key = QLineEdit()
        self.in_azure_key.setEchoMode(QLineEdit.Password)
        self.in_azure_endpoint = QLineEdit()
        self.in_azure_endpoint.setPlaceholderText("https://YOUR-RESOURCE.openai.azure.com")
        self.in_azure_version = QLineEdit("2024-06-01")
        self.in_azure_deployment = QLineEdit("gpt-4o-mini")
        ai_form.addRow("Azure API Key:", self.in_azure_key)
        ai_form.addRow("Azure Endpoint:", self.in_azure_endpoint)
        ai_form.addRow("API Version:", self.in_azure_version)
        ai_form.addRow("Deployment Name:", self.in_azure_deployment)

        # Anthropic
        self.in_anthropic_key = QLineEdit()
        self.in_anthropic_key.setEchoMode(QLineEdit.Password)
        self.in_anthropic_key.setPlaceholderText("sk-ant-...")
        self.in_anthropic_model = QLineEdit("claude-3-5-sonnet-20241022")
        ai_form.addRow("Anthropic API Key:", self.in_anthropic_key)
        ai_form.addRow("Anthropic Model:", self.in_anthropic_model)

        # Ollama
        self.in_ollama_host = QLineEdit("http://localhost:11434")
        self.in_ollama_model = QLineEdit("llama3.1:8b")
        ai_form.addRow("Ollama Host:", self.in_ollama_host)
        ai_form.addRow("Ollama Model:", self.in_ollama_model)

        # Local OpenAI-compatible server (LM Studio / llama.cpp / vLLM / GLM-4.6)
        self.in_local_base_url = QLineEdit("http://localhost:1234/v1")
        self.in_local_base_url.setPlaceholderText("http://localhost:1234/v1 (LM Studio default)")
        self.in_local_model = QLineEdit("glm-4.6")
        self.in_local_api_key = QLineEdit("local")
        self.in_local_api_key.setPlaceholderText("most local servers ignore this - put anything")
        ai_form.addRow("Local Server URL:", self.in_local_base_url)
        ai_form.addRow("Local Model Name:", self.in_local_model)
        ai_form.addRow("Local API Key:", self.in_local_api_key)

        # Behavior
        self.in_concurrency = QSpinBox()
        self.in_concurrency.setRange(1, 10)
        self.in_concurrency.setValue(3)
        ai_form.addRow("Max Concurrent Files:", self.in_concurrency)

        v.addWidget(ai_group)

        # Save / Reload
        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("Save Settings")
        self.btn_reload = QPushButton("Reload from File")
        self.btn_save.clicked.connect(self._on_save)
        self.btn_reload.clicked.connect(self._load)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_reload)
        btn_row.addWidget(self.btn_save)
        v.addLayout(btn_row)
        v.addStretch()

        v.addWidget(QLabel(
            "<small>Settings are stored in <code>config/settings.yaml</code>. "
            "Changes take effect on next processing run.</small>"
        ))

    def _load(self) -> None:
        data = load_yaml(SETTINGS_FILE)
        ai = data.get("ai", {})
        provider = ai.get("provider", "manual")
        for i in range(self.in_provider.count()):
            if self.in_provider.itemData(i) == provider:
                self.in_provider.setCurrentIndex(i)
                break

        openai_cfg = ai.get("openai", {}) or {}
        self.in_openai_key.setText(openai_cfg.get("api_key", ""))
        self.in_openai_model.setText(openai_cfg.get("model", "gpt-4o-mini"))

        azure_cfg = ai.get("azure_openai", {}) or {}
        self.in_azure_key.setText(azure_cfg.get("api_key", ""))
        self.in_azure_endpoint.setText(azure_cfg.get("endpoint", ""))
        self.in_azure_version.setText(azure_cfg.get("api_version", "2024-06-01"))
        self.in_azure_deployment.setText(azure_cfg.get("deployment_name", "gpt-4o-mini"))

        anthropic_cfg = ai.get("anthropic", {}) or {}
        self.in_anthropic_key.setText(anthropic_cfg.get("api_key", ""))
        self.in_anthropic_model.setText(anthropic_cfg.get("model", "claude-3-5-sonnet-20241022"))

        ollama_cfg = ai.get("ollama", {}) or {}
        self.in_ollama_host.setText(ollama_cfg.get("host", "http://localhost:11434"))
        self.in_ollama_model.setText(ollama_cfg.get("model", "llama3.1:8b"))

        local_cfg = ai.get("local_server", {}) or {}
        self.in_local_base_url.setText(local_cfg.get("base_url", "http://localhost:1234/v1"))
        self.in_local_model.setText(local_cfg.get("model", "glm-4.6"))
        self.in_local_api_key.setText(local_cfg.get("api_key", "local"))

        self.in_concurrency.setValue(ai.get("max_concurrent_files", 3))

    def _on_save(self) -> None:
        data = load_yaml(SETTINGS_FILE)
        ai = data.setdefault("ai", {})
        ai["provider"] = self.in_provider.currentData()
        ai["openai"] = {
            "api_key": self.in_openai_key.text().strip(),
            "model": self.in_openai_model.text().strip(),
        }
        ai["azure_openai"] = {
            "api_key": self.in_azure_key.text().strip(),
            "endpoint": self.in_azure_endpoint.text().strip(),
            "api_version": self.in_azure_version.text().strip(),
            "deployment_name": self.in_azure_deployment.text().strip(),
        }
        ai["anthropic"] = {
            "api_key": self.in_anthropic_key.text().strip(),
            "model": self.in_anthropic_model.text().strip(),
        }
        ai["ollama"] = {
            "host": self.in_ollama_host.text().strip(),
            "model": self.in_ollama_model.text().strip(),
        }
        ai["local_server"] = {
            "base_url": self.in_local_base_url.text().strip(),
            "model": self.in_local_model.text().strip(),
            "api_key": self.in_local_api_key.text().strip() or "local",
        }
        ai["max_concurrent_files"] = self.in_concurrency.value()
        save_yaml(SETTINGS_FILE, data)
        self.status_cb("Settings saved")
        QMessageBox.information(self, "Saved", "Settings saved to config/settings.yaml")
