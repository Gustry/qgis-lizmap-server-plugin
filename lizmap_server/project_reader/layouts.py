__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from typing import Dict, List, Union, Optional

from qgis.core import QgsLayoutItemLabel, QgsLayoutItemAttributeTable
from qgis.core import QgsLayoutItemMap, QgsPrintLayout, QgsProject
from qgis.server import QgsServerProjectUtils

from lizmap_server.logger import Logger


class LayoutReader:

    def __init__(self, project: QgsProject):
        """ Constructor. """
        self.logger = Logger()
        self.project = project
        self.manager = project.layoutManager()
        # noinspection PyArgumentList
        self.excluded_layout = QgsServerProjectUtils.wmsRestrictedComposers(self.project)

    def layout_by_name(self, name: str) -> Union[None, QgsPrintLayout]:
        """ Retrieve the layout by its name.

        Returns None if the layout is not found or if the layout is not published on QGIS server.
        """
        if name in self.excluded_layout:
            return None

        layout = self.manager.layoutByName(name)
        if not layout:
            return None

        return layout

    def layouts(self) -> List[str]:
        """ List of layouts. """
        layouts = self.manager.printLayouts()
        names = []
        for layout in layouts:
            name = layout.name()
            if name in self.excluded_layout:
                continue

            names.append(name)

        return names

    def to_json(self) -> List:
        """ Return the JSON for the project. """
        data = []
        for name in self.layouts():
            data.append(self.data_for_layout(name))
        return data

    def data_for_layout(self, name: str) -> Dict:
        """ JSON representation for a single layout. """
        layout = self.layout_by_name(name)
        pages = layout.pageCollection()
        if pages.pageCount() >= 2:
            self.logger.info(
                f"The layout {name} has more than 1 pages. We take only the first page to compute paper size.")
        page_size = pages.pages()[0].pageSize()
        width = page_size.width()
        height = page_size.height()

        data = {
            'title': name,
            'width': width,
            'height': height,
        }

        # Atlas configuration
        atlas = layout.atlas()
        data_atlas = {
            'enabled': atlas.enabled(),
            'coverage': atlas.coverageLayer().id() if atlas.coverageLayer() else None
        }
        data['atlas'] = data_atlas

        data['maps'] = []
        data['labels'] = []
        data['tables'] = []

        # Loop for all items
        map_counter = 0
        for item in layout.items():
            if isinstance(item, QgsLayoutItemMap):
                data['maps'].append(self._map_item(item, map_counter))
                map_counter += 1

            elif isinstance(item, QgsLayoutItemLabel):
                data['labels'].append({
                    'id': item.id(),
                    'is_html': True if item.mode() == QgsLayoutItemLabel.ModeHtml else False,
                    'text': item.currentText(),
                })

            elif item.type() == "65649":
                print("here")
                data['tables'].append(self._attribute_table_item(item))

            else:
                print(type(item))
            print(item.type())
            print(type(item.type()))

        return data

    @staticmethod
    def _attribute_table_item(item: QgsLayoutItemAttributeTable) -> Dict[str, str]:
        layer = item.vectorLayer()

        data = {
            'display_only_visible_features': item.displayOnlyVisibleFeatures(),
            'composer_map': None,
            'vector_layer': layer.id() if layer else None,
            'vector_layer_name': layer.name() if layer else None,
        }
        linked_map = item.map()
        if not linked_map:
            return data

        data['composer_map'] = linked_map.uuid()
        return data

    @staticmethod
    def _map_item(item: QgsLayoutItemMap, counter: int) -> Dict[str, str]:
        size = item.sizeWithUnits()
        data = {
            'id_desktop': item.id(),
            'id_server': f"map{counter}",
            'uuid': item.uuid(),
            'width': size.width(),
            'height': size.height(),
            'overview_map': None,
            'grid': False,
        }
        for grid in item.grids():
            if not grid:
                continue

            if grid.enabled():
                data['grid'] = True
                # Just one enabled grid is enough
                break

        overview = item.overview()
        if not overview:
            return data

        linked_map = overview.linkedMap()

        if not linked_map:
            return data

        data['overview_map'] = linked_map.uuid()
        return data
