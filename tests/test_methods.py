import unittest
import os
import pandas as pd
import geopandas as gpd
import osmnx as ox
import shapely
import time
from sdk.moveapps_io import MoveAppsIo

from tests.config.definitions import ROOT_DIR
from folium import Map
from shapely.geometry import Point
import logging
from app.app import App

from sdk.moveapps_io import MoveAppsIo
from movingpandas import TrajectoryCollection

from html.parser import HTMLParser


class TestApp(unittest.TestCase):

    def setUp(self) -> None:
        os.environ['APP_ARTIFACTS_DIR'] = os.path.join(ROOT_DIR, r'tests/resources/output')
        self.sut = App(moveapps_io=MoveAppsIo())

        self.case_input = pd.read_pickle(
            os.path.join(ROOT_DIR,
                         r'tests/resources/local_app_files/provided_only/provided-app-files/input1.pickle'
                         )
        )

        self.expected_points = pd.read_pickle(
            os.path.join(ROOT_DIR,
                         r'tests/resources/local_app_files/provided_only/provided-app-files/points_gabs_23.pickle'
                         )
        )

        self.expected_lines = pd.read_pickle(
            os.path.join(ROOT_DIR,
                         r'tests/resources/local_app_files/provided_only/provided-app-files/tracks_gabs_23.pickle'
                         )
        )

        ox.settings.use_cache = False

        # self.expected_buffer = pd.read_pickle(
        #  os.path.join(ROOT_DIR, r'tests/resources/local_app_files/provided_only/provided-app-files/buffers_gabs_23.pickle'
        #               ))

        self.expected_crossings = pd.read_pickle(
            os.path.join(ROOT_DIR,
                         r'tests/resources/local_app_files/provided_only/provided-app-files/crossings_gabs_23.pickle'
                         )
        )

        self.given_roads = pd.read_pickle(
            os.path.join(ROOT_DIR,
                         r'tests/resources/local_app_files/provided_only/provided-app-files/roads_gabs_23.pickle'
                         )
        )

        self.expected_output = pd.read_pickle(
            os.path.join(ROOT_DIR,
                         r'tests/resources/local_app_files/provided_only/provided-app-files/MPDPostInsert_gabs_23.pickle'
                         )
        )

    """
    Because the alternate method for acquiring roads uses a different buffer method, using the same buffer
    and checking for an exact match would result in a brittle test that would be subject to a change in a node or edge
    at the edge of the buffer. 

    Instead, we query our baseline roads by a larger buffer and check that our function is contained by the set.




    """

    def test_getRoads(self):
        """
        Expected:
        As a baseline to test the function,
        the test below uses an alternative method to get roads within 1500 meters of the OSM geocoded loc of the White House

        """

        graph = ox.graph_from_address(
            '1600 Pennsylvania Avenue NW, Washington, D.C.',
            dist=1500,
            dist_type='bbox',
            network_type='all_private',  # includes all roads, private or not
            truncate_by_edge=True,
            retain_all=True,  # includes roads that are not fully contained in geometry
            simplify=False)  # curves of roads and self-intersections will be nodes, but
        # we don't include nodes in our map, so the function is to reduce length of lines in resulting set of roads

        expected = ox.utils_graph.graph_to_gdfs(graph, nodes=False)

        """
        Actual:
        We query a shapely polygon representation of the White House from the OpenStreetMap geocoded place.
        We take all roads within 1000 meters of any point in the White House polygon.

        """

        white_house = ox.geocode_to_gdf('W238241022', by_osmid=True,
                                        ).to_crs(3857).buffer(1000)

        white_house = white_house.to_crs(4326)

        actual = App.get_roads(white_house.geometry[0])
        """
        Comparison:
        Finally, we compare the actual dataframe to the expected dataframe using an inner merge. if the length of the
        dataframe does not change after merging, then we have a 1 to 1 match on osmid and geometry, which is a pass.

        """

        OSMnx_check = pd.merge(actual, expected, on=('osmid', 'geometry'), how='inner', indicator=True)

        self.assertEqual(len(actual), len(OSMnx_check))

    def test_findCrossings(self):
        roads = pd.read_pickle(os.path.join(ROOT_DIR,
                                            r'tests/resources/local_app_files/provided_only/provided-app-files/roads_gabs_23.pickle'))
        tracks = pd.read_pickle(os.path.join(ROOT_DIR,
                                             r'tests/resources/local_app_files/provided_only/provided-app-files/tracks_gabs_23.pickle'))
        tracks = tracks.to_crs(roads.crs)

        actual = App.find_crossings(roads, tracks)

        expected = pd.read_pickle(os.path.join(ROOT_DIR,
                                               r'tests/resources/local_app_files/provided_only/provided-app-files/crossings_gabs_23.pickle'))

        # checks that the count of the calculated df is equal to count of expected df
        self.assertCountEqual(actual, expected)

        # checks that the geometry of the actual df is equal to
        self.assertTrue(actual.geometry.eq(expected.geometry).all())

    def test_insertCrossings(self):
        # I need to sort the values of the dataframe by the OSM ID, so I need to add the OSMID when I find the crossings

        expected_points_output = self.expected_output.to_point_gdf()
        expected_lines = self.expected_output.to_line_gdf()

        actual = App.insertCrossings(self,
                                     App.get_points(self, self.case_input),
                                     self.expected_crossings,
                                     self.case_input
                                     )

        actual_points = actual.to_point_gdf()
        actual_lines = App.get_tracks(self, actual)

        self.assertTrue(
            expected_points_output.geometry.eq(actual_points.geometry).all()
        )

        self.assertTrue(
            expected_lines.geometry.eq(actual_lines.geometry).all()
        )

    def test_CreateMap(self):
        m = App.createMap(App, self.expected_lines, self.given_roads, self.expected_crossings)

        self.assertIsInstance(m, Map)

        map_path = os.path.join(ROOT_DIR, r'tests/resources/output/test_map.html')

        m.save(map_path)

        self.assertTrue(
            os.path.isfile(map_path)
        )

    def test_createGeoPackage(self):
        self.sut.saveGeopackage(self.expected_lines, self.given_roads, self.expected_crossings)

        actual = gpd.read_file(
            os.path.join(ROOT_DIR, 'tests/resources/output/Crossings.gpkg')
        )

        expected = gpd.read_file(os.path.join(
            ROOT_DIR,
            r'tests/resources/local_app_files/provided_only/provided-app-files/geopackage_gabs_23.gpkg'))

        self.assertTrue(expected.geometry.eq(actual.geometry).all())


if __name__ == '__main__':
    unittest.main()
