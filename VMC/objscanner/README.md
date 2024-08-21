# objscanner
This software module uses the CSI camera to scan for field elements matching the images in the `targets` folder, and can both report the data and automatically align itself with the field element.
## MQTT Topics
### Topic: `avr/objscanner/params`
This topic is used to set the state of the scanning module.
Here is the payload schema:

```json
{
    "state": <state_int>
}
```

The value of `state_int` can either be 0, 1, or 2.

0 is no scanning, 1 is scan for objects and report relevant data, 2 is automatically move towards detected objects (aka auto-align).


### Topic: `avr/objscanner/scan_report`
This topic reports the results of a scan. Here is the payload schema:

```json
{
    "name": <name_of_matching_image>,
    "X": <estimated_forward_distance_to_element>, // Positive numbers = distance forward, from the camera
    "Y": <estimated_sideways_distance_to_element> // Positive numbers = distance to the right
}
```
Note that reported distances are relative to the orientation of the CSI camera

Reports will be broadcast on this topic whenever scanning is happening, so any value of `state_int` above zero will cause data to be sent out when a matching element is found

## Software Operation/Effect
### `state_int` set to zero:
Nothing
### `state_int` set to one:
Software will scan the CSI camera feed for field elements matching the images inside of the `targets` folder.
If the CSI camera feed contains elements matching one of the target images, the drone will broadcast relevant data.
### `state_int` set to two:
The drone will slowly creep towards the element on the X and Y axis using `goto_location_ned` commands. It will **NOT** automatically descend towards the field element.