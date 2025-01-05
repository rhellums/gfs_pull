GFS GRIB Data Downloader and Processor

This repository contains a Python script that downloads Global Forecast System (GFS) GRIB2 files from NOAA via AWS S3, extracts specific meteorological variables (such as temperature, surface pressure, and geopotential heights), and saves them as NumPy arrays cropped to North America (or globally, if desired). The script uses multithreading to speed up data extraction and logs all operations for easy troubleshooting.

-------------------------------------------------------------------------------
TABLE OF CONTENTS

1. Features
2. Requirements and Installation
3. Configuration
4. Usage
5. Logging
6. Script Overview
7. Contributing
8. License

-------------------------------------------------------------------------------
FEATURES

* Automated Data Download
  - Downloads GRIB2 files from the NOAA GFS S3 Bucket (https://registry.opendata.aws/noaa-gfs-bdp-pds/) using the boto3 library.

* Variable Extraction
  - Extracts a predefined list of meteorological variables (e.g., 2m temperature, surface pressure, geopotential heights).

* Geographical Cropping
  - Optionally crops data to North America for more targeted analyses and reduced file sizes.

* Multithreading
  - Uses Python's threading to parallelize the extraction of multiple variables from the same GRIB2 file.

* Logging
  - Outputs logs to both the console and a file with timestamps, runtime, and detailed status messages.

* Clean-Up
  - Optionally automatically deletes the downloaded GRIB files once the required data has been extracted.

-------------------------------------------------------------------------------
REQUIREMENTS AND INSTALLATION

1. Python Version
   - This script has been tested with Python 3.7+ (any modern Python 3 version should work).

2. Dependencies
   - boto3==1.35.92
   - numpy==2.0.2
   - pandas==2.2.3
   - pygrib==2.1.6
   - Additional dependencies listed in requirements.txt

3. Installation
   a) Via pip:
      pip install -r requirements.txt

      Note: You may need additional system-level libraries for pygrib (e.g., libgrib-api-dev or eccodes).
            Follow the pygrib installation instructions (https://github.com/jswhit/pygrib#installation)
            if you encounter issues.

   b) Cloning the Repository:
      git clone https://github.com/your-username/your-repo.git
      cd your-repo

      Then install Python dependencies:
      pip install -r requirements.txt

-------------------------------------------------------------------------------
CONFIGURATION

All user-configurable parameters are stored in a file named grib.json (by default).
An example grib.json might look like:

{
    "start_date": "20240301",
    "end_date": "20240302",
    "zulus": "00,06,12,18",
    "resolution": "1p00",
    "na_bounds": true,
    "cleanup": true
}

Parameter      | Description
--------------- | -------------------------------------------------------------------------
start_date     | Start date in YYYYMMDD format for downloading and processing GRIB data.
end_date       | End date in YYYYMMDD format for downloading and processing GRIB data.
zulus          | Comma-separated list of initialization times (00,06,12,18) you want to process.
resolution     | Spatial resolution of the forecast (e.g., 0p25, 0p50, 1p00).
na_bounds      | Boolean indicating whether to crop the data to North America.
                If set to false, the script saves global data.
cleanup        | Boolean indicating whether to delete GRIB files after processing.

-------------------------------------------------------------------------------
USAGE

1. Prepare the Configuration File
   - Update the grib.json file with your desired date range, resolution, and other parameters.

2. Run the Script
   python grib.py

   The script will:
   - Parse grib.json
   - Connect to the NOAA GFS S3 bucket
   - Download specified GFS GRIB files for each date and forecast hour
   - Extract the selected meteorological variables (2m temperature, surface pressure, geopotential heights)
   - Crop to North America if specified
   - Save each variable to a .npy file under a date-based directory in /data
   - Delete the raw GRIB files after successful processing (if cleanup=true)

3. Output Files
   - Within the data/ directory, subdirectories for each date (YYYYMMDD/) are created.
   - Inside these subdirectories, NumPy binary files (.npy) for each variable are saved,
     following a naming convention based on:
       * Date
       * Zulu time
       * Forecast hour
       * Variable name

-------------------------------------------------------------------------------
LOGGING

* Log Files
  - All log files are stored in a /logs directory.
  - The log filename follows the pattern:
    grib_<start_date>_to_<end_date>.log

* Console Output
  - The script outputs progress messages to the console for real-time feedback.

* Log Format
  - Each log entry includes:
    * Log level: INFO, ERROR, etc.
    * Timestamp: Date and time of the log event.
    * Runtime: Elapsed runtime since the script started.
    * Message: Human-readable log message describing the event or error.

Example log message:
INFO, timestamp: 2024-03-01 00:00:10, runtime: 10.12s, message: Downloading grib file for 2024-03-01 00 003

-------------------------------------------------------------------------------
SCRIPT OVERVIEW

Below is a high-level description of each part of the script:

1. Imports & Global Variables
   - Imports Python libraries (boto3, numpy, pandas, pygrib, logging, etc.).
   - Lists the meteorological variable names to extract (var_names).

2. Args Class
   - Reads configuration details from config (JSON file) and mimics argparse.Namespace for easy access throughout the script.

3. RuntimeFilter Class
   - A custom logging filter that inserts a runtime attribute into each log record to display elapsed time.

4. extract_grib_data Function
   - Extracts a specific meteorological variable from an open GRIB file.
   - Applies cropping if North American bounds are enabled.
   - Saves the extracted data as a NumPy binary (.npy) file.

5. main Function
   - Main driver of the script.
   - Iterates through each date, zulu time, and forecast hour to:
     * Download GRIB files from S3.
     * Open the GRIB file with pygrib.
     * Extract each variable in parallel (via threading).
     * Clean up (delete) the GRIB file afterward if specified.

6. __main__ Block
   - Sets up logging to both file and console.
   - Reads the config JSON (grib.json).
   - Initializes Args.
   - Calls main() to execute the entire process.

-------------------------------------------------------------------------------
CONTRIBUTING

Contributions are welcome! Please open a pull request with a clear description of changes, 
or submit an issue if you encounter bugs or have feature requests.

-------------------------------------------------------------------------------
LICENSE

This software is available under two licenses:

1. Non-Commercial License (LICENSE-NonCommercial)
   - Permits personal, educational, and non-commercial use
   - Requires attribution and sharing under same terms
   - No commercial use allowed
   - See LICENSE-NonCommercial for full terms

2. Commercial License (LICENSE-Commercial) 
   - Permits commercial use and redistribution
   - Includes rights to modify and incorporate into products
   - See LICENSE-Commercial for full terms

For commercial licensing inquiries, please contact hellumsr@yahoo.com.

-------------------------------------------------------------------------------
DISCLAIMER

GFS data is made available by the U.S. National Oceanic and Atmospheric Administration (NOAA). 
Ensure compliance with NOAA's usage policies and terms when using and redistributing the data.