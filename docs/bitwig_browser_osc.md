# Bitwig Studio Browser OSC Implementation

This document provides technical details about navigating the Bitwig Studio device browser via OSC. It was created based on research of the Bitwig API and the DrivenByMoss implementation.

## Browser Structure

The Bitwig Studio browser exposes the following elements via OSC:

1. **Browser State**

   - `/browser/isActive` - Indicates if the browser is open
   - `/browser/tab` - The name of the current browser tab (e.g., "Result")

2. **Filters** (1-6 columns)

   - `/browser/filter/{1-6}/exists` - Whether a filter column exists
   - `/browser/filter/{1-6}/name` - Name of the filter column
   - `/browser/filter/{1-6}/wildcard` - Wildcard option for the filter

3. **Filter Items** (1-16 items per filter)

   - `/browser/filter/{filter_index}/item/{1-16}/exists` - Whether a filter item exists
   - `/browser/filter/{filter_index}/item/{1-16}/name` - Name of the filter item
   - `/browser/filter/{filter_index}/item/{1-16}/hits` - Number of results matching this filter
   - `/browser/filter/{filter_index}/item/{1-16}/isSelected` - Whether the item is selected

4. **Results** (1-16 visible at a time)
   - `/browser/result/{1-16}/exists` - Whether a result exists
   - `/browser/result/{1-16}/name` - Name of the result
   - `/browser/result/{1-16}/isSelected` - Whether the result is selected

## Navigation Commands

The browser can be navigated with the following OSC messages:

1. **Opening the Browser**

   - `/browser/device` - Open browser to insert device after current device
   - `/browser/device/before` - Open browser to insert device before current device
   - `/browser/preset` - Open browser for presets of current device

2. **Tab Navigation**

   - `/browser/tab/+` - Navigate to next tab
   - `/browser/tab/-` - Navigate to previous tab

3. **Filter Navigation**

   - `/browser/filter/{index}/+` - Select next option in filter column
   - `/browser/filter/{index}/-` - Select previous option in filter column
   - `/browser/filter/{index}/reset` - Reset filter to default/wildcard

4. **Result Navigation**

   - `/browser/result/+` - Select next result
   - `/browser/result/-` - Select previous result

5. **Result Page Navigation**

   - `/browser/result/page/+` - Navigate to next page of results
   - `/browser/result/page/-` - Navigate to previous page of results

6. **Browser Actions**
   - `/browser/commit` - Commit current selection
   - `/browser/cancel` - Cancel browser session

## Limitations and Challenges

### Fixed Result Size

- The OSC interface only exposes 16 results at a time
- To access more than 16 results, page navigation must be used

### Limited Filter Items

- Each filter column only shows up to 16 items
- No direct way to get the total count of filter items

### No Direct Category Access

- No direct addressing of device categories
- Must navigate tabs and filters to find specific device types

### Browser State Persistence

- Browser state is not maintained between sessions
- Each browser session starts fresh, requiring navigation

## Pagination Implementation

The browser's pagination works as follows:

1. Each "page" of browser results contains up to 16 items
2. Use `/browser/result/page/+` to navigate to the next page
3. Use `/browser/result/page/-` to navigate to the previous page
4. After changing pages, the individual results in positions 1-16 represent the new page's content
5. When the end of results is reached, further page navigation has no effect

## Collecting All Results

To collect a comprehensive list of all devices:

1. Open the browser (e.g., `/browser/device`)
2. Navigate to the desired tab (e.g., "Result" or "Everything")
3. Collect the current page's results (indices 1-16)
4. Move to the next page with `/browser/result/page/+`
5. Repeat steps 3-4 until no more results are found
6. Before closing, check if all pages have been traversed

## Bitwig Tabs Structure

The browser typically contains the following tabs (may vary by Bitwig version):

1. **Device** - Contains all devices
2. **Preset** - Contains all device presets
3. **Sample** - Contains audio samples
4. **Music** - Contains audio clips
5. **MIDI File** - Contains MIDI clips
6. **Multi** - Contains multi-samples
7. **Result** - Main results tab (previously "Everything" in older versions)

## Device Metadata Structure

When collecting device metadata, the following information is typically available:

- **Name** - Device name (e.g., "Polysynth")
- **Type** - Device type (e.g., "Instrument", "Audio FX")
- **Category** - Device category (e.g., "Synthesizer", "Delay")
- **Creator** - Device creator (e.g., "Bitwig")
- **Tags** - Associated tags

This data is derived from the selected filter items when a device is selected in the results.

## Implementation Recommendations

For robust browser interaction:

1. **Pagination Awareness**

   - Always implement pagination to access all devices
   - Keep track of the current page position

2. **Error Handling**

   - Check for existence before accessing
   - Handle timeouts in browser communication
   - Implement retry logic for failed operations

3. **Efficient Navigation**

   - Minimize tab navigations, which are slow
   - Use filter selections to narrow results when possible

4. **State Management**

   - Don't assume browser state persists between operations
   - Verify browser state before critical operations

5. **Metadata Collection**
   - Extract metadata from filter selections when a result is selected
   - Map filter names to standard metadata fields
