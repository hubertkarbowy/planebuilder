from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from structure.Equipment import Equipment
from default_values import default_component

class EventController():
    def __init__(self):
        self.params_editor = None
        self.plane_painter = None
        self.project_name_input = None
        self.centerline_input = None
        self.fuselage_mass_input = None

    def set_params_editor(self, params_editor):
        self.params_editor = params_editor

    def set_plane_painter(self, plane_painter):
        self.plane_painter = plane_painter

    def set_global_parameter_input(self, input_tuple):
        if input_tuple[0] == 'project_name':
            self.project_name_input = input_tuple[1]
        elif input_tuple[0] == 'centerline':
            self.centerline_input = input_tuple[1]
        elif input_tuple[0] == 'fuselage_mass':
            self.fuselage_mass_input = input_tuple[1]

    def update_global_parameter(self, update_tuple, repaint=False):
        if update_tuple[0] == 'project_name':
            if update_tuple[1] == '':
                raise ValueError("Project name cannot be empty")
            self.project_name_input.setText(update_tuple[1])
            self.plane_painter.plane.project_name=update_tuple[1]
        else:
            try:
                new_val = float(update_tuple[1])
            except ValueError:
                raise ParseException("Please give a valid number")
            if update_tuple[0] == 'fuselage_centerline':
                if new_val <= 0:
                    raise ValueError("Centerline must be longer than zero")
                for _, elem in self.plane_painter.plane.x_axis.items():
                    print (f"Checking {_}")
                    if elem['end'] > new_val:
                        raise ValueError("New centerline cannot be shorter than the rightmost component's end")
                self.centerline_input.setText(str(round(new_val, 4)))
                self.plane_painter.plane.x_axis_len = new_val
            elif update_tuple[0] == 'fuselage_mass':
                if new_val <= 0:
                    raise ValueError("Fuselage mass must be larger than zero")
                self.fuselage_mass_input.setText(str(round(new_val, 4)))
                self.plane_painter.plane.fuselage_mass = new_val
            self.plane_painter._repaintConfiguration()

    def amend_plane(self, all_fields):
        self.plane_painter.plane.validate_param_update(input_fields=all_fields)
        self.plane_painter._repaintConfiguration()

    def remove_component(self):
        try:
            activeComponent = self.plane_painter.activeComponent
            component_name = activeComponent[0]
            orig_offset = self.plane_painter.plane.x_axis[component_name]['begin']
            self.plane_painter.plane.remove_component(component_name=component_name)
            self.disable_all()
            self.clear_all()
            self.plane_painter._repaintConfiguration()
        except ValueError:
            QMessageBox(None, "Cannot remove component")

    def update_params(self, caller_obj, params_dict, disabled_fields=None):
        self.clear_all()
        self.enable_all()
        for k,v in params_dict.items():
            print (f"k = {k}, v = {v}")
            self.params_editor.set_param(name=k, value=v)
        if disabled_fields is not None:
            self.disable(what=disabled_fields)

    def clear_all(self):
        self.params_editor.clear()

    def disable_all(self):
        self.params_editor.disable()

    def enable_all(self):
        self.params_editor.enable()

    def disable(self, what):
        self.params_editor.disable(which=what)

class ParamsEditor(QFormLayout):
    def __init__(self, *, ec: EventController):
        super().__init__()
        self.ec = ec
        self.save_button = QPushButton("&Update")
        self.remove_button = QPushButton("&Remove")
        self.all_fields = ['comp_name_orig_input', 'comp_name_input', 'comp_mass_input', 'comp_width_input', \
                           'comp_x_offset_input', 'comp_xfoil_data_input', 'comp_aoi_input', \
                           'comp_rootchord_input', 'comp_tipchord_input', \
                           'comp_charlen_input', 'comp_thickness', 'comp_wetted_area', 'comp_semispan_input']
        for field in self.all_fields:
            setattr(self, field, QLineEdit())

        self.addRow(QLabel("COMPONENT PARAMETERS"))
        self.addRow("Name", self.comp_name_input)
        self.addRow("Offset", self.comp_x_offset_input)
        self.addRow("Mass", self.comp_mass_input)
        self.addRow("Width", self.comp_width_input)
        self.addRow(QLabel("LIFTING SURFACES"))
        self.addRow("Root chord", self.comp_rootchord_input)
        self.addRow("Tip chord", self.comp_tipchord_input)
        self.addRow("Characteristic length", self.comp_charlen_input)
        self.addRow("Semi-span", self.comp_semispan_input)
        self.addRow("Thickness", self.comp_thickness)
        self.addRow("Wetted area", self.comp_wetted_area)
        self.addRow("Xfoil data", self.comp_xfoil_data_input)
        self.addRow("AOI", self.comp_aoi_input)
        self.addRow(self.remove_button)
        self.addRow(self.save_button)
        self.save_button.clicked.connect(self.amend_plane)
        self.remove_button.clicked.connect(self.remove_component)

    def set_param(self, *, name, value):
        getattr(self, name, None).setText(str(value))
        print (f"n = {name}, v = {value}")

    def clear(self):
        for field in self.all_fields:
            getattr(self, field, None).clear()

    def disable(self, *, which=None):
        iter_fields = self.all_fields if which is None else which
        for field in iter_fields:
            getattr(self, field, None).setReadOnly(True)
            
    def enable(self, *, which=None):
        iter_fields = self.all_fields if which is None else which
        for field in iter_fields:
            getattr(self, field, None).setReadOnly(False)

    def amend_plane(self):
        form_dict = {field:getattr(self, field, None).text() for field in self.all_fields}
        self.ec.amend_plane(form_dict)

    def remove_component(self):
        self.ec.remove_component()

def show_unable_window(msg, title="Unable, sir"):
    box = QMessageBox()
    box.setWindowTitle(title)
    box.setText(msg)
    box.exec_()

class NewPlaneForm(QDialog):
    def __init__(self, parent):
        super(NewPlaneForm, self).__init__(parent)
        self.setModal(True)
        new_plane_box = QVBoxLayout()
        params_box = QFormLayout()
        self.project_name_input = QLineEdit()
        self.fuselage_mass_input = QLineEdit()
        self.fuselage_centerline_input = QLineEdit()
        filename_box = QHBoxLayout()
        self.new_filename = QLineEdit()
        self.new_filename.setReadOnly(True)
        self.choose_file_btn = QPushButton("Choose...")
        self.choose_file_btn.clicked.connect(self.file_chooser)
        filename_box.addWidget(self.new_filename)
        filename_box.addWidget(self.choose_file_btn)
        params_box.addRow("Project name", self.project_name_input)
        params_box.addRow("Fuselage mass", self.fuselage_mass_input)
        params_box.addRow("Fuselage centerline", self.fuselage_centerline_input)
        params_box.addRow("File name", filename_box)

        self.ok_btn = QPushButton("&OK")
        self.ok_btn.clicked.connect(self.new_plane_accept)
        self.cancel_btn = QPushButton("&Cancel")
        self.cancel_btn.clicked.connect(self.reject)
 
        self.setWindowTitle("New plane")
        new_plane_box.addLayout(params_box)
        new_plane_box.addWidget(self.ok_btn)
        new_plane_box.addWidget(self.cancel_btn)
        self.setLayout(new_plane_box)
        self.setMinimumHeight(100); self.setMinimumWidth(100)

    def new_plane_accept(self):
        try:
            if self.project_name_input.text() == '':
                raise ParseException("Project name must not be empty")
            if self.new_filename.text() == '':
                raise ParseException("Please choose a file where the project will be stored")
            if float(self.fuselage_centerline_input.text()) <= 0:
                raise ParseException("Centerline must be larger than zero")
            if float(self.fuselage_mass_input.text()) <= 0:
                raise ParseException("Fuselage mass must be larger than zero")
        except ValueError:
            show_unable_window("Give a correct number")
            return
        except ParseException as e:
            show_unable_window(str(e))
            return
        self.accept()

    def file_chooser(self):
        filename, _ = QFileDialog.getSaveFileName(self, caption='Choose new plane file')
        if filename:
            self.new_filename.setText(filename)
class ParseException(Exception):
    pass
