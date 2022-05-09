__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

""" Test read QGIS layouts. """


import unittest

from pathlib import Path

from qgis.core import QgsProject

from lizmap_server.project_reader.layouts import LayoutReader


class TestReadLayouts(unittest.TestCase):

    maxDiff = None

    def test_core_read_projet(self):
        project_path = Path('data/print_layout.qgs')
        self.assertTrue(project_path.is_file())
        project = QgsProject()
        project.read(str(project_path))
        layout_manager = project.layoutManager()
        self.assertEqual(3, len(layout_manager.layouts()))

        reader = LayoutReader(project)

        self.assertIsNone(reader.layout_by_name("does not exist"))

        # Not published
        self.assertIsNotNone(layout_manager.layoutByName("excluded"))
        self.assertIsNone(reader.layout_by_name("excluded"))
        self.assertListEqual(['excluded'], reader.excluded_layout)

        # List of layouts
        self.assertListEqual(['A4 portrait not atlas', 'A4 landscape atlas'], reader.layouts())

        # A4 portrait not atlas
        expected = {
            'atlas': {
                'coverage': None,
                'enabled': False,
            },
            'height': 297.0,
            'labels': [
                {'id': '', 'is_html': False, 'text': 'Table not linked to map'},
                {'id': '', 'is_html': False, 'text': 'Map 2'},
                {'id': '', 'is_html': False, 'text': 'Map 1'},
                {'id': '', 'is_html': False, 'text': 'Table linked to map'},
                {'id': 'HTML subtitle', 'is_html': True, 'text': 'Long HTML text with UUID'},
                {'id': '', 'is_html': False, 'text': 'Label with uuid : "title"'},
                {'id': '', 'is_html': False, 'text': 'Overview map 1'},
                {'id': '', 'is_html': False, 'text': 'Label without uuid'}
            ],
            'maps': [
                {
                    'grid': True,
                    'height': 39.83723322751999,
                    'id_desktop': 'Carte 3',
                    'id_server': 'map0',
                    'overview_map': None,
                    'uuid': '{d81679dc-8ac8-4e9d-afc8-6486275607e5}',
                    'width': 198.844
                }, {
                    'grid': True,
                    'height': 40.77699122668595,
                    'id_desktop': 'Carte 2',
                    'id_server': 'map1',
                    'overview_map': '{c7d74f11-40e3-4df7-9ea0-fad6fc84c3df}',
                    'uuid': '{337fe57c-ca74-4ec5-8256-f956e735a5af}',
                    'width': 104.515
                }, {
                    'grid': True,
                    'height': 45.63113936430317,
                    'id_desktop': 'Carte 1',
                    'id_server': 'map2',
                    'overview_map': None,
                    'uuid': '{c7d74f11-40e3-4df7-9ea0-fad6fc84c3df}',
                    'width': 198.544
                }
            ],
            'tables': [],
            'title': 'A4 portrait not atlas',
            'width': 210.0
        }
        self.assertDictEqual(expected, reader.data_for_layout('A4 portrait not atlas'))

        # # A4 landscape atlas
        # expected = {
        #     'title': 'A4 landscape atlas',
        #     'width': 297.0,
        #     'height': 210.0,
        #     'atlas': {
        #         'enabled': True,
        #         'coverage': 'shop_bakery_498504eb_e818_4f86_af4c_3c7a02ed047c'
        #     },
        #     'maps': [{
        #         'id_desktop': 'Carte 3',
        #         'id_server': 0,
        #         'uuid': '{113c4c5f-f59a-4ad9-b23f-2f58b9751395}',
        #         'width': 142.921,
        #         'height': 39.83715490559831,
        #         'overview_map': None,
        #         'grid': True
        #     }, {
        #         'id_desktop': 'Carte 2',
        #         'id_server': 1,
        #         'uuid': '{4265874a-0f08-46be-a54d-85735d666f89}',
        #         'width': 104.515,
        #         'height': 40.77699122668595,
        #         'overview_map': '{5ac72656-dcf5-4a55-93cf-e35fc7e1674e}',
        #         'grid': True
        #     }, {
        #         'id_desktop': 'Carte 1',
        #         'id_server': 2,
        #         'uuid': '{5ac72656-dcf5-4a55-93cf-e35fc7e1674e}',
        #         'width': 142.706,
        #         'height': 45.63129104576091,
        #         'overview_map': None,
        #         'grid': True
        #     }],
        #     'labels': [
        #         {'id': '', 'is_html': False, 'text': 'Map 2'},
        #         {'id': '', 'is_html': False, 'text': 'Map 1'},
        #         {'id': 'HTML subtitle', 'is_html': True, 'text': 'Long HTML text with UUID'},
        #         {'id': '', 'is_html': False, 'text': 'Label with uuid : "title"'},
        #         {'id': '', 'is_html': False, 'text': 'Overview map 1'},
        #         {'id': '', 'is_html': False, 'text': 'Label without uuid'}
        #     ],
        #     'tables': []
        # }
        # result = reader.data_for_layout('A4 landscape atlas')
        # self.assertDictEqual(expected, result, result)
        assert False


if __name__ == '__main__':
    suite = unittest.makeSuite(TestReadLayouts, 'test')
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
