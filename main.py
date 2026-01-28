import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
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

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        top_layout = QHBoxLayout()
        layout.addLayout(top_layout)

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
        layout.addLayout(results_header_layout)

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Selected"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSortingEnabled(True)
        layout.addWidget(self.results_table)

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
        layout.addLayout(buttons_layout)

        export_layout = QHBoxLayout()
        self.export_md_button = QPushButton("Экспорт Markdown")
        self.export_json_button = QPushButton("Экспорт JSON")
        self.export_md_button.clicked.connect(self.on_export_markdown)
        self.export_json_button.clicked.connect(self.on_export_json)
        export_layout.addWidget(self.export_md_button)
        export_layout.addWidget(self.export_json_button)
        layout.addLayout(export_layout)

        self.load_prompts()

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
