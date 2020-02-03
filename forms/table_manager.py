"""Table manager."""

import logging

from typing import Type

from qgis.core import QgsMapLayerModel, QgsProject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QTableWidgetItem,
    QDialog,
    QAbstractItemView,
    QMessageBox,
)

from ..definitions.base import BaseDefinitions, InputType
from ..qgis_plugin_tools.tools.i18n import tr
from ..qgis_plugin_tools.tools.resources import plugin_name
from ..qgis_plugin_tools.tools.version import is_dev_version

LOGGER = logging.getLogger(plugin_name())


__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TableManager:

    def __init__(self, parent, definitions: BaseDefinitions, edition: Type[QDialog], table, remove_button, edit_button, up_button, down_button):
        self.parent = parent
        self.definitions = definitions
        self.edition = edition
        self.table = table
        self.remove_button = remove_button
        self.edit_button = edit_button
        self.up_button = up_button
        self.down_button = down_button

        self.table.setColumnCount(len(self.definitions.layer_config.keys()))

        for i, item in enumerate(self.definitions.layer_config.values()):
            column = QTableWidgetItem(item['header'])
            tooltip = item.get('tooltip')
            if tooltip:
                column.setToolTip(tooltip)
            self.table.setHorizontalHeaderItem(i, column)

        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

    def _unicity(self) -> dict:
        unicity_dict = dict()
        rows = self.table.rowCount()

        for key in self.definitions.unicity():
            unicity_dict[key] = list()
            for i, item in enumerate(self.definitions.layer_config.keys()):
                if item == key:
                    for row in range(rows):
                        item = self.table.item(row, i)
                        if item is None:
                            # Do not put if not item, it might be False
                            raise Exception('Cell is not initialized ({}, {})'.format(row, i))

                        cell = item.data(Qt.UserRole)
                        if cell is None:
                            # Do not put if not cell, it might be False
                            raise Exception('Cell has no data ({}, {})'.format(row, i))

                        unicity_dict[key].append(cell)

        return unicity_dict

    def add_new_row(self):
        # noinspection PyCallingNonCallable
        row = self.table.rowCount()
        if row >= 1 and self.definitions.key() == 'atlas' and not is_dev_version():
            message = tr('This feature is coming soon in Lizmap 3.4.')
            QMessageBox.warning(self.parent, tr('Lizmap'), message, QMessageBox.Ok)
            return

        dialog = self.edition(self._unicity())
        result = dialog.exec_()
        if result == QDialog.Accepted:
            data = dialog.save_form()
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)
            self._edit_row(row, data)

    def edit_existing_row(self):
        selection = self.table.selectedIndexes()

        if len(selection) <= 0:
            return

        row = selection[0].row()

        data = dict()
        for i, key in enumerate(self.definitions.layer_config.keys()):

            cell = self.table.item(row, i)
            value = cell.data(Qt.UserRole)
            data[key] = value

        dialog = self.edition()
        dialog.load_form(data)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            data = dialog.save_form()
            self._edit_row(row, data)

        return result

    def _edit_row(self, row, data):
        """Internal function to edit a row."""
        for i, key in enumerate(data.keys()):
            value = data[key]
            cell = QTableWidgetItem()

            input_type = self.definitions.layer_config[key]['type']

            if input_type == InputType.Layer:
                layer = QgsProject.instance().mapLayer(value)
                cell.setText(layer.name())
                cell.setData(Qt.UserRole, layer.id())
                cell.setIcon(QgsMapLayerModel.iconForLayer(layer))

            elif input_type == InputType.Field:
                cell.setText(value)
                cell.setData(Qt.UserRole, value)

                # Get the icon for the field
                layer_cell = self.table.item(row, 0)
                layer_value = layer_cell.data(Qt.UserRole)
                layer = QgsProject.instance().mapLayer(layer_value)
                if layer:
                    index = layer.fields().indexFromName(value)
                    if index >= 0:
                        cell.setIcon(layer.fields().iconForField(index))

            elif input_type == InputType.CheckBox:
                if value:
                    cell.setText('✓')
                    cell.setData(Qt.UserRole, True)
                else:
                    cell.setText('')
                    cell.setData(Qt.UserRole, False)

            elif input_type == InputType.List:
                cell.setText(value)
                cell.setData(Qt.UserRole, value)

            elif input_type == InputType.SpinBox:
                cell.setText(str(value))
                cell.setData(Qt.UserRole, value)

            else:
                raise Exception('InputType "{}" not implemented'.format(input_type))

            self.table.setItem(row, i, cell)
        self.table.selectRow(row)

    def move_layer_up(self):
        """Move the selected layer up."""
        row = self.table.currentRow()
        if row == 0:
            return
        column = self.table.currentColumn()
        self.table.insertRow(row - 1)
        for i in range(self.table.columnCount()):
            self.table.setItem(row - 1, i, self.table.takeItem(row + 1, i))
            self.table.setCurrentCell(row - 1, column)
        self.table.removeRow(row + 1)

    def move_layer_down(self):
        """Move the selected layer down."""
        row = self.table.currentRow()
        if row == self.table.rowCount() - 1:
            return
        column = self.table.currentColumn()
        self.table.insertRow(row + 2)
        for i in range(self.table.columnCount()):
            self.table.setItem(row + 2, i, self.table.takeItem(row, i))
            self.table.setCurrentCell(row + 2, column)
        self.table.removeRow(row)

    def remove_selection(self):
        """Remove the selected row from the table."""
        selection = self.table.selectedIndexes()
        if len(selection) <= 0:
            return

        row = selection[0].row()
        self.table.clearSelection()
        self.table.removeRow(row)

    def layers_has_been_deleted(self, layer_ids):
        """When some layers have been deleted from QGIS."""
        row = self.table.rowCount()
        for layer in layer_ids:
            for i in range(row):
                cell = self.table.item(0, i)
                value = cell.data(Qt.UserRole)
                if value == layer:
                    self.table.removeRow(i)

    def truncate(self):
        """Truncate the table."""
        self.table.setRowCount(0)

    def use_single_row(self):
        return self.definitions.use_single_row

    def to_json(self):
        data = dict()

        # TODO Lizmap 4
        # data['config'] = dict()

        data['layers'] = list()

        rows = self.table.rowCount()

        export_legacy_single_row = self.definitions.use_single_row and rows == 1

        for row in range(rows):
            layer_data = dict()
            for i, key in enumerate(self.definitions.layer_config.keys()):
                input_type = self.definitions.layer_config[key]['type']
                item = self.table.item(row, i)

                if export_legacy_single_row:
                    key = '{}{}{}'.format(self.definitions.key(), key[0].capitalize(), key[1:])

                if item is None:
                    # Do not put if not item, it might be False
                    raise Exception('Cell is not initialized ({}, {})'.format(row, i))

                cell = item.data(Qt.UserRole)
                if cell is None:
                    # Do not put if not cell, it might be False
                    raise Exception('Cell has no data ({}, {})'.format(row, i))

                if input_type == InputType.Layer:
                    layer_data[key] = cell
                elif input_type == InputType.Field:
                    layer_data[key] = cell
                elif input_type == InputType.CheckBox:
                    # Lizmap 4 #176
                    layer_data[key] = 'True' if cell else 'False'
                elif input_type == InputType.SpinBox:
                    layer_data[key] = cell
                elif input_type == InputType.List:
                    layer_data[key] = cell
                else:
                    raise Exception('InputType "{}" not implemented'.format(input_type))

            if export_legacy_single_row:
                if self.definitions.key() == 'atlas':
                    layer_data['atlasEnabled'] = 'True'
                    layer_data['atlasMaxWidth'] = 25
                return layer_data

            data['layers'].append(layer_data)

        if self.definitions.key() == 'locateByLayer':
            result = {}
            for i, layer in enumerate(data['layers']):
                layer_id = layer.get('layerId')
                vector_layer = QgsProject.instance().mapLayer(layer_id)
                layer_name = vector_layer.name()
                if result.get(layer_name):
                    LOGGER.warning(
                        'Skipping "{}" while saving "{}" JSON configuration. Duplicated entry.'.format(
                            layer_name, self.definitions.key()))
                result[layer_name] = layer
                result[layer_name]['order'] = i

            return result

        return data

    def _from_json_legacy(self, data) -> list:
        """Reformat the JSON data from 3.3 to 3.4 format."""
        layer = {}
        for key in data:
            if not key.startswith(self.definitions.key()):
                continue
            key_def = key[len(self.definitions.key()):]
            key_def = key_def[0].lower() + key_def[1:]
            definition = self.definitions.layer_config.get(key_def)
            if definition:
                layer[key_def] = data[key]

        return [layer]

    @staticmethod
    def _from_json_legacy_order(data):
        new_data = dict()
        new_data['layers'] = []

        def layer_from_order(layers, row):
            for l in layers.values():
                if l['order'] == row:
                    return l

        order = []
        for layer in data.values():
            order.append(layer.get('order'))

        order.sort()

        for i in order:
            new_data['layers'].append(layer_from_order(data, i))

        return new_data

    def from_json(self, data):
        """Load JSON into the table."""
        if self.definitions.key() == 'locateByLayer':
            data = self._from_json_legacy_order(data)

        layers = data.get('layers')

        if not layers:
            layers = self._from_json_legacy(data)

        for layer in layers:
            layer_data = {}
            valid_layer = True
            for key, definition in self.definitions.layer_config.items():
                value = layer.get(key)
                if value:
                    if definition['type'] == InputType.Layer:
                        layer_data[key] = value
                    elif definition['type'] == InputType.Field:
                        layer_data[key] = value
                    elif definition['type'] == InputType.CheckBox:
                        layer_data[key] = True if value in ['true', 'True'] else False
                    elif definition['type'] == InputType.List:
                        layer_data[key] = value
                    elif definition['type'] == InputType.SpinBox:
                        layer_data[key] = value
                    else:
                        raise Exception('InputType "{}" not implemented'.format(definition['type']))
                else:
                    default_value = definition.get('default')
                    if default_value is not None:
                        layer_data[key] = default_value
                    else:
                        # raise InvalidCfgFile(')
                        LOGGER.warning(
                            'In CFG file, section "{}", one layer is missing the key "{}" which is compulsory. Skipping that layer.'.format(
                                self.definitions.key(), key))
                        valid_layer = False
                        continue

            if valid_layer:
                row = self.table.rowCount()
                self.table.setRowCount(row + 1)
                self._edit_row(row, layer_data)
