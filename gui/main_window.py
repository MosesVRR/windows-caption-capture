"""Main window for Windows Caption Capture."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QLineEdit,
)

from capture.history import SessionHistory


class MainWindow(QMainWindow):
    """Main application window for browsing captured sessions."""

    def __init__(self) -> None:
        super().__init__()

        self.history = SessionHistory()
        self.sessions: list[dict] = []
        self.current_session_id: str | None = None
        self.saved_transcript = ""

        self.setWindowTitle("Windows Caption Capture")
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)

        self._build_ui()
        self.refresh_sessions()

    def _build_ui(self) -> None:
        """Create and arrange the main interface."""
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search sessions and transcripts..."
        )
        self.search_input.textChanged.connect(self.filter_sessions)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_sessions)

        self.rename_button = QPushButton("Rename Session")
        self.rename_button.clicked.connect(self.rename_selected_session)

        self.delete_button = QPushButton("Delete Session")
        self.delete_button.clicked.connect(self.delete_selected_session)

        self.session_list = QListWidget()
        self.session_list.currentItemChanged.connect(
            self.on_session_selected
        )

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Recording Sessions"))
        left_layout.addWidget(self.search_input)
        left_layout.addWidget(self.refresh_button)
        left_layout.addWidget(self.rename_button)
        left_layout.addWidget(self.delete_button)
        left_layout.addWidget(self.session_list)

        self.session_title = QLabel("Select a session")
        self.session_title.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )

        self.session_details = QLabel(
            "Choose a recording from the session list."
        )
        self.session_details.setWordWrap(True)

        self.transcript_viewer = QTextEdit()
        self.transcript_viewer.setReadOnly(False)
        self.transcript_viewer.setPlaceholderText(
            "The selected transcript will appear here."
        )
        self.transcript_viewer.textChanged.connect(
            self.update_editor_state
        )

        self.save_button = QPushButton("Save Changes")
        self.save_button.clicked.connect(self.save_transcript)

        self.discard_button = QPushButton("Discard Changes")
        self.discard_button.clicked.connect(self.discard_transcript_changes)

        editor_buttons = QWidget()
        editor_layout = QVBoxLayout(editor_buttons)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self.save_button)
        editor_layout.addWidget(self.discard_button)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(self.session_title)
        right_layout.addWidget(self.session_details)
        right_layout.addWidget(self.transcript_viewer, 1)
        right_layout.addWidget(editor_buttons)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 800])

        self.setCentralWidget(splitter)
        self.statusBar().showMessage("Ready")

        self.update_editor_state()

    def update_editor_state(self) -> None:
        """Enable or disable editor controls according to unsaved changes."""
        has_session = self.current_session_id is not None
        is_dirty = (
            self.transcript_viewer.toPlainText() != self.saved_transcript
        )

        self.save_button.setEnabled(has_session and is_dirty)
        self.discard_button.setEnabled(has_session and is_dirty)

        if has_session and is_dirty:
            self.session_title.setText(
                f"{self._current_session_name()} *"
            )

    def _current_session_name(self) -> str:
        """Return the current session's display name."""
        if not self.current_session_id:
            return "No session selected"

        session = self.history.get_session(self.current_session_id)
        if session is None:
            return self.current_session_id

        return session.get("name") or self.current_session_id

    def confirm_unsaved_changes(self) -> bool:
        """Ask how to handle unsaved changes before switching sessions."""
        current_text = self.transcript_viewer.toPlainText()

        if current_text == self.saved_transcript:
            return True

        answer = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved transcript changes. Save them before "
            "continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if answer == QMessageBox.StandardButton.Save:
            return self.save_transcript()

        if answer == QMessageBox.StandardButton.Discard:
            return True

        return False

    def refresh_sessions(self) -> None:
        """Reload saved sessions from disk."""
        if hasattr(self, "transcript_viewer"):
            if not self.confirm_unsaved_changes():
                return

        previous_id = self.current_session_id
        self.sessions = self.history.list_sessions()

        self.session_list.blockSignals(True)
        self.session_list.clear()

        selected_item = None

        for session in self.sessions:
            session_id = session.get("session_id", "")
            display_name = session.get("name") or session_id

            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, session_id)
            self.session_list.addItem(item)

            if session_id == previous_id:
                selected_item = item

        self.session_list.blockSignals(False)

        if selected_item:
            self.session_list.setCurrentItem(selected_item)
            self.load_session(selected_item)
        elif self.session_list.count():
            self.session_list.setCurrentRow(0)
        else:
            self.current_session_id = None
            self.clear_selected_session()

        self.filter_sessions(self.search_input.text())

        self.statusBar().showMessage(
            f"{len(self.sessions)} saved session(s)"
        )

    def filter_sessions(self, query: str) -> None:
        """Filter the session list by metadata or transcript content."""
        query = query.strip().casefold()
        selected_id = self.current_session_id

        self.session_list.blockSignals(True)
        self.session_list.clear()

        first_match = None
        selected_match = None

        for session in self.sessions:
            session_id = session.get("session_id", "")
            name = session.get("name") or session_id
            started_at = session.get("started_at", "")
            status = session.get("status", "")

            searchable = f"{name} {session_id} {started_at} {status}"
            matches = not query or query in searchable.casefold()

            if query and not matches:
                try:
                    transcript = self.history.read_transcript(session_id)
                    matches = query in transcript.casefold()
                except (OSError, ValueError):
                    matches = False

            if not matches:
                continue

            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, session_id)
            self.session_list.addItem(item)

            if first_match is None:
                first_match = item

            if session_id == selected_id:
                selected_match = item

        self.session_list.blockSignals(False)

        item_to_select = selected_match or first_match

        if item_to_select:
            self.session_list.setCurrentItem(item_to_select)
            if item_to_select.data(Qt.ItemDataRole.UserRole) != selected_id:
                self.load_session(item_to_select)
        else:
            self.current_session_id = None
            self.clear_selected_session()

    def on_session_selected(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None,
    ) -> None:
        """Handle session selection changes safely."""
        if current is None:
            return

        if not self.confirm_unsaved_changes():
            self.session_list.blockSignals(True)
            if previous is not None:
                self.session_list.setCurrentItem(previous)
            self.session_list.blockSignals(False)
            return

        self.load_session(current)

    def load_session(self, item: QListWidgetItem) -> None:
        """Load a session's metadata and transcript."""
        session_id = item.data(Qt.ItemDataRole.UserRole)
        session = self.history.get_session(session_id)

        if session is None:
            self.clear_selected_session()
            return

        try:
            transcript = self.history.read_transcript(session_id)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Unable to open transcript",
                f"Could not read this transcript:\n{exc}",
            )
            return

        self.current_session_id = session_id
        self.saved_transcript = transcript

        self.transcript_viewer.blockSignals(True)
        self.transcript_viewer.setPlainText(transcript)
        self.transcript_viewer.blockSignals(False)

        name = session.get("name") or session_id
        duration = session.get("duration_seconds")

        if duration is None:
            duration_text = "Not available"
        else:
            total_seconds = int(duration)
            minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            duration_text = (
                f"{hours}h {minutes}m {seconds}s"
                if hours
                else f"{minutes}m {seconds}s"
            )

        self.session_title.setText(name)
        self.session_details.setText(
            f"Started: {session.get('started_at', 'Unknown')}\n"
            f"Ended: {session.get('ended_at') or 'In progress'}\n"
            f"Duration: {duration_text}\n"
            f"Status: {session.get('status', 'unknown')}"
        )

        self.update_editor_state()
        self.statusBar().showMessage(f"Opened: {name}")

    def save_transcript(self) -> bool:
        """Save the edited transcript to its session file."""
        if not self.current_session_id:
            return False

        transcript = self.transcript_viewer.toPlainText()

        session = self.history.get_session(self.current_session_id)
        if session is None:
            QMessageBox.warning(
                self,
                "Session not found",
                "The selected session no longer exists.",
            )
            return False

        session_dir = Path(session["_directory"])
        transcript_name = session.get("transcript_file", "transcript.txt")
        transcript_path = session_dir / transcript_name

        try:
            if transcript_path.resolve().parent != session_dir.resolve():
                raise ValueError("Invalid transcript path.")

            transcript_path.write_text(transcript, encoding="utf-8")
        except (OSError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Save failed",
                f"Could not save the transcript:\n{exc}",
            )
            return False

        self.saved_transcript = transcript
        self.update_editor_state()
        self.statusBar().showMessage("Transcript saved successfully")
        return True

    def discard_transcript_changes(self) -> None:
        """Restore the last saved transcript."""
        self.transcript_viewer.blockSignals(True)
        self.transcript_viewer.setPlainText(self.saved_transcript)
        self.transcript_viewer.blockSignals(False)
        self.update_editor_state()

        self.statusBar().showMessage("Unsaved changes discarded")

    def rename_selected_session(self) -> None:
        """Rename the currently selected session."""
        item = self.session_list.currentItem()

        if item is None:
            QMessageBox.information(
                self,
                "No session selected",
                "Select a session before renaming it.",
            )
            return

        if not self.confirm_unsaved_changes():
            return

        session_id = item.data(Qt.ItemDataRole.UserRole)
        session = self.history.get_session(session_id)

        if session is None:
            QMessageBox.warning(
                self,
                "Session not found",
                "This session could not be found. Try refreshing the list.",
            )
            return

        current_name = session.get("name") or session_id
        new_name, accepted = QInputDialog.getText(
            self,
            "Rename Session",
            "Enter a name for this recording:",
            QLineEdit.EchoMode.Normal,
            current_name,
        )

        if not accepted:
            return

        new_name = new_name.strip()

        if not new_name:
            QMessageBox.warning(
                self,
                "Invalid name",
                "The session name cannot be empty.",
            )
            return

        try:
            self.history.rename_session(session_id, new_name)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Rename failed",
                f"Could not rename this session:\n{exc}",
            )
            return

        self.refresh_sessions()
        self.statusBar().showMessage(f"Session renamed to: {new_name}")

    def delete_selected_session(self) -> None:
        """Delete the selected session after explicit confirmation."""
        item = self.session_list.currentItem()

        if item is None:
            QMessageBox.information(
                self,
                "No session selected",
                "Select a session before deleting it.",
            )
            return

        if not self.confirm_unsaved_changes():
            return

        session_id = item.data(Qt.ItemDataRole.UserRole)
        session = self.history.get_session(session_id)

        if session is None:
            QMessageBox.warning(
                self,
                "Session not found",
                "This session could not be found. Try refreshing the list.",
            )
            return

        session_name = session.get("name") or session_id

        answer = QMessageBox.question(
            self,
            "Delete Session",
            f"Permanently delete '{session_name}' and all its files?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.history.delete_session(session_id)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Delete failed",
                f"Could not delete this session:\n{exc}",
            )
            return

        # Clear the deleted session before refreshing the list.
        self.session_list.blockSignals(True)
        self.session_list.clearSelection()
        self.session_list.setCurrentRow(-1)
        self.session_list.blockSignals(False)

        self.clear_selected_session()
        self.refresh_sessions()
        self.statusBar().showMessage(f"Deleted session: {session_name}")

    def clear_selected_session(self) -> None:
        """Clear the transcript panel when no session is selected."""
        self.current_session_id = None
        self.saved_transcript = ""

        self.transcript_viewer.blockSignals(True)
        self.transcript_viewer.clear()
        self.transcript_viewer.blockSignals(False)

        self.session_title.setText("No session selected")
        self.session_details.setText(
            "Select a recording from the session list."
        )

        self.update_editor_state()

    def closeEvent(self, event) -> None:
        """Prevent closing with unsaved changes without confirmation."""
        if self.confirm_unsaved_changes():
            event.accept()
        else:
            event.ignore()
