# forte-pacs
A python based dicom web server.

> [!WARNING]
> This is currently beta software and work in progress. In particular, the documention is sparse/missing and we do not yet have adequate testing in place. Please do not use this software in a production environment.

# Motivation

Our motivation for developing the software were to have a flexible, open source dicomweb R&D PACS system that could be easily modified and integrated with other tools and systems. Some of the design choices may seem unusual without this context.

# Goals
The main goals of this project are to develop a dicomweb R&D PACS system that is:

* Compliant
* Complete
* Flexible

While we don't prioritise performance, there are some steps and designs decisions taken to ensure we can be as performant as possible (use of asyncio, simple cache, backgrounding of tasks, modular design to add or remove functionality).

# Architecture

The platform is modular in nature and consists of services. The primary service is the data service and this provides persistent storage. Currently only a file based storage service is implemented but technically, any kind of storage maybe supported. The other currently implemented service is a query service. This is needed to suport QIDO queries. Currently, only a SQL based query service is implmented. Lastly, a task queue service is implemented for the background processing of tasks/callbacks. Currenlty only an rq (https://python-rq.org/) task service is implemented.


# Running

Docker compose is the simplest way to bring up a working system. The docker folder contains dockercompose.yaml and dockerfiles for the required services.

  1) Create a copy of the config folder and its contents. 
  2) Edit the copy of settings.toml if necessary. 
  3) Edit the .env file in docker/compose. You will need to provide values for UPLOAD_DIR_LOCAL (where data will be stored), CONFIG_DIR_LOCAL (this will be the same as the folder created in (1) ),LOGS_DIR_LOCAL (where logs will be stored) and DB_DIR_LOCAL (wehere db files will be stored).
  4) Bring up the stack.

# Roadmap / Issues / Caveats

There are a few things missing/untested from the current implementation as well as brief roadmap:

* There are no plans to support a full pacs system with user interfaces etc.
  * No authentication/authorisation support. Please use a reverse proxy to secure your server.
  * Worklist and MPPS support is missing and will not be implemented.
* Decode / Encode of images is still experimental / untested. See Codec documentation for details.
* DICOM Video support is untested.
* DICOM Whole Slide Image support has been briefly tested with Slim viewer (https://github.com/ImagingDataCommons/slim).
* For image data, we are strongly considering the decrecation of palatte color support. Any incoming data to STOW would be converted to RGB.
* Data is not stored directly as a PS31.0 file. This means that there will almost certainly be no binary no exact binary compatibility between data that is received and a response containing said data. In particular, see next re: charset.
* Charset handling is limited. If the content type of a response is application/dicom+json or application/dicom+xml then the response will be encoded in ISO_IR 192/UTF-8. If the response is application/dicom ( that is PS3.10 binary), then the content will be encoded in the specific charset of the original dataset if one was present. Otherwise it will default to ISO_IR 192/UTF-8 and not ISO_IR_6 / ASCII.
* Support for rendering and thumbnail is limited and only implementation is for instance based rendering. Currently 3d rendering and mpr is not implemented but the routes exists and return 501.

# ICC Profiles
The DICOM standard supports several color spaces for wado rendering. These profiles are included in forte-pacs with original sources mentioned below:

* sRGB : profile is from PIL
* ADOBE RGB : A compatible profile from https://github.com/saucecontrol/Compact-ICC-Profiles/blob/master/profiles/AdobeCompat-v2.icc
* ROMMRGB : https://www.color.org/chardata/rgb/rommrgb.xalter
* DISPLAYP3 : https://www.color.org/chardata/rgb/DisplayP3.xalter