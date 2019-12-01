import copy
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from structure.Plane import Plane, OutsideCenterlineException
from structure.Wing import Wing
from structure.Equipment import Equipment
from loader_utils import load_plane, save_plane
from default_values import default_component, default_wing
from EventController import EventController, show_unable_window

FUS_Y=240
APP_HDG="RC Plane Calculator v.0.0.1"

class PlanePainter(QLabel):
    def __init__(self, *, src_img, plane: Plane=None, ec: EventController, status_label: QLabel):
        super().__init__()
        self.ec = ec
        self.setMinimumHeight(600); self.setMinimumWidth(785)
        self.plane = plane
        self.origPixmap = QPixmap(src_img)
        self.modifPixmap = None
        self.drawnComponents = []
        self.activeComponent = None
        self.scale_factor = None
        self.xfoil_predictions = None
        self.status_label = status_label
        self._repaintConfiguration()
        self.setAcceptDrops(True)

    def _repaintConfiguration(self, setActive=None):
        self.drawnComponents = []
        self.modifPixmap = QPixmap(785,600)
        self.modifPixmap.fill(Qt.transparent)
        self.setPixmap(self.modifPixmap)
        painter = QPainter(self.modifPixmap)
        painter.drawPixmap(0, FUS_Y, self.origPixmap)
        if self.plane is not None:
            self.scale_factor = 785.0 / self.plane.x_axis_len
            # draw lifting surfaces
            for elem_name, elem_properties in self.plane.x_axis.items():
                if elem_name is not None:
                    drawn_component = (elem_name, self._get_component_pixmap(painter=painter, elem_name=elem_name, x_axis_elem=elem_properties, is_active=setActive))
                    self.drawnComponents.append(drawn_component)
                    if setActive is not None and setActive == elem_name:
                        self.activeComponent = drawn_component
                        new_param_values, disabled_fields = self.get_params_dict_to_update(elem_name)
                        self.ec.update_params(self, new_param_values, disabled_fields)
                else:
                    print (f"Skipping `{elem_name}` (unknown element type)")
            self._draw_cg(painter=painter)
        for coords in self.drawnComponents:
            print (self.activeComponent)
        self.setPixmap(self.modifPixmap)

    def dragEnterEvent(self, e):
        print(e.mimeData().formats())
        print(e.mimeData().data('airplane/component'))
        print (e)
        if 'airplane/component' in e.mimeData().formats():
            e.accept()

    def dropEvent(self, e):
        print (e.pos())
        component_type = e.mimeData().data('airplane/component').data().decode('utf-8')
        if component_type in ['wings', 'htail']:
            if self.plane.x_axis.get(component_type) is not None:
                show_unable_window(f"You already have {'wings' if component_type == 'wings' else 'a horizontal stabilizer/stabilator'} in your plane configuration.")
                return
        init_x_offset = (self.plane.x_axis_len * e.pos().x()) / 785
        self.new_component(component_type, init_x_offset)
        self.activeComponent = None
        self._repaintConfiguration()

    def new_component(self, component_type, init_x_offset):
        if component_type in ['wings', 'htail']:
            params_dict = {**default_component, **default_wing, "name": f"{component_type}"}
            new_wing = Wing(params_dict = params_dict, flight=None)
            self.plane.add_component(component=new_wing, x_offset=init_x_offset)
        else:
            comp_name, is_ok = QInputDialog.getText(None, 'New component', 'Enter the new component\'s name:')
            if is_ok:
                self.plane.add_equipment(name=comp_name, x_offset=init_x_offset, \
                                         length=0.1, mass=0.1, eq_type=component_type)
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            print(f"Click! {e.x()}, {e.y()}")
            newActiveComponent = None
            self.activeComponent = None
            for coords in self.drawnComponents:
                rect = coords[1]
                if rect.contains(e.x(), e.y()):
                    print (coords[0])
                    self.activeComponent = coords
                    new_param_values, disabled_fields = self.get_params_dict_to_update(coords[0])
                    self.ec.update_params(self, new_param_values, disabled_fields)
                    newActiveComponent = coords[0]
                    break
            if self.activeComponent is None:
                self.ec.clear_all()
                self.ec.disable_all()
            self._repaintConfiguration(setActive=newActiveComponent)

    def get_params_dict_to_update(self, component_name):
        ret_dict = {}
        comp_obj = self.plane.x_axis[component_name]['obj']
        ret_dict = { 'comp_name_orig_input': comp_obj.name, 'comp_name_input': comp_obj.name, \
                     'comp_mass_input': comp_obj.mass, \
                     'comp_x_offset_input': self.plane.x_axis[component_name]['begin'], \
                     'comp_width_input': comp_obj.root_chord if comp_obj.name in ['wings', 'htail'] else comp_obj.length
                   }
        disabled_fields = ['comp_rootchord_input', 'comp_tipchord_input', 'comp_charlen_input', 'comp_thickness',
                           'comp_wetted_area', 'comp_semispan_input', 'comp_xfoil_data_input', 'comp_aoi_input']
        if comp_obj.name in ['wings', 'htail']:
            disabled_fields = ['comp_name_input', 'comp_width_input']
            lifting_surfaces_dict = {'comp_xfoil_data_input': '', 
                    'comp_rootchord_input': round(comp_obj.root_chord, 4),
                    'comp_tipchord_input': round(comp_obj.tip_chord, 4),
                    'comp_charlen_input': round(comp_obj.characteristic_length, 4),
                    'comp_thickness': round(comp_obj.thickness, 4),
                    'comp_wetted_area': round(comp_obj.wetted_area, 4),
                    'comp_semispan_input': round(comp_obj.semispan, 4),
                    'comp_xfoil_data_input': comp_obj.xfoil_data,
                    'comp_aoi_input': round(comp_obj.aoi, 4)
            }
            ret_dict.update(lifting_surfaces_dict)
        return ret_dict, disabled_fields

    def setPlane(self, *, data_file):
        self.plane = load_plane(conf_file=data_file)
        global_params = [('project_name', self.plane.project_name), ('fuselage_centerline', self.plane.x_axis_len), ('fuselage_mass', self.plane.fuselage_mass)]
        [self.ec.update_global_parameter(p) for p in global_params]
        self._repaintConfiguration()

    def savePlane(self, *, data_file):
        save_plane(conf_file=data_file, plane=self.plane)

    def move_component(self, direction):
        if self.activeComponent is None:
            return
        try:
            x_axis_elem = self.plane.x_axis[self.activeComponent[0]]
            component_name=self.activeComponent[0]
            increment_fraction = 0.025 if direction == 'aft' else -0.025
            self.plane.move_component(name=component_name, distance=increment_fraction*self.plane.x_axis_len)
            #orig_offset = x_axis_elem['begin']
            #component_obj = x_axis_elem['obj']
            #component_obj_cpy = copy.deepcopy(component_obj)
            #self.plane.remove_component(component=component_obj, orig_offset=orig_offset)
            #self.drawnComponents.remove(self.activeComponent)
            #self.plane.add_component(component=component_obj_cpy, x_offset=orig_offset - 0.05*self.plane.x_axis_len)
            self._repaintConfiguration(setActive=component_name)
            print (f"Selected {x_axis_elem}")
        except OutsideCenterlineException as e:
            msg = QMessageBox()
            msg.setWindowTitle("Unable, sir")
            msg.setText(str(e))
            msg.exec_()
        except KeyError:
            print ("Unable to select")
        print (self.activeComponent[0])

    def _get_wing_rect(self, x_axis_elem, scale_factor):
        wing_x_offset = x_axis_elem['begin'] * scale_factor
        wing_y_offset = 330 - (x_axis_elem['obj'].semispan * scale_factor)
        wing_chord = x_axis_elem['obj'].root_chord * scale_factor
        wing_span = x_axis_elem['obj'].semispan * 2 * scale_factor
        return QRect(wing_x_offset, wing_y_offset, wing_chord, wing_span)
 
    def _get_component_pixmap(self, *, painter, elem_name, x_axis_elem, is_active):
        # y_offset = 240 + (0.5*wysokosc_obrazka z kadlubem=0.5*180=90) - (0.5*wysokosc obrazka nakladanego)
        comp_x_offset = x_axis_elem['begin'] * self.scale_factor
        comp_len = (x_axis_elem['end'] - x_axis_elem['begin']) * self.scale_factor
        painter_thickness = 3
        if elem_name in ['wings', 'htail']:
            # wing_y_offset = 330 - (x_axis_elem['obj'].semispan * scale_factor)
            comp_height = x_axis_elem['obj'].semispan * 2 * self.scale_factor # wingspan
            comp_y_offset = FUS_Y + (0.5*180) - (0.5 * comp_height)
            comp_len = x_axis_elem['obj'].root_chord * self.scale_factor # override with root chord
        elif elem_name == 'propeller':
            prop_pixmap = QPixmap('res/propeller_horiz2.png')
            comp_height = prop_pixmap.height()
            comp_y_offset = FUS_Y+ (0.5*180) - (0.5 * comp_height)
            painter.drawPixmap(comp_x_offset, comp_y_offset, prop_pixmap)
        else:
            comp_height = 50
            comp_y_offset = FUS_Y + (0.5*180) - (0.5 * comp_height)
            painter_thickness = 1
        coords=QRect(comp_x_offset, comp_y_offset, comp_len, comp_height)
        if is_active is None:
            pen = QPen(Qt.blue, painter_thickness)
        elif is_active == elem_name:
            pen = QPen(Qt.red, painter_thickness)
        else:
            pen = QPen(Qt.blue, painter_thickness)
        painter.setPen(pen)
        painter.drawRect(coords)
        return coords

    def _draw_cg(self, *, painter):
        cg_pixmap = QPixmap('res/cg_symbol40.png')
        cg_x_offset = (self.plane.cg_offset * self.scale_factor) - 40
        cg_y_offset = int(FUS_Y + (0.5*180) - (0.5 * 40))
        painter.drawPixmap(cg_x_offset, cg_y_offset, cg_pixmap)
        plane_np = self.plane.np_offset
        plane_np_xfoil = self.plane.np_xfoil
        if plane_np is None:
            self.status_label.setStyleSheet("QLabel{background-color: gray}")
            self.status_label.setText(f"{APP_HDG}\nStatic stability: UNDECIDED")
            return "UNDECIDED"
        np_pixmap = QPixmap('res/np_symbol40.png')
        np_x_offset = (plane_np * self.scale_factor) - 40
        np_y_offset = cg_y_offset
        painter.drawPixmap(np_x_offset, np_y_offset, np_pixmap)
        if plane_np_xfoil is not None:
            npx_pixmap = QPixmap('res/np_xfoil_symbol40.png')
            npx_x_offset = (plane_np_xfoil * self.scale_factor) - 40
            npx_y_offset = cg_y_offset
            painter.drawPixmap(npx_x_offset, npx_y_offset, npx_pixmap)
        print (f"NP = {plane_np}, NPX = {plane_np_xfoil}")
        if self.plane.cg_offset <= self.plane.np_offset:
            self.status_label.setStyleSheet("QLabel{background-color: green}")
            self.status_label.setText(f"{APP_HDG}\nStatic stability: STABLE")
            return "STABLE"
        else:
            self.status_label.setStyleSheet("QLabel{background-color: darkred}")
            self.status_label.setText(f"{APP_HDG}\nStatic stability: UNSTABLE")
            return "UNSTABLE"
