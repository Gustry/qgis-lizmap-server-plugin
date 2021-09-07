__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import configparser
import traceback

from os.path import dirname, join
from typing import Dict

from osgeo import gdal
from qgis.core import Qgis, QgsProject
from qgis.server import (
    QgsServerInterface,
    QgsServerRequest,
    QgsServerResponse,
    QgsService,
)

from lizmap.server.core import (
    find_vector_layer_from_params,
    get_lizmap_config,
    get_lizmap_groups,
    get_lizmap_layers_config,
    get_lizmap_user_login,
    is_editing_context,
    write_json_response,
)
from lizmap.server.exception import ServiceError
from lizmap.server.filter_by_polygon import FilterByPolygon
from lizmap.server.logger import Logger


class LizmapServiceError(ServiceError):
    # def __init__(self, code: str, msg: str, response_code: int = 500) -> None:
    #     super().__init__(code, msg, response_code)
    pass


class LizmapService(QgsService):

    def __init__(self, server_iface: QgsServerInterface) -> None:
        super().__init__()
        self.server_iface = server_iface
        self.logger = Logger()

    # QgsService inherited

    # noinspection PyMethodMayBeStatic
    def name(self) -> str:
        """ Service name
        """
        return 'LIZMAP'

    # noinspection PyMethodMayBeStatic
    def version(self) -> str:
        """ Service version
        """
        return "1.0.0"

    # def allowMethod(self, method: QgsServerRequest.Method) -> bool:
    #     """ Check supported HTTP methods
    #     """
    #     return method in (
    #         QgsServerRequest.GetMethod, QgsServerRequest.PostMethod)

    def executeRequest(self, request: QgsServerRequest, response: QgsServerResponse,
                       project: QgsProject) -> None:
        """ Execute a 'LIZMAP' request
        """

        params = request.parameters()

        # noinspection PyBroadException
        try:
            req_param = params.get('REQUEST', '').upper()

            try:
                bytes(request.data()).decode()
            except Exception:
                raise LizmapServiceError(
                    "Bad request error",
                    "Invalid POST DATA for '{}'".format(req_param),
                    400)

            if req_param == 'GETSERVERSETTINGS':
                self.get_server_settings(params, response, project)
            elif req_param == 'GETSUBSETSTRING':
                self.polygon_filter(params, response, project)
            else:
                raise LizmapServiceError(
                    "Bad request error",
                    "Invalid REQUEST parameter: must be one of GETSERVERSETTINGS, found '{}'".format(
                        req_param),
                    400)

        except LizmapServiceError as err:
            err.formatResponse(response)
        except Exception as e:
            self.logger.critical("Unhandled exception:\n{}".format(traceback.format_exc()))
            self.logger.critical(str(e))
            err = LizmapServiceError("Internal server error", "Internal 'lizmap' service error")
            err.formatResponse(response)

    def polygon_filter(
            self, params: Dict[str, str], response: QgsServerResponse, project: QgsProject) -> None:
        """ The subset string to use a on a layer."""
        flag, layer = find_vector_layer_from_params(params, project)
        if not flag:
            raise ServiceError("Bad request error", "Invalid LAYER parameter", 400)

        # Get Lizmap user groups provided by the request
        groups = get_lizmap_groups(self.server_iface.requestHandler())
        user_login = get_lizmap_user_login(self.server_iface.requestHandler())

        # If groups is empty, no Lizmap user groups provided by the request
        if len(groups) == 0 and not user_login:
            write_json_response({}, response)
            return

        # If headers content implies to check for filter, read the Lizmap config
        # Get Lizmap config
        cfg = get_lizmap_config(self.server_iface.configFilePath())
        if not cfg:
            write_json_response({}, response)
            return

        # Get layers config
        cfg_layers = get_lizmap_layers_config(cfg)
        if not cfg_layers:
            write_json_response({}, response)
            return

        # Get layer name
        layer_name = layer.name()
        # Check the layer in the CFG
        if layer_name not in cfg_layers:
            write_json_response({}, response)
            return

        # 1 = 0 results in a "false" in OGR/PostGIS
        # ET : I didn't find a proper false value in OGR
        body = {
            'filter': '1 = 0',
        }

        try:
            edition_context = is_editing_context(self.server_iface.requestHandler())
            filter_polygon_config = FilterByPolygon(cfg.get("filter_by_polygon"), layer, edition_context)
            if filter_polygon_config.is_filtered():
                if not filter_polygon_config.is_valid():
                    Logger.critical(
                        "The filter by polygon configuration is not valid.\n All features are hidden.")
                    write_json_response(body, response)
                    return
                else:
                    # polygon_filter is set, we have a value to filter
                    body = {
                        'filter': filter_polygon_config.subset_sql(groups),
                    }
                    write_json_response(body, response)
                    return

        except Exception as e:
            Logger.log_exception(e)
            Logger.critical(
                "An error occurred when trying to read the filtering by polygon.\nAll features are hidden.")
            write_json_response(body, response)

    def get_server_settings(
            self, params: Dict[str, str], response: QgsServerResponse, project: QgsProject) -> None:
        """ Get Lizmap Server settings
        """
        _ = params
        _ = project

        # create the body
        body = {
            'qgis': {},
            'gdalogr': {},
            'services': [],
            'lizmap': {},
        }

        # QGIS info
        qgis_version_split = Qgis.QGIS_VERSION.split('-')
        body['qgis']['version'] = qgis_version_split[0]
        body['qgis']['name'] = qgis_version_split[1]
        body['qgis']['version_int'] = Qgis.QGIS_VERSION_INT

        # GDAL/OGR
        body['gdalogr']['name'] = gdal.VersionInfo('NAME')
        body['gdalogr']['version_int'] = gdal.VersionInfo('VERSION_NUM')

        reg = self.server_iface.serviceRegistry()
        services = ['WMS', 'WFS', 'WCS', 'WMTS', 'ATLAS', 'CADASTRE', 'EXPRESSION', 'LIZMAP']
        for s in services:
            if reg.getService(s):
                body['services'].append(s)

        # Lizmap plugin metadata, do not use qgis_plugin_tools because of the packaging.
        file_path = join(dirname(dirname(__file__)), 'metadata.txt')
        config = configparser.ConfigParser()
        try:
            config.read(file_path, encoding='utf8')
        except UnicodeDecodeError:
            # Issue LWC https://github.com/3liz/lizmap-web-client/issues/1908
            # Maybe a locale issue ?
            self.logger.critical(
                "Error, an UnicodeDecodeError occurred while reading the metadata.txt. Is the locale "
                "correctly set on the server ?")
            version = 'NULL'
        else:
            version = config["general"]["version"]

        body['lizmap']['name'] = 'Lizmap'
        body['lizmap']['version'] = version

        write_json_response(body, response)
        return
