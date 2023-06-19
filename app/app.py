from sdk.moveapps_spec import hook_impl
from movingpandas import TrajectoryCollection
import pandas as pd
import geopandas as gpd
from geopandas import GeoDataFrame
import movingpandas as mpd
import osmnx as ox
import shapely
from shapely.geometry import linestring, point, polygon
import folium
from folium import Map
import sys
import tracemalloc
import logging


class App(object):

    def __init__(self, moveapps_io,):
        self.moveapps_io = moveapps_io

    common_crs = 4326
    proj_crs = 3857

    @hook_impl
    def execute(self, data: TrajectoryCollection, config: dict) -> TrajectoryCollection:
        """Your app code goes here"""

        ox.settings.use_cache = False

        tracemalloc.start()

        logging.info('\n-_-_-_-_-_- Road Crossings -_-_-_-_-_- \n'
                      '_____________________________________')




        OSM_roads = self.get_roads(self.get_buffers(data))

        self.memory_check('Buffers & Roads')

        crossing_points = self.find_crossings(
            OSM_roads,
            self.get_tracks(self, data).to_crs(OSM_roads.crs)
        )

        self.memory_check('Found Crossings')

        logging.info('found %s crossings', len(crossing_points.index))

        crossing_points.to_csv(
            self.moveapps_io.create_artifacts_file('Crossing Points.csv')
        )

        logging.info('saved CSV')



        # Creating map with the following layers:
        self.createMap(self,
            self.get_tracks(self, data),
            OSM_roads,
            crossing_points)


        # saving map to artefacts


        self.memory_check('Save Map')

        # Creating Geopackage with same layers as above
        self.saveGeopackage(
            self.get_tracks(self, data),
            OSM_roads,
            crossing_points
        )

        self.memory_check('Final Output')


        # Inserting crossing points to trajectories with 'mid_t' as the midpoint of 't' and 'prev_t':

        # return some useful data for next apps in the workflow
        return self.insertCrossings(
            self.get_points(self, data),
            crossing_points,
            data
        )
    @staticmethod
    def get_tracks(self, data) -> GeoDataFrame:

        dtype_conversion = {'prev_t': str, 't': str, 'timestamps': str}

        return data.to_line_gdf()[
            ['event.id',
            'deployment.id',
            'tag.id',
            'trackId',
            'individual.id',
            'timestamps',
            't',
            'prev_t',
            'geometry'
             ]
        ].astype(
            dtype_conversion
        ).set_crs(data.trajectories[0].crs)
    @staticmethod
    def get_points(self, data) -> GeoDataFrame:

        return data.to_point_gdf()[
            ['event.id',
             'trackId',
             'deployment.id',
             'tag.id',
             'individual.id',
             'timestamps',
             'geometry'
             ]
        ].set_crs(data.trajectories[0].crs)

    @staticmethod
    def get_buffers(data):

        logging.info('\n\n--- Creating Buffers ---')

        logging.info('\textracting buffer lines')
        buffers = gpd.GeoSeries(
            data.to_line_gdf().geometry, crs=data.trajectories[0].crs)



        buffers = buffers.to_crs(crs=3857)
        logging.info('\tdrawing buffer polygons')

        buffers = buffers.buffer(1000)


        buffers = gpd.GeoSeries(shapely.geometry.MultiPolygon([shape for shape in buffers]), crs=3857)

        buffers = buffers.to_crs(crs=4326)
        logging.info('\tcalculating union of buffers')
        buffers = buffers.unary_union
        logging.info('\tFound Buffers')
        return buffers

    @staticmethod
    def get_roads(buffers: GeoDataFrame):
        graph = ox.graph_from_polygon(
            buffers,
            network_type='all_private',  # includes all roads, private or not
            truncate_by_edge=True,  # includes roads that are not fully contained in geometry
            retain_all=True,
            simplify=False)  # curves of roads and self-intersections will be nodes, but
            # we don't include nodes in our map, so the function is to reduce length of lines in resulting set of roads

        roads = ox.utils_graph.graph_to_gdfs(graph, nodes=False)

        return roads

    def memory_check(self, checkpoint: str):

        size, peak = tracemalloc.get_traced_memory()
        logging.debug('%s Checkpoint ---- Memory Stats:', checkpoint)
        logging.debug('\t %s size: %s Mb', checkpoint, size / 1000000)
        logging.debug('\t %s peak: %s Mb', checkpoint, peak / 1000000)

    @staticmethod
    def find_crossings(roads, tracks):

        logging.info('--- Finding Crossing Points ---')

        logging.info('\t Overlaying Geometries')
        crossings = gpd.overlay(
            roads.to_crs(crs = App.common_crs),
            tracks.to_crs(crs = App.common_crs),
            how='intersection',
            keep_geom_type=False
        )

        logging.info('\t Extracting Crossing Points')
        crossings.geometry = crossings.geometry.apply(
            lambda x: shapely.geometry.MultiPoint(list(x.coords)))
        crossings = crossings.explode(index_parts=True).drop_duplicates(subset=['event.id', 'osmid',])

        logging.info('\t Calculating timestamp midpoints')
        crossings['crossing_point'] = True
        half_timestamp_range = (
                (pd.to_datetime(crossings['t']) - pd.to_datetime(crossings['prev_t'])) / 2
        )
        crossings['mid_t'] = (pd.to_datetime(crossings['prev_t']) + half_timestamp_range).astype('datetime64[ns]')
        return crossings

    @staticmethod
    def createMap(self,
                  tracks: GeoDataFrame,
                  roads: GeoDataFrame,
                  crossings: GeoDataFrame) -> Map:

        m = tracks.explore(name = 'Tracks',
                           color='darkcyan')  # Animal Movement

        m = roads.explore(  # Roads
            m=m,
            color="black",
            name="roads")

        m = crossings.astype({'mid_t': str, 'timestamps': str}).explore(m=m,  # points of road crossings
                              color='red',
                              name='crossings')

        folium.LayerControl().add_to(m)
        m.save(self.moveapps_io.create_artifacts_file('Crossings_Map.html'))

        return m

    def saveGeopackage(self,
                       tracks: GeoDataFrame,
                       roads: GeoDataFrame,
                       crossings: GeoDataFrame) -> None:

        logging.info('Writing to Geopackage')

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


    def insertCrossings(self,
                        track_points: GeoDataFrame,
                        crossings: GeoDataFrame,
                        data) -> TrajectoryCollection:

        track_points['crossing_point'] = False

        track_points = track_points.to_crs(self.common_crs)
        crossings = crossings.to_crs(self.common_crs)

        new_points = pd.concat([track_points, crossings])

        new_points['merged_t'] = new_points['mid_t']

        new_points['merged_t'] = new_points['merged_t'].fillna(new_points.index.to_series()).astype('datetime64[ns]')

        new_points = new_points.sort_values(by=['individual.id', 'merged_t'])

        new_collection = mpd.TrajectoryCollection(
            data=new_points,
            traj_id_col='trackId',
            t='merged_t')
        logging.info('inserted crossing points')
        return new_collection



# todo: make a small library to assist with parsing and seperating the points inserted by the output of the app
# todo: Write Documentation
