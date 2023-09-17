# SecuritiesCorrelations
The SecuritiesCorrelations project is a comprehensive tool that provides insights into the correlations between different securities. Leveraging rich datasets, the project offers interactive visualizations and detailed analysis of securities' relationships, helping users understand market dynamics and make informed decisions.


## Main Features:
1. Interactive Dashboard: The main_ui.py script provides an interactive dashboard built with Dash, allowing users to visualize correlations between securities.

2. Data Integration: The project integrates data from multiple sources, including FRED, FinDB, and Yahoo daily stock data.

3. Filtering Capabilities: Users can apply various filters to narrow down their analysis, such as ETF, Stock, Index, and more.

4. Customizable Plots: The tool provides the ability to detrend data, resample on a monthly basis, and exclude OTC data for a more refined analysis.

5. Advanced Correlation Analysis: The scripts directory contains various Python scripts to compute correlations, read files, and plot data.

## Setup
The 'mini' branch will run on its own, but it is a limited version that only considers about 100 securities, mainly stocks. For the 'main' branch you need to download a folder with 2gb of parquets from https://drive.google.com/drive/folders/1qMu7B6GzY_V7xWOgMbucciTM0ffjd97k?usp=drive_link and place it in the data/yahoo_daily folder so that every Stock, ETF, and Index has data.   

## Running the Dashboard:
To launch the interactive dashboard, navigate to the root directory of the project and run:

python ui/main_ui.py
This will start the Dash server and the dashboard will be accessible at http://127.0.0.1:8080/.

## Future Enhancements:
Integrate more data sources to provide a comprehensive analysis.
Add forecasting capabilities to predict future correlations.
Introduce machine learning models to identify potential market anomalies.
## Contributing:
Feel free to fork the repository and submit pull requests for any enhancements or bug fixes. We appreciate your contribution!

## License:
This project is open source and available under the MIT License.

