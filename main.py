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


from qt_objects import Circle, GraphicScene


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

        self.m = GraphicScene(PAINTABLE_AREA_WIDTH+PAINTABLE_AREA_PADDING_SIZE,
                              PAINTABLE_AREA_HEIGHT+PAINTABLE_AREA_PADDING_SIZE)

        master_node = MasterNode(Pos(x=PAINTABLE_AREA_WIDTH / 2,
                                     y=PAINTABLE_AREA_HEIGHT / 2),
                                      CIRCLE_DIAMETER,
                                      None, None, QColor('red'))

        self.node_pool = NodePool()
        self.m.addItem(master_node.get_qgraphics_item())
        self.node_pool.register_node(master_node)

        self.pulse = pulsectl.Pulse('volume-controller')
        for sink_input in self.pulse.sink_input_list():
            input_node = InputNode(Pos(x=100, y=100),
                                   CIRCLE_DIAMETER,
                                   self.pulse, sink_input)

            self.node_pool.register_node(input_node)
            self.m.addItem(input_node.get_qgraphics_item())

        self.audio_controller = AudioController(master_node,
                                                self.node_pool)

    def run(self):
        th = Thread(target=self.audio_controller.run)
        th.start()
        
        sys.exit(self.qapp.exec_())

        th.join()
        self.pulse.close()

class AudioController():
    def __init__(self, master_node, node_pool):
        self.node_pool = node_pool
        self.notifier = StateNotifier(node_pool)

        self.master_node = master_node

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
                input_nodes = list(filter(lambda x: isinstance(x, InputNode),
                                          self.node_pool.get_nodes()))

            else:
                input_nodes = [node]

            for input_node in input_nodes:
                _ = self.change_volume_by_distance(self.master_node,
                                                   input_node)
                    

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

        qpos = self.qgraphics_item.pos()
        self.prev_pos = Pos(qpos.x() + self.diameter / 2,
                            qpos.y() + self.diameter / 2)

    def get_id(self):
        pass

    # Don't Update Pos
    def get_pos(self):
        return self._get_current_pos_from_current_qpos()

    # Don't Update Pos
    def _get_current_pos_from_current_qpos(self):
        qpos = self.qgraphics_item.pos()
        return Pos(qpos.x() + self.diameter / 2,
                   qpos.y() + self.diameter / 2)

    def is_moved(self):
        curr_pos = self._get_current_pos_from_current_qpos()
        result = not((curr_pos.x == self.prev_pos.x) and \
            (curr_pos.y == self.prev_pos.y))
        self.prev_pos = curr_pos

        return result

    def get_qgraphics_item(self):
        return self.qgraphics_item


class InputNode(Node):
    def __init__(self, *args, **kwargs):
        super(InputNode, self).__init__(*args, **kwargs)

    def set_volume(self, value):
        volume = self.sink_input.volume
        volume.value_flat = value
        try:
            self.pulse.sink_input_volume_set(self.get_id(),
                                             volume)
            return True

        except PulseOperationFailed:
            return False

    def get_volume(self):
        return self.sink_input.volume

    def get_id(self):
        return self.sink_input.index


class MasterNode(Node):
    def __init__(self, *args, **kwargs):
        super(MasterNode, self).__init__(*args, **kwargs)

    def get_id(self):
        return -1


class StateNotifier():
    def __init__(self, node_pool):
        self.node_pool = node_pool

    def run(self):
        while True:
            for node in self.node_pool.get_nodes():
                if node.is_moved():
                    yield node
            time.sleep(SEC_PER_NOTIFICATION)


class NodePool():
    def __init__(self):
        self.nodes = dict()

    def register_node(self, node):
        self.nodes[node.get_id()] = node

    def unregister_node(self, node):
        del self.nodes[node.get_id()]

    def get_nodes(self):
        return self.nodes.values()


def main():
    app = App()
    app.run()

if __name__ == '__main__':
    main()
