# Copyright (c) 2025 Robert P. Hellums
# Licensed under the CC BY-NC 4.0. See LICENSE file in the project root for details.

# Import required libraries for AWS S3 access, date handling, logging, numerical operations, and GRIB file processing
import boto3
from datetime import datetime
import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
import pygrib
import threading
import time

# List of meteorological variables to extract from GRIB files
var_names = ['2_metre_temperature', 'surface_pressure', 'geopotential_height_200', 'geopotential_height_500', 'geopotential_height_700']

class Args:
    """
    Simple class to hold command line arguments parsed from config file.
    Mimics argparse.Namespace for compatibility with main function.
    """
    def __init__(self, config):
        self.start_date = config['start_date']
        self.end_date = config['end_date'] 
        self.zulus = config.get('zulus', '00,06,12,18')  # Default to standard synoptic times
        self.resolution = config.get('resolution', '1p00')  # Default to 0.25-degree resolution
        self.na_bounds = config.get('na_bounds', True)  # Default to using North American bounds
        self.cleanup = config.get('cleanup', True)  # Default to cleaning up GRIB files after processing

# Add a logging filter class to include runtime
class RuntimeFilter(logging.Filter):
    """Filter that adds runtime information to log records"""
    def __init__(self):
        super().__init__()
        self.start_time = time.time()

    def filter(self, record):
        record.runtime = f"{time.time() - self.start_time:.2f}s"
        return True

def extract_grib_data(grib_file, grib_index, date, zulu, forecast_hour, na_bounds=True):
    """
    Extracts specific meteorological parameters from a GRIB file and saves them as numpy arrays.
    
    Args:
        grib_file: Open GRIB file handle
        grib_index: Index of the variable to extract
        date: Date of the forecast
        zulu: Zulu time (forecast initialization time)
        forecast_hour: Forecast hour
        na_bounds: Boolean flag to include North American bounds
    """
    try:
        # Dispatch table mapping indices to GRIB parameter selection criteria
        dispatch_table = {
            0: (grib_file.select, (), {"name": "2 metre temperature"}),
            1: (grib_file.select, (), {"name": "Surface pressure"}),
            2: (grib_file.select, (), {"name": "Geopotential height", "level": 200}),
            3: (grib_file.select, (), {"name": "Geopotential height", "level": 500}),
            4: (grib_file.select, (), {"name": "Geopotential height", "level": 700}),
        }

        # Extract the requested parameter using the dispatch table
        func, args, kwargs = dispatch_table[grib_index]
        grib = func(*args, **kwargs)[0]
        
        # Get the data values and lat/lon coordinates
        grib_data = grib.values
        grib_lats, grib_lons = grib.latlons()

        # Define geographical bounds for North America
        if na_bounds:
            lat_min, lat_max = 15.0, 60.0  # From southern Mexico to northern Canada
            lon_min, lon_max = 220.0, 305.0  # From Pacific to Atlantic

            # Find indices for the desired geographical region
            lat_indices = np.where((grib_lats[:, 0] >= lat_min) & (grib_lats[:, 0] <= lat_max))[0]
            lon_indices = np.where((grib_lons[0, :] >= lon_min) & (grib_lons[0, :] <= lon_max))[0]

            # Crop the data to the desired region
            cropped_grib_data = grib_data[np.min(lat_indices):np.max(lat_indices) + 1,
                                        np.min(lon_indices):np.max(lon_indices) + 1]
                
            # Update path handling to ensure cross-platform compatibility
            data_dir = Path('data').resolve() / date.strftime("%Y%m%d")
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Use Path for binary file path construction
            binary_file = data_dir / f'{Path(grib_file.name).name}_{var_names[grib_index]}.npy'
            np.save(binary_file, cropped_grib_data if na_bounds else grib_data)
        else:
            # Save the data as a numpy binary file
            binary_file = data_dir / f'{grib_file.name}_{var_names[grib_index]}.npy'
            np.save(binary_file, grib_data)

    except Exception as e:
        logging.error("Error extracting grib file for %s %s %s %s: %s", 
                     date, zulu, forecast_hour, var_names[grib_index], e)

def main(args):
    """
    Main function to download and process GRIB files from NOAA GFS (Global Forecast System).
    
    Args:
        args: Object containing:
            - start_date (str): Start date in format YYYYMMDD
            - end_date (str): End date in format YYYYMMDD
            - zulus (str): Comma-separated list of initialization times (00,06,12,18)
            - resolution (str): Spatial resolution of the forecast (like '0p25' for 0.25 degrees, '0p50' for 0.5 degrees, '1p00' for 1 degree)
            - na_bounds (bool): Whether to crop data to North American bounds
    """

    logging.info("Starting run for %s to %s", args.start_date, args.end_date)

    # Update path handling
    data_dir = Path('data').resolve()
    data_dir.mkdir(exist_ok=True)

    # Convert input dates to datetime objects and create a range
    start_date = datetime.strptime(args.start_date, '%Y%m%d')
    end_date = datetime.strptime(args.end_date, '%Y%m%d')
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    zulus = args.zulus.split(',')
    resolution = args.resolution
    
    # Generate forecast hours from 0 to 180 in 3-hour intervals
    forecast_hours = [f'{i:03d}' for i in range(0, 385, 3)]

    # Initialize AWS S3 client for accessing NOAA GFS data
    s3 = boto3.client('s3')
    bucket = 'noaa-gfs-bdp-pds'

    # Process each combination of date, initialization time, and forecast hour
    for date in date_range:
        # Create date-specific directory under data
        date_dir = data_dir / date.strftime("%Y%m%d")
        date_dir.mkdir(exist_ok=True)

        for zulu in zulus:
            for forecast_hour in forecast_hours:
                logging.info("Downloading grib file for %s %s %s", date, zulu, forecast_hour)
                try:
                    # Update path handling for grib files
                    grib_path = date_dir / f'gfs.t{zulu}z.pgrb2.{resolution}.f{forecast_hour}'
                    s3_file = f'gfs.{date.strftime("%Y%m%d")}/{zulu}/atmos/gfs.t{zulu}z.pgrb2.{resolution}.f{forecast_hour}'
                    s3.download_file(bucket, s3_file, str(grib_path))
                
                except Exception as e:
                    logging.error("Error downloading grib file for %s %s %s: %s", 
                                date, zulu, forecast_hour, e)
                    continue    

                # Process the GRIB file using multiple threads for parallel extraction
                gribs = pygrib.open(str(grib_path))

                threads = []
                for var_index in range(len(var_names)):
                    thread = threading.Thread(target=extract_grib_data, args=(gribs, var_index, date, zulu, forecast_hour, args.na_bounds))
                    threads.append(thread)
                    thread.start()
                for thread in threads:
                    thread.join()

                # Only cleanup if specified in config
                if args.cleanup:
                    Path(grib_path).unlink()
                    logging.info(f"Deleted processed file: {grib_path}")

    logging.info("Ending run for %s to %s", args.start_date, args.end_date)

if __name__ == '__main__':
    # Update path handling for logs
    log_dir = Path('logs').resolve()
    log_dir.mkdir(exist_ok=True)
    
    # Update config file path handling
    config_path = Path('grib.json').resolve()
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    log_filename = log_dir / f"grib_{config['start_date']}_to_{config['end_date']}.log"
    file_handler = logging.FileHandler(str(log_filename), mode="a")
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(levelname)s, timestamp: %(asctime)s, runtime: %(runtime)s, message: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Add formatter to handlers
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add runtime filter to both handlers
    runtime_filter = RuntimeFilter()
    file_handler.addFilter(runtime_filter)
    console_handler.addFilter(runtime_filter)
    
    # Add handlers to logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Initialize arguments and execute main processing function
    args = Args(config)
    main(args)