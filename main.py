import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import db
import models
import network


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChatList")
        self.setGeometry(100, 100, 900, 600)

        db.init_db()
        self.current_prompt_id: Optional[int] = None
        self.temp_results = []
        self.all_prompts: List[Dict[str, str]] = []
        self.all_models: List[Dict[str, str]] = []

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.requests_tab = QWidget()
        requests_layout = QVBoxLayout()
        self.requests_tab.setLayout(requests_layout)
        self.tabs.addTab(self.requests_tab, "Запросы")

        top_layout = QHBoxLayout()
        requests_layout.addLayout(top_layout)

        prompt_layout = QVBoxLayout()
        prompt_layout.addWidget(QLabel("Введите промт:"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Введите текст запроса...")
        prompt_layout.addWidget(self.prompt_input)
        top_layout.addLayout(prompt_layout, 2)

        saved_layout = QVBoxLayout()
        saved_layout.addWidget(QLabel("Сохраненные промты:"))
        self.prompts_search = QLineEdit()
        self.prompts_search.setPlaceholderText("Поиск по промтам...")
        self.prompts_search.textChanged.connect(self.filter_prompts)
        saved_layout.addWidget(self.prompts_search)
        self.prompts_list = QListWidget()
        self.prompts_list.itemSelectionChanged.connect(self.on_prompt_selected)
        saved_layout.addWidget(self.prompts_list)
        top_layout.addLayout(saved_layout, 1)

        results_header_layout = QHBoxLayout()
        results_header_layout.addWidget(QLabel("Результаты:"))
        self.results_search = QLineEdit()
        self.results_search.setPlaceholderText("Поиск по результатам...")
        self.results_search.textChanged.connect(self.filter_results)
        results_header_layout.addWidget(self.results_search)
        requests_layout.addLayout(results_header_layout)

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Selected"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSortingEnabled(True)
        requests_layout.addWidget(self.results_table)

        buttons_layout = QHBoxLayout()
        self.send_button = QPushButton("Отправить")
        self.save_button = QPushButton("Сохранить")
        self.new_button = QPushButton("Новый запрос")
        self.send_button.clicked.connect(self.on_send_clicked)
        self.save_button.clicked.connect(self.on_save_clicked)
        self.new_button.clicked.connect(self.on_new_clicked)
        buttons_layout.addWidget(self.send_button)
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.new_button)
        requests_layout.addLayout(buttons_layout)

        export_layout = QHBoxLayout()
        self.export_md_button = QPushButton("Экспорт Markdown")
        self.export_json_button = QPushButton("Экспорт JSON")
        self.export_md_button.clicked.connect(self.on_export_markdown)
        self.export_json_button.clicked.connect(self.on_export_json)
        export_layout.addWidget(self.export_md_button)
        export_layout.addWidget(self.export_json_button)
        requests_layout.addLayout(export_layout)

        self.models_tab = QWidget()
        models_layout = QVBoxLayout()
        self.models_tab.setLayout(models_layout)
        self.tabs.addTab(self.models_tab, "Модели")

        models_layout.addWidget(QLabel("Управление моделями:"))
        self.models_table = QTableWidget(0, 4)
        self.models_table.setHorizontalHeaderLabels(
            ["Имя", "API URL", "API Key Env", "Активна"]
        )
        self.models_table.horizontalHeader().setStretchLastSection(True)
        self.models_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.models_table.setSelectionMode(QTableWidget.SingleSelection)
        self.models_table.itemSelectionChanged.connect(self.on_model_selected)
        self.models_table.setSortingEnabled(True)
        models_layout.addWidget(self.models_table)

        form_layout = QFormLayout()
        self.model_name_input = QLineEdit()
        self.model_url_input = QLineEdit()
        self.model_key_input = QLineEdit()
        self.model_active_checkbox = QCheckBox("Активна")
        form_layout.addRow("Имя", self.model_name_input)
        form_layout.addRow("API URL", self.model_url_input)
        form_layout.addRow("API Key Env", self.model_key_input)
        form_layout.addRow("", self.model_active_checkbox)
        models_layout.addLayout(form_layout)

        model_buttons_layout = QHBoxLayout()
        self.model_add_button = QPushButton("Добавить")
        self.model_update_button = QPushButton("Обновить")
        self.model_delete_button = QPushButton("Удалить")
        self.model_refresh_button = QPushButton("Обновить список")
        self.model_add_button.clicked.connect(self.on_model_add)
        self.model_update_button.clicked.connect(self.on_model_update)
        self.model_delete_button.clicked.connect(self.on_model_delete)
        self.model_refresh_button.clicked.connect(self.load_models)
        model_buttons_layout.addWidget(self.model_add_button)
        model_buttons_layout.addWidget(self.model_update_button)
        model_buttons_layout.addWidget(self.model_delete_button)
        model_buttons_layout.addWidget(self.model_refresh_button)
        models_layout.addLayout(model_buttons_layout)

        self.load_prompts()
        self.load_models()

    def load_prompts(self) -> None:
        self.prompts_list.clear()
        self.all_prompts = db.list_prompts()
        self.filter_prompts()

    def filter_prompts(self) -> None:
        query = self.prompts_search.text().strip().lower()
        self.prompts_list.clear()
        for row in self.all_prompts:
            prompt_text = row["prompt"]
            if query and query not in prompt_text.lower():
                continue
            item = QListWidgetItem(prompt_text)
            item.setData(Qt.UserRole, row["id"])
            self.prompts_list.addItem(item)
        self.prompts_list.sortItems()

    def on_prompt_selected(self) -> None:
        items = self.prompts_list.selectedItems()
        if not items:
            return
        selected = items[0]
        self.prompt_input.setPlainText(selected.text())

    def on_send_clicked(self) -> None:
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self.show_message("Введите промт или выберите сохраненный.")
            return

        created_at = datetime.utcnow().isoformat()
        self.current_prompt_id = db.add_prompt(created_at, prompt, "")
        self.load_prompts()

        active_models = models.get_active_models()
        if not active_models:
            self.show_message("Нет активных моделей. Добавьте модели в таблицу models.")
            return

        self.temp_results = []
        self.results_table.setRowCount(0)

        for model in active_models:
            try:
                response_text = network.send_prompt(model, prompt)
            except network.NetworkError as exc:
                response_text = f"ERROR: {exc}"

            self.temp_results.append(
                {
                    "model_id": model.id,
                    "model_name": model.name,
                    "response_text": response_text,
                }
            )
            self.add_result_row(model.id, model.name, response_text)

        self.filter_results()

    def add_result_row(self, model_id: int, model_name: str, response_text: str) -> None:
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)

        model_item = QTableWidgetItem(model_name)
        model_item.setData(Qt.UserRole, model_id)
        model_item.setFlags(model_item.flags() & ~Qt.ItemIsEditable)
        self.results_table.setItem(row, 0, model_item)

        response_item = QTableWidgetItem(response_text)
        response_item.setFlags(response_item.flags() & ~Qt.ItemIsEditable)
        self.results_table.setItem(row, 1, response_item)

        selected_item = QTableWidgetItem()
        selected_item.setFlags(selected_item.flags() | Qt.ItemIsUserCheckable)
        selected_item.setCheckState(Qt.Unchecked)
        selected_item.setFlags(selected_item.flags() & ~Qt.ItemIsEditable)
        self.results_table.setItem(row, 2, selected_item)

    def filter_results(self) -> None:
        query = self.results_search.text().strip().lower()
        for row in range(self.results_table.rowCount()):
            model_item = self.results_table.item(row, 0)
            response_item = self.results_table.item(row, 1)
            model_text = model_item.text() if model_item else ""
            response_text = response_item.text() if response_item else ""
            row_text = f"{model_text} {response_text}".lower()
            self.results_table.setRowHidden(row, bool(query and query not in row_text))

    def on_save_clicked(self) -> None:
        if self.current_prompt_id is None:
            self.show_message("Сначала отправьте промт.")
            return

        saved_any = False
        created_at = datetime.utcnow().isoformat()

        for row in range(self.results_table.rowCount()):
            selected_item = self.results_table.item(row, 2)
            if selected_item and selected_item.checkState() == Qt.Checked:
                model_item = self.results_table.item(row, 0)
                response_item = self.results_table.item(row, 1)
                if not model_item or not response_item:
                    continue
                model_id = int(model_item.data(Qt.UserRole))
                response_text = response_item.text()
                db.add_result(self.current_prompt_id, model_id, response_text, created_at)
                saved_any = True

        if not saved_any:
            self.show_message("Нет выбранных результатов для сохранения.")
            return

        self.temp_results = []
        self.results_table.setRowCount(0)
        self.show_message("Выбранные результаты сохранены.")

    def on_new_clicked(self) -> None:
        self.prompt_input.clear()
        self.prompts_list.clearSelection()
        self.results_table.setRowCount(0)
        self.current_prompt_id = None
        self.temp_results = []
        self.results_search.clear()

    def load_models(self) -> None:
        self.models_table.setRowCount(0)
        self.all_models = db.list_models()
        for row in self.all_models:
            table_row = self.models_table.rowCount()
            self.models_table.insertRow(table_row)

            name_item = QTableWidgetItem(row["name"])
            name_item.setData(Qt.UserRole, row["id"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.models_table.setItem(table_row, 0, name_item)

            url_item = QTableWidgetItem(row["api_url"])
            url_item.setFlags(url_item.flags() & ~Qt.ItemIsEditable)
            self.models_table.setItem(table_row, 1, url_item)

            key_item = QTableWidgetItem(row["api_key_env"])
            key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
            self.models_table.setItem(table_row, 2, key_item)

            active_text = "Да" if row["is_active"] else "Нет"
            active_item = QTableWidgetItem(active_text)
            active_item.setData(Qt.UserRole, row["is_active"])
            active_item.setFlags(active_item.flags() & ~Qt.ItemIsEditable)
            self.models_table.setItem(table_row, 3, active_item)

    def on_model_selected(self) -> None:
        items = self.models_table.selectedItems()
        if not items:
            return
        row = items[0].row()
        name_item = self.models_table.item(row, 0)
        url_item = self.models_table.item(row, 1)
        key_item = self.models_table.item(row, 2)
        active_item = self.models_table.item(row, 3)

        self.model_name_input.setText(name_item.text() if name_item else "")
        self.model_url_input.setText(url_item.text() if url_item else "")
        self.model_key_input.setText(key_item.text() if key_item else "")
        is_active = int(active_item.data(Qt.UserRole)) if active_item else 0
        self.model_active_checkbox.setChecked(bool(is_active))

    def get_selected_model_id(self) -> Optional[int]:
        items = self.models_table.selectedItems()
        if not items:
            return None
        row = items[0].row()
        name_item = self.models_table.item(row, 0)
        if not name_item:
            return None
        return int(name_item.data(Qt.UserRole))

    def on_model_add(self) -> None:
        name = self.model_name_input.text().strip()
        url = self.model_url_input.text().strip()
        key_env = self.model_key_input.text().strip()
        is_active = 1 if self.model_active_checkbox.isChecked() else 0

        if not name or not url or not key_env:
            self.show_message("Заполните имя, API URL и API Key Env.")
            return

        db.add_model(name, url, key_env, is_active)
        self.load_models()
        self.show_message("Модель добавлена.")

    def on_model_update(self) -> None:
        model_id = self.get_selected_model_id()
        if model_id is None:
            self.show_message("Выберите модель для обновления.")
            return

        name = self.model_name_input.text().strip()
        url = self.model_url_input.text().strip()
        key_env = self.model_key_input.text().strip()
        is_active = 1 if self.model_active_checkbox.isChecked() else 0

        if not name or not url or not key_env:
            self.show_message("Заполните имя, API URL и API Key Env.")
            return

        db.update_model(model_id, name, url, key_env, is_active)
        self.load_models()
        self.show_message("Модель обновлена.")

    def on_model_delete(self) -> None:
        model_id = self.get_selected_model_id()
        if model_id is None:
            self.show_message("Выберите модель для удаления.")
            return

        confirm = QMessageBox.question(
            self, "Подтвердите удаление", "Удалить выбранную модель?"
        )
        if confirm != QMessageBox.Yes:
            return

        db.delete_model(model_id)
        self.load_models()
        self.show_message("Модель удалена.")

    def get_selected_results(self) -> List[Dict[str, str]]:
        selected = []
        for row in range(self.results_table.rowCount()):
            selected_item = self.results_table.item(row, 2)
            if selected_item and selected_item.checkState() == Qt.Checked:
                model_item = self.results_table.item(row, 0)
                response_item = self.results_table.item(row, 1)
                if not model_item or not response_item:
                    continue
                selected.append(
                    {"model": model_item.text(), "response": response_item.text()}
                )
        return selected

    def on_export_markdown(self) -> None:
        selected = self.get_selected_results()
        if not selected:
            self.show_message("Нет выбранных результатов для экспорта.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить Markdown", "results.md", "Markdown (*.md)"
        )
        if not path:
            return

        prompt_text = self.prompt_input.toPlainText().strip()
        lines = [f"# Результаты ChatList", "", f"**Промт:** {prompt_text}", ""]
        for item in selected:
            lines.append(f"## {item['model']}")
            lines.append("")
            lines.append(item["response"])
            lines.append("")
        content = "\n".join(lines).strip() + "\n"

        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)

        self.show_message("Экспорт в Markdown завершен.")

    def on_export_json(self) -> None:
        selected = self.get_selected_results()
        if not selected:
            self.show_message("Нет выбранных результатов для экспорта.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить JSON", "results.json", "JSON (*.json)"
        )
        if not path:
            return

        data = {
            "prompt": self.prompt_input.toPlainText().strip(),
            "results": selected,
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

        self.show_message("Экспорт в JSON завершен.")

    def show_message(self, text: str) -> None:
        QMessageBox.information(self, "ChatList", text)


def main() -> None:
    logging.basicConfig(
        filename="chatlist.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
