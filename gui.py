"""
PyQt6 GUI for AI Research Agent
"""
import sys
from typing import Dict, List
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QTextEdit,
    QTextBrowser,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QFileDialog,
    QMessageBox,
    QMenu,
    QProgressDialog,
)
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal, QSettings, QPoint
from PyQt6.QtGui import QAction, QKeySequence

from research_agent import AIResearchAgent


class ResearchWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, query: str, depth: str, max_sources: int, use_ai: bool, ai_backend: str, news: bool):
        super().__init__()
        self.query = query
        self.depth = depth
        self.max_sources = max_sources
        self.use_ai = use_ai
        self.ai_backend = ai_backend
        self.news = news

    def run(self):
        try:
            agent = AIResearchAgent(use_ai=self.use_ai, ai_backend=self.ai_backend)
            self.progress.emit(f"Researching: {self.query}")
            data = agent.research(
                query=self.query,
                depth=self.depth,
                max_sources=self.max_sources,
                news=self.news,
                progress_cb=self.progress.emit,
            )
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Research Agent - PyQt6")
        self.resize(1000, 700)

        self.thread: QThread | None = None
        self.worker: ResearchWorker | None = None
        self.last_results: Dict | None = None
        self.agent_for_save = AIResearchAgent(use_ai=False)  # for saving history if user wants
        self.progress_dlg: QProgressDialog | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # Controls row
        controls = QHBoxLayout()
        root.addLayout(controls)

        controls.addWidget(QLabel("Query:"))
        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("Enter research topic or question")
        controls.addWidget(self.query_edit, stretch=2)

        controls.addWidget(QLabel("Depth:"))
        self.depth_combo = QComboBox()
        self.depth_combo.addItems(["quick", "standard", "deep"])  # must match CLI
        self.depth_combo.setCurrentText("standard")
        controls.addWidget(self.depth_combo)

        controls.addWidget(QLabel("Sources:"))
        self.sources_spin = QSpinBox()
        self.sources_spin.setRange(1, 50)
        self.sources_spin.setValue(5)
        controls.addWidget(self.sources_spin)

        controls.addWidget(QLabel("AI Backend:"))
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["ollama", "transformers", "none"])  # must match CLI
        self.backend_combo.setCurrentText("ollama")
        controls.addWidget(self.backend_combo)

        self.news_check = QCheckBox("News search")
        controls.addWidget(self.news_check)

        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self.on_run)
        controls.addWidget(self.run_btn)

        self.save_btn = QPushButton("Save JSON")
        self.save_btn.clicked.connect(self.on_save)
        controls.addWidget(self.save_btn)

        # Shortcuts
        self.action_save = QAction("Save", self)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.triggered.connect(self.on_save)
        self.addAction(self.action_save)

        self.action_run = QAction("Run", self)
        self.action_run.setShortcut(QKeySequence("Ctrl+R"))
        self.action_run.triggered.connect(self.on_run)
        self.addAction(self.action_run)

        # Status banner
        self.status_label = QLabel()
        self.status_label.setObjectName("statusLabel")
        self.status_label.setVisible(False)
        self.status_label.setStyleSheet("QLabel#statusLabel { padding: 6px; border-radius: 4px; background: #f0f0f0; color: #333; }")
        root.addWidget(self.status_label)

        # Tabs for results
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, stretch=1)

        # Hints / tooltips
        self.depth_combo.setToolTip("Research depth: quick (search), standard (search+scrape), deep (search+scrape+AI)")
        self.sources_spin.setToolTip("Maximum number of sources to scrape")
        self.backend_combo.setToolTip("AI backend for deep analysis")
        self.news_check.setToolTip("Search for news articles instead of general results")

        # Enter to run
        self.query_edit.returnPressed.connect(self.on_run)

        # Settings persistence
        self.settings = QSettings("AIResearch", "ResearchAgentGUI")
        self.load_settings()

        # Search Results tab
        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["#", "Title", "URL"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSortingEnabled(True)
        # Interactions: double-click opens URL, right-click context menu
        self.results_table.cellDoubleClicked.connect(self.open_result_at_row)
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.on_results_context_menu)
        self.tabs.addTab(self.results_table, "Search Results")

        # Sources tab (QTextBrowser for clickable links)
        self.sources_view = QTextBrowser()
        self.sources_view.setOpenExternalLinks(True)
        self.sources_view.setReadOnly(True)
        self.tabs.addTab(self.sources_view, "Sources")

        # Analysis tab
        self.analysis_view = QTextEdit()
        self.analysis_view.setReadOnly(True)
        self.analysis_view.setPlaceholderText("Run deep research with AI to see analysis here.")
        self.tabs.addTab(self.analysis_view, "Analysis")

        # Log tab
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.tabs.addTab(self.log_view, "Log")

    def log(self, msg: str):
        self.log_view.append(msg)

    def on_worker_progress(self, msg: str):
        self.log(msg)
        self.show_progress_dialog(msg)

    def show_progress_dialog(self, text: str):
        if self.progress_dlg is None:
            self.progress_dlg = QProgressDialog("", "", 0, 0, self)
            self.progress_dlg.setWindowTitle("Working...")
            self.progress_dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
            # Hide cancel button and close button (best effort across PyQt6 variants)
            try:
                self.progress_dlg.setCancelButtonText("")
            except Exception:
                pass
            try:
                self.progress_dlg.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
            except Exception:
                pass
            self.progress_dlg.setAutoClose(False)
            self.progress_dlg.setAutoReset(False)
            self.progress_dlg.setMinimumDuration(0)
            self.progress_dlg.setRange(0, 0)  # Busy indicator
        self.progress_dlg.setLabelText(text)
        self.progress_dlg.show()

    def close_progress_dialog(self):
        try:
            if self.progress_dlg is not None:
                self.progress_dlg.hide()
                self.progress_dlg.deleteLater()
        finally:
            self.progress_dlg = None

    def closeEvent(self, event):
        try:
            self.save_settings()
        finally:
            super().closeEvent(event)

    def set_status(self, msg: str, level: str = "info"):
        colors = {
            "info": ("#e8f4fd", "#0b4f71"),      # light blue bg, dark blue text
            "success": ("#e7f7ec", "#1b5e20"),   # light green bg, dark green text
            "warn": ("#fff7e6", "#8a6d3b"),     # light orange bg, brown text
            "error": ("#fdecea", "#c62828"),    # light red bg, dark red text
        }
        bg, fg = colors.get(level, colors["info"])
        self.status_label.setStyleSheet(
            f"QLabel#statusLabel {{ padding: 6px; border-radius: 4px; background: {bg}; color: {fg}; }}"
        )
        self.status_label.setText(msg)
        self.status_label.setVisible(True)

    def on_run(self):
        query = self.query_edit.text().strip()
        if not query:
            QMessageBox.warning(self, "Input required", "Please enter a query.")
            return

        depth = self.depth_combo.currentText()
        max_sources = self.sources_spin.value()
        backend = self.backend_combo.currentText()
        use_ai = backend != "none" and depth == "deep"
        news = self.news_check.isChecked()

        # Disable UI while running
        self.run_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.log_view.clear()
        self.analysis_view.clear()
        self.sources_view.clear()
        self.results_table.setRowCount(0)
        self.log("Starting research...")
        self.set_status("Running research...", "info")

        # Threaded worker
        self.thread = QThread()
        self.worker = ResearchWorker(query, depth, max_sources, use_ai, backend, news)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        # Save the current preferences
        self.save_settings()

        # Show busy dialog
        self.show_progress_dialog("Starting research...")

    def on_error(self, msg: str):
        self.log(f"Error: {msg}")
        self.set_status(f"Error: {msg}", "error")
        self.close_progress_dialog()
        QMessageBox.critical(self, "Error", msg)
        self.run_btn.setEnabled(True)
        self.save_btn.setEnabled(True)

    def on_finished(self, data: Dict):
        self.last_results = data
        self.agent_for_save.research_history.append(data)
        self.populate_results(data)
        if data.get("error"):
            self.log(f"Warning: {data['error']}")
            self.set_status(data["error"], "warn")
        else:
            n_res = len(data.get("search_results", []) or [])
            n_src = len(data.get("sources", []) or [])
            self.set_status(f"Completed. {n_res} results; {n_src} sources scraped.", "success")
        # Close any progress UI and re-enable controls
        self.close_progress_dialog()
        self.run_btn.setEnabled(True)
        self.save_btn.setEnabled(True)

    def populate_results(self, data: Dict):
        # Populate search results table
        results: List[Dict] = data.get("search_results", [])
        # Faster table update: disable sorting/updates during population
        prev_sorting = self.results_table.isSortingEnabled()
        self.results_table.setSortingEnabled(False)
        self.results_table.setUpdatesEnabled(False)
        try:
            self.results_table.setRowCount(len(results))
            for i, r in enumerate(results, start=1):
                self.results_table.setItem(i - 1, 0, QTableWidgetItem(str(i)))
                self.results_table.setItem(i - 1, 1, QTableWidgetItem(r.get("title", "")))
                self.results_table.setItem(i - 1, 2, QTableWidgetItem(r.get("url", "")))
        finally:
            self.results_table.setUpdatesEnabled(True)
            self.results_table.setSortingEnabled(prev_sorting)

        # Heuristic: If entries don't have news-specific fields, but user requested news,
        # we likely fell back due to rate limiting. Inform the user in the log.
        if results:
            has_news_fields = any(("date" in r) or ("source" in r) for r in results)
            if self.news_check.isChecked() and not has_news_fields:
                self.log("Warning: News search may have been rate-limited; showing general web results instead.")
                self.log("Tip: Try again in a bit or reduce 'Sources' to lessen requests.")
                self.set_status("News rate-limited; showing general web results.", "warn")
        else:
            self.set_status("No results returned.", "warn")

        # Populate sources view
        sources: List[Dict] = data.get("sources", [])
        parts = [
            f"<b>{idx}. {s.get('title','')}</b><br>"
            f"URL: <a href='{s.get('url','')}'>{s.get('url','')}</a><br>"
            f"{'Authors: ' + ', '.join(s.get('authors', [])) + '<br>' if s.get('authors') else ''}"
            f"{'Published: ' + s.get('publish_date') + '<br>' if s.get('publish_date') else ''}"
            f"<i>{(s.get('text') or '')[:600]}{'...' if s.get('text') and len(s.get('text'))>600 else ''}</i>"
            for idx, s in enumerate(sources, start=1)
        ]
        self.sources_view.setHtml("<br><br>".join(parts) if parts else "<i>No sources scraped.</i>")

        # Populate analysis
        analysis = data.get("analysis")
        if analysis:
            self.analysis_view.setPlainText(analysis)
        else:
            self.analysis_view.setPlainText("No analysis available.")

        # Log header
        header = f"Query: {data.get('query','')}\nTimestamp: {data.get('timestamp','')}"
        self.log(header)
        if data.get("error"):
            self.log(f"Error: {data['error']}")
            if "No search results" in data["error"]:
                self.log("Tip: DuckDuckGo may be throttling requests. Try again later or lower 'Sources'.")

    def on_save(self):
        if not self.agent_for_save.research_history:
            QMessageBox.information(self, "Nothing to save", "Run a search first.")
            return
        file, _ = QFileDialog.getSaveFileName(self, "Save research JSON", "research.json", "JSON Files (*.json)")
        if not file:
            return
        try:
            fname = self.agent_for_save.save_research(file)
            QMessageBox.information(self, "Saved", f"Saved to {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))


    def load_settings(self):
        try:
            self.depth_combo.setCurrentText(self.settings.value("depth", "standard"))
            self.sources_spin.setValue(int(self.settings.value("sources", 5)))
            self.backend_combo.setCurrentText(self.settings.value("backend", "ollama"))
            self.news_check.setChecked(self.settings.value("news", "false").lower() == "true")
            self.query_edit.setText(self.settings.value("query", ""))
        except Exception:
            pass

    def save_settings(self):
        try:
            self.settings.setValue("depth", self.depth_combo.currentText())
            self.settings.setValue("sources", self.sources_spin.value())
            self.settings.setValue("backend", self.backend_combo.currentText())
            self.settings.setValue("news", str(self.news_check.isChecked()).lower())
            self.settings.setValue("query", self.query_edit.text())
        except Exception:
            pass

    def open_result_at_row(self, row: int, column: int = 0):
        try:
            url_item = self.results_table.item(row, 2)
            if not url_item:
                return
            url = url_item.text().strip()
            if url:
                import webbrowser
                webbrowser.open(url)
        except Exception as e:
            self.log(f"Failed to open URL: {e}")

    def on_results_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        open_act = menu.addAction("Open in browser")
        copy_url_act = menu.addAction("Copy URL")
        copy_both_act = menu.addAction("Copy Title + URL")
        action = menu.exec(self.results_table.mapToGlobal(pos))
        row = self.results_table.currentRow()
        if row < 0:
            return
        title = self.results_table.item(row, 1).text() if self.results_table.item(row, 1) else ""
        url = self.results_table.item(row, 2).text() if self.results_table.item(row, 2) else ""
        if action == open_act:
            self.open_result_at_row(row)
        elif action == copy_url_act:
            QApplication.clipboard().setText(url)
        elif action == copy_both_act:
            QApplication.clipboard().setText(f"{title}\n{url}")

def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
