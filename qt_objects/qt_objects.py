from PyQt5.QtCore import QRectF, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QColor, QPen, QBrush
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
from PyQt5.QtWidgets import QLabel, QGraphicsScene, QGraphicsView, QGraphicsItem
from PyQt5.QtWidgets import QMainWindow, QGraphicsLineItem


class Circle(QGraphicsItem):
    def __init__(self, x, y, diameter, color=None):
        super().__init__()
        self.x = x
        self.y = y
        self.diameter = diameter
        self.setPos(self.x, self.y)

        if color is not None:
            self.color = color
        else:
            self.color = QColor('blue')

        self.prev_x = self.x

        self.setAcceptDrops(True)
        self.setCursor(Qt.OpenHandCursor)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)

    def setColor(self, color):
        self.color = QColor(color)

    def boundingRect(self):
        return QRectF(-self.diameter / 2.0, -self.diameter / 2.0, self.diameter, self.diameter)

    def paint(self, painter, options, widget):
        painter.setPen(QPen(QColor('black')))
        painter.setBrush(self.color)
        painter.drawEllipse(QRectF(-self.diameter / 2.0, -self.diameter / 2.0, self.diameter, self.diameter))


class GraphicScene(QMainWindow):
    def __init__(self, width, height):
        super().__init__()
        self.rect=QRectF(0, 0, width, height)

        self.Scene=QGraphicsScene(self.rect)
        self.View=QGraphicsView()
        self.View.setCacheMode(QGraphicsView.CacheNone)

        self.initScene()
        self.displayUI()

    def initScene(self):
        self.Scene.setBackgroundBrush(QBrush(QColor('yellow'),Qt.SolidPattern))
        self.View.setScene(self.Scene)

    def addItem(self, item):
        self.Scene.addItem(item)
        self.View.setScene(self.Scene)

    def removeItem(self, item):
        self.Scene.removeItem(item)
        self.View.setScene(self.Scene)

    def displayUI(self):
        print('Is scene active', self.Scene.isActive())
        self.setCentralWidget(self.View)
        #self.resize(PAINTABLE_AREA_WIDTH, PAINTABLE_AREA_HEIGHT)
        self.show()
