import contextlib, os

from PySide6 import QtGui, QtWidgets

from .qt_icon import IMG_DIR


class IntLineEdit(QtWidgets.QLineEdit):
    # region IntLineEdit
    def __init__(self, min: int = 0, max: int = 1000000, *args, **kwargs) -> None:
        """Integer-only line edit widget

        Args:
            min (int, optional): Smallest allowable value. Defaults to 0.
            max (int, optional): Highest allowable value. Defaults to 1000000.
        """
        super().__init__(*args, **kwargs)
        self.setValidator(QtGui.QIntValidator(min, max))
    
    def text_int(self) -> int:
        """Returns the content of the IntLineEdit widget as an integer.
        """
        return int(super().text())


class FloatLineEdit(QtWidgets.QLineEdit):
    # region FloatLineEdit
    def __init__(self, bottom: float = 0.00, top: float = 100.00, decimals: int = 2, *args, **kwargs) -> None:
        """Float-only line edit widget

        Args:
            bottom (float, optional): Minimum acceptable value. Defaults to 0.00.
            top (float, optional): Maximum acceptable value. Defaults to 100.00.
            decimals (int, optional): Maximum number of digits after the decimal point. Defaults to 2.
        """
        super().__init__(*args, **kwargs)
        self.setValidator(QtGui.QDoubleValidator(bottom, top, decimals))

    def text_float(self) -> float:
        """Returns the content of the FloatLineEdit widget as an float.
        """
        return float(super().text())
    

class DisplayLineEdit(QtWidgets.QLineEdit):
    # region DisplayLineEdit
    def __init__(self, *args, round_digits: int = 4, **kwargs) -> None:
        """Initializes a read-only line edit with a specified number of decimal places for rounding.
        Applies a grayish background color and limits maximum width.

        Args:
            round_digits (int, optional): The number of decimal places to round to. Defaults to 4.
        """

        super().__init__(*args, **kwargs)

        self.round_digits = round_digits

        self.setReadOnly(True)
        self.setStyleSheet("background-color: rgb(220, 220, 220)")
        self.setMaximumWidth(100)

    def setText(self, arg__1: str) -> None:
        """Sets the text of the widget, rounding incoming float values if specified.
        This method checks if rounding is enabled and, if so, rounds the input value to the specified number of decimal places before converting it to a string. It then calls the superclass method to set the text of the widget.

        Args:
            arg__1 (str): The text to be set as the widget's text.
        """
        if self.round_digits is not None: # round incoming float values
            with contextlib.suppress(ValueError):
                arg__1 = str(round(float(arg__1), self.round_digits))

        return super().setText(arg__1)


class StatusLabel(QtWidgets.QWidget):
    # region StatusLabel
    def __init__(self, text: str):
        """Initializes a widget that displays an icon and a text label.
        This constructor creates a horizontal layout for the widget, adds an icon with a fixed width, and includes a text label. The health status of the icon is initialized to False.

        Args:
            text (str): The text to be displayed in the label.
        """
        super().__init__()

        # create a horizontal layout
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # create a label for the icon
        self.icon = QtWidgets.QLabel()
        self.icon.setFixedWidth(20)
        layout.addWidget(self.icon)
        self.set_health(False)

        # add text label
        layout.addWidget(QtWidgets.QLabel(text))

    def set_health(self, healthy: bool) -> None:
        """Sets the health state of the status label.
        This method updates the icon displayed in the status label based on the health state provided. If the state is healthy, a green icon is shown; otherwise, a red icon is displayed.

        Args:
            healthy (bool): Indicates whether the status is healthy (True) or not (False).
        """
        if healthy:
            self.icon.setPixmap(QtGui.QPixmap(os.path.join(IMG_DIR, "green.png")))
        else:
            self.icon.setPixmap(QtGui.QPixmap(os.path.join(IMG_DIR, "red.png")))
