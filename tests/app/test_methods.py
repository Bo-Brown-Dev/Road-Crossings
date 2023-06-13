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

        ox.settings.use_cache=False

        #self.expected_buffer = pd.read_pickle(
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


    def test_parseMovingPandas(self):

        gdf_list = App.parseMovingPandas(self, self.case_input)

        self.assertIsInstance(gdf_list, list)

        points, track_lines, buffer = gdf_list

        expected_buffer = gpd.GeoDataFrame(
            self.expected_lines,
            geometry=self.expected_lines.to_crs(crs=3857).buffer(1000)).dissolve().to_crs(crs=4326)


        for gdf in gdf_list:
            self.assertIsInstance(gdf, gpd.GeoDataFrame)

        # Check if all geometries in each gdf are of appropriate geom_type (Point, LineString, Polygon)
        expected_geom_types = ['Point', 'LineString', 'Polygon']

        for i, gdf in enumerate(gdf_list):
            self.assertTrue(gdf.geometry.geom_type.eq(expected_geom_types[i]).all())

        # check that method output geometry matches output from test_case
        self.assertTrue(points.geometry.eq(self.expected_points.geometry).all())

        self.assertTrue(track_lines.geometry.eq(self.expected_lines.geometry).all())

        self.assertTrue(buffer.geometry.eq(expected_buffer.geometry).all())

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

        actual = App.getRoads(white_house)
        """
        Comparison:
        Finally, we compare the actual dataframe to the expected dataframe using an inner merge. if the length of the
        dataframe does not change after merging, then we have a 1 to 1 match on osmid and geometry, which is a pass.
        
        """

        OSMnx_check = pd.merge(actual, expected, on=('osmid', 'geometry'), how='inner', indicator=True)

        self.assertEqual(len(actual), len(OSMnx_check))

    def test_findCrossings(self):
        roads = pd.read_pickle(os.path.join(ROOT_DIR, r'tests/resources/local_app_files/provided_only/provided-app-files/roads_gabs_23.pickle'))
        tracks = pd.read_pickle(os.path.join(ROOT_DIR, r'tests/resources/local_app_files/provided_only/provided-app-files/tracks_gabs_23.pickle'))
        tracks = tracks.to_crs(roads.crs)

        actual = App.findCrossings(roads, tracks)

        expected = pd.read_pickle(os.path.join(ROOT_DIR, r'tests/resources/local_app_files/provided_only/provided-app-files/crossings_gabs_23.pickle'))

        # checks that the count of the calculated df is equal to count of expected df
        self.assertCountEqual(actual, expected)

        # checks that the geometry of the actual df is equal to
        self.assertTrue(actual.geometry.eq(expected.geometry).all())

    def test_insertCrossings(self):

        expected = self.expected_output
        expected_points = expected.to_point_gdf()
        expected_lines = expected.to_line_gdf()

        actual = App.insertCrossings(
                                     self.expected_points,
                                     self.expected_crossings,
                                     self.given_roads
        )

        actual_points = actual.to_point_gdf()
        actual_lines = actual.to_line_gdf()

        self.assertTrue(
            expected_points.geometry.eq(actual_points.geometry).all()
        )

        self.assertTrue(
            expected_lines.geometry.eq(actual_lines.geometry).all()
        )

    def test_CreateMap(self):
        m = App.createMap(self.expected_lines, self.given_roads, self.expected_crossings)

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
