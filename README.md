# SecuritiesCorrelations
The SecuritiesCorrelations project is a tool that provides insights into the correlations between different securities. The project offers interactive visualizations and analysis of securities' relationships, helping users understand market dynamics.


## Main Features:
1. Interactive Dashboard: The main_ui.py script provides an interactive dashboard built with Dash, allowing users to visualize correlations between securities.

2. Filtering Capabilities: Users can apply various filters to narrow down their analysis, such as ETF, Stock, Index, and more.

3. Customizable Plots: The tool provides the ability to detrend data, resample on a monthly basis, and exclude OTC data for a more refined analysis.

4. Advanced Correlation Analysis: The scripts directory contains various Python scripts to compute correlations, read files, and plot data.
    
## Setup
Make sure python is installed, preferably ≥ 3.10, and run the following command, in a conda or venv environment if you prefer:

    pip install -r requirements.txt

Next 

It will download about 2gb of Stock, ETF, and Index data from Google Drive that is used to calculate correlations. 

Once the environment has been set up, running run.bat will start the interface. For easy access, you can make a shortcut for run.bat by right-clicking it and selecting "Create Shortcut", and adding it to your desktop.

## Running the Dashboard:
To launch the interactive dashboard, navigate to the root directory of the project and run:

python main_ui.py
This will start the Dash server and the dashboard will be accessible in your browser at localhost:8080. 

First time calculations will take a minute, but subsequent calculations will only take a few seconds due to caching data retrieval. Once a calculation is made it should be saved to data/Graphs/pickled_security_correlations/.
Entering a ticker into the top "Enter New..." box will always calculate the correlation from scratch. You can also do this by clicking "Reload"  

FRED button makes the dropdown show different macroeconomic indicators form the FRED-MD dataset that can be selected from.

The year button will adjust from which starting point the correlation calculation begins. 

The input next to the year is the number of stocks to include in the plot.

'Exclude OTC' will exclude Pink Sheet Stocks.

'Detrend' will show the data as detrended (it is always calculated as detrended) so the user can get a better visualization of the correlation.

'Monthly Resample' will show the data resampled into monthly granularity, mainly to help with visualizing FRED-MD data which is only available monthly anyways.

Stock Filters is a list of filters that will only apply to stocks. Metadata is taken from FinanceDB, which has accurate information for the majority of stocks but occasionally has "Missing" or "nan" values.

### Tips:
Click on a security in the legend to hide it from the graph.

Modifying the plot using anything other than the filter options will reset the filters.

Click and drag on the plot to zoom in to select a time range to zoom in on. Double click to zoom back out.

In rare circumstances localhost:8080 might not work for you due to the port being in use by another process. In this case find `port=int(os.environ.get('PORT', 8080)))` at the bottom of main_ui.py and change the port to another number. 

## Future Enhancements:
Integrate more data sources to provide a comprehensive analysis.

Be able to calculate correlations for more recent timeframes, e.g. for the  last month using 15-minute resolution data.

Database to query for .pkl files so that calculations are no necessary for non-recent correlations. 

Add anomaly detection.

If fred is selected, there's another switch to select if you want fred data from the fred-md csv or from the fred api. If fred api is selected, can choose if you want the data to be as-reported or not.

Fred-api switch will change dropdown values to values supports by api, which is mostly identical except for HWIRATIO, CONSPI, and COMPAPFFx.

Radio buttons - Securities - FRED MD - FRED API & As Reported

As reported data correlations will give a better insight into what was truly following the movement. Fred api data will allow for as-reported data as well as more granular data retrieval for series such as VIXCLSx. 

Navigable Fred-md release archive calendar

Add Crypto, Funds, and more macroeconomic data.

## Contributing:
Feel free to fork the repository and submit pull requests for any enhancements or bug fixes. I appreciate your contribution!

## License:
This project is open source and available under the GNU General Public License.

![RPI Plot](ui/screenshots/RPI_fred_2010.png)

![Dropdown Filters](ui/screenshots/GME_filters.png)

![AMD Plot](ui/screenshots/AMD_detrended_monthly_2010.png)
