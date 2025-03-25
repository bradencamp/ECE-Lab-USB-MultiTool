"""
aesthetic.py

This module provides functions to apply aesthetic styles to the PyQt6 application.
It includes functionalities to set a dark mode stylesheet and configure the application icon.
"""

import os
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication


def get_icon() -> QIcon:
    """
    Retrieves the application's icon.

    Constructs the path to the icon image relative to the current file's directory
    and returns a QIcon object.

    Returns:
        QIcon: The icon object to be used as the application icon.
    """
    # Construct the icon path relative to this file
    icon_path = os.path.join(os.path.dirname(__file__), 'images', 'logo.png')
    return QIcon(icon_path)


def apply_styles(app: QApplication) -> None:
    """
    Applies aesthetic styles to the PyQt6 application.

    This function sets a dark mode stylesheet for the entire application and
    configures the application's window icon.

    Args:
        app (QApplication): The PyQt6 application instance to style.
    """
    # Dark mode stylesheet
    dark_style = """
    QWidget {
        background-color: #2e2e2e;
        color: #ffffff;
    }
    QPushButton {
        background-color: #3c3c3c;
        color: #ffffff;
        border: 1px solid #555;
        border-radius: 5px;
        padding: 5px;
    }
    QPushButton:checked {
        background-color: #4d4d4d;
    }
    QPushButton:hover {
        background-color: #4d4d4d;
    }
    QComboBox {
        background-color: #3c3c3c;
        color: #ffffff;
        border: 1px solid #555;
        padding: 5px;
    }
    QComboBox QAbstractItemView {
        background-color: #3c3c3c;
        color: #ffffff;
        selection-background-color: #4d4d4d;
    }
    QLineEdit {
        background-color: #3c3c3c;
        color: #ffffff;
        border: 1px solid #555;
        padding: 5px;
    }
    QMenu {
        background-color: #3c3c3c;
        color: #ffffff;
        border: 1px solid #555;
    }
    QMenu::item:selected {
        background-color: #4d4d4d;
    }
    """
    # Apply the stylesheet
    app.setStyleSheet(dark_style)

    # Set the application icon
    app.setWindowIcon(get_icon())
