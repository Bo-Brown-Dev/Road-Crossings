# Road Crossings

MoveApps

Github repository: *https://github.com/Bo-Brown-Dev/Road-Crossings.git*


## Description
Takes input of animal movement data and runs analysis with roads data from OpenStreetMap to find points where animals 
crossed a road. Map data is queried from OpenStreetMap and available  for the entire globe at a spatial resolution of 10 meters (per OpenStreetMap)



## Documentation
Road Crossings is an app that takes animal movement data in the form of a movingpandas TrajectoryCollection and 
synthesizes data on where and when animals likely crossed a road.

### Quick Start Guide

#### Setup:

While the analysis is flexible in terms of scope and can take input data from anywhere in the world, it also 
intentionally performs some memory-intensive geospatial operations that can cause the app to run slower or shut down unexpectedly with large datasets. 
This is especially true for datasets that span greater distances or are centered in urban areas with a lot of roads. 
Follow the steps below if experiencing slow performance within a work-flow.

- #### Consider filtering spatially:
  The app will work quicker with datasets that span a smaller range. Conducting analysis 
  for as many animals as possible within one region at a time will result in the most efficient workflow. 
  This will always improve performance but should only be necessary when working with very large datasets.

  There is an app for filtering by bounding box on MoveBank:
  [Click Here](https://www.moveapps.org/apps/browser/afa3c727-39d2-4738-88a6-177634505c18)

- #### Remove unused or blank columns:
  When a crossing is found, the app associates the Animal Tracking data with attributes from the road that was crossed.
  Removing columns will greatly reduce clutter when interpreting the resulting dataset and help the app to run more efficiently.

  This can be done in the starting MoveBank app, or later if in a larger workflow.

- #### Convert your data to TrajectoryCollection:
    The app accepts input strictly in the form of a movingpandas TrajectoryCollection. To make sure your data is in the 
    proper format, it is recommended that you get the data via a workflow in the proper format or convert it using the 
    MoveBank app for that purpose.

    MoveStack to TrajectoryCollection: [Click Here](https://www.moveapps.org/apps/browser/28c48bf4-687c-4e34-aa58-5c78958a3d36)

Follow these steps, and you are ready to run the app.

#### Results: 
**Inferential Data Inserted*

The resulting output of the app will be a TrajectoryCollection with points of Road Crossings inserted into the Lines 
that make up each individual's Trajectory. The timestamps of each point is estimated as the mid-point of the Timestamps
before and after the crossing.



For instance, consider the following case:
- an individual's coordinates are recorded as (0,0) at 6:00 PM.
- The individual is recorded with coordinates (4,4) 1 hour later at 7:00 PM.
- The straight line that connects these two points intersects with a road at location (1,1)

In this case, a road crossing point will be inserted in the animal's path at the coordinates of the intersection (1,1). 
The point will have the attributes of the road that was crossed and the individual who crossed it.
The timestamp for this crossing is not knowable, but is estimated as halfway between the start timestamp and end 
timestamp of that line at 6:30 PM. 


**Note that the timestamps of crossing points must be estimated to preserve the order of movement 
in the resulting dataset. This is handled by the app, and the inferential time and location is included in the output. This data can be easily filtered out by removing points where the "CrossingPoint?" column is "True".*

**for information on artifacts available for download, scroll down to see the 
"artifacts" section below.*
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
 
    
To see definitions of these attributes please see the wiki linked here:
https://wiki.openstreetmap.org/wiki/Key:highway

#### Animal Movement Data:
For animal movement data, the app accepts strictly the output of a preceding app in the format of a movingpandas
TrajectoryCollection (the pickle file output from the translator app). 

The TrajectoryCollection is broken into three dataframes:

* **Track Points:** The collection of point locations of each unique Animal ID and timestamp pair.
<br></br>

* **Track Lines:** A collection of LineStrings made by connecting each point from the Track Points collection to the associated
animal's next location by timestamp.


  ![Tracks Only Reference](https://github.com/Bo-Brown-Dev/Road-Crossings/blob/5921fcba8a56c052e3dc7ae3573ef6da43331901/documentation/tracks_pre_mcp.png)


<br></br>
<br></br>

* **Track MCP:** The smallest convex polygon that contains all line segments within a given animal's tracks
in the Track Lines dataframe.

 
![Tracks With MCP Reference](https://github.com/Bo-Brown-Dev/Road-Crossings/blob/5921fcba8a56c052e3dc7ae3573ef6da43331901/documentation/tracks%20with%20mcp.png)

*(See below for more info)*

<br></br>
<br></br>

* **Retrieving roads from OSM:** The polygon is then used in a request to the Overpass API as a bounding polygon.
The app only selects roads from within the polygon.

  ![Roads within Buffers Reference](https://github.com/Bo-Brown-Dev/Road-Crossings/blob/5921fcba8a56c052e3dc7ae3573ef6da43331901/documentation/roads%20with%20mcp.png)

  
  *the polygon in this figure is the Track Buffer created in the previous step. The orange lines show the full extent of
 the roads data that was ingested*
<br></br>
<br></br>

### Function & Behavior Guide

**Crossings Analysis:** 
The resulting roads and the Track Lines are overlayed on one another, and the intersection is
taken from this overlay. Attributes from both datasets are retained.

Also note the following:
* an animal track with a line segment that happens to follow the exact path of a road will appear as 2 crossing points at either end of the line segment.
* an animal track that crosses the exact point of an intersection of 2 or more roads will always appear as a single crossing point

![Tracks with Roads and Crossings Reference](https://github.com/Bo-Brown-Dev/Road-Crossings/assets/116322660/c46bb398-2518-409d-89e3-5151f3024fcf)
  

<br></br>
<br></br>

**Inserting Crossings to Trajectories:**
* The crossing points are inserted into the path of the animal as though they're normal points in their tracking data.
  Since trajectories are sequenced by the timestamps of the points within the Trajectory, the timestamp of crossing points is estimated to be halfway between
  the timestamps of the starting point and ending point for that line segment. The result is that LineStrings (segments) which crossed a road are
  split into two LineStrings, one before the road was crossed and one after.

  There are some important considerations when using this data which are covered in the next section. 
<br></br>
  **Example of change between input and output:**
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
  If you do not wish to introduce inferential data to your dataset, care should be taken to either validate or remove crossing points.
  
  
  **Validating Crossings:**
  
  Validating that a road was able to be crossed for the subject animal is a good idea. If validating the data, keep in mind that a trajectory may cross a road, but that doesn't mean that
  the animal was ever recorded to be in this location. Use tracker accuracy and proximity of recorded observations to determine which crossing points are valid. 
  Note also that the animal could go around the road, under the road, and over the road. It is also possible that inaccurate gps data indicates that an animal has crossed the road when they 
  simply approached a road but turned back before crossing it. Using the attributes provided by OSM may help to identify how likely it 
  is that a crossing point is valid in these cases.

**Removing Crossings from the dataset:**


  The data can be removed by converting the Trajectory to a DataFrame (table), and filtering out points where the "crossing_point?" 
  attribute is True.

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
The app will not log an error and will sometimes appear "idle". This seems to happen most often with 
animal tracking data that spans a wide geographic range. It may be a good idea to filter down data to a small geographic
location.

**Unexpected Data Handling:** 

When an animal Trajectory's line segment matches a road segment exactly, the default behavior
of the method used to match them would return a line where a crossing point is expected. To ensure that data is returned
in a standardized way, the app breaks the line into its constituent points from the tracking data. The app returns both 
of those points as crossing points instead of a single crossing point as would normally be returned.

