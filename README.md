# Road Crossings

MoveApps

Github repository: *https://github.com/Bo-Brown-Dev/Road-Crossings.git*


## Description
Takes input of animal movement data and runs analysis with roads data from OpenStreetMap to find points where animals 
crossed a road. Map data is queried from OpenStreetMap and available  for the entire globe at a spatial resolution of 10 meters (per OpenStreetMap)



## Documentation
Road Crossings is an app that takes animal movement data in the form of a movingpandas TrajectoryCollection and 
synthesizes data on where and when animals crossed a road.

### Quick Start Guide

#### Setup:

While the analysis is flexible in terms of scope and can take input data from anywhere in the world, it also 
intentionally performs some complex geospatial operations that can cause the app to run slower with large datasets. 
This is especially true for datasets that span greater distances or are centered in urban areas with a lot of roads. 
Follow the steps below if experiencing slow performance within a work-flow.

- #### Consider filtering spatially:
  The app will work quicker with datasets that span a smaller range. Conducting analysis 
  for as many animals as possible within one region at a time will result in the most efficient workflow. 
  This will always improve performance but should only be necessary when working with very large datasets.

- #### Remove unused or blank columns:
  When a crossing is found, the app associates the Animal Tracking data with attributes from the road that was crossed.
  Removing columns will greatly reduce clutter when interpreting the resulting dataset and help the app to run faster.

- #### Convert your data to TrajectoryCollection:
    The app accepts input strictly in the form of a movingpandas TrajectoryCollection. To make sure your data is in the 
proper format, it is recommended that you get the data via a workflow in the proper format or convert it using the 
MoveBank app for that purpose.

Follow these steps, and you are ready to run the app.

#### Results:
**for information on artifacts available for download, scroll down to see the 
"artifacts" section below.*

The resulting output of the app will be a TrajectoryCollection with points of Road Crossings inserted into the Lines 
that make up each individual's Trajectory. The timestamps of these points is estimated as the mid-point of the Timestamps
before and after the crossing.



For instance, consider the following case:
- an individual's coordinates are recorded as (0,0) at 6:00 PM.
- The individual is recorded with coordinates (4,4) 1 hour later at 7:00 PM.
- The straight line that connects these two points intersects with a road at location (1,1)

In this case, a road crossing point will be inserted in the animal's path at the coordinates of the intersection (1,1). 
The point will have the attributes of the road that was crossed and the individual who crossed it.
The timestamp for this crossing is not knowable, but is estimated as halfway between the start timestamp and end 
timestamp of that line at 6:30 PM. 

**Note that for a TrajectoryCollection to be output, the timestamp must be estimated to preserve the order of movement 
in the resulting dataset. This data can be easily filtered out using the True / False "CrossingPoint?" column.*

### User Guide & Reference

#### Roads Data:
Roads are processed as a collection of LineString data with some helpful attributes that can be informative when 
evaluating crossings. OpenStreetMap is used to retrieve roads as LineStrings via the Overpass API. This is facilitated
by the OSMnx library. Note the following features:
* 10-meter Geospatial Resolution
* Roads are selected dynamically to optimize performance
* Helpful data points that can tell you:
  * The type of road
  * bridges
  * tunnels
  * speed limit
  * width
  * access (private or public)
* More info on any given road or it's surroundings can be found via OpenStreetMap using the osmID

#### Animal Movement Data:
For animal movement data, the app accepts strictly the output of a preceding app in the format of a movingpandas
TrajectoryCollection (the pickle file output from the translator app). 

The TrajectoryCollection is broken into three dataframes:

* **Track Points:** The collection of point locations of each unique Animal ID and timestamp pair.
<br></br>

* **Track Lines:** A collection of LineStrings made by connecting each point from the Track Points collection to the associated
animal's next location by timestamp.
  ![Tracks Only Reference](https://github.com/Bo-Brown-Dev/Road-Crossings/assets/116322660/886f4204-074d-413c-9f77-760c29b28a47)


<br></br>
<br></br>

* **Track Buffer:** A single geometry representing the area within a 1000-meter radius of any point on the LineStrings 
in the Track Lines collection. The buffer creates a collection of Polygons which are all dissolved into a single Polygon.
This polygon is used later as the shape to query roads data from OpenStreetMap.

  *(See below for more info)*
![Tracks With Buffers Reference](https://github.com/Bo-Brown-Dev/Road-Crossings/assets/116322660/6d59bb8d-4925-49a1-8c82-e54f72de9b96)

  ![Uploading Tracks With Buffers Reference.png…]()

<br></br>
<br></br>

* **Retrieving roads from OSM:** The polygon is then used in a request to the Overpass API as a bounding polygon.
The app only selects roads from within the polygon, which greatly reduces the processing power needed to ingest and 
analyze the roads data. Since the polygon is 1000 meters from any point on our tracking lines, the API returns all roads within 1 kilometer of 
our tracking data.

  ![Roads within Buffers Reference](https://github.com/Bo-Brown-Dev/Road-Crossings/assets/116322660/68d7bc26-efcd-46ca-8546-016da6755bd6)

  
  *the polygon in this figure is the Track Buffer created in the previous step. The black lines show the full extent of
 the roads data that was ingested*
<br></br>
<br></br>

### Function & Behavior Guide

* **Crossings Analysis:** The resulting roads and the Track Lines are overlayed on one another, and the intersection is
taken from this overlay. Attributes from both datasets are retained. Also note that an animal track with a line segment 
that happens to follow the exact path of a road will appear as 2 crossing points at either end of the line segment.
  ![Tracks with Roads and Crossings Reference](https://github.com/Bo-Brown-Dev/Road-Crossings/assets/116322660/c46bb398-2518-409d-89e3-5151f3024fcf)

<br></br>
<br></br>

* **Inserting Crossings to Trajectories:** The crossing points are inserted into the TrajectoryCollection such that
points where the road is crossed are added to the Trajectory of the animal. Since trajectories are sequenced by the
timestamps of the points within the Trajectory, the timestamp of crossing points is estimated to be halfway between 
the timestamp of the starting point and the timestamp of the ending point for that segment of the Trajectory. The result
is that LineStrings (segments) which crossed a road are split into two LineStrings, one before the road was crossed and 
one after. There are some important considerations when using this data which are covered in the next section. 
<br></br>
  **Let's look at an example of the change between the input TrajectoryCollection and the output TrajectoryCollection:**
<br></br>
  The input is shown below mapped entirely in blue. The TrajectoryCollection contains only one Trajectory. 
The points in the trajectory are shown as circles and the Trajectory is the set of lines that connects all these points. The segments of
the Trajectory are the smaller lines that connect each pair of points. Roads are represented by black lines
<br></br>
  ![Before Insert Ref](https://github.com/Bo-Brown-Dev/Road-Crossings/assets/116322660/042b527b-12f5-4787-b48c-07d26da6b611)

<br></br>
The output is mapped below. New points inserted as crossing points are shown in red. Segments are split at the location
of crossing points, which can be seen where lines turn orange after intersecting with a road. 
<br></br>

  ![Insert Crossings Reference](https://github.com/Bo-Brown-Dev/Road-Crossings/assets/116322660/75f29244-11f8-4b7b-9bf2-6e8a195e8ccc)

 **These points are inferences, not observations.** 
<br></br>
  If you do not wish to introruce inferential data to your dataset, care should be taken to either validate or remove crossing points. 
Validating that a road was crossable for the subject animal is a good idea. The data can be removed by filtering out points where "crossing_point?" 
attribute is True. If validating the data, keep in mind that a trajectory may cross a road, but that doesn't mean that
the animal was ever recorded to be in this location. Use tracker accuracy and proximity of observations to determine which crossing points are valid. 
Note also that the animal could go around the road, under the road, and over the 
road. Using the attributes provided by OSM may help to identify how likely it is that a crossing point is valid in these cases.
It is also possible that inaccurate gps data indicates that an animal has crossed the road when they simply approached a
road but turned back before crossings it.
<br></br>

## I/O Dictionary

### Input data
MovingPandas TrajectoryCollection in Movebank format

### Output data
MovingPandas TrajectoryCollection with crossing points inserted where roads were crossed.

### Artefacts

#### HTML Map:
The app returns a map like the one from the Crossings Analysis section above as an HTML file that can be rendered in google Chrome. 
Too much data can cause the map and browser as a whole to run slow, and caution is advised when opening an HTML map from
a large dataset.

#### CSV:
A CSV is returned with records of Crossing Points only.

#### Geopackage:
A geopackage is somewhat similar to a shapefile. It is self-contained which cuts down on the need for folder
organization and compression. The output Geopackage has three layers:

* Track Lines - the lines of animal movement from the input

* Roads - The roads from OpenStreetMap returned by the Overpass API

* Crossing Points - The crossing points created by the map's analysis

The geopackage can also conveniently be connected directly to ArcGIS as a GeoDataBase or folder.


#### Trajectories_with_Crossings.pickle 
Also the primary output of the application, this is a trajectory collection with 
points of crossing inserted into the LineString Geometries that make up each trajectory where applicable. See the 
function "add_crossings_to_tracks()" for more details on how points are inserted to the resulting dataset.

### Settings 
Currently the app accepts no settings. A future update will provide more function and flexibility through settings. 
Be sure to submit requests to the github!

### Null or error handling

**Out Of Memory Errors**
The app can quickly run out of memory when processing datasets larger than 3-7 MB.
The app will not log an error and will sometimes appear "idle". 
Please try to filter your data to less than 5MB for the time being. 
A solution to optimize memory use and prevent OOM errors is in development.

**Unexpected Data Handling:** 

When an animal Trajectory's line segment matches a road segment exactly, the default behavior
of the method used to match them would return a line where a crossing point is expected. To ensure that data is returned
in a standardized way, the app breaks the line into its constituent points from the tracking data. The app returns both 
of those points as crossing points instead of a single crossing point as would normally be returned.

