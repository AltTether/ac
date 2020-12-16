import sys
import time
import math
from threading import Thread
from collections import namedtuple

import pulsectl
from pulsectl.pulsectl import PulseOperationFailed

from PyQt5.QtCore import QRectF, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QColor, QPen, QBrush
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
from PyQt5.QtWidgets import QLabel, QGraphicsScene, QGraphicsView, QGraphicsItem
from PyQt5.QtWidgets import QMainWindow, QGraphicsLineItem


CIRCLE_DIAMETER = 30
PAINTABLE_AREA_HEIGHT = 500
PAINTABLE_AREA_WIDTH = 500
PAINTABLE_AREA_PADDING_SIZE = 100

SEC_PER_NOTIFICATION = 0.1

HEARABLE_DISTANCE = 200

def calculate_distance(pos1, pos2):
    return math.sqrt((pos2.x - pos1.x)**2 + \
                     (pos2.y - pos1.y)**2)

class App():
    def __init__(self):
        self.qapp = QApplication(sys.argv)

        self.m = MyGraphicScene()

        master_node = MasterNode(Pos(x=PAINTABLE_AREA_WIDTH / 2,
                                     y=PAINTABLE_AREA_HEIGHT / 2),
                                      CIRCLE_DIAMETER,
                                      None, None, QColor('red'))

        self.audio_controller = AudioController(master_node)

        self.m.addItem(master_node.get_qgraphics_item())

        self.pulse = pulsectl.Pulse('volume-controller')
        for sink_input in self.pulse.sink_input_list():
            pos = Pos(x=100, y=100)
            input_node = InputNode(Pos(x=100, y=100),
                                   CIRCLE_DIAMETER,
                                   self.pulse, sink_input)

            self.audio_controller.register_input_node(input_node)
            self.m.addItem(input_node.get_qgraphics_item())

    def run(self):
        th = Thread(target=self.audio_controller.run)
        th.start()
        
        sys.exit(self.qapp.exec_())

        th.join()
        self.pulse.close()

class AudioController():
    def __init__(self, master_node):
        self.notifier = StateNotifier()

        self.master_node = master_node
        self.notifier.register_node(master_node)
        
        self.input_nodes = dict()

    def register_input_node(self, input_node):
        self.input_nodes[input_node.get_index()] = input_node
        self.notifier.register_node(input_node)

    def unregister_input_node(self, input_node):
        del self.input_nodes[input_node.get_index()]
        self.notifier.unregister_node(input_node)

    def change_volume_by_distance(self, master_node, input_node):
        distance = calculate_distance(master_node.get_pos(),
                                      input_node.get_pos())

        print(master_node.get_pos())
        print(input_node.get_pos())
        print(distance)
        volume = 0.0
        if distance >= HEARABLE_DISTANCE:
            volume = 0.0
        else:
            volume = 1.0 - (1.0 * (distance / HEARABLE_DISTANCE))

        return input_node.set_volume(volume)

    def run(self):
        for node in self.notifier.run():
            if isinstance(node, MasterNode):
                input_nodes = self.input_nodes.values()

            else:
                input_nodes = [node]

            for input_node in input_nodes:
                is_suceed = self.change_volume_by_distance(self.master_node,
                                                           input_node)
                if not is_suceed:
                    self.unregister_input_node(input_node)

class Pos(namedtuple('Pos', ['x', 'y'])):
    pass


class Node():
    # xとyは中心座標
    def __init__(self, pos, diameter, pulse, sink_input, color=None):
        self.diameter = diameter
        self.qgraphics_item = Circle(pos.x - diameter / 2,
                                     pos.y - diameter / 2,
                                     diameter, color)
        self.sink_input = sink_input
        self.pulse = pulse

    def get_id(self):
        pass

    def get_pos(self):
        qpos = self.qgraphics_item.pos()
        return Pos(qpos.x() + self.diameter / 2,
                   qpos.y() + self.diameter / 2)

    def get_qgraphics_item(self):
        return self.qgraphics_item


class InputNode(Node):
    def __init__(self, *args, **kwargs):
        super(InputNode, self).__init__(*args, **kwargs)

    def set_volume(self, value):
        volume = self.sink_input.volume
        volume.value_flat = value
        try:
            self.pulse.sink_input_volume_set(self.get_index(),
                                             volume)
            return True

        except PulseOperationFailed:
            return False

    def get_volume(self):
        return self.sink_input.volume

    def get_id(self):
        return self.sink_input.index

    def get_index(self):
        return self.sink_input.index


class MasterNode(Node):
    def __init__(self, *args, **kwargs):
        super(MasterNode, self).__init__(*args, **kwargs)

    def get_id(self):
        return -1

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


class MyGraphicScene(QMainWindow):
    def __init__(self):
        super().__init__()
        self.rect=QRectF(0, 0,
                         PAINTABLE_AREA_WIDTH+PAINTABLE_AREA_PADDING_SIZE,
                         PAINTABLE_AREA_HEIGHT+PAINTABLE_AREA_PADDING_SIZE)

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
        self.resize(PAINTABLE_AREA_WIDTH, PAINTABLE_AREA_HEIGHT)
        self.show()


class StateNotifier():
    def __init__(self):
        self.nodes = dict()
        self.prev_poses = dict()

    def register_node(self, node):
        self.nodes[node.get_id()] = node
        self.prev_poses[node.get_id()] = node.get_pos()

    def unregister_node(self, node):
        del self.nodes[node.get_id()]

    def run(self):
        while True:
            for node, prev_pos in zip(self.nodes.values(), self.prev_poses.values()):
                pos = node.get_pos()
                if prev_pos != pos:
                    self.prev_poses[node.get_id()] = pos
                    yield node
            time.sleep(SEC_PER_NOTIFICATION)


def main():
    app = App()
    app.run()

if __name__ == '__main__':
    main()
