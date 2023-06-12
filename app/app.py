from sdk.moveapps_spec import hook_impl
from movingpandas import TrajectoryCollection
import pandas as pd
import geopandas as gpd
from geopandas import GeoDataFrame
import movingpandas as mpd
import osmnx as ox
import shapely
from shapely.geometry import linestring, point, polygon
from folium import Map


class App(object):

    def __init__(self, moveapps_io):
        self.moveapps_io = moveapps_io

    @hook_impl
    def execute(self, data: TrajectoryCollection, config: dict) -> TrajectoryCollection:
        """Your app code goes here"""

        print('starting')

        parsed_data: list[GeoDataFrame] = self.parseMovingPandas(data)

        print('data parsed')

        track_points: GeoDataFrame[point] = parsed_data[0]

        track_lines: GeoDataFrame[linestring] = parsed_data[1]

        track_buffer: GeoDataFrame[polygon] = parsed_data[2]

        OSM_roads = self.getRoads(track_buffer)  # Ingesting roads data from OSM

        print('got roads')

        track_lines = track_lines.to_crs(OSM_roads.crs)  # Converting to like CRS

        # Take points where Animal Movement LineStrings cross paths with roads from OSM:
        crossing_points = self.findCrossings(OSM_roads, track_lines)

        print('found crossings')

        crossing_points.to_csv(self.moveapps_io.create_artifacts_file('Crossing Points.csv'))

        print('saved CSV')

        # Inserting crossing points to trajectories with 'mid_t' as the midpoint of 't' and 'prev_t':
        new_collection = self.insertCrossings(track_points, crossing_points, OSM_roads)

        print('inserted crossing points')

        # Creating map with the following layers:
        m = self.createMap(track_lines, OSM_roads, crossing_points)

        # saving map to artefacts
        m.save(self.moveapps_io.create_artifacts_file('Crossings_Map.html'))

        print('saved map')

        # Creating Geopackage with same layers as above
        self.saveGeopackage(track_lines, OSM_roads, crossing_points)

        print('saved GPKG')
        # return some useful data for next apps in the workflow

        return new_collection

    def parseMovingPandas(self, data: TrajectoryCollection) -> list[GeoDataFrame]:

        if type(data) == TrajectoryCollection:
            movingpandas = data
        elif type(data) == str:
            movingpandas = pd.read_pickle(data)

        dtype_conversion = {
            'prev_t': str,
            't': str,
            'timestamps': str
        }

        points = movingpandas.to_point_gdf()

        lines = movingpandas.to_line_gdf().astype(dtype_conversion).set_crs(points.crs)

        buffers = gpd.GeoDataFrame(
            lines,
            geometry=lines.to_crs(crs=3857).buffer(1000)).dissolve().to_crs(crs=4326)

        return [points, lines, buffers]

    # noinspection PyUnresolvedReferences
    @staticmethod
    def getRoads(buffers: GeoDataFrame):
        graph = ox.graph_from_polygon(
            buffers.geometry[0],
            network_type='all_private',  # includes all roads, private or not
            truncate_by_edge=True,  # includes roads that are not fully contained in geometry
            retain_all=True,
            simplify=False)  # curves of roads and self-intersections will be nodes, but
        # we don't include nodes in our map, so the function is to reduce length of lines in resulting set of roads

        roads = ox.utils_graph.graph_to_gdfs(graph, nodes=False)

        return roads

    @staticmethod
    def findCrossings(roads, tracks):
        crossings = gpd.overlay(
            roads,
            tracks,
            how='intersection',
            keep_geom_type=False
        )

        crossings.geometry = crossings.geometry.apply(
            lambda x: shapely.geometry.MultiPoint(list(x.coords)))

        crossings = crossings.explode(index_parts=True).drop_duplicates(subset=['event.id', 'osmid'])

        crossings['crossing_point'] = True
        half_timestamp_range = (
                (pd.to_datetime(crossings['t']) - pd.to_datetime(crossings['prev_t'])) / 2
        )
        crossings['mid_t'] = (pd.to_datetime(crossings['prev_t']) + half_timestamp_range).astype(str)
        return crossings

    @staticmethod
    def createMap(
                  tracks: GeoDataFrame,
                  roads: GeoDataFrame,
                  crossings: GeoDataFrame) -> Map:

        m = tracks.explore()  # Animal Movement
        m = roads.explore(  # Roads
            m=m,
            color="black",
            name="roads")

        m = crossings.explore(m=m,  # points of road crossings
                              color='red',
                              name='crossings')
        return m

    def saveGeopackage(self,
                       tracks: GeoDataFrame,
                       roads: GeoDataFrame,
                       crossings: GeoDataFrame) -> None:

        crossings.to_file(
            self.moveapps_io.create_artifacts_file("Crossings.gpkg")
            , layer='Intersection_Points'
            , driver='GPKG'
        )

        roads.to_file(
            self.moveapps_io.create_artifacts_file("Crossings.gpkg")
            , layer='roads'
            , driver='GPKG'
        )

        tracks.to_file(
            self.moveapps_io.create_artifacts_file("Crossings.gpkg")
            , layer='track_lines'
            , driver='GPKG'
        )

    @staticmethod
    def insertCrossings(
            track_points: GeoDataFrame,
            crossings: GeoDataFrame,
            roads: GeoDataFrame) -> TrajectoryCollection:

        track_points['crossing_point'] = False

        crossing_columns = crossings.columns
        track_columns = track_points.columns

        track_points = track_points[track_points.columns.intersection(crossing_columns.union(['timestamps']))].to_crs(roads.crs)

        crossings = crossings[crossings.columns.intersection(
            track_columns.union(roads.columns).union(['t', 'prev_t', 'mid_t'])
            )].set_crs(crossings.crs)

        crossings.to_crs(roads.crs)

        new_points = pd.concat([track_points, crossings])

        new_points['merged_t'] = new_points['mid_t']

        new_points['merged_t'] = new_points['merged_t'].fillna(new_points['timestamps'])

        new_points = new_points.sort_values(by=['individual.id', 'merged_t'])

        new_collection = mpd.TrajectoryCollection(
            data=new_points,
            traj_id_col='individual.id',
            t='merged_t')
        return new_collection



# todo: make a small library to assist with parsing and seperating the points inserted by the output of the app
# todo: Write Documentation
