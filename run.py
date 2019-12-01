from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PlanePainter import PlanePainter
from DraggableLabel import DraggableLabel
from EventController import EventController, ParamsEditor, NewPlaneForm, show_unable_window
from loader_utils import new_plane_from_gui

appli = QApplication([]) # ugly global variable
APP_HDG = "RC Plane Calculator"

class config_window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_HDG)
        self.win_title = QLabel(f"{APP_HDG} v. 0.0.1")
        #self.peditor = ParamsEditor()
        #self.ec = EventController(params_editor = self.peditor)
        #self.pp = PlanePainter(src_img="res/fuselage_horiz.png", ec=self.ec)
        self.ec = EventController()
        self.peditor = ParamsEditor(ec=self.ec)
        self.pp = PlanePainter(src_img="res/fuselage_horiz2.png", ec=self.ec, status_label=self.win_title)
        self.ec.set_params_editor(self.peditor)
        self.ec.set_plane_painter(self.pp)
        self.curr_plane_file = None
        self.project_name_input = None
        self.fuselage_mass_input = None
        self.fuselage_centerline_input = None
        self.global_params = []
        self.initUI()

    def initUI(self):
        win = QWidget(self)
        win.setMinimumHeight(800)
        main_vbox = QVBoxLayout()
        
        ####### TITLE ######
        self.win_title.setAlignment(Qt.AlignCenter)
        self.win_title.setStyleSheet("QLabel{background-color: gray}")
    
        ###### MENU #######
        menubar = self.menuBar()
        menu_file_newAction = QAction("&New plane", self)
        menu_file_newAction.setShortcut('Ctrl+N')
        menu_file_newAction.triggered.connect(self.new_plane)

        menu_file = menubar.addMenu("&File")
        menu_file_loadAction = QAction("&Load plane config", self)
        menu_file_loadAction.setShortcut('Ctrl+O')
        menu_file_loadAction.triggered.connect(self.load_plane)

        menu_file_saveAction = QAction("&Save", self)
        menu_file_saveAction.setShortcut('Ctrl+S')
        menu_file_saveAction.triggered.connect(self.save_plane)

        menu_file_saveAsAction = QAction("Save &as...", self)
        menu_file_saveAsAction.setShortcut('Ctrl+Alt+S')
        menu_file_saveAsAction.triggered.connect(self.save_as_plane)

        menu_file_exitAction = QAction('E&xit', self)
        menu_file_exitAction.triggered.connect(self.close)
        menu_file.addAction(menu_file_newAction)
        menu_file.addAction(menu_file_loadAction)
        menu_file.addAction(menu_file_saveAction)
        menu_file.addAction(menu_file_saveAsAction)
        menu_file.addAction(menu_file_exitAction)

        menu_xfoil = menubar.addMenu("&Xfoil")
        menu_xfoil_setTASAction = QAction("Set &TAS (True AirSpeed)", self)
        menu_xfoil_setDownwash = QAction("Set &downwash angle", self)
        menu_xfoil_setPitchAngle = QAction("Set &pitch angle", self)
        menu_xfoil_NPforTAS = QAction("Calculate NP from Cl interpolations", self)
        menu_xfoil_NPforTAS.setCheckable(True)
        menu_xfoil.addAction(menu_xfoil_setTASAction)
        menu_xfoil.addAction(menu_xfoil_NPforTAS)
        menu_xfoil.addAction(menu_xfoil_setPitchAngle)
        menu_xfoil_setTASAction.triggered.connect(self.set_tas)
        menu_xfoil_setPitchAngle.triggered.connect(self.set_pitch)
        # main_vbox.addWidget(menubar)
    
        ###### MAIN WORKING AREA ######
        rhs_box = QVBoxLayout()
        lhs_box = QVBoxLayout()
    
        ###### LEFT-HAND SIDE (plane drawing + fuselage params)
        params_box = QFormLayout()
        self.project_name_input = QLineEdit()
        self.project_name_input.editingFinished.connect(lambda: self.try_update_global_param('project_name', self.project_name_input.text()))
        #self.project_name_input.setReadOnly(True)
        self.fuselage_mass_input = QLineEdit()
        self.fuselage_mass_input.editingFinished.connect(lambda: self.try_update_global_param('fuselage_mass', self.fuselage_mass_input.text()))
        #self.fuselage_mass_input.setReadOnly(True)
        self.fuselage_centerline_input = QLineEdit()
        self.fuselage_centerline_input.editingFinished.connect(lambda: self.try_update_global_param('fuselage_centerline', self.fuselage_centerline_input.text()))
        #self.fuselage_centerline_input.setReadOnly(True)
        params_box.addRow("Project name", self.project_name_input)
        params_box.addRow("Fuselage mass (kg)", self.fuselage_mass_input)
        params_box.addRow("Fuselage centerline (m)", self.fuselage_centerline_input)
        self.global_params=[('project_name', self.project_name_input), ('centerline', self.fuselage_centerline_input), ('fuselage_mass', self.fuselage_mass_input)]
        [self.ec.set_global_parameter_input(t) for t in self.global_params]
        [t[1].setReadOnly(True) for t in self.global_params]
        lhs_box.addLayout(params_box)

        spacer = QSpacerItem(100, 200, QSizePolicy.Fixed, QSizePolicy.Fixed)
        # self.pp
        lhs_box.addWidget(self.pp)

        fore_aft_box = QHBoxLayout()
        fore_btn = QPushButton("Fore")
        fore_btn_icon = QIcon(QApplication.style().standardIcon(QStyle.SP_ArrowLeft))
        fore_btn.setIcon(fore_btn_icon)
        fore_btn.clicked.connect(lambda: self.pp.move_component('fore'))
        aft_btn = QPushButton("Aft")
        aft_btn_icon = QIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight))
        aft_btn.setIcon(aft_btn_icon)
        aft_btn.clicked.connect(lambda: self.pp.move_component('aft'))
        fore_aft_box.addWidget(fore_btn)
        fore_aft_box.addWidget(aft_btn)
        lhs_box.addLayout(fore_aft_box)

        #### RIGHT-HAND SIDE (components and parameters) #####
        self.xfoil_predictions = QLabel("Xfoil out")
        components_box1 = QHBoxLayout()
        components_box2 = QHBoxLayout()
        form_box = QFormLayout()

        add_powerplant = DraggableLabel('propeller')
        add_powerplant.setPixmap(QPixmap('res/propeller.png').scaled(64,64))
        add_battery = DraggableLabel('battery')
        add_battery.setPixmap(QPixmap('res/battery.png').scaled(64,64))
        add_wing = DraggableLabel('wings')
        add_wing.setPixmap(QPixmap('res/wing.png').scaled(64,64))
    
        add_tail = DraggableLabel('htail')
        add_tail.setPixmap(QPixmap('res/tail.png').scaled(64,64))
        add_cargo = DraggableLabel('cargo')
        add_cargo.setPixmap(QPixmap('res/cargo.png').scaled(64,64))
        add_other = DraggableLabel('other')
        add_other.setPixmap(QPixmap('res/other.png').scaled(64,64))
    
        for widget in [add_powerplant, add_battery, add_wing]:
            components_box1.addWidget(widget)
        for widget in [add_tail, add_cargo, add_other]:
            components_box2.addWidget(widget)
    
        rhs_box.addWidget(self.xfoil_predictions)
        rhs_box.addLayout(components_box1)
        rhs_box.addLayout(components_box2)
        rhs_box.addLayout(self.peditor)
    
        #### PLANE DRAWING AND COMPONENT CONFIGURATION ####
        plane_config_box = QHBoxLayout()
        # component_editor_box = QVBoxLayout()
        plane_config_box.addLayout(lhs_box)
        plane_config_box.addLayout(rhs_box)
    
        #### SET UP THE MAIN WINDOW ####
        main_vbox.addWidget(self.win_title)
        main_vbox.addLayout(plane_config_box)
    
        win.setLayout(main_vbox)
        self.setCentralWidget(win)
        self.show()

    def new_plane(self):
        nd = NewPlaneForm(self)
        res = nd.exec_()
        if res == QDialog.Accepted:
            dialog_params = {'project_name': nd.project_name_input.text(), 'centerline': float(nd.fuselage_centerline_input.text()), \
                             'fuselage_mass': float(nd.fuselage_mass_input.text()), \
                             'centerline': float(nd.fuselage_centerline_input.text()), \
                             'new_file': nd.new_filename.text()
                            }
            new_plane_from_gui(dialog_params)
            self.curr_plane_file = nd.new_filename.text()
            self.pp.setPlane(data_file=self.curr_plane_file)
            self.setWindowTitle(f"{APP_HDG} - {self.curr_plane_file}")
            [t[1].setReadOnly(False) for t in self.global_params]

    def load_plane(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', '', '')
        if fname[0] != '':
            self.pp.setPlane(data_file=fname[0])
            self.curr_plane_file = fname[0]
            self.setWindowTitle(f"{APP_HDG} - {fname[0]}")
            [t[1].setReadOnly(False) for t in self.global_params]
    
    def save_plane(self):
        if self.curr_plane_file is None:
            show_unable_window("Create a new plane first")
            return
        self.pp.savePlane(data_file=self.curr_plane_file)
        show_unable_window("OK, saved changes.", "Saved")

    def save_as_plane(self, blah):
        if self.curr_plane_file is None:
            show_unable_window("Create a new plane first")
            return
        fd = QFileDialog()
        fd.setAcceptMode(QFileDialog.AcceptSave)
        fname = fd.getSaveFileName(self, 'Save file', '', '')
        if fname[0] != '':
            self.pp.savePlane(data_file=fname[0])
            self.curr_plane_file = fname[0]
            self.setWindowTitle(f"{APP_HDG} - {fname[0]}")

    def try_update_global_param(self, param_name, new_val):
        if self.curr_plane_file is None:
            return
        try:
            self.ec.update_global_parameter((param_name, new_val), True)
        except Exception as e:
            show_unable_window(str(e))
            orig_field = getattr(self, f"{param_name}_input")
            if param_name == 'project_name':
                orig_field.setText(self.pp.plane.project_name)
            elif param_name == 'fuselage_centerline':
                orig_field.setText(str(round(self.pp.plane.x_axis_len, 4)))
            elif param_name == 'fuselage_mass':
                orig_field.setText(str(round(self.pp.plane.fuselage_mass, 4)))
            else:
                show_unable_window("Unknown global parameter")

    def set_tas(self): # set true airspeed
        if self.pp.plane is None:
            show_unable_window("Please load/create a plane first")
            return
        tas, ok = QInputDialog.getDouble(self, "NP from Xfoil interpolations", \
                  "Please set the new TAS (True Airspeed) in m/sec", self.pp.plane.flight.true_airspeed, 0.0, 500, 2)
        if ok:
            self.pp.plane.flight.true_airspeed = tas
            self.xfoil_predictions.setText(f"Re = {self.pp.plane.x_axis['wings']['obj'].Re}")

    def set_pitch(self): # set pitch angle (the airfoils' AOA will be calculated on this basis)
        if self.pp.plane is None:
            show_unable_window("Please load/create a plane first")
            return
        pitch, ok = QInputDialog.getDouble(self, "NP from Xfoil interpolations", \
                  "Please set the new pitch angle relative to the fuselage centerline in degrees", self.pp.plane.flight.pitch, -12.0, 14.0, 3)
        if ok:
            self.pp.plane.flight.pitch = pitch

def qt_app_runner():
    #appli = QApplication([])
    win = config_window()
    appli.exec_()

#app = QApplication([])
qt_app_runner()
#window()
#app.exec_()
