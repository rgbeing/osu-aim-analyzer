from PyQt6.QtWidgets import QLineEdit

class DroppableQLineEdit(QLineEdit):
    def __init__(self, parent):
        super(QLineEdit, self).__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            self.setText(f)
