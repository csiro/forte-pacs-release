// Define extensions for image dimensions
Extension: ImageRows
Id: image-rows
Title: "Image Rows"
Description: "Number of rows (height) in the image instance"
* value[x] only unsignedInt

Extension: ImageColumns
Id: image-columns
Title: "Image Columns"
Description: "Number of columns (width) in the image instance"
* value[x] only unsignedInt

Extension: ImageFrames
Id: image-frames
Title: "Image Frames"
Description: "Number of frames in the image instance"
* value[x] only unsignedInt

Extension: ImageBitsAllocated
Id: image-bits-allocated
Title: "Image Bits Allocated"
Description: "Number of bits allocated in the image instance"
* value[x] only unsignedInt


// Profile for ImagingStudy with dimension extensions on instances
Profile: ImagingStudyQidoSearchProfile
Parent: ImagingStudy
Id: imaging-study-qido-search-profile
Title: "ImagingStudy with extensions for QIDO"
Description: "An ImagingStudy profile where instances have extensions for rows, columns, bits allocated and frames"

* series.instance.extension contains
    image-rows named rows 0..1 MS and
    image-columns named columns 0..1 MS and
    image-frames named number_of_frames 0..1 MS and
    image-bits-allocated named bits_allocated 0..1 MS

Instance: RowsSearchParam
InstanceOf: SearchParameter
Usage: #definition
* url = "http://forte.com/fhir/StructureDefinition/imaging-study-qido-search-profile-rows"
* name = "Rows"
* status = #active
* description = "Search by number of rows in series"
* code = #image-study-qido-rows
* base = #ImagingStudy
* type = #number
* expression = "series.instance.extension('https://forte.com/fhir/StructureDefinition/image-rows').value"

Instance: ColumnsSearchParam
InstanceOf: SearchParameter
Usage: #definition
* url = "http://forte.com/fhir/StructureDefinition/imaging-study-qido-search-profile-columns"
* name = "Columns"
* status = #active
* description = "Search by number of columns in series"
* code = #image-study-qido-columns
* base = #ImagingStudy
* type = #number
* expression = "series.instance.extension('https://forte.com/fhir/StructureDefinition/image-columns').value"

Instance: FramesSearchParam
InstanceOf: SearchParameter
Usage: #definition
* url = "http://forte.com/fhir/StructureDefinition/imaging-study-qido-search-profile-num-frames"
* name = "NumberOfFrames"
* status = #active
* description = "Search by number of frames in series"
* code = #image-study-qido-num-frames
* base = #ImagingStudy
* type = #number
* expression = "series.instance.extension('https://forte.com/fhir/StructureDefinition/image-frames').value"

Instance: BitAllocatedSearchParam
InstanceOf: SearchParameter
Usage: #definition
* url = "http://forte.com/fhir/StructureDefinition/imaging-study-qido-search-profile-bits-allocated"
* name = "BitsAllocated"
* status = #active
* description = "Search by bits allocated in series"
* code = #image-study-qido-bits-allocated
* base = #ImagingStudy
* type = #number
* expression = "series.instance.extension('https://forte.com/fhir/StructureDefinition/image-bits-allocated').value"

Instance: SeriesDescriptionSearchParam
InstanceOf: SearchParameter
Usage: #definition
* url = "http://forte.com/fhir/StructureDefinition/imaging-study-qido-search-profile-series-description"
* name = "SeriesDescription"
* status = #active
* description = "Search by series description"
* code = #image-study-qido-series-description
* base = #ImagingStudy
* type = #string
* expression = "series.description"

Instance: StudyDescriptionSearchParam
InstanceOf: SearchParameter
Usage: #definition
* url = "http://forte.com/fhir/StructureDefinition/imaging-study-qido-search-profile-study-description"
* name = "StudyDescription"
* status = #active
* description = "Search by study description"
* code = #image-study-qido-study-description
* base = #ImagingStudy
* type = #string
* expression = "description"


Instance: SeriesNumberSearchParam
InstanceOf: SearchParameter
Usage: #definition
* url = "http://forte.com/fhir/StructureDefinition/imaging-study-qido-search-profile-series-number"
* name = "SeriesNumber"
* status = #active
* description = "Search by series number"
* code = #image-study-qido-series-number
* base = #ImagingStudy
* type = #number
* expression = "series.number"

Instance: ImageNumberSearchParam
InstanceOf: SearchParameter
Usage: #definition
* url = "http://forte.com/fhir/StructureDefinition/imaging-study-qido-search-profile-image-number"
* name = "ImageNumber"
* status = #active
* description = "Search by image number"
* code = #image-study-qido-image-number
* base = #ImagingStudy
* type = #number
* expression = "number"