import os
import traceback
import webbrowser
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QVBoxLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot
import sys

from util import config, qt_theme
from modules import extract, inject

MAX_UINT = 4294967295
myFont = QtGui.QFont()
myFont.setBold(True)

def startup(cls):
	appQt = QtWidgets.QApplication([])
	
	#style
	appQt.setStyle(QtWidgets.QStyleFactory.create('Fusion'))
	appQt.setPalette(qt_theme.dark_palette)
	appQt.setStyleSheet("QToolTip { color: #ffffff; background-color: #353535; border: 1px solid white; }")
	
	win = cls()
	win.show()
	appQt.exec_()
	config.write_config("config.ini", win.cfg)

def abort_open_new_file(parent, newfile, oldfile):
	# only return True if we should abort
	if newfile == oldfile:
		return True
	if oldfile:
		qm = QtWidgets.QMessageBox
		return qm.No == qm.question(parent.parent,'', "Do you really want to load "+os.path.basename(newfile)+"? You will lose unsaved work on "+os.path.basename(oldfile)+"!", qm.Yes | qm.No)

def showdialog(str):
	msg = QtWidgets.QMessageBox()
	msg.setIcon(QtWidgets.QMessageBox.Information)
	msg.setText(str)
	#msg.setInformativeText("This is additional information")
	msg.setWindowTitle("Error")
	#msg.setDetailedText("The details are as follows:")
	msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
	retval = msg.exec_()

def vbox(parent, grid):
	"""Adds a grid layout"""
	# vbox = QtWidgets.QVBoxLayout()
	# vbox.addLayout(grid)
	# vbox.addStretch(1.0)
	# vbox.setSpacing(0)
	# vbox.setContentsMargins(0,0,0,0)
	parent.setLayout(grid)


import tempfile
import os


class DelayedMimeData(QtCore.QMimeData):
	def __init__(self):
		super().__init__()
		self.callbacks = []

	def add_callback(self, callback):
		self.callbacks.append(callback)

	def retrieveData(self, mime_type: str, preferred_type: QtCore.QVariant.Type):
		for callback in self.callbacks.copy():
			result = callback()
			if result:
				self.callbacks.remove(callback)
		return QtCore.QMimeData.retrieveData(self, mime_type, preferred_type)


class TableModel(QtCore.QAbstractTableModel):
	def __init__(self, data, header_names):
		super(TableModel, self).__init__()
		self._data = data
		self.header_labels = header_names

	def data(self, index, role):
		if role == QtCore.Qt.DisplayRole:
			# See below for the nested-list data structure.
			# .row() indexes into the outer list,
			# .column() indexes into the sub-list
			return self._data[index.row()][index.column()]

		if role == QtCore.Qt.ForegroundRole:
			dtype = self._data[index.row()][1]
			if dtype in extract.IGNORE_TYPES:
				return QtGui.QColor('grey')

		if role == QtCore.Qt.DecorationRole:
			if index.column() == 0:
				dtype = self._data[index.row()][1]
				return get_icon(dtype)

	def rowCount(self, index):
		# The length of the outer list.
		return len(self._data)

	def columnCount(self, index):
		# The following takes the first sub-list, and returns
		# the length (only works if all rows are an equal length)
		return len(self._data[0])

	def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
		if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
			return self.header_labels[section]
		return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)

	def flags(self, index):
		# QtCore.Qt.ItemIsEditable |
		dtype = self._data[index.row()][1]
		if dtype in extract.IGNORE_TYPES:
			return QtCore.Qt.ItemIsDropEnabled
		else:
			return QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDropEnabled


class TableView(QtWidgets.QTableView):
	def __init__(self, header_names, main_window):
		super().__init__()
		# self.setHorizontalHeaderLabels(header_names)
		# list of lists
		# row first
		self.data = [[],]
		self.main_window = main_window
		self.ovl_data = main_window.ovl_data

		self.model = TableModel(self.data, header_names)
		self.setModel(self.model)

		self.resizeColumnsToContents()

		self.setAcceptDrops(True)
		self.setDragEnabled(True)
		self.setDropIndicatorShown(True)
		self.verticalHeader().hide()
		self.setSelectionBehavior(self.SelectRows)

	def startDrag(self, actions):
		"""Starts a drag from inside the app towards the outside"""
		drag = QtGui.QDrag(self)
		ids = set([x.row() for x in self.selectedIndexes()])
		names = [self.model._data[x][0] for x in ids]
		print("DRAGGING", ids, names)
		data = QtCore.QMimeData()

		archive = self.ovl_data.ovs_files[0]
		temp_dir = tempfile.gettempdir()
		path_list = [QtCore.QUrl.fromLocalFile(path) for path in extract.extract_names(archive, names, temp_dir, self.main_window.show_temp_files, self.main_window.update_progress)]

		data.setUrls(path_list)
		drag.setMimeData(data)
		drag.exec_()
		# todo - clear temp sub dir
		# mime = DelayedMimeData()
		# path_list = []
		# for name in names:
		# 	path = os.path.join(tempfile.gettempdir(), 'DragTest', name)
		# 	os.makedirs(os.path.dirname(path), exist_ok=True)
		#
		# 	def write_to_file(path=path, contents=name, widget=self):
		# 		if widget.underMouse():
		# 			return False
		# 		else:
		# 			with open(path, 'w') as f:
		# 				import time
		# 				# time.sleep(1)  # simulate large file
		# 				f.write(contents)
		#
		# 			return True
		#
		# 	mime.add_callback(write_to_file)
		#
		# 	path_list.append(QtCore.QUrl.fromLocalFile(path))
		# mime.setUrls(path_list)
		# drag.setMimeData(mime)
		# drag.exec_(QtCore.Qt.CopyAction)

	def set_data(self, data):
		if not data:
			data = [[], ]
		self.model.beginResetModel()
		self.model._data = data
		self.model.endResetModel()
		self.resizeColumnsToContents()

	def dragMoveEvent(self, e):
		e.accept()

	def dragEnterEvent(self, e):
		# print("e", e)
		e.accept()

	def get_files(self, event):
		data = event.mimeData()
		urls = data.urls()
		if urls and urls[0].scheme() == 'file':
			return urls

	def dropEvent(self, e):
		position = e.pos()
		# print('blah', position)
		# self.button.move(position)

		e.setDropAction(QtCore.Qt.CopyAction)

		urls = self.get_files(e)
		if urls:
			files = [str(url.path())[1:] for url in urls]
			# print(files)
			if self.main_window.file_widget.filename:
				# self.cfg["dir_inject"] = os.path.dirname(files[0])
				try:
					inject.inject(self.ovl_data, files, self.main_window.show_temp_files, self.main_window.write_2K)
					self.main_window.file_widget.dirty = True
				except Exception as ex:
					traceback.print_exc()
					showdialog(str(ex))
				print("Done!")
			else:
				showdialog("You must open an OVL file before you can inject files!")
			# self.accept_file(filepath)
		# self.resize(720, 400)
		e.accept()


class LabelEdit(QtWidgets.QWidget):
	def __init__(self, name, ):
		QtWidgets.QWidget.__init__(self,)
		self.shader_container = QtWidgets.QWidget()
		self.label = QtWidgets.QLabel(name)
		self.entry = QtWidgets.QLineEdit()
		vbox = QtWidgets.QHBoxLayout()
		vbox.addWidget(self.label)
		vbox.addWidget(self.entry)
		# vbox.addStretch(1)
		self.setLayout(vbox)


class CleverCombo(QtWidgets.QComboBox):
	""""A combo box that supports setting content (existing or new), and a callback"""
	def __init__(self, options=[], link_inst=None, link_attr=None, *args, **kwargs):
		super(CleverCombo, self).__init__(*args, **kwargs)
		self.addItems(options)
		self.link_inst = link_inst
		self.link_attr = link_attr
		if link_inst and link_attr:
			name = str(getattr(link_inst, link_attr))
			self.setText(name)
			self.currentIndexChanged.connect(self.update_name)

	def setText(self, txt):
		flag = QtCore.Qt.MatchFixedString
		indx = self.findText(txt, flags=flag)
		# add new item if not found
		if indx == -1:
			self.addItem(txt)
			indx = self.findText(txt, flags=flag)
		self.setCurrentIndex(indx)

	def update_name(self, ind):
		"""Change data on pyffi struct if gui changes"""
		setattr(self.link_inst, self.link_attr, self.currentText())


class LabelCombo(QtWidgets.QWidget):
	def __init__(self, name, options, link_inst=None, link_attr=None):
		QtWidgets.QWidget.__init__(self,)
		sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
		sizePolicy.setHorizontalStretch(0)
		sizePolicy.setVerticalStretch(0)
		self.shader_container = QtWidgets.QWidget()
		self.label = QtWidgets.QLabel(name)
		self.entry = CleverCombo(options=options, link_inst=link_inst, link_attr=link_attr)
		sizePolicy.setHeightForWidth(self.entry.sizePolicy().hasHeightForWidth())
		self.entry.setSizePolicy(sizePolicy)
		# self.entry.setMaxVisibleItems(10)
		self.entry.setEditable(True)
		vbox = QtWidgets.QHBoxLayout()
		vbox.addWidget(self.label)
		vbox.addWidget(self.entry)
		self.setLayout(vbox)


class MySwitch(QtWidgets.QPushButton):
	PRIMARY =   QtGui.QColor(53, 53, 53)
	SECONDARY = QtGui.QColor(35, 35, 35)
	OUTLINE = QtGui.QColor(122, 122, 122)
	TERTIARY =  QtGui.QColor(42, 130, 218)
	BLACK =  QtGui.QColor(0, 0, 0)
	WHITE =     QtGui.QColor(255, 255, 255)
	def __init__(self, parent = None):
		super().__init__(parent)
		self.setCheckable(True)
		self.setMinimumWidth(66)
		self.setMinimumHeight(22)

	def setValue(self, v):
		self.setChecked(v)

	def paintEvent(self, event):
		label = "ON" if self.isChecked() else "OFF"
		bg_color = self.TERTIARY if self.isChecked() else self.PRIMARY

		radius = 10
		width = 32
		center = self.rect().center()

		painter = QtGui.QPainter(self)
		painter.setRenderHint(QtGui.QPainter.Antialiasing)
		painter.translate(center)
		painter.setBrush(self.SECONDARY)

		pen = QtGui.QPen(self.WHITE)
		pen.setWidth(0)
		painter.setPen(pen)

		painter.drawRoundedRect(QtCore.QRect(-width, -radius, 2*width, 2*radius), radius, radius)
		painter.setBrush(QtGui.QBrush(bg_color))
		sw_rect = QtCore.QRect(-radius, -radius, width + radius, 2*radius)
		if not self.isChecked():
			sw_rect.moveLeft(-width)
		painter.drawRoundedRect(sw_rect, radius, radius)
		painter.drawText(sw_rect, QtCore.Qt.AlignCenter, label)


class CollapsibleBox(QtWidgets.QWidget):
	def __init__(self, title="", parent=None):
		super(CollapsibleBox, self).__init__(parent)

		self.toggle_button = QtWidgets.QToolButton(
			text=title, checkable=True, checked=False
		)
		self.toggle_button.setStyleSheet("QToolButton { border: none; }")
		self.toggle_button.setToolButtonStyle(
			QtCore.Qt.ToolButtonTextBesideIcon
		)
		self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
		self.toggle_button.pressed.connect(self.on_pressed)

		self.toggle_animation = QtCore.QParallelAnimationGroup(self)

		self.content_area = QtWidgets.QScrollArea(
			maximumHeight=0, minimumHeight=0
		)
		self.content_area.setSizePolicy(
			QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
		)
		self.content_area.setFrameShape(QtWidgets.QFrame.NoFrame)

		lay = QtWidgets.QVBoxLayout(self)
		lay.setSpacing(0)
		lay.setContentsMargins(0, 0, 0, 0)
		lay.addWidget(self.toggle_button)
		lay.addWidget(self.content_area)

		self.toggle_animation.addAnimation(
			QtCore.QPropertyAnimation(self, b"minimumHeight")
		)
		self.toggle_animation.addAnimation(
			QtCore.QPropertyAnimation(self, b"maximumHeight")
		)
		self.toggle_animation.addAnimation(
			QtCore.QPropertyAnimation(self.content_area, b"maximumHeight")
		)

	@QtCore.pyqtSlot()
	def on_pressed(self):
		checked = self.toggle_button.isChecked()
		self.toggle_button.setArrowType(
			QtCore.Qt.DownArrow if not checked else QtCore.Qt.RightArrow
		)
		self.toggle_animation.setDirection(
			QtCore.QAbstractAnimation.Forward
			if not checked
			else QtCore.QAbstractAnimation.Backward
		)
		self.toggle_animation.start()

	def setLayout(self, layout):
		lay = self.content_area.layout()
		del lay
		self.content_area.setLayout(layout)
		collapsed_height = (
			self.sizeHint().height() - self.content_area.maximumHeight()
		)
		content_height = layout.sizeHint().height()
		for i in range(self.toggle_animation.animationCount()):
			animation = self.toggle_animation.animationAt(i)
			animation.setDuration(100)
			animation.setStartValue(collapsed_height)
			animation.setEndValue(collapsed_height + content_height)

		content_animation = self.toggle_animation.animationAt(
			self.toggle_animation.animationCount() - 1
		)
		content_animation.setDuration(100)
		content_animation.setStartValue(0)
		content_animation.setEndValue(content_height)


class MatcolInfo():
	def __init__(self, attrib, tooltips={}):
		"""attrib must be pyffi matcol InfoWrapper object"""
		# QtWidgets.QWidget.__init__(self,)
		self.attrib = attrib
		self.label = QtWidgets.QLabel(str(attrib.name))
		
		self.data = QtWidgets.QWidget()
		layout = QtWidgets.QHBoxLayout()
		layout.setSpacing(0)
		layout.setContentsMargins(0,0,0,0)
		buttons = [self.create_field(i) for i, v in enumerate(attrib.info.flags) if v]
		for button in buttons:
			layout.addWidget(button)
		self.data.setLayout(layout)
		# get tooltip
		tooltip = tooltips.get(self.attrib.name, "Undocumented attribute.")
		self.data.setToolTip(tooltip)
		self.label.setToolTip(tooltip)

	def create_field(self, ind):
		default = self.attrib.info.value[ind]

		def update_ind( v):
			# use a closure to remember index
			# print(self.attrib, ind, v)
			self.attrib.info.value[ind] = v

		# always float
		field = QtWidgets.QDoubleSpinBox()
		field.setDecimals(3)
		field.setRange(-10000, 10000)
		field.setSingleStep(.05)
		field.valueChanged.connect(update_ind)

		field.setValue(default)
		field.setMinimumWidth(50)
		field.setAlignment(QtCore.Qt.AlignCenter)
		field.setContentsMargins(0,0,0,0)
		return field


class QColorButton(QtWidgets.QPushButton):
	'''
	Custom Qt Widget to show a chosen color.

	Left-clicking the button shows the color-chooser, while
	right-clicking resets the color to None (no-color).
	'''

	colorChanged = QtCore.pyqtSignal(object)

	def __init__(self, *args, **kwargs):
		super(QColorButton, self).__init__(*args, **kwargs)

		self._color = None
		self.setMaximumWidth(32)
		self.pressed.connect(self.onColorPicker)

	def setColor(self, color):
		if color != self._color:
			self._color = color
			self.colorChanged.emit(color)

		if self._color:
			self.setStyleSheet("background-color: %s;" % self._color.name(QtGui.QColor.NameFormat.HexArgb))
		else:
			self.setStyleSheet("")

	def color(self):
		return self._color

	def onColorPicker(self):
		'''
		Show color-picker dialog to select color.

		Qt will use the native dialog by default.

		'''
		dlg = QtWidgets.QColorDialog(self)
		dlg.setOption(QtWidgets.QColorDialog.ShowAlphaChannel)
		if self._color:
			dlg.setCurrentColor(self._color)
		if dlg.exec_():
			self.setColor(dlg.currentColor())

	def mousePressEvent(self, e):
		if e.button() == QtCore.Qt.RightButton:
			self.setColor(None)

		return super(QColorButton, self).mousePressEvent(e)

	def setValue(self, c):
		self.setColor(QtGui.QColor(c.r, c.g, c.b, c.a))

	def getValue(self, ):
		if self._color:
			print(self._color.getRgb())


class VectorEntry:
	def __init__(self, attrib, tooltips={}):
		"""attrib must be pyffi attrib object"""
		# QtWidgets.QWidget.__init__(self,)
		self.attrib = attrib
		self.label = QtWidgets.QLabel(attrib.name)
		self.delete = QtWidgets.QPushButton("x")
		self.delete.setMinimumWidth(15)
		self.data = QtWidgets.QWidget()
		layout = QtWidgets.QHBoxLayout()
		buttons = [self.create_field(i) for i in range(len(attrib.value))]
		for button in buttons:
			layout.addWidget(button)
		self.data.setLayout(layout)

		# get tooltip
		tooltip = tooltips.get(self.attrib.name, "Undocumented attribute.")
		self.data.setToolTip(tooltip)
		self.label.setToolTip(tooltip)

	def create_field(self, ind):
		default = self.attrib.value[ind]

		def update_ind( v):
			# use a closure to remember index
			# print(self.attrib, ind, v)
			self.attrib.value[ind] = v

		def update_ind_int( v):
			# use a closure to remember index
			# print(self.attrib, ind, v)
			self.attrib.value[ind] = int(v)

		def update_ind_color( c):
			# use a closure to remember index
			# print(self.attrib, ind, v)
			color = self.attrib.value[ind]
			c_new = c.getRgb()
			color.r = c_new[0]
			color.g = c_new[1]
			color.b = c_new[2]
			color.a = c_new[3]

		t = str(type(default))
		# print(t)
		if "float" in t:
			field = QtWidgets.QDoubleSpinBox()
			field.setDecimals(3)
			field.setRange(-10000, 10000)
			field.setSingleStep(.05)
			field.valueChanged.connect(update_ind)
		elif "bool" in t:
			# field = QtWidgets.QSpinBox()
			field = MySwitch()
			field.clicked.connect(update_ind)
		elif "int" in t:
			default = int(default)
			# field = QtWidgets.QSpinBox()
			field = QtWidgets.QDoubleSpinBox()
			field.setDecimals(0)
			field.setRange(-MAX_UINT, MAX_UINT)
			field.valueChanged.connect(update_ind_int)
		elif "Color" in t:
			field = QColorButton()
			field.colorChanged.connect(update_ind_color)
		field.setValue(default)
		field.setMinimumWidth(50)
		return field


class FileWidget(QtWidgets.QWidget):
	"""An entry widget that starts a file selector when clicked and also accepts drag & drop.
	Displays the current file's basename.
	"""

	def __init__(self, parent, cfg, ask_user=True, dtype="OVL"):
		super(FileWidget, self).__init__(parent)
		self.entry = QtWidgets.QLineEdit()
		self.icon = QtWidgets.QPushButton()
		self.icon.setIcon(get_icon("dir"))
		self.icon.setFlat(True)
		self.icon.mousePressEvent = self.ignoreEvent
		self.entry.mousePressEvent = self.ignoreEvent
		self.icon.dropEvent = self.dropEvent
		self.entry.dropEvent = self.dropEvent
		self.icon.dragMoveEvent = self.dragMoveEvent
		self.entry.dragMoveEvent = self.dragMoveEvent
		self.icon.dragEnterEvent = self.dragEnterEvent
		self.entry.dragEnterEvent = self.dragEnterEvent
		self.dtype = dtype
		self.dtype_l = dtype.lower()

		self.parent = parent
		self.cfg = cfg
		if not self.cfg:
			self.cfg[f"dir_{self.dtype_l}s_in"] = "C://"
		self.entry.setDragEnabled(True)
		self.entry.setReadOnly(True)
		self.filepath = ""
		self.filename = ""
		self.ask_user = ask_user
		# this checks if the data has been modified by the user, is set from the outside
		self.dirty = False

		self.qgrid = QtWidgets.QGridLayout()
		self.qgrid.setContentsMargins(0,0,0,0)
		self.qgrid.addWidget(self.icon, 0, 0)
		self.qgrid.addWidget(self.entry, 0, 1)

		self.setLayout(self.qgrid)

	def abort_open_new_file(self, new_filepath):
		# only return True if we should abort
		if not self.ask_user:
			return False
		if new_filepath == self.filepath:
			return True
		if self.filepath and self.dirty:
			qm = QtWidgets.QMessageBox
			return qm.No == qm.question(self, '', "Do you really want to load "+os.path.basename(new_filepath)+"? You will lose unsaved work on "+os.path.basename(self.filepath)+"!", qm.Yes | qm.No)

	def accept_file(self, filepath):
		if os.path.isfile(filepath):
			if os.path.splitext(filepath)[1].lower() in (f".{self.dtype_l}",):
				if not self.abort_open_new_file(filepath):
					self.filepath = filepath
					self.cfg[f"dir_{self.dtype}s_in"], self.filename = os.path.split(filepath)
					self.setText(self.filename)
					self.parent.poll()
			else:
				showdialog("Unsupported File Format")

	def setText(self, text):
		self.entry.setText(text)

	def get_files(self, event):
		data = event.mimeData()
		urls = data.urls()
		if urls and urls[0].scheme() == 'file':
			return urls

	def dragEnterEvent(self, event):
		if self.get_files(event):
			event.acceptProposedAction()
			self.setFocus(True)

	def dragMoveEvent(self, event):
		if self.get_files(event):
			event.acceptProposedAction()
			self.setFocus(True)

	def dropEvent(self, event):
		urls = self.get_files(event)
		if urls:
			filepath = str(urls[0].path())[1:]
			self.accept_file(filepath)

	def ask_open(self):
		filepath = QtWidgets.QFileDialog.getOpenFileName(self, f'Load {self.dtype}', self.cfg.get(f"dir_{self.dtype_l}s_in", "C://"), f"{self.dtype} files (*.{self.dtype_l})")[0]
		self.accept_file(filepath)

	def ignoreEvent(self, event):
		event.ignore()

	def mousePressEvent(self, event):
		self.ask_open()


def get_icon(name):
	base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
	return QtGui.QIcon(os.path.join(base_dir, f'icons/{name}.png'))


class MainWindow(QtWidgets.QMainWindow):

	def __init__(self, name, ):
		QtWidgets.QMainWindow.__init__(self)		
		
		self.central_widget = QtWidgets.QWidget(self)
		self.setCentralWidget(self.central_widget)
		
		self.name = name
		# self.resize(720, 400)
		self.setWindowTitle(name)
		self.setWindowIcon(get_icon("frontier"))
		
		self.cfg = config.read_config("config.ini")

	def poll(self):
		if self.file_widget.filepath:
			self.load()

	def report_bug(self):
		webbrowser.open("https://github.com/OpenNaja/cobra-tools/issues/new", new=2)
		
	def online_support(self):
		webbrowser.open("https://github.com/OpenNaja/cobra-tools/wiki", new=2)

	def update_file(self, filepath):
		self.cfg["dir_in"], file_name = os.path.split(filepath)
		self.setWindowTitle(f"{self.name} {file_name}")
		
	def add_to_menu(self, button_data):
		for submenu, name, func, shortcut, icon_name in button_data:
			button = QtWidgets.QAction(name, self)
			if icon_name:
				icon = get_icon(icon_name)
				# if not icon:
				# 	icon = self.style().standardIcon(getattr(QtWidgets.QStyle, icon))
				button.setIcon(icon)
			button.triggered.connect(func)
			if shortcut:
				button.setShortcut(shortcut)
			submenu.addAction(button)
