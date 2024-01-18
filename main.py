import sys
import pyautogui
from pynput.mouse import Listener as MouseListener
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QPushButton, QLineEdit, QHBoxLayout, QLabel, \
    QListWidget, QWidget, QComboBox, QProgressBar, QMessageBox


class AutomationThread(QThread):
    update_progress = pyqtSignal(int)
    update_loop_indicator = pyqtSignal(int, int)
    automation_completed = pyqtSignal()

    def __init__(self, commands, num_loops):
        super().__init__()
        self.commands = commands
        self.num_loops = num_loops
        self.paused = False
        self.running = True
        self.current_loop = 0

    def run(self):
        try:
            for self.current_loop in range(1, self.num_loops + 1):
                for command in self.commands:
                    position, interval, action, *extra_data = command
                    text = extra_data[0] if extra_data else ""

                    while self.paused or not self.running:
                        if not self.running:
                            return
                        QThread.msleep(100)

                    if action == 'click':
                        pyautogui.click(position)
                    elif action == '2click':
                        pyautogui.doubleClick(position)
                    elif action == 'right click':
                        pyautogui.rightClick(position)
                    elif action == 'copy':
                        pyautogui.hotkey('ctrl', 'c')
                    elif action == 'paste':
                        pyautogui.hotkey('ctrl', 'v')
                    elif action == 'enter':
                        pyautogui.press('enter')
                    elif action == 'close tab':
                        pyautogui.hotkey('ctrl', 'w')
                    elif action == 'select all':
                        pyautogui.hotkey('ctrl', 'a')
                    elif action == 'text':
                        pyautogui.typewrite(text)
                    elif action == 'move up':
                        pyautogui.press('up')
                    elif action == 'move down':
                        pyautogui.press('down')
                    elif action == 'move left':
                        pyautogui.press('left')
                    elif action == 'move right':
                        pyautogui.press('right')
                    elif action == 'go to end':
                        pyautogui.hotkey('end')
                    elif action == 'go to beginning':
                        pyautogui.hotkey('home')
                    elif action == 'backspace':
                        pyautogui.press('backspace')
                    elif action == 'none':
                        pyautogui.moveTo(position)

                    QThread.msleep(int(interval * 1000))
                    if not self.running:
                        return

                self.update_progress.emit(int(self.current_loop / self.num_loops * 100))
                self.update_loop_indicator.emit(self.current_loop, self.num_loops)

            self.automation_completed.emit()

        except Exception as e:
            print(f"Error during automation: {e}")

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.running = False
        while self.isRunning():
            QThread.msleep(100)

class ClickAutomationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.paused = False  # Initialize paused attribute

        self.commands = []
        self.num_loops = 0
        self.running = False
        self.automation_thread = None
        self.positionMessageShown = False  # Add this line
        self.mouse_listener = None

        self.estimated_time_timer = QTimer(self)
        self.estimated_time_timer.timeout.connect(self.updateEstimatedTime)
        self.estimated_time_seconds = 0

    def initUI(self):
        # Main layout
        self.layout = QVBoxLayout()
        layout = QVBoxLayout()

        self.setFixedWidth(313)
        self.setFixedHeight(313)

        # Row for position input
        self.position_input = QLineEdit(self)
        self.get_position_button = QPushButton('Get Position', self)
        self.get_position_button.clicked.connect(self.getPosition)

        position_layout = QHBoxLayout()
        position_layout.addWidget(self.position_input)
        position_layout.addWidget(self.get_position_button)

        # Row for interval input
        self.interval_input = QLineEdit(self)
        self.interval_label = QLabel('Interval')
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(self.interval_label)
        interval_layout.addWidget(self.interval_input)

        # Row for number of loops input
        self.num_loops_input = QLineEdit(self)
        self.loops_label = QLabel('Number of loops')
        loops_layout = QHBoxLayout()
        loops_layout.addWidget(self.loops_label)
        loops_layout.addWidget(self.num_loops_input)

        # Add More and Start buttons
        self.add_more_button = QPushButton('Add', self)
        self.add_more_button.clicked.connect(self.addMore)

        # Start button
        self.start_button = QPushButton('Start', self)
        self.start_button.clicked.connect(self.startAutomation)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.add_more_button)
        buttons_layout.addWidget(self.start_button)

        # List to display commands
        self.command_list = QListWidget(self)

        # Action dropdown list
        self.action_dropdown = QComboBox(self)
        self.action_dropdown.addItems(["None", "Click", "2Click", "Right Click",
                                       "Copy", "Paste", "Enter", "Close Tab",
                                       "Select All", "Text", "Move Up", "Move Down",
                                       "Move Left", "Move Right", "Go to End",
                                       "Go to Beginning", "Backspace"])
        self.action_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #424242; /* Dark gray background */
                color: #EEEEEE; /* Light gray text */
                border: 1px solid #555555; /* Gray border */
                min-height: 18px; /* Minimum height */
                min-width: 240px; /* Minimum width */
            }

            QComboBox::drop-down {
                background: #424242;
                border: none;
            }

            QComboBox QAbstractItemView {
                background-color: #424242; /* Background color for the dropdown list */
                selection-background-color: #333333; /* Slightly darker color for selected item */
            }
        """)
        # self.action_dropdown.currentIndexChanged.connect(self.handleActionChange)

        action_layout = QHBoxLayout()
        action_label = QLabel('Action', self)
        action_layout.addWidget(action_label)
        action_layout.addWidget(self.action_dropdown)  # Add the ComboBox to the action layout

        self.text_input = QLineEdit(self)
        self.text_label = QLabel('Text')
        text_layout = QHBoxLayout()
        text_layout.addWidget(self.text_label)
        text_layout.addWidget(self.text_input)

        self.action_dropdown.currentIndexChanged.connect(self.onTextAction)
        self.onTextAction(self.action_dropdown.currentIndex())

        # Add all rows to main layout
        layout.addLayout(position_layout)
        layout.addLayout(interval_layout)
        layout.addLayout(loops_layout)
        layout.addLayout(action_layout)
        layout.addLayout(text_layout)
        layout.addWidget(self.command_list)
        layout.addLayout(buttons_layout)

        self.control_buttons_layout = QHBoxLayout()  # New horizontal layout for control buttons

        self.pause_resume_button = QPushButton('Pause', self)
        self.pause_resume_button.clicked.connect(self.togglePauseResume)
        self.pause_resume_button.hide()
        self.control_buttons_layout.addWidget(self.pause_resume_button)

        self.stop_button = QPushButton('Stop', self)  # New stop button
        self.stop_button.clicked.connect(self.stopAutomation)
        self.stop_button.hide()
        self.control_buttons_layout.addWidget(self.stop_button)

        layout.addLayout(self.control_buttons_layout)

        # Loop indicator and Estimated Time layout11
        status_layout = QHBoxLayout()
        self.loop_indicator_label = QLabel('Loop: 0/0', self)
        self.loop_indicator_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.loop_indicator_label.hide()

        self.estimated_time_label = QLabel('Estimated Time: 00:00:00', self)
        self.estimated_time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.estimated_time_label.hide()

        status_layout.addWidget(self.loop_indicator_label)
        status_layout.addStretch()
        status_layout.addWidget(self.estimated_time_label)

        # Add status_layout above the progress bar
        layout.addLayout(status_layout)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Create Edit and Remove buttons but hide them initially
        self.edit_button = QPushButton('Edit', self)
        self.edit_button.clicked.connect(self.editCommand)
        self.edit_button.hide()

        self.remove_button = QPushButton('Remove', self)
        self.remove_button.clicked.connect(self.removeCommand)
        self.remove_button.hide()

        self.back_button = QPushButton('Back', self)
        self.back_button.clicked.connect(self.onBackClicked)
        self.back_button.hide()

        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.remove_button)
        buttons_layout.addWidget(self.back_button)

        # Setting up keyboard shortcut for pause/resume
        self.pause_resume_shortcut = QShortcut(QKeySequence('P'), self)

        # Reset button
        self.reset_button = QPushButton('Reset', self)
        self.reset_button.clicked.connect(self.resetList)

        # Add the reset button to the buttons layout
        buttons_layout.addWidget(self.reset_button)

        self.setLayout(layout)
        self.setWindowTitle('Clicker')

        # Connect item clicked signal
        self.command_list.itemClicked.connect(self.onCommandSelected)
        self.command_list.itemSelectionChanged.connect(self.resetUIState)

    @pyqtSlot()
    def addMore(self):
        try:
            # Extract position, interval and action.
            position = tuple(map(int, self.position_input.text().split(',')))
            interval = float(self.interval_input.text())
            action = self.action_dropdown.currentText().lower()

            # Special handling for 'Text' action
            if action == 'text':
                text = self.text_input.text()
                # Append command details to the list
                self.commands.append((position, interval, action, text))
            else:
                # Append command details to the list
                self.commands.append((position, interval, action))

            self.command_list.addItem(f'Action: {action}, Interval: {interval}s')

            # Disable number of loops input after the first command is added
            if len(self.commands) == 1:
                self.num_loops_input.setDisabled(True)

            # Clear the input fields
            self.text_input.clear()

        except ValueError as e:
            # Handle errors like incorrect data formats
            print("Error adding command:", e)

    def onCommandSelected(self, item):
        if item:
            self.add_more_button.hide()
            self.start_button.hide()
            self.reset_button.hide()

            self.edit_button.show()
            self.remove_button.show()
            self.back_button.show()
        else:
            self.resetUIAfterEditOrRemove()

    def editCommand(self):
        selected_item = self.command_list.currentItem()
        if selected_item:
            index = self.command_list.row(selected_item)
            position, interval, action, *extra = self.commands[index]

            self.position_input.setText(f'{position[0]}, {position[1]}')
            self.interval_input.setText(str(interval))
            self.action_dropdown.setCurrentText(action.capitalize())

            if action == 'text':
                self.text_input.setText(extra[0])

            self.add_more_button.setText('Update')
            self.add_more_button.clicked.disconnect()
            self.add_more_button.clicked.connect(lambda: self.updateCommand(index))

            self.reset_button.setText('Cancel')
            self.reset_button.clicked.disconnect()
            self.reset_button.clicked.connect(self.cancelEdit)

            self.edit_button.hide()
            self.start_button.hide()
            self.add_more_button.show()
            self.reset_button.show()
            self.remove_button.hide()
            self.back_button.hide()

            self.num_loops_input.setEnabled(index == 0)

    def removeCommand(self):
        selected_item = self.command_list.currentItem()
        if selected_item:
            index = self.command_list.row(selected_item)
            del self.commands[index]
            self.command_list.takeItem(index)
            self.resetUIAfterEditOrRemove()

            if len(self.commands) == 0:
                self.num_loops_input.setEnabled(True)

    def onBackClicked(self):
        self.command_list.clearSelection()
        self.resetUIState()
        self.back_button.hide()

    def updateCommand(self, index):
        try:
            position = tuple(map(int, self.position_input.text().split(',')))
            interval = float(self.interval_input.text())
            action = self.action_dropdown.currentText().lower()
            text = self.text_input.text() if action == 'text' else ''

            self.commands[index] = (position, interval, action, text) if action == 'text' else (position, interval, action)
            self.command_list.item(index).setText(f'Action: {action}, Interval: {interval}s')

            self.resetUIAfterEditOrRemove()

            if index == 0 and len(self.commands) > 1:
                self.num_loops_input.setDisabled(True)

        except ValueError as e:
            print("Error updating command:", e)

    def cancelEdit(self):
        self.resetUIAfterEditOrRemove()
        if len(self.commands) == 1:
            self.num_loops_input.setDisabled(True)

    def resetUIState(self):
        if not self.command_list.selectedItems():

            self.add_more_button.setText('Add')
            self.add_more_button.clicked.disconnect()
            self.add_more_button.clicked.connect(self.addMore)
            self.add_more_button.show()

            self.start_button.show()

            self.reset_button.setText('Reset')
            self.reset_button.clicked.disconnect()
            self.reset_button.clicked.connect(self.resetList)
            self.reset_button.show()

            self.edit_button.hide()
            self.remove_button.hide()
            self.back_button.hide()

    def resetUIAfterEditOrRemove(self):
        # Reset the button text and connections
        self.add_more_button.setText('Add')
        self.add_more_button.clicked.disconnect()
        self.add_more_button.clicked.connect(self.addMore)
        self.add_more_button.show()

        self.reset_button.setText('Reset')
        self.reset_button.clicked.disconnect()
        self.reset_button.clicked.connect(self.resetList)
        self.reset_button.show()

        self.start_button.show()

        self.edit_button.hide()
        self.remove_button.hide()
        self.back_button.hide()

        if len(self.commands) == 1:
            self.num_loops_input.setDisabled(True)
        else:
            self.num_loops_input.setEnabled(True)

        self.position_input.clear()
        self.interval_input.clear()

    def resetList(self):
        # Code to reset the entire command list
        self.commands.clear()
        self.command_list.clear()
        self.resetUIState()
        self.num_loops_input.setEnabled(True)

    @pyqtSlot()
    def getPosition(self):
        if not self.positionMessageShown:
            QMessageBox.information(self, 'Get Position',
                                    'Move your cursor to the desired position. The position will be captured in 3 seconds.')
            self.positionMessageShown = True  # Set the flag to True after showing the message
        QTimer.singleShot(3000, self.capturePosition)

    def capturePosition(self):
        x, y = pyautogui.position()
        self.position_input.setText(f'{x}, {y}')

    def onTextAction(self, index):
        # Enable the text input if "Text" is selected, disable otherwise
        selected_action = self.action_dropdown.currentText()
        if selected_action == "Text":
            self.text_input.setEnabled(True)
        else:
            self.text_input.setEnabled(False)
            self.text_input.clear()

    @pyqtSlot()
    def startAutomation(self):
        if self.running:
            QMessageBox.information(self, 'Already running', 'Automation is already running.')
            return
        elif not self.commands:
            QMessageBox.warning(self, 'No commands', 'Please add at least one command before starting.')
            return

        try:
            self.num_loops = int(self.num_loops_input.text())
        except ValueError:
            QMessageBox.warning(self, 'Invalid Input', 'Please enter a valid number of loops.')
            return

        # Reset the progress bar to 0
        self.updateProgressBar(0)

        # Initialize loop indicator
        self.updateLoopIndicator(0, self.num_loops)

        # Calculate and set the estimated time
        self.calculate_total_estimated_time()
        self.displayEstimatedTime(self.estimated_time_seconds)

        # Start the timer for the estimated time
        self.estimated_time_timer.start(1000)

        self.running = True
        self.startMouseListener()
        self.automation_thread = AutomationThread(self.commands, self.num_loops)
        self.automation_thread.update_progress.connect(self.updateProgressBar)
        self.automation_thread.update_loop_indicator.connect(self.updateLoopIndicator)
        self.automation_thread.automation_completed.connect(self.onAutomationCompleted)

        self.automation_thread.start()
        self.AutomationState(True)

    def AutomationState(self, is_running):
        # Enable or disable UI elements based on the running state
        self.get_position_button.setEnabled(not is_running)
        self.command_list.setEnabled(not is_running)
        self.position_input.setEnabled(not is_running)
        self.interval_input.setEnabled(not is_running)
        self.action_dropdown.setEnabled(not is_running)
        self.text_input.setEnabled(not is_running)

        # Show or hide buttons based on whether automation is running
        self.add_more_button.setVisible(not is_running)
        self.start_button.setVisible(not is_running)
        self.reset_button.setVisible(not is_running)

        self.pause_resume_button.setVisible(is_running)
        self.stop_button.setVisible(is_running)
        self.progress_bar.setVisible(is_running)
        self.loop_indicator_label.setVisible(is_running)
        self.estimated_time_label.setVisible(is_running)

    @pyqtSlot()
    def stopAutomation(self):
        if self.automation_thread and self.automation_thread.isRunning():
            current_loop = self.automation_thread.current_loop
            remaining_loops = self.num_loops - current_loop + 1
            self.num_loops = max(0, remaining_loops)
            self.num_loops_input.setText(str(self.num_loops))
            self.automation_thread.stop()
            while self.automation_thread.isRunning():
                QApplication.processEvents()

            # Reset loop indicator
            self.updateLoopIndicator(0, self.num_loops)

            # Stop the estimated time timer
            self.estimated_time_timer.stop()
            self.estimated_time_seconds = 0
            self.displayEstimatedTime(self.estimated_time_seconds)

            self.running = False
            self.AutomationState(False)
            self.updateProgressBar(0)
            self.loop_indicator_label.hide()
            self.pause_resume_button.setText('Pause')
            self.paused = False
            self.pause_resume_button.hide()
            self.stop_button.hide()
            self.progress_bar.hide()
            self.estimated_time_label.hide()

            # Show the elements that were hidden during processing
            self.position_input.show()
            self.get_position_button.show()
            self.interval_input.show()
            self.interval_label.show()
            self.num_loops_input.show()
            self.add_more_button.show()
            self.start_button.show()
            self.reset_button.show()
            self.command_list.show()

            # Disable the number of loops input if there are commands
            if len(self.commands) > 0:
                self.num_loops_input.setDisabled(True)


    @pyqtSlot()
    def togglePauseResume(self):
        if self.paused:
            # Resuming the automation
            self.automation_thread.resume()
            self.estimated_time_timer.start(1000)  # Resume the estimated time countdown, if you are using one
            self.pause_resume_button.setText('Pause')
            self.paused = False

            # Restart the mouse listener
            if not self.mouse_listener:
                self.mouse_listener = MouseListener(on_move=self.on_mouse_move)
                self.mouse_listener.start()
        else:
            # Pausing the automation
            self.automation_thread.pause()
            self.estimated_time_timer.stop()  # Pause the estimated time countdown, if you are using one
            self.pause_resume_button.setText('Resume')
            self.paused = True

            # Stop the mouse listener
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None

    def startMouseListener(self):
        # Start listening for mouse movements
        self.mouse_listener = MouseListener(on_move=self.on_mouse_move)
        self.mouse_listener.start()

    def on_mouse_move(self, x, y):
        # Pause the automation when mouse movement is detected
        if self.running and not self.paused:
            self.togglePauseResume()

    def updateProgressBar(self, progress):
        self.progress_bar.setValue(progress)

    def updateLoopIndicator(self, current_loop, total_loops):
        self.loop_indicator_label.setText(f'Loop: {current_loop}/{total_loops}')

    def calculate_total_estimated_time(self):
        total_interval = sum(command[1] for command in self.commands)
        self.estimated_time_seconds = total_interval * self.num_loops

    def displayEstimatedTime(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        self.estimated_time_label.setText(f'Estimated Time: {time_str}')

    def updateEstimatedTime(self):
        if self.estimated_time_seconds > 0:
            self.estimated_time_seconds -= 1
            self.displayEstimatedTime(self.estimated_time_seconds)

    def onAutomationCompleted(self):
        self.running = False
        self.AutomationState(False)
        QMessageBox.information(self, 'Completed', 'Automation completed.')


def main():
    app = QApplication(sys.argv)

    # Set the global stylesheet for the application
    app.setStyleSheet("""
    QWidget {
        background-color: #323232;
        color: #EEEEEE;
    }
    QLineEdit, QListWidget {
        background-color: #424242;
        border: 1px solid #555555;
    }
    QPushButton {
        background-color: #EEEEEE;
        color: #000000;
    }
    """)

    ex = ClickAutomationApp()
    ex.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

